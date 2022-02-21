import logging
logger = logging.getLogger(__name__)

import glfw
import OpenGL.GL as gl
import numpy as np
import ctypes

def draw(count : int):
    gl.glDrawElements(gl.GL_TRIANGLES, count, gl.GL_UNSIGNED_INT, ctypes.c_void_p(0))

def drawLines(count : int):
    gl.glDrawElements(gl.GL_LINES, count, gl.GL_UNSIGNED_INT, ctypes.c_void_p(0))

def drawInstanced(count : int, instanceCount : int, start : int = 0):
    gl.glDrawElementsInstanced(gl.GL_TRIANGLES, count, gl.GL_UNSIGNED_INT, ctypes.c_void_p(start*4), instanceCount)

def drawLinesInstanced(count : int, instanceCount, start : int = 0):
    gl.glDrawElementsInstanced(gl.GL_LINES, count, gl.GL_UNSIGNED_INT, ctypes.c_void_p(start*4), instanceCount)

