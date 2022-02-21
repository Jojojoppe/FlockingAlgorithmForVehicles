#version 450 core

/* Header for all simulation shaders
*  ---------------------------------
*  This file contains all the global buffer bindings for
*  the simulation and globally used constants. This file
*  is prepended to all shaders which are compiled.
*
*  Assume N vehicles and M obstacles (line segments)
*/

struct posState_s{      // Size (5+3)*4
    vec4 pos;           // Current position in world space
    float rot;          // Current rotation in world space
    float padding[3];
};

struct movState_s{      // Size (10+6)*4
    vec4 vel;           // Current velocity in world space
    vec4 dvel;          // Desired velocity to steer towards in world space
    float angle;        // Current steering angle in local space
    float speed;        // Current speed of rear axis
    float padding[6];
};

struct simState_s{      // Size (2+2)*4
    uint steps;         // Amount of simulated steps
    uint collided;      // 1 if collision has happened
    float time;         // Elapsed time
    uint start;         // Start frame number
};

struct distanceState_s{ // Size (3+1)*4
    float dist;         // Distance between two objects
    float angle;        // Angle towards object in world space
};

struct wallInfo_s{      // Size (1+1)*4
    float norm;         // Normal on wall in world space
};

struct internalData_s{
    vec4 cohesion;
    vec4 alignment;
    vec4 seperation;
    vec4 padding;
};

// The global uniforms
layout(binding=1) uniform globalSettingsBuffer{
    mat4 uViewProjection;
    float uDeltaTime;       // [1][0][0]
    float uN;               // [1][0][1]
    float uM;               // [1][0][2]
    float uw_coh;           // [1][0][3]
    float uw_ali;           // [1][1][0]
    float uw_sep;           // [1][1][1]
    float ud_v;             // [1][1][2]
    float ud_s;             // [1][1][3]
    float dphi_max;         // [1][2][0]
    float phi_max;          // [1][2][1]
};

// State of each vehicle
layout(binding=2) buffer posStateBuffer{
    posState_s bPosState[];     // size of N
};

// Moving state of each vehicle
layout(binding=3) buffer movStateBuffer{
    movState_s bMovState[];     // size of N
};

// Simulation state of each vehicle
layout(binding=4) buffer simStateBuffer{
    simState_s bSimState[];     // size of N
};

// Distance buffer
layout(binding=5) buffer distanceBuffer{
    distanceState_s bDistanceState[];          // Size of N*(N+M)
};


// Wall position buffer
layout(binding=6) buffer wallPosBuffer{
    vec2 bWallPos[];                           // Size of 2*M
};

// Wall information buffer
layout(binding=7) buffer wallInfoBuffer{
    wallInfo_s bWallInfo[];                    // Size of M
};

// Internal data buffer
layout(binding=9) buffer internalDataBuffer{
    internalData_s bInternalData[];
};

// Constants
#define PI_F 3.1415926535897932384626433832795
#define PI_S 3.1415927

const float scale = 1.0;

// Toyota Camry LE 2019: 
// 4.9m long, 1.8m wide. 
// wheelbase is 2.8m
// Max steering angle 37*
// Max delta steering angle 37*/s
const float l = 2.8 * scale;
const float collisionDistance = 2.45 * scale; //2.61 * scale;
//const float phi_max = PI_F/360*90;
//const float dphi_max = PI_F/360*90;
// Maximum acceleration
// TODO search for values
const float amaxpos = 1.0; // m/s2
const float amaxneg = -1.0; // m/s2
const float vmax = 120/3.6; // m/s
