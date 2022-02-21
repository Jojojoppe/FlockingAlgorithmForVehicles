import logging
logger = logging.getLogger(__name__)

import graphics as gr
import simulation as Sim

import random
import numpy as np
import imgui.core as imgui
import matplotlib.pyplot as plt
import glm
import csv
import os
import csv

from contextlib import contextmanager
from timeit import default_timer
import time
import sys

@contextmanager
def elapsed_timer():
    start = default_timer()
    elapser = lambda: default_timer() - start
    yield lambda: elapser()
    end = default_timer()
    elapser = lambda: end-start

class Vehicle():
    def __init__(self, x, y, rot, speed, start):
        self.x = x
        self.y = y
        self.rot = rot
        self.speed = speed
        self.start = start
    def __str__(self):
        return '[%.2f, %.2f] %.2f -> %.2f @ %d'%(self.x, self.y, self.rot, self.speed, self.start)

# -------------------------------------------------------------------------

# Algorithm pass
#   This function is called each frame
#   Simulation object is passed as parameter
def aPass(sim:Sim.Simulation):
    algoProgram.dispatch(sim.N)

# Data gathering pass
#   This function is called after period amount of steps
#   Simulation object is passed as parameter
posY = [[], [], []]
posX = [[], [], []]
velY = [[], [], []]
velX = [[], [], []]
dvelY = [[], [], []]
dvelX = [[], [], []]
frames = []
time = []

