layout(location=0) in vec3 aPos;

#define L 2.0

void main(){

    posState_s posState = bPosState[gl_InstanceID];
    vec4 position = posState.pos;
    float rotation = posState.rot;

    movState_s movState = bMovState[gl_InstanceID];
    vec4 velocity = movState.dvel;
    float angle = movState.angle;

    // Translation matrix
    mat4 tMat = mat4(
        1.0,    0.0,    0.0,    0.0,
        0.0,    1.0,    0.0,    0.0,
        0.0,    0.0,    1.0,    0.0,
        position.x,    position.y,    position.z,    1.0
    );
    
    // Rotation matrix
    float speed = length(velocity);
    mat4 rMat = mat4(
        velocity.y/speed,       -velocity.x/speed,    0.0,    0.0,
        velocity.x/speed,       velocity.y/speed,    0.0,    0.0,
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