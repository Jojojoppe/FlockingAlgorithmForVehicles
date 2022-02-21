import graphics as gr
import simulation as Sim

import numpy as np
import imgui.core as imgui
import glm

import sys
import random
import csv

# Read the world files
# Information is used later on in aInit
# Using the Vehicle class to store vehicle data
class Vehicle():
    def __init__(self, x, y, rot, speed, start):
        self.x = x
        self.y = y
        self.rot = rot
        self.speed = speed
        self.start = start
    def __str__(self):
        return '[%.2f, %.2f] %.2f -> %.2f @ %d'%(self.x, self.y, self.rot, self.speed, self.start)
walls = []
vehicles = []
def readWorld(file, simtime):
    N = 0
    M = 0

    with open(file + '.wls', 'r') as f:
        reader = csv.reader(f)
        for r in reader:
            if r[0].startswith('#'):
                continue
            M += 1
            walls.append([float(r[0]), float(r[1]), float(r[2]), float(r[3])])
            # walls.append([float(r[2]), float(r[3]), float(r[0]), float(r[1])])

    with open(file + '.spn', 'r') as f:
        reader = csv.reader(f)
        for r in reader:
            if r[0].startswith('#'):
                continue
            center = glm.vec2(float(r[0]), float(r[1]))
            pointer = glm.vec2(float(r[2]), float(r[3]))
            rate = float(r[4])
            speed = float(r[5])
            rot = glm.atan(pointer.y-center.y, pointer.x-center.x)

            for i in range(0, simtime, int(60/rate)):
                N += 1
                v = Vehicle(center.x, center.y, rot, speed, i)
                #print(v)
                vehicles.append(v)

    return N, M


# Algorithm pass
#   This function is called each frame
#   Simulation object is passed as parameter
def aPass(sim:Sim.Simulation):
    algoProgram.dispatch(sim.N)

def aData(sim:Sim.Simulation):
    # Get data from first car
    posState = np.frombuffer(sim.posStateBuffer.getData(0), dtype='f').reshape((sim.N, 8))
    movState = np.frombuffer(sim.movStateBuffer.getData(0), dtype='f').reshape((sim.N, 16))
    internalData = np.frombuffer(sim.internalDataBuffer.getData(0), dtype='f').reshape((sim.N, 16))
    simState = np.frombuffer(sim.simStateBuffer.getData(0), dtype='uint32').reshape((sim.N, 4))
    # Do something with the data

# Initializing routine
#   This function is called before running simulation
#       the posStateBuffer and movStateBuffer should be set with initial data
#       in this function
#   Simulation object is passed as parameter
#   Must return a numpy array of floats with the positions of obstacles
#       in the form of [start.x start.y end.x end.y] dtype=float
def aInit(sim:Sim.Simulation):
    global walls, vehicles

    posState = np.zeros([sim.N, 8], dtype="f")
    movState = np.zeros([sim.N, 16], dtype="f")
    simState = np.zeros([sim.N, 4], dtype='uint32')

    # Fill posState, movState and simState buffers
    i = 0
    for v in vehicles:
        posState[i][0:4] = [v.x, v.y, 0.0, 1.0]
        posState[i][4] = v.rot-glm.pi()/2
        unitv = glm.vec2(glm.cos(v.rot), glm.sin(v.rot))
        movState[i][0:4] = [unitv.x*v.speed, unitv.y*v.speed, 0.0, 0.0]
        movState[i][4:8] = [unitv.x*v.speed, unitv.y*v.speed, 0.0, 0.0]
        movState[i][8] = 0.0
        movState[i][9] = 0.0
        simState[i][3] = v.start
        i+=1

    sim.posStateBuffer.setData(posState)
    sim.movStateBuffer.setData(movState)

    wallVertices = np.zeros([len(walls)*4], dtype='f')

    # Fill wallVertices
    i = 0
    for w in walls:
        wallVertices[i:i+4] = w
        i += 4

    return wallVertices, simState

# GUI drawing routine
#   This function should draw the GUI using ImGui
#       Changes can be made in sim.globalSettings
#   Simulation object is passed as parameter
def aGUI(sim:Sim.Simulation):
    imgui.begin("Settings")
    imgui.text("N=%d, M=%d"%(sim.globalSettings[1][0][1], sim.globalSettings[1][0][2]))
    # uDeltaTime
    _, sim.globalSettings[1][0][0] = imgui.slider_float("dt", sim.globalSettings[1][0][0], 0.0, 0.5, '%.4f')
    _, sim.globalSettings[1][0][3] = imgui.slider_float("coh", sim.globalSettings[1][0][3], 0.0, 10.0, '%.4f')
    _, sim.globalSettings[1][1][0] = imgui.slider_float("ali", sim.globalSettings[1][1][0], 0.0, 10.0, '%.4f')
    _, sim.globalSettings[1][1][1] = imgui.slider_float("sep", sim.globalSettings[1][1][1], 0.0, 10.0, '%.4f')
    _, sim.globalSettings[1][1][2] = imgui.slider_float("d_v", sim.globalSettings[1][1][2], 0.0, 100.0, '%.1f')
    _, sim.globalSettings[1][1][3] = imgui.slider_float("d_s", sim.globalSettings[1][1][3], 0.0, 100.0, '%.1f')
    _, sim.globalSettings[1][2][1] = imgui.slider_float("phi_max", sim.globalSettings[1][2][1], 0.0, 3.141592/360*90, '%.4f')
    _, sim.globalSettings[1][2][0] = imgui.slider_float("dphi_max", sim.globalSettings[1][2][0], 0.0, 3.141592/360*90, '%.4f')

    if imgui.button('Reset'):
        random.seed(sim.seed)
        sim.reset()
    imgui.end()

def main():
    global algoProgram

    # cohesion, alignment and separation factors
    c=0.1
    a=6.0
    s=3.0
    # visual distance and seperation distance
    dv = 15.0
    ds = 10.0
    # maximum steering angle and steering angle speed
    # now practically infinite
    dphi_max = 3.141592/360*37
    phi_max = 3.141592/360*37

    # Simulation time in frames
    simtime=15*60

    # name of world definition files (spn and wls)
    file='out'

    N, M = readWorld(file, simtime)

    # Initialize simulation
    # Needs to be ran before doing graphics stuff! (this creates the openGL context)
    sim = Sim.Simulation(N, False, simtime, aInit, aPass, aGUI, aData, 1, True) 

    # Create algorithm shader
    shaders = []
    with open("shaders/algorithm.comp") as f:
        shaders.append(gr.Shader(sim.header + f.read(), gr.COMPUTE_SHADER))
    algoProgram = gr.ShaderProgram(shaders)

    sim.globalSettings[1][0][3] = c           # cohesion
    sim.globalSettings[1][1][0] = a           # alignment
    sim.globalSettings[1][1][1] = s           # seperation
    sim.globalSettings[1][1][2] = dv          # d_v
    sim.globalSettings[1][1][3] = ds          # d_s
    sim.globalSettings[1][2][0] = dphi_max
    sim.globalSettings[1][2][1] = phi_max
    sim.globalSettings[1][0][0] = 0.05      # Time step per frame

    # Start simulation
    sim.start()

    sim.window.close()
    sim.window.shutdown()

if __name__=='__main__':
    main()