# Internal data
iCohesion = []
iAlignment = []
iSeperation = []
iCollisions = []
def aData(sim:Sim.Simulation):
    # Get data from first car
    posState = np.frombuffer(sim.posStateBuffer.getData(0), dtype='f').reshape((sim.N, 8))
    movState = np.frombuffer(sim.movStateBuffer.getData(0), dtype='f').reshape((sim.N, 16))
    internalData = np.frombuffer(sim.internalDataBuffer.getData(0), dtype='f').reshape((sim.N, 16))
    simState = np.frombuffer(sim.simStateBuffer.getData(0), dtype='uint32').reshape((sim.N, 4))
    posX[0].append(posState[0,0])
    posY[0].append(posState[0,1])
    velX[0].append(movState[0,0])
    velY[0].append(movState[0,1])
    dvelX[0].append(movState[0,4])
    dvelY[0].append(movState[0,5])
    posX[1].append(posState[sim.N//2,0])
    posY[1].append(posState[sim.N//2,1])
    velX[1].append(movState[sim.N//2,0])
    velY[1].append(movState[sim.N//2,1])
    dvelX[1].append(movState[sim.N//2,4])
    dvelY[1].append(movState[sim.N//2,5])
    posX[2].append(posState[1+(sim.N//2),0])
    posY[2].append(posState[1+(sim.N//2),1])
    velX[2].append(movState[1+(sim.N//2),0])
    velY[2].append(movState[1+(sim.N//2),1])
    dvelX[2].append(movState[1+(sim.N//2),4])
    dvelY[2].append(movState[1+(sim.N//2),5])
    frames.append(sim.stepCount)
    time.append(sim.time)

    # SAVE CAS DATA

    C = 0
    A = 0
    S = 0
    for i in range(sim.N):
        coh = np.array(internalData[i, 0:4])
        ali = np.array(internalData[i, 4:8])
        sep = np.array(internalData[i, 8:12])
        C += np.sqrt(np.dot(coh, coh))
        A += np.sqrt(np.dot(ali, ali))
        S += np.sqrt(np.dot(sep, sep))
    iCohesion.append(C/sim.N)
    iAlignment.append(A/sim.N)
    iSeperation.append(S/sim.N)

    # CHECK IF A CAR HAS COLLIDED
    collisions = 0
    for i in range(sim.N):
        collisions += simState[i, 1]
    iCollisions.append(collisions)

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

    # Normals are from Start to end clockwise (PI/2)
    wallVertices = np.zeros([len(walls)*4], dtype='f')
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

# -------------------------------------------------------------------------

def runSimulation(sim, c, a, s, dv, ds, phi_max, dphi_max):
    #print(c, a, s, dv, ds, phi_max, dphi_max)
    sim.seed = 0
    sim.globalSettings[1][0][3] = c           # cohesion
    sim.globalSettings[1][1][0] = a           # alignment
    sim.globalSettings[1][1][1] = s           # seperation
    sim.globalSettings[1][1][2] = dv          # d_v
    sim.globalSettings[1][1][3] = ds          # d_s
    sim.globalSettings[1][2][0] = dphi_max
    sim.globalSettings[1][2][1] = phi_max
    # sim.globalSettings[1][0][0] = 0.05

    # Start simulation
    sim.start()

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

def main(c=0.1, a=6.0, s=3.0, simtime=60*15):
    global algoProgram

    walls.clear()
    vehicles.clear()

    file = 'out'
    # simtime = 60*15
    N, M = readWorld(file, simtime)

    # Initialize simulation
    # Number of vehicles, VSync, time, aInit function, aPass function, 
    #   aGUI function, aData function, aData period, Rendering
    sim = Sim.Simulation(N, False, simtime, aInit, aPass, aGUI, aData, 1, True)

    # Create algorithm shader
    shaders = []
    with open("shaders/algorithm.comp") as f:
        shaders.append(gr.Shader(sim.header + f.read(), gr.COMPUTE_SHADER))
    algoProgram = gr.ShaderProgram(shaders)

    with elapsed_timer() as elapsed:
        runSimulation(sim, c, a, s, 15.0, 10.0, 3.141592/360*37, 3.141592/360*37)
    t_el = elapsed()
    sim.window.close()
    sim.window.shutdown()

    print("distanceBuffer", sim.distanceBuffer.ID)
    print("movStateBuffer", sim.movStateBuffer.ID)

    del(sim)
    del(algoProgram)
    return t_el, N
    
# if __name__=='__main__':

#     c = float(sys.argv[1])
#     a = float(sys.argv[2])
#     s = float(sys.argv[3])

#     nrstreams = 3
#     w = float(sys.argv[4])

#     # Create config files
#     with open('out.wls', 'w') as f:
#         f.write('%f, %f, %f, %f\r\n'%(0,-50,0,280))
#         f.write('%f, %f, %f, %f\r\n'%(w,280,w,-50))
        
#     with open('out.spn', 'w') as f:
#         # dist = 10.0
#         xoff = float(w)/2.0 - 10
#         dist = 10

#         if xoff <= 5:
#             dist = float(w)/float(nrstreams+1)
#             xoff = dist
#         for x in range(nrstreams):
#             for y in range(3):
#                     f.write('%f, %f, %f, %f, 0.01, 1.0\r\n'%(x*dist+xoff, y*dist, x*dist+xoff, y*dist+1.0))

#     t_el, N = main(c, a, s, int(60*20))
#     print('%d : %f'%(N, t_el))
if __name__=='__main__':

    c = float(sys.argv[1])
    a = float(sys.argv[2])
    s = float(sys.argv[3])

    fl = float(sys.argv[4])
    fph = float(sys.argv[5])

    nrstreams = 3
    w = 40

    # Create config files
    with open('out.wls', 'w') as f:
        f.write('%f, %f, %f, %f\r\n'%(0,-50,0,80))
        f.write('%f, %f, %f, %f\r\n'%(0,80,5,80+fl))
        f.write('%f, %f, %f, %f\r\n'%(5,80+fl,5,280+fl))
        f.write('%f, %f, %f, %f\r\n'%(35,280+fl,35,80+fl))
        f.write('%f, %f, %f, %f\r\n'%(35,80+fl,40,80))
        f.write('%f, %f, %f, %f\r\n'%(40,80,40,-50))


        
    with open('out.spn', 'w') as f:
        # dist = 10.0
        xoff = float(w)/float(nrstreams+1)
        dist = xoff
        for x in range(nrstreams):
            for y in range(3):
                if x==1:
                    f.write('%f, %f, %f, %f, 0.01, 1.0\r\n'%(x*dist+xoff, y*dist+dist*fph, x*dist+xoff, y*dist+1.0+dist*fph))
                else:
                    f.write('%f, %f, %f, %f, 0.01, 1.0\r\n'%(x*dist+xoff, y*dist, x*dist+xoff, y*dist+1.0))

    t_el, N = main(c, a, s, int(60*20+fl))
    print('%d : %f'%(N, t_el))

    # plt.plot(time, iCohesion, label='cohesion')
    # plt.plot(time, iAlignment, label='alignment')
    # plt.plot(time, iSeperation, label='seperation')
    # plt.plot(time, iCollisions, label='collisions')
    # plt.legend()
    # plt.savefig('width/w%f.png'%(w))
    # plt.close()

    # # Save data to csv
    # with open('width/%f.csv'%(w), 'w') as f:
    #     writer = csv.writer(f)
    #     writer.writerow(['frame','time','posx0','posx1','poxy0','posy1','velx0','velx1','vely0','vely1','dvelx0','dvelx1','dvely0','dvely1', 'C', 'A', 'S', 'collisions'])
    #     for i,f in enumerate(frames):
    #         writer.writerow([
    #             f, time[i],
    #             posX[0][i], posX[1][i], posY[0][i], posY[1][i],
    #             velX[0][i], velX[1][i], velY[0][i], velY[1][i],
    #             dvelX[0][i], dvelX[1][i], dvelY[0][i], dvelY[1][i],
    #             iCohesion[i], iAlignment[i], iSeperation[i], iCollisions[i]
    #         ])

