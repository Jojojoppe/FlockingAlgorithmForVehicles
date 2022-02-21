#!/usr/bin/python

import logging
logger = logging.getLogger(__name__)

import graphics as gr
import OpenGL.GL as gl
import imgui.core as imgui
import numpy as np
import glm
import glfw
import csv

class SpawnOptions():
    def __init__(self, rate=0.5, speed=1.0):
        self.rate = rate       # car per second
        self.speed = speed     # meters per second

    def __repr__(self):
        return str(self.rate)

class MapBuilder():

    def __init__(self, file=None):
        self.walls = []
        self.walls_comments = []
        self.spawns = [((0.0, 0.0), (0.0, 1.0))]
        self.spawns_comments = []
        self.spawnOptions = [SpawnOptions()]
        self.inAction = None
        self.line_count = 0
        self.cursor = None
        self.selectNearby = None
        self.selectIndex = None
        self.mode = None
        self.centerPos = glm.vec3(0.0)
        self.scrollPos = 1.0
        self.showSpawnOptions = None

        if file is not None:
            self._import(file)

        self.window = gr.Window(800, 800, self._onEvent, self.onUpdate, self._onResize)
        glfw.set_mouse_button_callback(self.window.glfw_window, self._onMouseButtonEvent)
        glfw.set_cursor_pos_callback(self.window.glfw_window, self._onMouseMoveEvent)
        glfw.set_key_callback(self.window.glfw_window, self._onKeyEvent)
        glfw.set_scroll_callback(self.window.glfw_window, self._onScrollEvent)
        self.ratio = float(self.window.width)/float(self.window.height)

        # Initialize render stuff
        self._initShaders()
        self._initBuffers()

        self._onResize(self.window)
        self.createLines()

        self.window.run()

    def _import(self, file):
        self.spawns = []
        self.spawnOptions = []
        with open(file + '.spn', 'r') as f:
            reader = csv.reader(f)
            i = 0
            for r in reader:
                if r[0].startswith('#'):
                    self.spawns_comments.append((i, r))
                else:
                    self.spawns.append(((float(r[0]), float(r[1])), (float(r[2]), float(r[3]))))
                    self.spawnOptions.append(SpawnOptions(float(r[4]), float(r[5])))
                i += 1
        self.walls = []
        with open(file + '.wls', 'r') as f:
            reader = csv.reader(f)
            i = 0
            for r in reader:
                if r[0].startswith('#'):
                    self.walls_comments.append((i, r))
                else:
                    self.walls.append(((float(r[0]), float(r[1])), (float(r[2]), float(r[3]))))
                i += 1

    def export(self, file='out'):
        with open(file + '.spn', 'w') as f:
            writer = csv.writer(f)
            for s, op in zip(self.spawns, self.spawnOptions):
                writer.writerow([*s[0], *s[1], op.rate, op.speed])
            for r in self.spawns_comments:
                writer.writerow(r[1])

        with open(file + '.wls', 'w') as f:
            writer = csv.writer(f)
            for w in self.walls:
                writer.writerow([*w[0], *w[1]])
            for r in self.walls_comments:
                writer.writerow(r[1])

    def createPoint(self, curPos):
        if self.inAction is None:
            if self.mode == 'place wall':
                # Create wall
                self.inAction = 'start_create_wall'
                self.cursor = curPos

            elif self.mode == 'place spawn':
                # Create spawn
                self.inAction = 'start_create_spawn'
                self.cursor = curPos
        
        elif self.inAction == 'start_create_wall':
            self.inAction = None
            self.walls.append((self.cursor, curPos))
            self.cursor = None
            print(self.walls[-1])

        elif self.inAction == 'start_create_spawn':
            self.inAction = None
            self.spawns.append((self.cursor, curPos))
            self.spawnOptions.append(SpawnOptions())
            self.showSpawnOptions = len(self.spawns)-1
            self.cursor = None

        self.createLines()

    def checkSelect(self, curPos):
        for i, w in enumerate(self.walls):
            r1 = glm.sqrt((w[0][0]-curPos[0])**2 + (w[0][1]-curPos[1])**2)
            r2 = glm.sqrt((w[1][0]-curPos[0])**2 + (w[1][1]-curPos[1])**2)
            if r1<0.02/self.scrollPos:
                self.selectNearby = w[0]
                self.selectIndex = self.walls, i, 0
                self.createLines()
                return
            if r2<0.02/self.scrollPos:
                self.selectNearby = w[1]
                self.selectIndex = self.walls, i, 1
                self.createLines()
                return

        for i, w in enumerate(self.spawns):
            r1 = glm.sqrt((w[0][0]-curPos[0])**2 + (w[0][1]-curPos[1])**2)
            r2 = glm.sqrt((w[1][0]-curPos[0])**2 + (w[1][1]-curPos[1])**2)
            if r1<0.02/self.scrollPos:
                self.selectNearby = w[0]
                self.selectIndex = self.spawns, i, 0
                self.createLines()
                return
            if r2<0.02/self.scrollPos:
                self.selectNearby = w[1]
                self.selectIndex = self.spawns, i, 1
                self.createLines()
                return

        if self.selectNearby is not None:
            self.selectNearby = None
            self.createLines()

    def moveSelect(self, curPos):
        ls = self.selectIndex[0]
        i = self.selectIndex[1]
        if self.selectIndex[2] == 0:
            ls[i] = (curPos, ls[i][1])
        else:
            ls[i] = (ls[i][0], curPos)
        self.createLines()

    def deleteSelect(self):
        ls = self.selectIndex[0]
        i = self.selectIndex[1]
        if len(ls)>0:
            ls.pop(i)
            if ls is self.spawns:
                self.spawnOptions.pop(i)
                self.showSpawnOptions = None
            self.selectIndex = None
            self.selectNearby = None
            self.createLines()

    def createLines(self):
        self.line_count = len(self.walls)*2
        self.line_count += len(self.spawns)*4
        if self.cursor is not None:
            self.line_count += 2

        line_data = np.zeros([self.line_count*2, 8], dtype='f')    
        line_indices = np.zeros([self.line_count*2], dtype='uint32')
        i = 0

        for wall in self.walls:
            # Create wall
            line_data[i][0:4] = [wall[0][0], wall[0][1], 0.0, 1.0]    # Wall start position
            line_data[i+1][0:4] = [wall[1][0], wall[1][1], 0.0, 1.0]  # Wall end position
            line_data[i][4:8] = [1.0, 0.0, 0.0, 1.0]                  # Wall color
            line_data[i+1][4:8] = line_data[i][4:8]
            line_indices[i:i+2] = [i, i+1]

            if self.selectNearby == wall[0]:
                line_data[i][4:8] = [0.0, 0.0, 1.0, 1.0]
            elif self.selectNearby == wall[1]:
                line_data[i+1][4:8] = [0.0, 0.0, 1.0, 1.0]

            i += 2

            # Create wall shadow
            angle = glm.atan(wall[1][1]-wall[0][1], wall[1][0]-wall[0][0]) - glm.pi()/2
            unitv = glm.vec2(glm.cos(angle), glm.sin(angle))

            line_data[i][0:4] = [wall[0][0]-unitv.x/(100*self.scrollPos), wall[0][1]-unitv.y/(100*self.scrollPos), 0.0, 1.0]    # Wall shadow start position
            line_data[i+1][0:4] = [wall[1][0]-unitv.x/(100*self.scrollPos), wall[1][1]-unitv.y/(100*self.scrollPos), 0.0, 1.0]  # Wall shadow end position
            line_data[i][4:8] = [0.4, 0.0, 0.0, 1.0]                                          # Wall shadow color
            line_data[i+1][4:8] = line_data[i][4:8]
            line_indices[i:i+2] = [i, i+1]

            i += 2

        for spawn in self.spawns:

            r = glm.sqrt((spawn[1][1]-spawn[0][1])**2 + (spawn[1][0] - spawn[0][0])**2)
            angle = glm.atan(spawn[1][1]-spawn[0][1], spawn[1][0]-spawn[0][0])

            unitv = glm.vec2(glm.cos(angle)*r, glm.sin(angle)*r)
            line_data[i][0:4] =   [spawn[0][0], spawn[0][1], 0.0, 1.0]
            line_data[i+1][0:4] = [spawn[0][0]+unitv.x, spawn[0][1]+unitv.y, 0.0, 1.0]

            angle -= glm.pi()/2.0
            unitv = glm.vec2(glm.cos(angle)*r, glm.sin(angle)*r)
            line_data[i+2][0:4] = [spawn[0][0], spawn[0][1], 0.0, 1.0]
            line_data[i+3][0:4] = [spawn[0][0]+unitv.x, spawn[0][1]+unitv.y, 0.0, 1.0]

            angle -= glm.pi()/2.0
            unitv = glm.vec2(glm.cos(angle)*r, glm.sin(angle)*r)
            line_data[i+4][0:4] = [spawn[0][0], spawn[0][1], 0.0, 1.0]
            line_data[i+5][0:4] = [spawn[0][0]+unitv.x, spawn[0][1]+unitv.y, 0.0, 1.0]

            angle -= glm.pi()/2.0
            unitv = glm.vec2(glm.cos(angle)*r, glm.sin(angle)*r)
            line_data[i+6][0:4] = [spawn[0][0], spawn[0][1], 0.0, 1.0]
            line_data[i+7][0:4] = [spawn[0][0]+unitv.x, spawn[0][1]+unitv.y, 0.0, 1.0]

            line_data[i][4:8] = [0.0, 0.5, 0.0, 1.0]
            line_data[i+1][4:8] = line_data[i][4:8]
            line_data[i+2][4:8] = [0.0, 0.8, 0.0, 1.0]
            line_data[i+3][4:8] = line_data[i+2][4:8]
            line_data[i+4][4:8] = line_data[i+2][4:8]
            line_data[i+5][4:8] = line_data[i+2][4:8]
            line_data[i+6][4:8] = line_data[i+2][4:8]
            line_data[i+7][4:8] = line_data[i+2][4:8]
            line_indices[i:i+8] = [i, i+1, i+2, i+3, i+4, i+5, i+6, i+7]

            if self.selectNearby == spawn[0]:
                line_data[i][4:8] = [0.0, 0.0, 1.0, 1.0]
            elif self.selectNearby == spawn[1]:
                line_data[i+1][4:8] = [0.0, 0.0, 1.0, 1.0]

            i += 8

        # Create cross if clicked
        if self.cursor is not None:
            line_data[i][0:4] = [self.cursor[0]-0.005/self.scrollPos, self.cursor[1]-0.005/self.scrollPos, 0.0, 1.0]
            line_data[i+1][0:4] = [self.cursor[0]+0.005/self.scrollPos, self.cursor[1]+0.005/self.scrollPos, 0.0, 1.0]
            line_data[i][4:8] = [0.4, 0.4, 0.4, 1.0]
            line_data[i+1][4:8] = line_data[i][4:8]
            line_indices[i:i+2] = [i, i+1]
            i += 2
            line_data[i][0:4] = [self.cursor[0]+0.005/self.scrollPos, self.cursor[1]-0.005/self.scrollPos, 0.0, 1.0]
            line_data[i+1][0:4] = [self.cursor[0]-0.005/self.scrollPos, self.cursor[1]+0.005/self.scrollPos, 0.0, 1.0]
            line_data[i][4:8] = [0.4, 0.4, 0.4, 1.0]
            line_data[i+1][4:8] = line_data[i][4:8]
            line_indices[i:i+2] = [i, i+1]
            i += 2

        self._lineVBuffer.setData(line_data)
        self._lineIBuffer.setData(line_indices)

    def _initShaders(self):
        shaders = []
        with open('shaders/mapbuilder/basic.vert') as f:
            shaders.append(gr.Shader(f.read(), gr.VERTEX_SHADER))
        with open('shaders/mapbuilder/color.frag') as f:
            shaders.append(gr.Shader(f.read(), gr.FRAGMENT_SHADER))
        self.basicProgram = gr.ShaderProgram(shaders)

        shaders = []
        with open('shaders/mapbuilder/cursor.vert') as f:
            shaders.append(gr.Shader(f.read(), gr.VERTEX_SHADER))
        with open('shaders/mapbuilder/color.frag') as f:
            shaders.append(gr.Shader(f.read(), gr.FRAGMENT_SHADER))
        self.cursorProgram = gr.ShaderProgram(shaders)

    def _initBuffers(self):
        # Create uniform buffers
        self.settingsBuffer = gr.Buffer(gr.UNIFORM_BUFFER, gr.DYNAMIC_DRAW)
        self.settingsData = np.zeros([2, 4, 4], dtype='f')
        self.settingsBuffer.setData(self.settingsData)

        self._lineVBuffer = gr.Buffer(gr.VERTEX_BUFFER, gr.STATIC_DRAW)
        self._lineIBuffer = gr.Buffer(gr.INDEX_BUFFER, gr.STATIC_DRAW)
        self.lineVAO = gr.VertexArray(self._lineVBuffer, self._lineIBuffer, [
            gr.VertexElement(4, gr.FLOAT),  # aPos
            gr.VertexElement(4, gr.FLOAT)   # aColor
        ])

        # Create cursor circle
        self._cursorVBuffer = gr.Buffer(gr.VERTEX_BUFFER, gr.STATIC_DRAW)
        self._cursorIBuffer = gr.Buffer(gr.INDEX_BUFFER, gr.STATIC_DRAW)
        cursorVertices = np.array([
            -1.0, -1.0, 0.0, 1.0, 0.4, 0.4, 0.4, 1.0,
            1.0, 1.0, 0.0, 1.0, 0.4, 0.4, 0.4, 1.0,
            -1.0, 1.0, 0.0, 1.0, 0.4, 0.4, 0.4, 1.0,
            1.0, -1.0, 0.0, 1.0, 0.4, 0.4, 0.4, 1.0,
        ], dtype='f')
        cursorIndices = np.array([
            0, 1, 2, 3
        ], dtype='uint32')
        self._cursorVBuffer.setData(cursorVertices)
        self._cursorIBuffer.setData(cursorIndices)
        self.cursorVAO = gr.VertexArray(self._cursorVBuffer, self._cursorIBuffer, [
            gr.VertexElement(4, gr.FLOAT),  # aPos
            gr.VertexElement(4, gr.FLOAT)   # aColor
        ])

    def _onMouseButtonEvent(self, window, btn, action, mods):
        curPos = glfw.get_cursor_pos(window)
        curPos = ((curPos[0]/self.window.width)*2-1)*self.ratio, ((-curPos[1]/self.window.height)*2+1)
        curPos = curPos[0]/self.scrollPos, curPos[1]/self.scrollPos
        curPos = curPos[0]-self.centerPos.x, curPos[1]-self.centerPos.y
        if btn == glfw.MOUSE_BUTTON_LEFT and action == glfw.PRESS:
            self.createPoint(curPos)
        elif btn == glfw.MOUSE_BUTTON_RIGHT and action == glfw.PRESS:
            if self.selectNearby is not None:
                self.deleteSelect()
            else:
                self.inAction = None
                self.cursor = None
                self.createLines()
                self.showSpawnOptions = None
        elif btn == glfw.MOUSE_BUTTON_MIDDLE and action == glfw.PRESS:
            if self.selectNearby is not None and self.selectIndex[0] == self.spawns:
                self.showSpawnOptions = self.selectIndex[1]
            else:
                self.showSpawnOptions = None

    def _onMouseMoveEvent(self, window, x, y):
        curPos = x,y
        curPos = ((curPos[0]/self.window.width)*2-1)*self.ratio, ((-curPos[1]/self.window.height)*2+1)
        curPos = curPos[0]/self.scrollPos, curPos[1]/self.scrollPos
        curPos = curPos[0]-self.centerPos.x, curPos[1]-self.centerPos.y
        self.checkSelect(curPos)

        if glfw.get_key(window, glfw.KEY_LEFT_ALT) == glfw.PRESS:
            self.moveSelect(curPos)
        else:
            # Snap to closest
            if glfw.get_key(self.window.glfw_window, glfw.KEY_LEFT_CONTROL) == glfw.PRESS and self.selectNearby is not None:
                curPos = self.selectNearby[0]+self.centerPos.x, self.selectNearby[1]+self.centerPos.y
                curPos = curPos[0]*self.scrollPos, curPos[1]*self.scrollPos
                glfw.set_cursor_pos(self.window.glfw_window, (curPos[0]/self.ratio + 1)/2*self.window.width, (-curPos[1]+1)/2*self.window.height)

    def _onKeyEvent(self, window, key, scancode, action, mods):
        if key == glfw.KEY_W and action == glfw.PRESS:
            self.mode = 'place wall'
        elif key == glfw.KEY_S and action == glfw.PRESS:
            self.mode = 'place spawn'
        elif key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            self.mode = None

        # THIS WORKED BEFORE BUT NOW SOMETHING IS REALLY BROKEN HERE...
        # moveDir = glm.vec3(0.0)
        # if key == glfw.KEY_UP and (action == glfw.PRESS or action == glfw.REPEAT):
        #     moveDir += glm.vec3(0.0, -1.0, 0.0)
        # if key == glfw.KEY_DOWN and (action == glfw.PRESS or action == glfw.REPEAT):
        #     moveDir += glm.vec3(0.0, 1.0, 0.0)
        # if key == glfw.KEY_LEFT and (action == glfw.PRESS or action == glfw.REPEAT):
        #     moveDir += glm.vec3(1.0, 0.0, 0.0)
        # if key == glfw.KEY_RIGHT and (action == glfw.PRESS or action == glfw.REPEAT):
        #     moveDir += glm.vec3(-1.0, 0.0, 0.0)
        # self.settingsData[0] = glm.translate(self.settingsData[0], 0.05*moveDir/self.scrollPos).to_list()
        # self.centerPos += 0.05*moveDir/self.scrollPos

        if key == glfw.KEY_R and action==glfw.PRESS and self.selectIndex is not None:
            print(self.selectIndex[0][self.selectIndex[1]])
            self.selectIndex[0][self.selectIndex[1]] = (self.selectIndex[0][self.selectIndex[1]][1], self.selectIndex[0][self.selectIndex[1]][0])

    def _onScrollEvent(self, window, x, y):
        if y<0:
            self.settingsData[0] = glm.scale(self.settingsData[0], glm.vec3(0.5)).to_list()
            self.scrollPos *= 0.5
            self.centerPos /= 0.5
        elif y>0:
            self.settingsData[0] = glm.scale(self.settingsData[0], glm.vec3(1/0.5)).to_list()
            self.scrollPos /= 0.5
            self.centerPos *= 0.5
        self.createLines()

    def _onEvent(self, window):
        pass

    def _onResize(self, window):
        self.ratio = float(self.window.width)/float(self.window.height)
        self.settingsData[0] = glm.ortho(-self.ratio, self.ratio, -1.0, 1.0).to_list()
        self.settingsData[0] = glm.scale(self.settingsData[0], glm.vec3(self.scrollPos)).to_list()

    def onUpdate(self):
        gl.glClearColor(0.8, 0.8, 0.8, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        # Set settings uniform buffer data
        self.settingsData[1][0][0] = self.scrollPos
        curPos = glfw.get_cursor_pos(self.window.glfw_window)
        curPos = ((curPos[0]/self.window.width)*2-1)*self.ratio, ((-curPos[1]/self.window.height)*2+1)
        self.settingsData[1][0][1] = curPos[0]
        self.settingsData[1][0][2] = curPos[1]
        self.settingsBuffer.subData(self.settingsData)
        self.settingsBuffer.bindBase(1)

        # Draw lines
        if self.line_count>0:
            self.basicProgram.use()
            self.lineVAO.bind()
            gl.glLineWidth(2)
            gr.drawLines(self.line_count*2)

        # Draw cursor
        self.cursorProgram.use()
        self.cursorVAO.bind()
        gr.drawLines(4)

        imgui.begin('Map builder')
        imgui.text('Left click to place item')
        imgui.text('Right click to delete item')
        imgui.text('CTRL to snap to items')
        imgui.text('ALT to move items')
        imgui.text('W : place walls')
        imgui.text('S : place spawns')
        imgui.text('Use arrow keys to move around')
        imgui.text('When spawn highlighted use middle\nmouse button to show options')
        imgui.text('Center position: (%.2f, %.2f), Scroll position: %.2f'%(self.centerPos.x, self.centerPos.y, self.scrollPos))
        imgui.text('Mode: %s'%self.mode)
        imgui.end()

        if self.showSpawnOptions is not None:
            spawn = self.spawns[self.showSpawnOptions]
            options = self.spawnOptions[self.showSpawnOptions]
            imgui.begin('Spawn options [%d]'%self.showSpawnOptions)

            imgui.text('Spawn: [%.2f, %.2f], [%.2f, %.2f]'%(*spawn[0], *spawn[1]))

            imgui.text('Vehicle spawn rate')
            _, options.rate = imgui.slider_float('cars/s', options.rate, 0.0, 2.0, '%.2f')

            imgui.text('Vehicle start speed')
            _, options.speed = imgui.slider_float('m/s', options.speed, 0.0, 10.0, '%.2f')
            imgui.end()

def main():
    # Start map builder
    mbuild = MapBuilder('out')
    mbuild.export()

if __name__ == '__main__':
    main()