layout(location=0) in vec3 aPos;

void main(){

    posState_s posState = bPosState[gl_InstanceID];
    vec4 position = posState.pos;
    float rotation = posState.rot;

    // Translation matrix
    mat4 tMat = mat4(
        1.0,    0.0,    0.0,    0.0,
        0.0,    1.0,    0.0,    0.0,
        0.0,    0.0,    1.0,    0.0,
        position.x,    position.y,    position.z,    1.0
    );
    
    // Rotation matrix
    mat4 rMat = mat4(
        cos(rotation),    -sin(rotation),    0.0,    0.0,
        sin(rotation),    cos(rotation),    0.0,    0.0,
        0.0,    0.0,    1.0,    0.0,
        0.0,    0.0,    0.0,    1.0
    );

    // Scale matrix
    mat4 sMat = mat4(
        scale,    0.0,    0.0,    0.0,
        0.0,    scale,    0.0,    0.0,
        0.0,    0.0,    scale,    0.0,
        0.0,    0.0,    0.0,    1.0
    );

    gl_Position = uViewProjection * tMat * sMat * rMat * vec4(aPos.xyz, 1.0);
}