layout(location=0) in vec3 aPos;

void main(){

    posState_s posState = bPosState[gl_InstanceID];
    vec4 position = posState.pos;
    float rotation = posState.rot;

    movState_s movState = bMovState[gl_InstanceID];
    float angle = movState.angle;

    // Translation matrix
    mat4 tMat1 = mat4(
        1.0,    0.0,    0.0,    0.0,
        0.0,    1.0,    0.0,    0.0,
        0.0,    0.0,    1.0,    0.0,
        0.0,    l/2,    0.0,    1.0
    );
    mat4 tMat2 = mat4(
        1.0,    0.0,    0.0,    0.0,
        0.0,    1.0,    0.0,    0.0,
        0.0,    0.0,    1.0,    0.0,
        position.x,    position.y,    position.z,    1.0
    );
    
    // Rotation matrix
    mat4 rMat1 = mat4(
        cos(angle),    -sin(angle),    0.0,    0.0,
        sin(angle),    cos(angle),    0.0,    0.0,
        0.0,    0.0,    1.0,    0.0,
        0.0,    0.0,    0.0,    1.0
    );
    mat4 rMat2 = mat4(
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

    gl_Position = uViewProjection * tMat2 * sMat * rMat2 * tMat1 * rMat1 * vec4(aPos.xyz, 1.0);
}