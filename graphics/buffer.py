import logging
logger = logging.getLogger(__name__)

import glfw
import OpenGL.GL as gl
import numpy as np
import ctypes

from typing import Sequence

VERTEX_BUFFER = gl.GL_ARRAY_BUFFER
INDEX_BUFFER = gl.GL_ELEMENT_ARRAY_BUFFER
UNIFORM_BUFFER = gl.GL_UNIFORM_BUFFER
SHADER_STORAGE_BUFFER = gl.GL_SHADER_STORAGE_BUFFER

STATIC_DRAW = gl.GL_STATIC_DRAW
DYNAMIC_DRAW = gl.GL_DYNAMIC_DRAW

class Buffer():
    def __init__(self, type : gl.Constant, usage : gl.Constant):
        self.type = type
        self.usage = usage

        self.ID = gl.glGenBuffers(1)
        self.length = 0

    def __del__(self):
        gl.glDeleteBuffers(1, self.ID)

    def setData(self, data : np.array):
        self.bind()
        gl.glBufferData(self.type, data, self.usage)
        self.length = data.nbytes

    def reserveData(self, length : int):
        self.bind()
        gl.glBufferData(self.type, length, None, self.usage)
        self.length = length

    def subData(self, data : np.array, offset : int = 0):
        self.bind()
        gl.glBufferSubData(self.type, offset, data)

    def getData(self, length : int, offset : int = 0):
        self.bind()
        if length == 0:
            length = self.length
        return gl.glGetBufferSubData(self.type, offset, length)

    def bind(self):
        gl.glBindBuffer(self.type, self.ID)

    def bindBase(self, index : int, type=None):
        if type is None:
            gl.glBindBufferBase(self.type, index, self.ID)
        else:
            gl.glBindBufferBase(SHADER_STORAGE_BUFFER, index, self.ID)

FLOAT = gl.GL_FLOAT
INT = gl.GL_INT
UINT = gl.GL_UNSIGNED_INT

typesizes = {FLOAT : 4, INT : 4, UINT : 4}

class VertexElement():
    def __init__(self, number : int, type : gl.Constant, normalized : bool = False):
        self.number = number
        self.type = type
        self.normalized = normalized

class VertexArray():
    def __init__(self, vertexBuffer : Buffer, indexBuffer : Buffer, layout : Sequence[VertexElement]):
        self.ID = gl.glGenVertexArrays(1)

        self.bind()
        vertexBuffer.bind()
        indexBuffer.bind()

        # Calculate stride
        self.stride = 0
        for e in layout:
            self.stride += e.number*typesizes[e.type]

        # Enable vertex attributes
        offset = 0
        for i,e in enumerate(layout):
            #gl.glVertexAttribPointer(i, e.number, e.type, e.normalized, e.number*typesizes[e.type], ctypes.c_void_p(offset))
            gl.glVertexAttribPointer(i, e.number, e.type, e.normalized, self.stride, ctypes.c_void_p(offset))
            offset += e.number*typesizes[e.type]
            gl.glEnableVertexAttribArray(i)

        self.unbind()

    def __del__(self):
        gl.glDeleteVertexArrays(1, self.ID)

    def bind(self):
        gl.glBindVertexArray(self.ID)

    def unbind(self):
        gl.glBindVertexArray(0)