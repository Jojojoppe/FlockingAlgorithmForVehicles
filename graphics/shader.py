import logging
logger = logging.getLogger(__name__)

import glfw
import OpenGL.GL as gl
import numpy as np
import ctypes

from typing import Sequence

VERTEX_SHADER = gl.GL_VERTEX_SHADER
FRAGMENT_SHADER = gl.GL_FRAGMENT_SHADER
COMPUTE_SHADER = gl.GL_COMPUTE_SHADER

class Shader():
    def __init__(self, source, type):
        self.ID = gl.glCreateShader(type)
        gl.glShaderSource(self.ID, [source])
        gl.glCompileShader(self.ID)
        if gl.glGetShaderiv(self.ID, gl.GL_COMPILE_STATUS) != gl.GL_TRUE:
            logger.error("ERROR: could not compile shader:\r\n" + str(gl.glGetShaderInfoLog(self.ID), "utf-8"))
            logger.error("%s:\r\n%s"%(str(type), source))

    def __del__(self):
        gl.glDeleteShader(self.ID)


class ShaderProgram():
    def __init__(self, shaders : Sequence[Shader]):
        self.shaders = shaders

        self.ID = gl.glCreateProgram()

        for shd in self.shaders:
            if shd.ID==0:
                logger.error("ERROR: tried to add empty shader")
                continue
            gl.glAttachShader(self.ID, shd.ID)

        gl.glLinkProgram(self.ID)
        if gl.glGetProgramiv(self.ID, gl.GL_LINK_STATUS) != gl.GL_TRUE:
            logger.error("ERROR: could not link shader program:\r\n" + str(gl.glGetProgramInfoLog(self.ID), "utf-8"))

    def __del__(self):
        gl.glDeleteProgram(self.ID)

    def use(self):
        gl.glUseProgram(self.ID)

    def dispatch(self, groupsX : int = 1, groupsY : int = 1, groupsZ : int = 1):
        self.use()
        gl.glDispatchCompute(groupsX, groupsY, groupsZ)