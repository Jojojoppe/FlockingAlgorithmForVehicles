# Simulation environment written for my BSc thesis 'Distributed Control Algorithm for Cooperative Autonomous Driving Vehicles Inspired by Flocking Behaviour'


Abstract — Control strategies for cooperatively autonomous driving vehicles are becoming more and more complex to ensure safe operation while, when taking inspiration from nature, more simple mathematical descriptions exist which describe behaviour of animals moving in a flocking or herding manner. In the eighties Reynolds came up with a set of heuristic rules [1] which form a model for flocking behaviour of birds and his work has been an inspiration for constructing a control strategy based on flocking behaviour for self-driving vehicles. Previous research relied on more simple kinematic models of vehicles and thus using it directly in real vehicles would be difficult. This research provides an algorithm inspired by flocking behaviour as found in swarms of birds and a bridge between said algorithm and a vehicle. A dedicated simulation environment which uses parallelism on a GPU is written and is used to determine the performance of the proposed algorithm. It is found that the proposed algorithm performs relatively well under the tested situations and is found that a wide range of parameters could be used which result in stable behaviour.

## Description
This is the code base used for my Bachelor thesis written in Python and OpenGL shaders. For this code to work the packages noted in `requirements.txt` should be installed with `pip`. The OpenGL context is created and managed by the graphics module which contains code for manipulating buffers (be it vertex/index buffers or general data buffers), the window (using GLFW) and shaders. An important note: The code uses OpenGL Compute shaders and these are not available with older versions of OpenGL! In older versions it can maybe included with the `ARB_compute_shader` extension but from OpenGL 4.3 and higher it is implemented in the OpenGL core. A last important note: the code is written on and ran on a Linux based system (Arch Linux) with a Ryzen 5 (2600) and an NVIDIA GeForce GTX 1060 6GB. The code has been tested on a laptop with an older graphics card but that was still an Arch system thus this code has never been tested on any other operating system let alone Windows!

The graphics context and window drawing is abstracted in the `Simulation` class in `simulation.py`. This class manages the context and order of the dispatch calls. It uses callback functions to let the user customize the flow and data in the simulation. The docstring of the constructor should explain it a bit:
```
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
```

A detailed example is shown in `main.py` which reads the world data from `out.spn` and `out.wls`, both csv files containing information about the vehicle spawn points and the obstacles (walls). The vehicle data from the file is stored in a `Vehicle` object. Then the `Simulation` object is created and the algorithm shader is loaded into the graphics context (which is done outside of the `Simulation` object to allow simple customization of the algorithm like using mulitple shaders or loading a dirrerent shader when needed). Some global settings are set (which are used in the shaders, see `header.glsl` for the layout of the buffers).

The layout of the obstacle world file is simple:
```
startx, starty, endx, endy
```
Note: the road facing side of the obstacle is from start to end at the right

Vehicles are (with this system) modelled as spawn points:
```
spawnx, spawny, directionx, directiony, rate, speed
```
Here the rate is the number of vehicles per second (?) and the speed is the driving speed in m/s from the start. These world files can be created and manipulated by hand, with python code and with `mapbuilder.py` which provides a simple graphical interface.

#### Notes
This codebase is currently over a year old and I used an older version of python back then. At the moment with all the requirements installed it should run as its supposed to run. There is one small exception though: there was a way to move the camera over the world with the wasd keys and zoom with the q and e keys in the simulation and move with the arrow keys in the mapbuilder. For some reason the translation of the camera now results in rotating in 3D space which gives strange artifacts. I commented out the moving in `simulation.py` and `mapbuilder.py`, the zooming still works as intended.

The way I gathered data from the simulation is shown in the `ex` folder. There a mostly unannotated `main.py` can be found which I used in one of the last experiments. In that file an example of `aData()` can be seen as well as the world creation in code. I used some shell scripts to run the `main.py` for different parameter ranges. This setup created loads and loads of csv files which I then analized with some python scripts (added them in the folder as well: `process.py` for extracting the data and creating one big csv and `images.py` to create lots and lots of graphs) Yes, its ugly...  but it worked! These files are just included for completeness and examples and are by no means ready to be ran in this code base!

Even though I cleaned up much of the codebase I still think it is an ugly mess... Somewhere in the beginning it started as a neatly organized thing but it grew and grew slowly in this frankenstein monster with callbacks onto callbacks to get some data here and manipulate some data there. The shaders became monstrosities with a shared mega-header in an attempt to correctly define the buffers. Luckily it is not production software but merely a research project. Although it is a long time ago since I really looked into this code feel free to ask any questions (can be done via my student mail or github@joppeb.nl)