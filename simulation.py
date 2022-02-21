import graphics as gr

import random
import numpy as np
import glm
import glfw
import OpenGL.GL as gl
import ctypes
from typing import Callable, Sequence

import imgui.core as imgui

CAMSPEED = 0.4
ZOOMSPEED = 0.05

ANGLESPEED = 0.05

class Simulation:


    def __init__(self, N:int=10, fastrun:bool=False, steps:int=0, algoInit:Callable=None, algoPass:Callable=None, guiPass:Callable=None, dataPass:Callable=None, dataPassPeriod:int=100, rendering:bool=True):
        """ Create simulation object
        parameters:
            N : int                 Number of vehicles
            fastrun : bool          If True, VSync is turned off, if false it runs at VSync
            steps : int             Amount of steps/frames are ran. 0 for endless run
            algoInit : function     Initializer function. This is called before the simulation 
                is started. Use this to fill the world with vehicles and obstacles. Vehicles are
                placed into the simulation by creating their posState and movState buffers (see
                shaders/header.glsl). Next to that obstacles (walls) are created by returning a
                numpy array with the vertices of the walls (start x,y end x,y). Road facing side
                of a wall is the right facing side (clockwise) from start to end. At last the
                simulation state buffer must be returned in a numpy array
                In short -> posState:[{4*float position, float rotation, 
                3*float padding}]. Note: rotation is with 0* up increasing clockwise!!!
                movState: [{4*float velocity, 4*float desired velocity (set to velocity),
                float steering angle (set to 0), float speed of rear axis (set to 0) and
                6*float padding}]
                wall vertices -> [{startx, starty, endx, endy}] all floats
                simState -> [{uint ran steps for vehicle, uint used as bool for collision,
                float elapsed time in sim, uint start frame number for vehicle}]. With the last
                member one can set the start time of a vehicle entering the simulation. All
                the vehicles must be created at the start of the simulation and this is the way
                to let them enter one after each other
            algoPass : function     Algorithm pass function. Function should dispatch the shader(s)
                with the algorithm. Using algoProgram.dispatch(sim.N) should work
            guiPass : function      Gui pass function. Draw the GUI (i.e. imgui). Settings of the
                simulation are stored in Simulation.globalSettings. See header.glsl for all the
                settings
            dataPass : function     Data pass function is called after period steps. This function
                can be used to gather simulation data. One can retrieve data from the buffers using
                the np.frombuffer functions 
                (i.e. sim.frombuffer(sim.posSataBuffer.getData(0), dtype='f')).reshape((sim.N,8))
            dataPassPeriod : int    Period of data pass function
            rendering : bool        Set to false if rendering must be disabled
        """

        self.N = N
        self.steps = steps
        self.algoInit = algoInit
        self.algoPass = algoPass
        self.guiPass = guiPass
        self.dataPass = dataPass
        self.dataPassPeriod = dataPassPeriod
        self.rendering = rendering
        self.seed = 0 # Cant remember why I needed this...

        # Create window and OpenGL context
        self.window = gr.Window(800, 800, self._onEvent, self._renderPass, self._resize)

        # Create assets and buffers
        self._createAssets()
        self._createBuffers()

        # If fastrun is enabled
        if fastrun:
            glfw.swap_interval(0)

        # Create global settings
        self.globalSettings = np.zeros([2,4,4], dtype="f")
        ratio = float(self.window.width)/float(self.window.height)                          # Calculate ratio for orhtographic projection
        self.globalSettings[0] = glm.ortho(-ratio*10, ratio*10, -10.0, 10.0).to_list()              # ViewProjection matrix
        self.globalSettings[1][0][0] = 0.1                                                  # deltaTime

        self.stepCount = 0
        self.time = 0.0
        self.inReset = False
        self.zoomLevel = 1.0
        self.started = False

    """ Start simulation
    """
    def start(self):
        if self.started:
            self._reset()
            return
        self.started = True

        # Initialize algorithm by calling algoInit function
        wallVertices, simState = self.algoInit(self)
        # Create obstacle vertex and index buffers
        self._wallVBuffer.setData(wallVertices)
        wallIndices = np.arange(0, len(wallVertices), 1, dtype="uint32")
        self._wallIBuffer.setData(wallIndices)
        self.M = len(wallVertices)//4           # M = amount of obstacles

        print("N = %d, M = %d"%(self.N, self.M))

        # Set global settings
        self._bindBuffers()
        self.globalSettings[1][0][1] = float(self.N)
        self.globalSettings[1][0][2] = float(self.M)
        self.globalSettingsBuffer.setData(self.globalSettings)
        gl.glMemoryBarrier(gl.GL_UNIFORM_BARRIER_BIT)

        # Reserve space for M dependent buffers
        self.distanceBuffer.reserveData(4*2*self.N*(self.N+self.M))
        self.wallInfoBuffer.reserveData(4*1*self.M)

        # Zero out simStateBuffer
        #simState = np.zeros([self.N, 4], dtype="uint32")
        self.simStateBuffer.setData(simState)

        # Execute precalc shader
        # This will calculate obstacle normals
        self.precalcProgram.dispatch(self.M)
        gl.glMemoryBarrier(gl.GL_SHADER_STORAGE_BARRIER_BIT)

        # Run the simulation
        self.stepCount = 0
        self.window.run()

    """ Create buffers for simulation
    """
    def _createBuffers(self):
        # Create buffer objects
        self.posStateBuffer = gr.Buffer(gr.SHADER_STORAGE_BUFFER, gr.STATIC_DRAW)
        self.movStateBuffer = gr.Buffer(gr.SHADER_STORAGE_BUFFER, gr.STATIC_DRAW)
        self.simStateBuffer = gr.Buffer(gr.SHADER_STORAGE_BUFFER, gr.STATIC_DRAW)
        self.globalSettingsBuffer = gr.Buffer(gr.UNIFORM_BUFFER, gr.DYNAMIC_DRAW)
        self.wallInfoBuffer = gr.Buffer(gr.SHADER_STORAGE_BUFFER, gr.STATIC_DRAW)
        self.distanceBuffer = gr.Buffer(gr.SHADER_STORAGE_BUFFER, gr.STATIC_DRAW)
        self.debugBuffer = gr.Buffer(gr.SHADER_STORAGE_BUFFER, gr.STATIC_DRAW)
        self.internalDataBuffer = gr.Buffer(gr.SHADER_STORAGE_BUFFER, gr.STATIC_DRAW)

        # Reserve space for buffers
        self.posStateBuffer.reserveData(self.N*8*4)
        self.movStateBuffer.reserveData(self.N*16*4)
        self.globalSettingsBuffer.reserveData(22*4)
        self.debugBuffer.reserveData(self.N*16*4)
        self.internalDataBuffer.reserveData(self.N*16*4)

        # Zero out simStateBuffer
        simState = np.zeros([self.N, 4], dtype="uint32")
        self.simStateBuffer.setData(simState)

    """ Bind buffers to right binding
    """
    def _bindBuffers(self):
        self.globalSettingsBuffer.bindBase(1)
        self.posStateBuffer.bindBase(2)
        self.movStateBuffer.bindBase(3)
        self.simStateBuffer.bindBase(4)
        self.distanceBuffer.bindBase(5)
        self._wallVBuffer.bindBase(6, type=gr.SHADER_STORAGE_BUFFER)
        self.wallInfoBuffer.bindBase(7)
        self.debugBuffer.bindBase(8)
        self.internalDataBuffer.bindBase(9)

    """ Create assets for drawing
    """
    def _createAssets(self):
        # CAR VAO (H)
        self._carVBuffer = gr.Buffer(gr.VERTEX_BUFFER, gr.STATIC_DRAW)
        vertices = np.array([
            # X, Y, Z,
            # H shape top
            -0.9, 1.4, 0.0,
            0.9, 1.4, 0.0,
            0.9, 1.3, 0.0,
            -0.9, 1.3, 0.0,
            # H shape center
            -0.05, 1.3, 0.0,
            0.05, 1.3, 0.0,
            0.05, -1.3, 0.0,
            -0.05, -1.3, 0.0,
            # H shape bottom
            -0.9, -1.3, 0.0,
            0.9, -1.3, 0.0,
            0.9, -1.4, 0.0,
            -0.9, -1.4, 0.0,
            # size Box
            -0.9, 2.45, 0.0,            #// 0 3
            0.9, 2.45, 0.0,             #// 1
            0.9, 2.42, 0.0,
            -0.9, 2.42, 0.0,
            -0.9, -2.45, 0.0,           #// 5
            0.9, -2.45, 0.0,            #// 2 4
            0.9, -2.42, 0.0,
            -0.9, -2.42, 0.0,
            -0.9, 2.45, 0.0,
            -0.87, 2.45,0.0,
            -0.87, -2.45, 0.0,
            -0.9, -2.45, 0.0,
            0.9, 2.45, 0.0,
            0.87, 2.45,0.0,
            0.87, -2.45, 0.0,
            0.9, -2.45, 0.0,
        ], dtype="f")
        self._carVBuffer.setData(vertices)
        self._carIBuffer = gr.Buffer(gr.INDEX_BUFFER, gr.STATIC_DRAW)
        indices = np.array([
            0, 1, 2, 0, 2, 3,
            4, 5, 6, 4, 6, 7,
            8, 9, 10, 8, 10, 11,
            12, 13, 14, 12, 14, 15,
            16, 17, 18, 16, 18, 19,
            20, 21, 22, 20, 22, 23,
            24, 25, 26, 24, 26, 27,
            12, 13, 17,
            12, 17, 16,
        ], dtype="uint32")
        self._carIBuffer.setData(indices)
        self.carVAO = gr.VertexArray(self._carVBuffer, self._carIBuffer, [
            gr.VertexElement(3, gr.FLOAT)
        ])

        # LINE VAO
        self._lineVBuffer = gr.Buffer(gr.VERTEX_BUFFER, gr.STATIC_DRAW)
        vertices = np.array([
            -0.02, 0.0, 0.0,
            -0.02, 1.0, 0.0,
            0.02, 1.0, 0.0,
            0.02, 0.0, 0.0,
        ], dtype="f")
        self._lineVBuffer.setData(vertices)
        self._lineIBuffer = gr.Buffer(gr.INDEX_BUFFER, gr.STATIC_DRAW)
        indices = np.array([
            0, 1, 2, 0, 2, 3
        ], dtype="uint32")
        self._lineIBuffer.setData(indices)
        self.lineVAO = gr.VertexArray(self._lineVBuffer, self._lineIBuffer, [
            gr.VertexElement(3, gr.FLOAT)
        ])

        # Wall
        # ----
        self._wallVBuffer = gr.Buffer(gr.VERTEX_BUFFER, gr.STATIC_DRAW)
        self._wallIBuffer = gr.Buffer(gr.INDEX_BUFFER, gr.STATIC_DRAW)
        self.wallVAO = gr.VertexArray(self._wallVBuffer, self._wallIBuffer, [
            gr.VertexElement(2, gr.FLOAT)
        ])

        # Create shaders
        # --------------
        # The header contains all the buffer bindings and will be prepended to all the shaders
        header = ''
        with open("shaders/header.glsl") as f:
            header = f.read()

        # Car drawing program
        # Draws vehicle as red 'H'
        shaders = []
        with open("shaders/graphics/car.vert") as f:
            shaders.append(gr.Shader(header + f.read(), gr.VERTEX_SHADER))
        with open("shaders/graphics/red.frag") as f:
            shaders.append(gr.Shader(header + f.read(), gr.FRAGMENT_SHADER))
        self.carProgram = gr.ShaderProgram(shaders)

        # Car filling program
        # Fill in vehicle
        shaders = []
        with open("shaders/graphics/car.vert") as f:
            shaders.append(gr.Shader(header + f.read(), gr.VERTEX_SHADER))
        with open("shaders/graphics/darkred.frag") as f:
            shaders.append(gr.Shader(header + f.read(), gr.FRAGMENT_SHADER))
        self.carFillingProgram = gr.ShaderProgram(shaders)

        # Steering angle program
        # Draws a yellow line at the front of the vehicle
        shaders = []
        with open("shaders/graphics/angle.vert") as f:
            shaders.append(gr.Shader(header + f.read(), gr.VERTEX_SHADER))
        with open("shaders/graphics/yellow.frag") as f:
            shaders.append(gr.Shader(header + f.read(), gr.FRAGMENT_SHADER))
        self.angleProgram = gr.ShaderProgram(shaders)

        # Velocity program
        # Draws a green line at the center of the vehicle
        shaders = []
        with open("shaders/graphics/velocity.vert") as f:
            shaders.append(gr.Shader(header + f.read(), gr.VERTEX_SHADER))
        with open("shaders/graphics/green.frag") as f:
            shaders.append(gr.Shader(header + f.read(), gr.FRAGMENT_SHADER))
        self.velocityProgram = gr.ShaderProgram(shaders)

        # Desired velocity program
        # Draws a blue line at the center of the vehicle
        shaders = []
        with open("shaders/graphics/dvelocity.vert") as f:
            shaders.append(gr.Shader(header + f.read(), gr.VERTEX_SHADER))
        with open("shaders/graphics/blue.frag") as f:
            shaders.append(gr.Shader(header + f.read(), gr.FRAGMENT_SHADER))
        self.dVelocityProgram = gr.ShaderProgram(shaders)

        # Obstacle program
        # Draws yellow lines as walls
        shaders = []
        with open("shaders/graphics/wall.vert") as f:
            shaders.append(gr.Shader(header + f.read(), gr.VERTEX_SHADER))
        with open("shaders/graphics/blue.frag") as f:
            shaders.append(gr.Shader(header + f.read(), gr.FRAGMENT_SHADER))
        self.wallProgram = gr.ShaderProgram(shaders)

        # Distance calculation program
        # Creates a N+M,N sized matrix with distances between vehicle i and object j
        shaders = []
        with open("shaders/distance.comp") as f:
            shaders.append(gr.Shader(header + f.read(), gr.COMPUTE_SHADER))
        self.distanceProgram = gr.ShaderProgram(shaders)

        # Vehicle movement program
        # Calculates the velocity and steering angle from a desired velocity 
        shaders = []
        with open("shaders/vehiclemovement.comp") as f:
            shaders.append(gr.Shader(header + f.read(), gr.COMPUTE_SHADER))
        self.moveProgram = gr.ShaderProgram(shaders)

        # Precalc program
        # Calculates the normals on each obstacle
        shaders = []
        with open("shaders/precalc.comp") as f:
            shaders.append(gr.Shader(header + f.read(), gr.COMPUTE_SHADER))
        self.precalcProgram = gr.ShaderProgram(shaders)

        self.header = header

    """ Draw vehicles and obstacles
    """
    def _drawObjects(self):
        # Draw car
        self.carVAO.bind()
        self.carFillingProgram.use()
        gr.drawInstanced(6, self.N, 42)
        self.carProgram.use()
        gr.drawInstanced(42, self.N)


        # Draw steering angle vector
        self.angleProgram.use()
        self.lineVAO.bind()
        gr.drawInstanced(6, self.N)

        # Draw velocity vector
        self.velocityProgram.use()
        gr.drawInstanced(6, self.N)

        # Draw desired velocity vector
        self.dVelocityProgram.use()
        gr.drawInstanced(6, self.N)

        # Draw walls
        self.wallProgram.use()
        self.wallVAO.bind()
        gl.glDrawElements(gl.GL_LINES, self._wallIBuffer.length//4, gl.GL_UNSIGNED_INT, ctypes.c_void_p(0))

    """ Render pass callback
    """
    def _renderPass(self):
        # Update globalSettingsBuffer
        self.globalSettingsBuffer.setData(self.globalSettings)

        self._bindBuffers()

        self.distanceProgram.dispatch(self.N, self.N+self.M)
        gl.glMemoryBarrier(gl.GL_SHADER_STORAGE_BARRIER_BIT)

        self.algoPass(self)
        gl.glMemoryBarrier(gl.GL_SHADER_STORAGE_BARRIER_BIT)

        self.moveProgram.dispatch(self.N)
        gl.glMemoryBarrier(gl.GL_SHADER_STORAGE_BARRIER_BIT)

        if self.rendering:
            # Draw objects to screen
            self._drawObjects()

            # Draw GUI
            self.guiPass(self)

        # Increase step count
        self.stepCount += 1
        self.time += self.globalSettings[1][0][0]
        if self.steps>0 and self.stepCount==self.steps:
            # self.window.close()
            self.window.softclose()

        # Run dataPass after period
        if self.dataPassPeriod>0 and self.stepCount%self.dataPassPeriod == 0:
            self.dataPass(self)

        if self.inReset:
            self.inReset = False
            imgui.render()
            self._reset()

    """ Window resize callback
    """
    def _resize(self, window):
        ratio = float(self.window.width)/float(self.window.height)
        self.globalSettings[0] = glm.ortho(-ratio*50, ratio*50, -50.0, 50.0).to_list()

    """ Window event callback
    """
    def _onEvent(self, window):
        # Move camera
        # THIS WORKED BEFORE BUT NOW SOMETHING IS REALLY BROKEN HERE...
        # moveDir = glm.vec3(0.0)
        # if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
        #     moveDir += glm.vec3(0.0, -1.0, 0.0)
        # if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
        #     moveDir += glm.vec3(0.0, 1.0, 0.0)
        # if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
        #     moveDir += glm.vec3(1.0, 0.0, 0.0)
        # if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
        #     moveDir += glm.vec3(-1.0, 0.0, 0.0)
        # if glm.length(moveDir)>0:
        #     moveDir = glm.normalize(moveDir)
        #     self.globalSettings[0] = glm.translate(self.globalSettings[0], CAMSPEED*moveDir) #*self.zoomLevel)
        
        # Zoom camera
        zoom = 1.0
        if glfw.get_key(window, glfw.KEY_Q) == glfw.PRESS:
            zoom *= 1+ZOOMSPEED
            self.zoomLevel *= 1-ZOOMSPEED
        if glfw.get_key(window, glfw.KEY_E) == glfw.PRESS:
            zoom *= 1-ZOOMSPEED
            self.zoomLevel *= 1+ZOOMSPEED
        if zoom!=1.0:
            self.globalSettings[0] = glm.scale(self.globalSettings[0], glm.vec3(zoom))

        if glfw.get_key(window, glfw.KEY_ESCAPE):
            self.window.close()

    """ Reset simulation
    """
    def reset(self):
        self.inReset = True

    """ Internal reset function
    """
    def _reset(self):
        # Initialize algorithm by calling algoInit function
        wallVertices, simState = self.algoInit(self)
        # Create obstacle vertex and index buffers
        self._wallVBuffer.setData(wallVertices)
        wallIndices = np.arange(0, len(wallVertices), 1, dtype="uint32")
        self._wallIBuffer.setData(wallIndices)
        self.M = len(wallVertices)//4           # M = amount of obstacles

        print("N = %d, M = %d"%(self.N, self.M))

        # Set global settings
        self._bindBuffers()
        self.globalSettings[1][0][1] = float(self.N)
        self.globalSettings[1][0][2] = float(self.M)
        self.globalSettingsBuffer.setData(self.globalSettings)
        gl.glMemoryBarrier(gl.GL_UNIFORM_BARRIER_BIT)

        # Reserve space for M dependent buffers
        self.distanceBuffer.reserveData(4*2*self.N*(self.N+self.M))
        self.wallInfoBuffer.reserveData(4*1*self.M)

        # Zero out simStateBuffer
        #simState = np.zeros([self.N, 4], dtype="uint32")
        self.simStateBuffer.setData(simState)

        # Execute precalc shader
        # This will calculate obstacle normals
        self.precalcProgram.dispatch(self.M)
        gl.glMemoryBarrier(gl.GL_SHADER_STORAGE_BARRIER_BIT)

        # Run the simulation
        self.stepCount = 0
        self.time = 0.0
        self.window.run()