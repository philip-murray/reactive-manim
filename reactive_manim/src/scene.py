import manim
from .animation import attach_progress_interceptors, SceneManager, DynamicMobject





def scan(id, *mobjects):

    def recursive_find(curr, id, path):

        path = [ *path, curr ]

        if isinstance(curr, DynamicMobject) and curr.id == id:
            raise Exception()
            print(path)
        else:
            for m in curr.submobjects:
                recursive_find(m, id, path)

    for m in mobjects:
        recursive_find(m, id, [])
    


class Scene(manim.Scene):
    
    def __init__(self, *args, **kwargs):

        self.super_add = super().add
        super().__init__(*args, **kwargs)
        attach_progress_interceptors(self)

    def add(self, *mobjects):
        self.super_add(*mobjects)
        scan(111, *mobjects)
        mycontains(111)
        return self

    #def add(self, *mobjects):
    #    print("A")
    ##    super().add(*mobjects)
    #    mycontains(111)
    # #   return self
        
        

def mycontains(id):

    scene = SceneManager.scene_manager().scene

    def recursive_find(curr, id, path):

        path = [ *path, curr ]

        if isinstance(curr, DynamicMobject) and curr.id == id:
            raise Exception()
            print(path)
        else:
            for m in curr.submobjects:
                recursive_find(m, id, path)

    for m in scene.mobjects:
        recursive_find(m, id, [])

def quick_morph(mobject: DynamicMobject):
    scene = SceneManager.scene_manager()
    
    rm = RecoverMobject()
    rm.save_recover_point(mobject.identity)
    rm.submobjects = []

    def fn():
        rm.recover_mobject(mobject.identity)

    return fn
