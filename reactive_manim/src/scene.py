
import manim
from .animation import attach_progress_interceptors

scene_init = manim.Scene.__init__

def intercept_scene_init(self, *args, **kwargs):
    scene_init(self, *args, **kwargs)
    #print("INTERCEPTOR SCENE INIT")
    attach_progress_interceptors(self)

manim.Scene.__init__ = intercept_scene_init

x = 5

"""
import manim
from .animation import attach_progress_interceptors


class Scene(manim.Scene):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        attach_progress_interceptors(self)
"""