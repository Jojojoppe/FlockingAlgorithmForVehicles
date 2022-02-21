#version 450 core

layout(location=0) in vec4 aPos;
layout(location=1) in vec4 aColor;

out vec4 vColor;

layout(binding=1) uniform settings{
    mat4 uVPmat;
    float uScrollPos;
    float uCurX;
    float uCurY;
};

void main(){
    mat4 sMat = mat4(
        uScrollPos,    0.0,    0.0,    0.0,
        0.0,    uScrollPos,    0.0,    0.0,
        0.0,    0.0,    uScrollPos,    0.0,
        uCurX,    uCurY,    0.0,    1.0
    );
    gl_Position = sMat * aPos;
    vColor = aColor;
}