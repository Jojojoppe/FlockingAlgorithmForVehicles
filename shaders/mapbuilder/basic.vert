#version 450 core

layout(location=0) in vec4 aPos;
layout(location=1) in vec4 aColor;

out vec4 vColor;

layout(binding=1) uniform settings{
    mat4 uVPmat;
};

void main(){
    gl_Position = uVPmat * aPos;
    vColor = aColor;
}