import glfw
import OpenGL.GL as gl
import imgui.core as imgui
import imgui.integrations.glfw as imgui_glfw
from typing import Callable

class Window:

    def __init__(self, width : int, height : int, eventHandler: Callable[[glfw._GLFWwindow],None], renderPass : Callable[[],None], resizeHandler : Callable[[glfw._GLFWwindow],None]):
        self.width = width
        self.height = height
        self.renderPass = renderPass
        self.eventHandler = eventHandler
        self.resizeHandler = resizeHandler

        # Initialize GLFW
        glfw.init()
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint_string(glfw.X11_INSTANCE_NAME, "BSCOPD-JPBLD")
        glfw.window_hint_string(glfw.X11_CLASS_NAME, "BSCOPD-JPBLD")
        glfw.window_hint(glfw.FOCUSED, glfw.FALSE)

        self.glfw_window = glfw.create_window(width, height, __file__, None, None)
        if not self.glfw_window:
            glfw.terminate()
            raise glfw.GLFWError("GLFW window could not be created")

        glfw.make_context_current(self.glfw_window)

        glfw.swap_interval(1)

        gl.glViewport(0, 0, width, height)
        glfw.set_framebuffer_size_callback(self.glfw_window, self._framebuffer_size_callback)

        imgui.create_context()
        self.imgui_context = imgui_glfw.GlfwRenderer(self.glfw_window)

    def __del__(self):
        self.imgui_context.shutdown()
        glfw.terminate()

    def run(self):
        self.softstop = False
        self.resizeHandler(self)
        while not glfw.window_should_close(self.glfw_window) and not self.softstop:
            glfw.poll_events()
            self.imgui_context.process_inputs()
            self.eventHandler(self.glfw_window)

            imgui.new_frame()
            gl.glClearColor(1.0, 1.0, 1.0, 1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            self.renderPass()
            imgui.render()
            self.imgui_context.render(imgui.get_draw_data())
            glfw.swap_buffers(self.glfw_window)
        # glfw.destroy_window(self.glfw_window)

    def _framebuffer_size_callback(self, window, width, height):
        self.height = height
        self.width = width
        gl.glViewport(0, 0, width, height)
        self.resizeHandler(self)

    def close(self):
        glfw.set_window_should_close(self.glfw_window, True)

    def shutdown(self):
        self.__del__()

    def softclose(self):
        self.softstop = True