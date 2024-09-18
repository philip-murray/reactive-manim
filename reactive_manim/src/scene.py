import manim
from .animation import attach_progress_interceptors


class Scene(manim.Scene):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        attach_progress_interceptors(self)