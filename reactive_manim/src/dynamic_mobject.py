from __future__ import annotations
from abc import abstractmethod
from typing_extensions import *
from typing import List, Dict, overload, Tuple
import copy
import numpy as np
from .helpers import *
from manim import *
import functools



scene_init = Scene.__init__

def intercept_scene_init(self, *args, **kwargs):
    scene_init(self, *args, **kwargs)
    attach_progress_interceptors(self)

Scene.__init__ = intercept_scene_init


animation_init = Animation.__init__

def intercept_animation_init(self, *args, **kwargs):
    animation_init(self, *args, **kwargs)

    if self.remover:

        dynamic_mobjects = extract_direct_dynamic_mobjects(self.mobject)

        for mobject in dynamic_mobjects:
            for dm in mobject.get_dynamic_family():
                SceneManager.scene_manager().construct_remover_animation(dm)

    if self.introducer:

        dynamic_mobjects = extract_direct_dynamic_mobjects(self.mobject)

        for mobject in dynamic_mobjects:
            for dm in mobject.get_dynamic_family():
                SceneManager.scene_manager().construct_introducer_animation(dm)

Animation.__init__ = intercept_animation_init



def attach_progress_interceptors(scene: Scene) -> SceneManager:

    if hasattr(scene, "scene_manager"):
        return scene.scene_manager
    
    scene_manager = attach_progress_interceptors_function(scene)

    scene.scene_manager = scene_manager
    SceneManager._scene_manager = scene_manager

    return scene_manager


def attach_progress_interceptors_function(scene: Scene) -> SceneManager:

        scene_manager = SceneManager(scene)
        
        scene_add = scene.add
        scene_wait = scene.wait
        scene_remove = scene.remove

        def _add(*mobjects: Mobject) -> Scene:
            
            for mobject in mobjects:
                
                for m in mobject.get_family():
                    if isinstance(m, MobjectIdentity): 
                        raise Exception()

                for m in extract_direct_dynamic_mobjects(mobject):
                    if isinstance(m, DynamicMobject):
                        for dm in m.get_dynamic_family():
                            scene_manager.scene_add(dm)

            return scene_add(*mobjects)
        
        def _wait(*args, **kwargs) -> None:
            scene_manager.scene_wait()
            scene_wait(*args, **kwargs)

        def _remove(*mobjects):

            for mobject in mobjects:
                
                for m in mobject.get_family():
                    if isinstance(m, MobjectIdentity): 
                        raise Exception()

                for m in extract_direct_dynamic_mobjects(mobject):
                    if isinstance(m, DynamicMobject):
                        for dm in m.get_dynamic_family():
                            scene_manager.scene_remove(dm)

            for mobject in mobjects:
                scene_add(mobject)
                scene_remove(mobject)

            return scene

        scene.add = _add
        scene.wait = _wait
        scene.remove = _remove

        scene.scene_add = scene_add
        scene.scene_wait = scene_wait
        scene.scene_remove = scene_remove

        return scene_manager

def extract_direct_dynamic_mobjects(mobject: Mobject):
    dynamic_mobjects: Set[DynamicMobject] = set()

    def recursive_extract(mobject):
        for submobject in mobject.submobjects:
            if isinstance(submobject, DynamicMobject):
                dynamic_mobjects.add(submobject)
            else:
                recursive_extract(submobject)

    if isinstance(mobject, DynamicMobject):
        return [ mobject ]
    else:
        recursive_extract(mobject)
        return list(dynamic_mobjects)
    

graph_references = []
graph_references_memo = {}

class SceneManager():

    _scene_manager: SceneManager | None = None
    _scene: Scene | None = None

    _client_context: bool = True
    

    @staticmethod
    def disable_client_context():
        SceneManager._client_context = False

    @staticmethod
    def enable_client_context():
        SceneManager._client_context = True

    @staticmethod
    def client_context() -> bool:
        return SceneManager._client_context

    @staticmethod
    def scene_manager():

        scene_manager = SceneManager._scene_manager
        
        if scene_manager is None:
            raise Exception("Missing attach_progress_interceptors(self) in the body of `def construct(self)`")
        
        return scene_manager
    
    def __init__(
        self,
        scene: Scene
    ):
        self.scene = scene
        self.graph_managers: Dict[DynamicMobjectGraph, GraphStateManager] = {}

    def graph_of_root_mobject(self, root_mobject: MobjectIdentity):

        def correct(root, graph):
            return root in graph.root_mobjects

        if root_mobject in graph_references_memo:
            graph = graph_references_memo[root_mobject]
            if correct(root_mobject, graph):
                return graph
            
        for graph in graph_references:
            if correct(root_mobject, graph):
                graph_references_memo[root_mobject] = graph
                return graph
            
        raise Exception()

        for manager in self.graph_managers.values():
            if root_mobject in manager.graph.root_mobjects:
                return manager.graph
            
        raise Exception()

    def graph_manager(self, graph: DynamicMobjectGraph):
        return self.graph_managers[graph]

    def scene_add(self, mobject: DynamicMobject):
        self.graph_managers[mobject.graph].scene_add(mobject.identity)

    def scene_wait(self):
        for manager in list(self.graph_managers.values()).copy():
            manager.scene_wait()

    def scene_remove(self, mobject: DynamicMobjectGraph):
        self.graph_managers[mobject.graph].scene_remove(mobject.identity)

    def construct_remover_animation(self, mobject: DynamicMobject):
        self.graph_managers[mobject.graph].construct_remover_animation(mobject.identity)

    def construct_introducer_animation(self, mobject: MobjectIdentity):
        self.graph_managers[mobject.graph].construct_introducer_animation(mobject.identity)

    
class GraphProgressManager():

    def __init__(
        self,
        graph: DynamicMobjectGraph,
        scene: Scene
    ):
        self.scene = scene
        self.graph = graph

        # copied mobjects from stack, f(id-carrier)
        self.source_graph: DynamicMobjectGraph | None = None
        self.target_graph: DynamicMobjectGraph | None = None

        # stack mobjects, id-carries
        self.source_mobjects: Dict[UUID, MobjectIdentity] = {}
        self.target_mobjects: Dict[UUID, MobjectIdentity] = {}
    
    def save_source_graph(self, clear_source_target_flags=False):

        """
        ID-POLICY, CLEAR ID FLAGS SET BY PREVIOUS TRANSFORMATION
        # we moved this into create_progress_point() from end_transforms(), after moving begin_transforms() into save_target_graph()
        # this acts on graph-of-interest, which in the case of a progress transform, does not include remover mobject identities
        # what about auto disconncet removers
        """
        
        if clear_source_target_flags:
            for mobject in self.graph.dynamic_mobjects:
                mobject.reactive_lock = True
                mobject.source_id = None
                mobject.target_id = None
                mobject.reactive_lock = False


        self.source_graph = self.graph.copy()
        self.target_graph = None
        self.source_mobjects = { mobject.id: mobject for mobject in self.graph.mobjects }
        self.target_mobjects = None

    def save_target_graph(self):


        for mobject in self.source_graph.dynamic_mobjects:
            mobject.reactive_lock = True
            mobject.source_id = None # this is applied to GOC -> source_graph
            mobject.target_id = None # this isn't applied to GOC -> target_graph
            mobject.reactive_lock = False

        self.target_graph = self.graph.copy()
        self.target_mobjects = { mobject.id: mobject for mobject in self.graph.mobjects }

        """ 
        ID-POLICY, UPDATE SOURCE-GRAPH WITH TARGET-ID FLAGS SET BY USER DURING EDIT-MODE
        
        The target_id flag is used to specify that a remover-mobject should appear to merge onto a transformer-mobject
        The remover-mobject is found only in the source_graph, so the DTC expects source_graph[remover.id].target_id to be set
        However, the source_graph is saved from graph.copy() prior to the user setting the target_id flag in edit-mode
        This updates the source_graph with target_id flags set by the user in edit-mode
        """
    
        mobject_union = [ mobject.current_dynamic_mobject for mobject in set(self.source_mobjects.values()).union(set(self.target_mobjects.values())) ]

        # switched array from self.graph.dynamic_mobjects (which does not include removers), to mobject_union, after exponent example didn't work as expected
        for mobject in mobject_union: # stack-mobjects
            if (mobject.target_id is not None) and self.source_graph.contains(mobject.id):

                dynamic_mobject = self.source_graph.find_dynamic_mobject(mobject.id)
                dynamic_mobject.reactive_lock = True
                dynamic_mobject.target_id = mobject.target_id
                dynamic_mobject.reactive_lock = False


class RecoverMobject():

    def __init__(self):
        self.recover_points = {}
        self.recover_submobjects = {}

    def save_recover_point(self, mobject: DynamicMobject):
        self.recover_points[mobject] = mobject.points.copy()
        self.recover_submobjects[mobject] = mobject.submobjects.copy()
    
    def recover_mobject(self, mobject: DynamicMobject):
        mobject.points = self.recover_points[mobject]
        mobject.submobjects = self.recover_submobjects[mobject]


class TransformContainer(VMobject):
    
    def __init__(self, id):
        super().__init__()
        self.id = id

    def __repr__(self):
        return f"Container({self.id})"
    

"""
The DynamicTransformManager (ADTM) is a class that assists with running multiple partial transforms,

---

For progress transforms, this would look like:

scene.play(TransformInStages.progress(tex[0])) # creates an ADTM, this reverts and restructures mobjects in `tex`
scene.play(TransformInStages.progress(tex[1]))
scene.play(TransformInStages.progress(tex[2]))

tex.some_edit() # causes ADTM.end_transforms(), which unrestructures mobjects

---

For from_copy transforms, this would look like:

scene.play(TransformInStages.from_copy(src, tex[0])) # creates ADTM, which fades-out tex, until each partial tex[i] transform fades-in over copy-source
scene.play(TransformInStages.from_copy(src, tex[1]))
scene.play(TransformInStages.from_copy(src, tex[2]))

tex.some_edit() causes ADMT.end_transforms(), which unrestrucutres mobjects
"""

class AbstractDynamicTransformManager():

    def __init__(
        self,
        graph: DynamicMobjectGraph,
        source_graph: DynamicMobjectGraph,
        target_graph: DynamicMobjectGraph,
    ):
        self.graph = graph
        self.source_graph = source_graph
        self.target_graph = target_graph
        self.scene_manager = SceneManager.scene_manager()
        self.scene = self.scene_manager.scene
    
    def begin_transforms(self):

        """ Currently, begin_transforms() -> save_target_graph, so for .progress() target_graph is None until begin_transforms()"""
        self.source_graph_manager = self.scene_manager.graph_manager(self.source_graph)
        self.target_graph_manager = self.scene_manager.graph_manager(self.target_graph)
        
        """
        INVALIDATION POLICY
        In from_copy(tex1, tex2); from_copy(tex2, tex3)

        tex2 is still in a restructured state when from_copy(tex2, tex3) is called, 
        so self.source_graph_manager.require_default() is called to unrestructure tex2
        so that the GraphTransformDescriptor(tex2, tex3) is not corrupted

        Need to change this so that .copy() returns an uncorrupted copy provided by the state-manager
        """
        self.source_graph_manager.require_default()
        
        # begin_transforms() runs on the first partial-transform call, i.e. scene.play(TransformInStages.some_constructor(tex)) in a series of some_constructor-partial-transforms
        # Subsequent partial-transforms will skip to animating the existing transform_containers, that have not yet been animated by previous partial-transforms
        # self.graph.subscribe(lambda graph: self.end_transforms(), self.subscription_id)
        
        self.transform_descriptor = GraphTransformDescriptor(self.source_graph.copy(), self.target_graph.copy())
        self.transform_containers = { id: TransformContainer(id) for id in self.transform_descriptor.ids() }
        self.save_recover_point()


        
        for container in self.transform_containers.values(): # ADD TRANSFORM-CONTAINERS TO SCENE
            self.scene.scene_add(container)

        for mobject in self.filter_observers(self.observers()): # REMOVE OBSERVERS FROM SCENE
            mobject.submobjects = []
            
        for mobject in self.filter_observers(self.observers()):  # due to auto-disconnect, this could corrupt progress(src) after doing from_copy(src, trg) ?
            self.scene.scene_add(mobject).scene_remove(mobject)

        for id, container in self.transform_containers.items(): # SET TIME=0 MOBJECT FOR EACH TRANSFORM-CONTAINER
            self.create_source_mobject_for_container(container, id)

        for id, container in self.transform_containers.items(): # perhaps we might want to move this to RF area. 
            if id in self.transform_descriptor.prevent_ids():
                container.set_opacity(0)

        # RESTRUCTURE OBSERVERS TO POINT INTO TRANSFORM-CONTAINERS
        self.restructure_participant_observers(participant_observers=self.transform_containers.keys())
    

    def filter_observers(self, observers):

        arr = []
        for m in observers:
            if m.identity not in self.hashset:
                arr.append(m)

        return arr

    def restructure_participant_observers(self, participant_observers):

        
        # remember that there can be two (mobject.id) observers per transform_container[id], in the case of replacement_transform

        for mobject in self.filter_observers(self.observers()):
            if mobject.id in participant_observers:
                
                def is_source_or_target_parent(child_id):
                    return (
                        self.transform_descriptor.is_source_parent(mobject.id, child_id) or
                        self.transform_descriptor.is_target_parent(mobject.id, child_id) # is_xyz_parent allows clones, hopefully using clones here is okay
                    )
                
                mobject.submobjects = [ self.transform_containers[mobject.id], *[ self.transform_containers[id] for id in self.transform_descriptor.ids() if is_source_or_target_parent(id) ] ]

                def has_points_recursive(m):
                    if m.has_points():
                        return True
                    for submobject in m.submobjects:
                        if has_points_recursive(submobject):
                            return True
                    return False
                
                if not has_points_recursive(self.transform_containers[mobject.id]):
                    mobject.submobjects = [ self.transform_containers[id] for id in self.transform_descriptor.ids() if is_source_or_target_parent(id) ]


    @abstractmethod
    def observers(self) -> List[DynamicMobject]:
        """ transform-observers are the mobjects the user declares in the scene.construct method, it is best understood by replacement_transform """
        pass
        # these are the user's mobjects declared on the stack, that are used to connect the scene to the transform_containers
        # Scene -> root_mobject -> transform_container[root]
        # Scene -> root_mobject -> root_mobject.child[i] -> transform_container[child[i]]
        # The transform_container[id] contain's graph[id]'s direct submobjects, that does not include graph[id]'s children which are also apart of graph[some-id]

    @abstractmethod
    def create_source_mobject_for_container(self, container, id):
        """
        This sets the initial visual state of each containers[id] to time=0, 
        it is required because the first transform might not animate every container[id] at once,
        the ensures that containers that are not being animated, look like time=0, which the animated containers look like some time=t

        This default implementation is okay for replacement_transform and progress, but for from_copy, the source_graph does not observe the transform containers
        Therefore, the FromCopyTransformManager will set opacity=0, 
        so non-animated containers don't create a thicker-overlay effect where the target_mobject (copy) is hovering over source_mobject
        """

        if self.transform_descriptor.is_introducer(id):
            container.points = VMobject().points
            container.submobjects = []
        else:
            container.points = self.transform_descriptor.find_source_dynamic_mobject(id).copy().points
            container.submobjects = self.transform_descriptor.find_source_dynamic_mobject(id).direct_submobjects().copy()

    def save_recover_point(self):
        self.mobject_recovery = RecoverMobject()

        for mobject in self.observers():
            self.mobject_recovery.save_recover_point(mobject)


    def end_transforms(self):

        # REMOVE TRANSFORM CONTAINERS FROM SCENE
        for container in self.transform_containers.values():
            self.scene.scene_add(container).scene_remove(container)

        # In case user does not transform every ID, we manually recover observers in the graph-of-interest, or target_observers
        for observer in self.graph.dynamic_mobjects:
            self.recover_mobject(observer)

        for mobject in self.graph.root_dynamic_mobjects():
            self.scene.scene_add(mobject)

        # Introduction via scene.add() creates a progress manager,
        # for progress, create_progress_manager() returns the existing manager
        # for from_copy/replacement_transform, it creates one since none exists, as these are introductory transforms for the graph-of-interest (target_graph)

        #self.graph.unsubscribe(self.subscription_id)
        #self.scene_manager.delete_transform_manager(self.graph)
        """ delete_transform_manager now occurs by set_state(DefaultState()) by either require_default() or begin_edit() """

        # Restricted clear_source_target_flags to progress-finish only, so in from_copy(tex1, tex2); from_copy(tex2, tex3)
        # from_copy(tex1, tex2) does not clear the id-linking required for from_copy(tex2, tex3)

        #self.scene_manager.create_progress_manager(self.graph).create_progress_point(clear_source_target_flags=clear_source_target_flags)
        self.graph.manager().save_source_graph(clear_source_target_flags=True)#hasattr(self, "progress_manager"))


    def recover_mobject(self, mobject):
        self.mobject_recovery.recover_mobject(mobject)

    def recover_mobjects(self):

        for mobject in self.observers():
            self.mobject_recovery.recover_mobject(mobject)

    def restore_participant_observers(self, participant_observers: Set[UUID]):

        # maybe we should only be restoring target_observers?
        for mobject in self.observers():
            if mobject.id in participant_observers:
                self.mobject_recovery.recover_mobject(mobject)

    @abstractmethod
    def on_finish_scene_update(self, scene):
        pass
    
    
    """ 
    constructor_name and matches_constructor_gaurd,
    are used to ensure that subsequent partial-transforms match the constructor pattern of the first partial-transform
    """

    def set_abstract_dynamic_transform(self, cls: type[AbstractDynamicTransform]) -> Self:
        self.abstract_dynamic_transform_cls = cls
        return self

    @abstractmethod
    def constructor_name(self) -> str:
        pass

    def matches_construction_guard(self, next_transform_manager: AbstractDynamicTransformManager):
        return # todo

        if not (
            self.source_graph is next_transform_manager.source_graph and
            self.target_graph is next_transform_manager.target_graph and
            self.constructor_name() == next_transform_manager.constructor_name()
        ):
            raise Exception(
                f"Cannot mix partial-transform constructors on the same mobject-graph \n"
                f"Attempted \n "
                f"{self.abstract_dynamic_transform_cls.__name__}{self.constructor_name()} \n"
                f"{next_transform_manager.abstract_dynamic_transform_cls.__name__}{next_transform_manager.constructor_name()} \n"
            )
        
class GraphTransformDescriptor():

    def __init__(
        self, 
        source_graph: DynamicMobjectGraph,
        target_graph: DynamicMobjectGraph
    ):
        self.source_graph = source_graph
        self.target_graph = target_graph

        self.source_memo = {}
        self.target_memo = {}

    def prevent_ids(self):
        
        ids = self.ids()
        prevent_ids = set()

        # finding (idS, idT) such that 
        # find_target_dynamic_mobject(idS) -> target_graph[idT]
        # find_source_dynamic_mobject(idT) -> source_graph[idS]
        # this is essentially an id changing its name, but two containers are animated which has a double-overlay
        # we remove the idS by putting it in prevent_ids() for the TransformItinerary to set_opacity(0)

        
        for id in ids:
            if self.is_scene_remover(id) and self.has_target(id):
                target = self.find_target_dynamic_mobject(id)
                if self.is_scene_introducer(target.id) and self.has_source(target.id):
                    source = self.find_source_dynamic_mobject(target.id)
                    if source.id == id:
                        prevent_ids.add(id)

        return prevent_ids

        

        
        for id in ids:
            # given x' -> x, is_remover(x') is false. This is_scene_remover might cause problems later
            if self.is_scene_remover(id):
                auto_disconnect_source_id = self.source_graph.find_dynamic_mobject(id).source_id

                for mobject in self.target_graph.dynamic_mobjects:

                    if mobject.source_id is not None and mobject.source_id == id:
                        if id not in ids:
                            raise Exception()
                        if id in ids:
                            print("prevent A ", id, )
                            prevent_ids.add(id) # fix y in xyxyxy example

                    
                    if auto_disconnect_source_id is not None and mobject.id == auto_disconnect_source_id:
                        if id not in ids: 
                            raise Exception()
                        if id in ids: # uh what is with the id in ids?
                            if id == 64:
                                print("ID PREVENT B")
                            prevent_ids.add(id) # fix x in xyxyxy example

        return prevent_ids

    def ids(self):
        return { mobject.id for mobject in self.source_graph.mobjects }.union({ mobject.id for mobject in self.target_graph.mobjects })

    def find_source_dynamic_mobject_(self, id: UUID) -> DynamicMobject | None:
        if id is None:
            raise Exception()
        
        # DIRECT MATCH
        if self.source_graph.contains(id):
            return self.source_graph.get_dynamic_mobject(id)
        else:
            # DIRECT FLAG
            source_id = self.target_graph.get_dynamic_mobject(id).source_id

            if not none(source_id) and self.source_graph.contains(source_id):
                return self.source_graph.get_dynamic_mobject(source_id)

            # SOURCE-FINDER-1
            # It's unlikely that m1.target_id = m2 would be set on an m2-introducer. 

            # SOURCE-FINDER 2
            for mobject in self.target_graph.dynamic_mobjects:
                if mobject.id == source_id:
                    if self.find_source_dynamic_mobject_(mobject.id) is not None:
                        return self.find_source_dynamic_mobject_(mobject.id)
                    
            return None

    def find_source_dynamic_mobject(self, id: UUID) -> DynamicMobject | None:
        if id in self.source_memo:
            return self.source_memo[id]
        else:
            source = self.find_source_dynamic_mobject_(id)
            self.source_memo[id] = source
            return source
        

    def find_target_dynamic_mobject_(self, id: UUID, checked: List[DynamicMobject]) -> DynamicMobject | None:
        if id is None:
            raise Exception()
        
        checked.add(id)

        # DIRECT MATCH
        if self.target_graph.contains(id):
            return self.target_graph.get_dynamic_mobject(id)
        else:
            # DIRECT FLAG
            target_id = self.source_graph.get_dynamic_mobject(id).target_id

            if not none(target_id) and self.target_graph.contains(target_id):
                return self.target_graph.get_dynamic_mobject(target_id)

            # TARGET-FINDER-1, given a <-sid- a.clone(), then target(a) = a.clone(), if there only exists one a.clone()
            for mobject in self.target_graph.dynamic_mobjects:
                if mobject.source_id == id:
                    return mobject
                
                    # a = MathString("a")
                    # tex1 = MathTex(a)
                    # tex2 = MathTex(a)  REQUIRED-PREVENT-ID since tex1[a].id and tex2[a].id have the same itinerary



            """
            MathMatrix printout:
            FTDM
            A
            B
            C
            id=18 18->* source --- (sid,tid)=(-, N) cross-id=N
            FTDM
            A
            B
            id=84 84->167 source --- (sid,tid)=(-, N) cross-id=18
            FTDM
            A
            id=167 84->167 ______ --- (sid,tid)=(84, -) cross-id=-

            We see that  [*] <- [*]
                                 ^
                                 |
                                [*]

            This happens in non-trival horizontal contructions, liken to Tex(a, a, a) but more complex like constructions like Tex(Tex(a), Tex(a))
            We are not looking for mobjects whose id is the current cross_id, but mobjects who the their cross_id is the current_id                
            
            
            """


            # TARGET-FINDER-2, if source_graph DM is an a.clone() to another source_graph[a], check if source_graph[a] has a corresponding target_mobject
            #cross_id = self.source_graph.get_dynamic_mobject(id).source_id
            for mobject in self.source_graph.dynamic_mobjects:
                if mobject.source_id == id:
                    if mobject.id not in checked:
                        if self.find_target_dynamic_mobject_(mobject.id, checked) is not None:
                            return self.find_target_dynamic_mobject_(mobject.id, checked)
                    
                        # a = MathString("a")
                        # tex1 = MathTex(a, a)
                        # tex2 = MathTex(a)      # this policy enables both tex1[0] and tex1[1] to merge onto tex2[0]

            """
            We see that  [*] <- [*]
                          ^
                          |
                         [*]

            this happens because of Tex(a, a, a) causing a1 and a2 to be clones of a0, we could change register_child implemenation perhaps?
            Not just the claim: `We are not looking for mobjects whose id is the current cross_id, but mobjects who the their cross_id is the current_id`    

            """

            cross_id = self.source_graph.get_dynamic_mobject(id).source_id
            for mobject in self.source_graph.dynamic_mobjects:
                if mobject.id == cross_id:
                    if mobject.id not in checked:
                        if self.find_target_dynamic_mobject_(mobject.id, checked) is not None:
                            return self.find_target_dynamic_mobject_(mobject.id, checked)
                    
            return None
            
    def find_target_dynamic_mobject(self, id: UUID) -> DynamicMobject | None:

        if id in self.target_memo:
            return self.target_memo[id]
        else:
            checked = set()
            target = self.find_target_dynamic_mobject_(id, checked=checked)
            self.target_memo[id] = target
            return target

    def has_source(self, id: UUID):
        return True if self.find_source_dynamic_mobject(id) is not None else False
    
    def has_target(self, id: UUID):
        return True if self.find_target_dynamic_mobject(id) is not None else False
    
    def is_remover(self, id: UUID):
        return self.has_source(id) and not self.has_target(id)
    
    def is_introducer(self, id: UUID):
        return self.has_target(id) and not self.has_source(id)
        
    def is_transformer(self, id: UUID):
        return not self.is_remover(id) and not self.is_introducer(id)
    
    def is_scene_remover(self, id: UUID):
        return self.source_graph.contains(id) and not self.target_graph.contains(id)
    
    def is_scene_introducer(self, id: UUID):
        return self.target_graph.contains(id) and not self.source_graph.contains(id)
    
    def is_source_parent(self, parent_id, child_id):
        # maybe find child, check child.parent which may be None

        child = self.find_source_dynamic_mobject(child_id)
        parent = self.find_source_dynamic_mobject(parent_id)

        if child is not None and parent is not None:
            if child.parent is parent:
                return True
            
        return False

    def is_target_parent(self, parent_id, child_id):
        # maybe find child, check child.parent which may be None

        child = self.find_target_dynamic_mobject(child_id)
        parent = self.find_target_dynamic_mobject(parent_id)

        if child is not None and parent is not None:
            if child.parent is parent:
                return True
            
        return False
    
    def is_continuous_ancestor(self, ancestor_id: UUID, child_id: UUID):
        
        a1 = self.has_source(ancestor_id) and self.has_target(ancestor_id)
        a2 = self.has_source(ancestor_id) and not a1
        a3 = self.has_target(ancestor_id) and not a1

        b1 = self.has_source(child_id) and self.has_target(child_id)
        b2 = self.has_source(child_id) and not b1
        b3 = self.has_target(child_id) and not b1
        
        if a2 and b2:
            return self.is_source_ancestor(ancestor_id, child_id)
        
        if a1 and b2:
            return self.is_source_ancestor(ancestor_id, child_id)
        
        if b3 and a3:
            return self.is_target_ancestor(ancestor_id, child_id)
        
        if b3 and a1:
            return self.is_target_ancestor(ancestor_id, child_id)
        
        if a1 and b1:
            return self.is_source_ancestor(ancestor_id, child_id) and self.is_target_ancestor(ancestor_id, child_id)
        
        return False

    def is_source_ancestor(self, ancestor_id: UUID, child_id: UUID):

        def recursive_has_ancestor_with_id(mobject: DynamicMobject):

            if mobject.id == ancestor_id:
                return True

            if mobject.parent:
                return recursive_has_ancestor_with_id(mobject.parent)
            else:
                return False

        source_child = self.find_source_dynamic_mobject(child_id)

        if source_child is None:
            return False
        else:
            return recursive_has_ancestor_with_id(source_child)
        
    def is_target_ancestor(self, ancestor_id: UUID, child_id: UUID):

        def recursive_has_ancestor_with_id(mobject: DynamicMobject):

            if mobject.id == ancestor_id:
                return True

            if mobject.parent:
                return recursive_has_ancestor_with_id(mobject.parent)
            else:
                return False

        target_child = self.find_target_dynamic_mobject(child_id)

        if target_child is None:
            return False
        else:
            return recursive_has_ancestor_with_id(target_child)
        

def reactive(dynamic_mobject_method):

    @functools.wraps(dynamic_mobject_method)

    def interceptor(self: DynamicMobject, *args, **kwargs):
        self.begin_edit()
        result = dynamic_mobject_method(self, *args, **kwargs)
        self.end_edit()
        return result
    
    return interceptor









class GraphStateInterface():

    def __init__(
        self, 
        manager: GraphStateManager
    ):
        self.manager = manager

    @abstractmethod
    def begin(self):
        raise NotImplementedError()
    
    @abstractmethod
    def end(self):
        raise NotImplementedError()


    @abstractmethod
    def begin_edit(self, mobject: MobjectIdentity):
        raise NotImplementedError()

    @abstractmethod
    def end_edit(self, mobject: MobjectIdentity):
        raise NotImplementedError()


    @abstractmethod
    def accept_transform_manager(
        self, 
        transform_manager: AbstractDynamicTransformManager
    ):
        raise NotImplementedError()
    

    @abstractmethod
    def scene_add(self, mobject: MobjectIdentity):
        raise NotImplementedError()
    
    @abstractmethod
    def scene_wait(self):
        raise NotImplementedError()
    
    @abstractmethod
    def scene_remove(self, mobject: MobjectIdentity):
        raise NotImplementedError()
    

    #@abstractmethod
    #def construct_introducer_animation(self, mobject: DynamicMobject):
    #    raise NotImplementedError()

    @abstractmethod
    def construct_remover_animation(self, mobject: DynamicMobject):
        raise NotImplementedError()
    
    @abstractmethod
    def construct_introducer_animation(self, mobject: MobjectIdentity):
        raise NotImplementedError()

    
    




class TransformState(GraphStateInterface):

    def __init__(
        self, 
        manager: GraphStateManager,
        #transform_manager: AbstractDynamicTransformManager
    ):
        self.manager = manager
        self.transform_manager: Optional[AbstractDynamicTransformManager] = None
        #self.transform_manager = transform_manager

    def begin(self):
        #self.transform_manager.begin_transforms()

        self.hashset: Dict[MobjectIdentity, bool] = {}
    
    def end(self):
        #self.transform_manager.end_transforms()
        #detach_supplemental_ids = self.transform_manager.end_transforms()
        #self.manager.create_progress_manager2()
        #self.manager.progress_manager.save_source_graph(clear_source_target_flags=detach_supplemental_ids)
        if self.transform_manager is not None:
            self.transform_manager.end_transforms()
        else:
            self.manager.save_source_graph(clear_source_target_flags=True)

        self.manager.graph.set_auto_disconnect_memory()


    def begin_edit(self, mobject: MobjectIdentity):
        self.manager.set_state(DefaultState(self.manager))
        self.manager.state.begin_edit(mobject)

        """
        TransformInStages.progress(tex[0])
        TransformInStages.progress(tex[1])
        TransformInStages.progress(tex[2])
        tex[0].some_edit() # -> causes TransformState.end()
        """

    def accept_transform_manager(
        self, 
        transform_manager: AbstractDynamicTransformManager
    ):
        if self.transform_manager is None:
            self.transform_manager = transform_manager
            self.transform_manager.hashset = self.hashset
            self.transform_manager.begin_transforms()
        else:
            self.transform_manager.matches_construction_guard(transform_manager)
            
        return self.transform_manager
    
    def require_default(self):
        self.manager.set_state(DefaultState(self.manager))
        
    def scene_add(self, mobject: MobjectIdentity): # pass on partial-transform FadeIn() ?
        return

    def scene_wait(self):
        return

    def scene_remove(self, mobject: MobjectIdentity): 
        # FadeOut(m) after partial transforms without going to edit
        # at some point we need to track ID progression to we know when partial transforms is done without an edit 
        self.require_default()
        self.manager.scene_remove(mobject)

    def construct_introducer_animation(self, mobject: MobjectIdentity):
        self.hashset[mobject] = True
        if self.transform_manager is not None:
            self.transform_manager.recover_mobject(mobject.current_dynamic_mobject)
    
    def construct_remover_animation(self, mobject: MobjectIdentity):
        self.require_default()
        self.manager.construct_remover_animation(mobject)

class ProgressToEmpty(GraphStateInterface):

    def __init__(self, *args, **kwargs):
        self.hashset: Dict[MobjectIdentity, bool] = {}
        super().__init__(*args, **kwargs)

    def begin(self):
        pass

    def end(self):
        pass

    def complete(self):
        for mobject, comp in self.hashset.items():
            if mobject.current_dynamic_mobject.has_direct_points():
                if not comp:
                    return False
        return True

    def scene_add(self, mobject: MobjectIdentity):
        return # I think FadeOut(m) can add it, 

    def scene_wait(self):
        return

    def scene_remove(self, mobject: MobjectIdentity): 
        
        self.hashset[mobject] = True

        if self.complete():
            self.manager.set_state(DefaultState(self.manager))
    
    def construct_remover_animation(self, mobject: MobjectIdentity):
        return


class DefaultState(GraphStateInterface):

    def begin(self):
        #self.manager.graph.set_auto_disconnect_memory() 
        return
    
    def end(self):
        return

    def begin_edit(self, mobject: MobjectIdentity):
        self.manager.set_state(EditState(self.manager, mobject))
        self.manager.state.begin_edit(mobject)

    def accept_transform_manager(
        self, 
        transform_manager: AbstractDynamicTransformManager
    ):
        #self.manager.set_state(TransformState(self.manager, transform_manager))
        self.manager.set_state(TransformState(self.manager))
        self.manager.accept_transform_manager(transform_manager)
        return transform_manager
    
    def require_default(self):
        return

    def scene_add(self, mobject: MobjectIdentity):
        self.manager.save_source_graph()

        #PATCH

        # so previously DefaultState().begin() would set_auto_disconnect_memory, 
        # so immediately on edit -> default_state, set_auto_disconnect_memory would get cleared
        # so we need to have it on end_transforms()

        #self.manager.set_state(TransformState(self.manager))
        #self.manager.set_state(DefaultState(self.manager)) # need to trigger set_auto_disconnect_memory()

        # PATCH CONSEQUENCE
        # I guess we don't have to do .save_source_graph() if we do TransformState().end()

        #self.manager.graph.set_auto_disconnect_memory() # This should be on leaving transform-state, which is caused by scene_add

        # PATCH PATCH, to prevent cross-ID deletion on scene.add()
        self.manager.graph.set_auto_disconnect_memory()


    def scene_wait(self):
        # a graph that is not added to the scene will not have a progress manager, it is assumed to still be in construction
        # on scene.add() it gets its first progress point, and wait() refresh it, unless in transform mode which assumes wait() is apart of transformation

        if self.manager.has_progress_manager(): # in TransformState, exists progress_manager, but we don't update on wait(), 
            self.manager.save_source_graph()

        self.manager.graph.add_auto_disconnect_memory()

        #self.manager.graph.set_auto_disconnect_memory() 

    def scene_remove(self, mobject: MobjectIdentity): 
        self.manager.set_state(ProgressToEmpty(self.manager))
        self.manager.scene_remove(mobject)
    
    def construct_remover_animation(self, mobject: MobjectIdentity):
        self.manager.set_state(ProgressToEmpty(self.manager))

    def construct_introducer_animation(self, mobject: MobjectIdentity):
        self.manager.set_state(TransformState(self.manager))
        self.manager.construct_introducer_animation(mobject)
    

class EditState(GraphStateInterface):

    def __init__(
        self,
        manager: GraphStateManager,
        mobject: MobjectIdentity
    ):
        super().__init__(manager)
        self.graph = manager.graph
        self.edit_manager = GraphEditManager(manager.graph, mobject)

    def begin(self):
        
        for mobject in self.manager.graph.mobjects:
            try:
                center = mobject.current_dynamic_mobject.get_center()
                mobject.mobject_center = center
            except:
                raise Exception()
            
    def end(self):
        return
    
    def begin_edit(self, mobject: MobjectIdentity):
        self.edit_manager.begin_edit(mobject)

    def end_edit(self, mobject: MobjectIdentity):
        self.edit_manager.end_edit(mobject)

        if self.edit_manager.finished():
            self.manager.set_state(DefaultState(self.manager))
        



class GraphStateManager():

    def __init__(self, graph: DynamicMobjectGraph):
        self.graph = graph
        self.state = DefaultState(self)
        self.progress_manager: Optional[GraphProgressManager] = None
        self.scene_manager = SceneManager.scene_manager()

    def save_source_graph(self, clear_source_target_flags: bool = False):

        if self.progress_manager is None:
            scene_manager = SceneManager.scene_manager()
            self.progress_manager = GraphProgressManager(self.graph, scene_manager.scene)

        self.progress_manager.save_source_graph(clear_source_target_flags=clear_source_target_flags)
    
    def save_target_graph(self):
        self.progress_manager.save_target_graph()

    def has_progress_manager(self):
        return self.progress_manager is not None
    
    
    def require_default_if_transform(self):
        if isinstance(self.state, (TransformState, ProgressToEmpty)):
            self.set_state(DefaultState(self))

    def __deepcopy__(self, memo):
        raise Exception()
    
    def set_state(self, state: GraphStateInterface):
        self.state.end()
        self.state = state
        self.state.begin()

    def begin_edit(self, mobject: MobjectIdentity):
        self.state.begin_edit(mobject)

    def end_edit(self, mobject: MobjectIdentity):
        self.state.end_edit(mobject)

    def accept_transform_manager(
        self,
        transform_manager: AbstractDynamicTransformManager
    ):
        return self.state.accept_transform_manager(transform_manager)
            
    def require_default(self):
        self.state.require_default()

    def scene_add(self, mobject: MobjectIdentity):
        self.state.scene_add(mobject)
        
    def scene_wait(self):
        self.state.scene_wait()
    
    def scene_remove(self, mobject: MobjectIdentity):
        self.state.scene_remove(mobject)


    def construct_remover_animation(self, mobject: MobjectIdentity):
        self.state.construct_remover_animation(mobject)

    def construct_introducer_animation(self, mobject: MobjectIdentity):
        self.state.construct_introducer_animation(mobject)

    
class DynamicMobjectGraph(Mobject):

    def manager(self) -> GraphStateManager:
        scene_manager = SceneManager.scene_manager()
        return scene_manager.graph_managers[self]
        
    def create_manager(self):
        scene_manager = SceneManager.scene_manager()
        scene_manager.graph_managers[self] = GraphStateManager(self)

    def set_auto_disconnect_memory(self):
        self.auto_disconnect_memory = {}
        self.add_auto_disconnect_memory()

    def add_auto_disconnect_memory(self):
        for mobject in self.mobjects:
            self.auto_disconnect_memory[mobject] = (
                mobject.current_dynamic_mobject.id, 
                mobject.current_dynamic_mobject.source_id, 
                mobject.current_dynamic_mobject.target_id
            )
                    

    def __init__(self):
        super().__init__()
        graph_references.append(self)
        self.root_mobjects: Set[MobjectIdentity] = []
        self.create_manager()

        self.auto_disconnect_memory: Dict[MobjectIdentity, Tuple[UUID, UUID, UUID]] = {}


    @property
    def mobjects(self) -> List[MobjectIdentity]:
        mobjects: Set[MobjectIdentity] = set()

        for root_mobject in self.root_mobjects:
            connected_mobjects = self.connected_from_root(root_mobject)
            for mobject in connected_mobjects:
                mobjects.add(mobject)
        
        return list(mobjects)

    def root_dynamic_mobjects(self):
        return [ mobject.current_dynamic_mobject for mobject in self.root_mobjects ]

    @property
    def dynamic_mobjects(self) -> List[DynamicMobject]:
        return [ mobject.current_dynamic_mobject for mobject in self.mobjects ]
    
    def contains(self, id: UUID) -> bool:
        for mobject in self.dynamic_mobjects:
            if mobject.id == id:
                return True
            
        return False
    
    def find_dynamic_mobject(self, id: UUID) -> DynamicMobject | None:
        for mobject in self.dynamic_mobjects:
            if mobject.id == id:
                return mobject
            
        return None

    def __getitem__(self, id):

        for mobject in self.mobjects:
            if mobject.id == id:
                return mobject
        
        raise Exception(f"No mobject with id={id} found in graph")
    
    def get_dynamic_mobject(self, id: UUID) -> DynamicMobject:

        mobject = self.find_dynamic_mobject(id)

        if mobject is None:
            raise Exception(f"No mobject with id {id} found in graph")
        
        return mobject
    
    @staticmethod
    def connected_from_root(root_mobject: MobjectIdentity) -> Set[MobjectIdentity]:
        mobjects: Set[MobjectIdentity] = set()

        def recursive_extract(mobject: MobjectIdentity):
            mobjects.add(mobject)
            for child in mobject.children:
                recursive_extract(child)

        recursive_extract(root_mobject)
        return mobjects
    
    def __deepcopy__(self, memo):

        """
        if graph.copy(), then memo will not return, construct new graph, and copy root_mobjects using override,
        so that for each root_mobject.__deepcopy__ it will not attempt to construct a new graph by the copy-selected-node process
        """

        if memo.get("override"):
            return memo["graph"] 
            # this will not occur in the current implementation, since deep-copying a DynamicMobject will not traverse any direct graph-references
            # if graph.__deepcopy__() is called, therefore, it must be from a graph.copy() call since dynamic_mobject.copy() will not reach the graph
        
        copy_graph = DynamicMobjectGraph()
        copy_root_mobjects = copy.deepcopy(self.root_mobjects, memo={ "override": True })
        copy_graph.root_mobjects = copy_root_mobjects
        return copy_graph

    def copy(self) -> DynamicMobjectGraph:
        copy_graph = copy.deepcopy(self)
        copy_graph.create_manager()
        return copy_graph
    
    def set_root_mobjects(self, root_mobjects: Set[MobjectIdentity]):

        for next_root in root_mobjects:
            if next_root.parent is not None:
                raise Exception(
                    f"Attempted set_root_mobjects` call on mobject {next_root}, that is a child of mobject {next_root.parent}."
                    "A root mobject cannot have another mobject as its parent."
                )

        for curr_root in self.root_mobjects.copy():
            if curr_root not in root_mobjects:

                self.root_mobjects.remove(curr_root)
                
                graph = DynamicMobjectGraph()
                graph.root_mobjects = { curr_root }
                
                #curr_root.graph = graph
        
        for next_root in root_mobjects:
            if next_root not in self.root_mobjects:
                
                next_root.graph.root_mobjects.remove(next_root)

                self.root_mobjects.add(next_root)

                #next_root.graph = self

    def set_root(self, mobject: MobjectIdentity):
        self.set_root_mobjects({ mobject })

    def add_root(self, mobject: MobjectIdentity):
        self.set_root_mobjects({ *self.root_mobjects, mobject })

    def remove_root(self, mobject: MobjectIdentity):
        next_root_mobjects = self.root_mobjects.copy()
        next_root_mobjects.remove(mobject)
        self.set_root_mobjects(next_root_mobjects)
        

    

    def connect_parent_child(self, parent: MobjectIdentity, child: MobjectIdentity):  

        graph1 = parent.graph
        graph2 = child.graph

        """
        if graph1 is graph2:
            graph1.root_mobjects.remove(child) ###
            child.graph = None
        else: """
        if graph1 is not graph2:
            root_connected_mobjects1 = graph1.mobjects
            root_connected_mobjects2 = graph2.mobjects

            

            m = {}
            for mobject in root_connected_mobjects1:
                m[mobject.id] = mobject

            def auto_disconnect_check(new_mobject):
        
                if new_mobject.id in m:
                    if self in [ f() for f in new_mobject.tracked_graphs ]:
                        new_mobject.current_dynamic_mobject.source_id = new_mobject.id
                        new_mobject.tracked_graphs = [ ]
                    new_mobject.current_dynamic_mobject.id = uuid.uuid4()
                else:
                    progress_manager = self.manager().progress_manager
                    if progress_manager is not None:
                        if new_mobject.id in progress_manager.source_mobjects:
                            progress_manager.source_mobjects[new_mobject.id] = new_mobject

            for mobject in root_connected_mobjects2:
                auto_disconnect_check(mobject)
                continue
                if mobject.id in m:
                    raise Exception(
                        "Mobject graph cannot contain duplicate ids."
                        "Use mobject.clone() instead of mobject.copy() for duplication."
                    )
            
            graph2_root_mobjects = graph2.root_mobjects.copy()
            graph2.root_mobjects = set()
            graph1.root_mobjects = graph1.root_mobjects.union(graph2_root_mobjects)

        if child in graph1.root_mobjects:
            graph1.root_mobjects.remove(child) ###
            #child.graph = None
        
        parent.children.add(child)
        child.parent = parent

        for mobject in self.connected_from_root(child):
            mobject.tracked_graphs.append(lambda: self)
        

        



    def disconnect_parent_child(self, parent: MobjectIdentity, child: MobjectIdentity):

        parent.children.remove(child)
        child.parent = None

        graph = DynamicMobjectGraph()
        graph.root_mobjects = { child }
        #child.graph = graph


class AutoDisconnectPacket():

    def __init__(
        self,
        current_parent: MobjectIdentity,
        next_parent: MobjectIdentity,
        child: MobjectIdentity,
        child_clone: MobjectIdentity
    ):
        self.current_parent = current_parent
        self.next_parent = next_parent
        self.child = child
        self.child_clone = child_clone

    def extract(self):
        return (self.current_parent, self.next_parent, self.child, self.child_clone)
    

class GraphEditManager():

    def __init__(
        self,
        graph, 
        primary_mobject: MobjectIdentity
    ):
        self.graph = graph
        self.primary_mobject = primary_mobject
        self.invalidation_lock = False

        self.auto_disconnect_queue: List[AutoDisconnectPacket] = []
        self.auto_disconnect_same_graph_parents: List[MobjectIdentity] = []

        self.composite_stack: List[MobjectIdentity] = []
        self.composite_queue: List[MobjectIdentity] = []
        self.composite_depth: Dict[MobjectIdentity, int] = {}

    def finished(self):
        return empty(self.composite_stack)

    def begin_edit(self, mobject: MobjectIdentity):
        self.register_composite(mobject)

    def end_edit(self, mobject: MobjectIdentity):

        back_mobject = self.composite_stack.pop()

        if (back_mobject is not mobject) or (empty(self.composite_stack) and back_mobject is not self.primary_mobject):
            raise Exception() # this should never happen

        if empty(self.composite_stack):
            self.process_composites()
            self.process_primary_mobject()
        
    def register_composite(self, mobject: MobjectIdentity):
        self.composite_stack.append(mobject)
        self.composite_queue.append(mobject)
        self.composite_depth[mobject] = len(self.composite_stack)

    def execute_invalidation(self, mobject: MobjectIdentity, propagate: bool, permit_auto_disconnects: bool):
        self.invalidation_lock = True
        mobject.invalidate(propagate=propagate, permit_auto_disconnects=permit_auto_disconnects)
        self.invalidation_lock = False

    def sort_composite_queue(self):
        return sorted(set(self.composite_queue), key=lambda mobject: self.composite_depth[mobject], reverse=True)
    
    def process_composites(self):

        for mobject in self.sort_composite_queue():
            if mobject is not self.primary_mobject:

                self.execute_invalidation(mobject, propagate=False, permit_auto_disconnects=False)

                if len(self.auto_disconnect_queue) > 0:
                    raise Exception("Auto-disconnect is not supported inside nested-level composite-edits")
        
    def process_primary_mobject(self):
        self.execute_invalidation(self.primary_mobject, propagate=True, permit_auto_disconnects=True) # first invalidation-pass yields auto-disconnects
        self.process_auto_disconnects()

    def queue_auto_disconnect(self, packet: AutoDisconnectPacket):
        self.auto_disconnect_queue.append(packet)

    def process_auto_disconnects(self):

        for packet in self.auto_disconnect_queue:
            self.process_auto_disconnect(packet) # may yiled same-graph-parent for invalidation 
        
        for mobject in self.auto_disconnect_same_graph_parents:
            self.execute_invalidation(mobject, propagate=True, permit_auto_disconnects=False)

        self.execute_invalidation(self.primary_mobject, propagate=True, permit_auto_disconnects=False)

    def process_auto_disconnect(self, packet: AutoDisconnectPacket):
        
        (current_parent, next_parent, child, child_clone) = packet.extract()

        #print((child.parent is not current_parent) , child_clone.parent is not next_parent, next_parent is not self.primary_mobject)

        if (child.parent is not current_parent) or (child_clone.parent is not next_parent) or (next_parent is not self.primary_mobject):
            raise Exception()

        if current_parent is None or next_parent is None or child is None or child_clone is None:
            raise Exception()
        
        if current_parent.graph is self.graph:
            clone_dynamic_mobject = child.current_dynamic_mobject.clone()

            current_parent.change_parent_mobject = child
            current_parent.change_parent_mobject_replacement = clone_dynamic_mobject.identity

            self.execute_invalidation(current_parent, propagate=False, permit_auto_disconnects=False)
            self.auto_disconnect_same_graph_parents.append(current_parent)
        else:
            child_replacement = child.current_dynamic_mobject.clone()
            clone_dynamic_mobject = child_replacement

          
            current_parent.current_dynamic_mobject.replace(child.current_dynamic_mobject, child_replacement)

            if child.graph is current_parent.graph:
                raise Exception()


        if child.graph is current_parent.graph:
            raise Exception()
        
        if child.graph is self.primary_mobject.graph:
            raise Exception()

        if child.graph is current_parent.graph or child.graph is self.primary_mobject.graph:
            raise Exception()
        

        self.primary_mobject.change_parent_mobject = child_clone
        self.primary_mobject.change_parent_mobject_replacement = child.current_dynamic_mobject.identity
        self.execute_invalidation(self.primary_mobject, propagate=False, permit_auto_disconnects=False)


        dynamic_mobject = child.current_dynamic_mobject

        #clone_dynamic_mobject.id, dynamic_mobject.id = dynamic_mobject.id, clone_dynamic_mobject.id
        #clone_dynamic_mobject.source_id, dynamic_mobject.source_id = dynamic_mobject.source_id, clone_dynamic_mobject.source_id
        #clone_dynamic_mobject.target_id, dynamic_mobject.target_id = dynamic_mobject.target_id, clone_dynamic_mobject.target_id


        # want to make it so dynamic_mobject (or child) looks like the clone
        # 

        mobject1 = clone_dynamic_mobject
        mobject2 = dynamic_mobject

        pairs = []
        
        for m1 in mobject1.get_dynamic_family():
            for m2 in mobject2.get_dynamic_family():
                if m1.source_id == m2.id:
                    pairs.append((m1, m2))

        for (m1, m2) in pairs:
            m1.reactive_lock = True
            m2.reactive_lock = True

            m1.id = m2.id
            m1.source_id = m2.source_id
            m1.target_id = m2.target_id
            #m1.id, m2.id = m2.id, m1.id
            #m1.source_id, m2.source_id = m2.source_id, m1.source_id
            #m1.target_id, m2.target_id = m2.target_id, m1.target_id

            m1.reactive_lock = False
            m2.reactive_lock = False

        # replace_source_mobject
        for (m1, m2) in pairs:
            m1 = m1.identity
            m2 = m2.identity
            
            for graph_manager in SceneManager.scene_manager().graph_managers.values():
                progress_manager = graph_manager.progress_manager
                if progress_manager is not None:
                    for idm, source_mobject in progress_manager.source_mobjects.items():
                        if source_mobject is m2:
                            progress_manager.source_mobjects[idm] = m1
        



class MobjectIdentity():

    def __init__(
        self, 
        mobject: DynamicMobject,
        construct_graph: bool
    ):
        super().__init__()
        self.id = uuid.uuid4()
        self.source_ids: List[UUID] = []
        self.target_ids: List[UUID] = [] 
        self.parent: MobjectIdentity | None = None
        self.children: Set[MobjectIdentity] = set()

        self.tracked_graphs = []
        
        if construct_graph:
            #self.mobject_graph: DynamicMobjectGraph | None = None
            #self.mobject_graph = DynamicMobjectGraph()
            mobject_graph = DynamicMobjectGraph()
            mobject_graph.root_mobjects = { self }
            self.tracked_graphs.append(lambda: mobject_graph)
            #self.mobject_graph.root_mobjects = { self }

        self.current: DynamicMobject | None = mobject
        self.mobject_center = VMobject().get_center()

        self._change_parent_mobject: MobjectIdentity | None = None
        self._change_parent_mobject_replacement: MobjectIdentity | None = None
        self._replace_mobject: DynamicMobject | None = None
        self._replace_mobject_replacement: DynamicMobject | None = None 
        self.override_permit_auto_disconnects = False

    @property
    def change_parent_mobject(self):
        return self._change_parent_mobject
    
    @change_parent_mobject.setter
    def change_parent_mobject(self, mi):
        if isinstance(mi, DynamicMobject):
            raise Exception()
        self._change_parent_mobject = mi

    @property
    def change_parent_mobject_replacement(self):
        return self._change_parent_mobject_replacement
    
    @change_parent_mobject_replacement.setter
    def change_parent_mobject_replacement(self, mi):
        if isinstance(mi, DynamicMobject):
            raise Exception()
        self._change_parent_mobject_replacement = mi

    def descendants(self) -> List[MobjectIdentity]:
        descendants: List[MobjectIdentity] = []

        def recursive_extract(mobject: MobjectIdentity):
            descendants.append(mobject)
            for child in mobject.children:
                recursive_extract(child)

        return descendants

    @property
    def current_dynamic_mobject(self) -> DynamicMobject:
        if self.current is not None:
            return self.current
        raise Exception()
    
    @current_dynamic_mobject.setter
    def current_dynamic_mobject(self, mobject: DynamicMobject):
        self.current = mobject
   
    @property
    def root_parent(self) -> MobjectIdentity:
        if self.parent is not None:
            return self.parent.root_parent
        else:
            return self
    
    def is_root(self) -> bool:
        return self.root_parent is self
    
    @property
    def graph(self) -> DynamicMobjectGraph:

        root_parent = self.root_parent #.mobject_graph
        scene_manager = SceneManager.scene_manager()
        graph = scene_manager.graph_of_root_mobject(root_parent)
        return graph

    """
    @graph.setter
    def graph(self, graph: DynamicMobjectGraph):
        if self.root_parent is not self:
            raise Exception()
        self.mobject_graph = graph
    """

    def set_dynamic_mobject(self, mobject: DynamicMobject):

        if mobject.mobject_identity is not None and mobject.mobject_identity is not self:
            raise Exception()
        
        """
        So, begin_state_invalidation SAVE_CENTERS must be called prior to setting the new dynamic-mobject? 
        If GraphInvalidationManager.begin_entrance_invalidation() does SAVE_CENTERS, 
        then by that point, the Mi already has a new DM with a new center? 
        """
        
        self.current = mobject
        self.current.mobject_identity = self

    def complete_child_registration(self):
        self.set_children(self.next_children)

    def invalidate(self, propagate=True, permit_auto_disconnects=True):
        
        # this is to handle tex1 = Tex(a); tex2 = Tex(a, a, a), where the 2nd and 3rd `a` need to return a clone without queing an auto-disconnect
        # in this new 0.0.2 invalidation system, the 1st `a` return a.clone() while queueing an auto-disconnect, so `a` is not yet in next_children
        # so we need the next_from_auto_disconnect to know that we need to return clones for the 2nd and 3rd `a`.
        self.next_from_auto_disconnect = set()

        self.permit_auto_disconnects = permit_auto_disconnects
        self.next_children: List[MobjectIdentity] = []
        self.current_dynamic_mobject.execute_compose()

        """
        dynmaic_mobject.execute_compose() runs compose() which adds children to next_children
        dynamic_mobject.execute_compose() then runs complete_child_registration() prior to returning
        this process enables for downscaling ManimMatrix in e^ManimMatrix, 
        since ManimMatrix, upon accepting new submobjects, will have the information that,
        ManimMatrix.parent = Term and Term.superscript = ManimMatrix
        """

        if propagate:
            self.invalidate_parent()
        
    def invalidate_parent(self):
        if self.parent is not None:
            self.parent.invalidate(propagate=True, permit_auto_disconnects=False)
        else:
            pass

    def pre_conditional_clone(self, mobject: DynamicMobject) -> DynamicMobject:
        
        # this swaps out curr with next, 
        # if next is reserved, the next is replaced with next.clone() until auto-disconnect-queue

        if mobject is self._replace_mobject:
            replacement = self._replace_mobject_replacement
            self._replace_mobject = None
            self._replace_mobject_replacement = None
            return replacement
        
        return mobject


    
    def conditional_clone(self, mobject: DynamicMobject) -> DynamicMobject:

        if mobject.identity in self.next_children or mobject.identity in self.next_from_auto_disconnect:
            return mobject.clone()
        
        
        #if mobject.identity.parent is not None and mobject.identity.parent is self:
        #    raise Exception("CAN THIS HAPPEN?")
        # yes, because while every mobject a graph, not every mobject has a parent. 
        
        # mobject has another parent
        if mobject.identity.parent is not None and mobject.identity.parent is not self:
            
            self.next_from_auto_disconnect.add(mobject.identity)

            if not self.permit_auto_disconnects or self.override_permit_auto_disconnects:
                raise Exception(f"Inval {self.current_dynamic_mobject}-{self.id},  {mobject}-{mobject.id} has parent {mobject.parent}-{mobject.parent.id}")

            clone = mobject.clone()
            
            self.graph.manager().state.edit_manager.queue_auto_disconnect(
                AutoDisconnectPacket(current_parent=mobject.identity.parent, next_parent=self, child=mobject.identity, child_clone=clone.identity)
            )
            return clone
        
        if mobject.identity is self.change_parent_mobject:
            replacement = self.change_parent_mobject_replacement.current_dynamic_mobject
            self.change_parent_mobject = None
            self.change_parent_mobject_replacement = None
            return replacement

        
        return mobject

    def register_child(self, mobject: Mobject):

        if isinstance(mobject, DynamicMobject):
            mobject = self.pre_conditional_clone(mobject)
            mobject = self.conditional_clone(mobject)
            self.next_children.append(mobject.identity)
            mobject = mobject.identity.current_dynamic_mobject
        
        return mobject
    
    def set_children(self, next_children: List[MobjectIdentity]):
        
        for identity in self.children.copy():
            if identity not in next_children:
                MobjectIdentity.remove_parent_connection(parent=self, child=identity)

        for identity in next_children:
            if identity not in self.children.copy():
                MobjectIdentity.add_parent_connection(parent=self, child=identity)
            
    @staticmethod
    def add_parent_connection(parent: MobjectIdentity, child: MobjectIdentity):
        parent.graph.connect_parent_child(parent, child)
    
    @staticmethod
    def remove_parent_connection(parent: MobjectIdentity, child: MobjectIdentity):
        parent.graph.disconnect_parent_child(parent, child)

    def __str__(self) -> str:
        return f"{self.current_dynamic_mobject}-{str(self.id).split('-')[0]}"


MobjectType = TypeVar("MobjectType")
DynamicMobjectType = TypeVar("DynamicMobjectType")

class DynamicMobjectSubgraph(VMobject):

    @property
    def dynamic_mobjects(self) -> List[DynamicMobject]:
        return [ mobject.current_dynamic_mobject for mobject in self.mobjects ]

    def __init__(self, *dynamic_mobjects: DynamicMobject, graph: DynamicMobjectGraph | None = None):

        if not dynamic_mobjects and graph is None:
            raise Exception()
        
        if graph is None:
            graph = dynamic_mobjects[0].graph
        
        #for mobject in dynamic_mobjects:
        #    if mobject.graph is not graph:
        #        raise Exception()
        
        self.mobjects: List[MobjectIdentity] = [ mobject.identity for mobject in dynamic_mobjects ]
        self.graph = graph
        super().__init__()
        self.submobjects = [ mobject.direct_submobjects() for mobject in self.dynamic_mobjects ]

    def contains(self, id: UUID):
        for mobject in self.mobjects:
            if mobject.id == id:
                return True
        
        return False

    def find_dynamic_mobject(self, id: UUID) -> DynamicMobject:
        if not self.contains(id):
            return None
        else:
            return self.graph.find_dynamic_mobject(id)
        
    def get_dynamic_mobject(self, id: UUID) -> DynamicMobject:
        if not self.contains(id):
            raise Exception(f"No mobject with id {id} found in subgraph")
        else:
            return self.graph.find_dynamic_mobject(id)

    @staticmethod
    def from_adapt(mobject: Mobject) -> DynamicMobjectSubgraph:
        
        if not isinstance(mobject, DynamicMobjectSubgraph):
            if not isinstance(mobject, DynamicMobject):
                raise Exception()

            mobject = DynamicMobjectSubgraph.from_dynamic_mobject(mobject)

        return mobject
    
    @classmethod
    def from_dynamic_mobject(cls, mobject: DynamicMobject) -> DynamicMobjectSubgraph:
        return cls(*mobject.get_dynamic_family())
    
    def __sub__(self, mobject: Mobject) -> DynamicMobjectSubgraph:
        subgraph = DynamicMobjectSubgraph.from_adapt(mobject)
        dynamic_mobjects = set(self.dynamic_mobjects).difference(set(subgraph.dynamic_mobjects))
        return DynamicMobjectSubgraph(*dynamic_mobjects)

    def __add__(self, mobject: Mobject) -> DynamicMobjectSubgraph:
        subgraph = DynamicMobjectSubgraph.from_adapt(mobject)
        dynamic_mobjects = set(self.dynamic_mobjects).union(set(subgraph.dynamic_mobjects))
        return DynamicMobjectSubgraph(*dynamic_mobjects)



class DynamicMobject(VMobject):

    def __init__(
        self,
        id: UUID | None = None, 
        construct_graph: bool = True,
        scale_factor = 1,
        **kwargs
    ):
        self.shift_flag = False
        self.scale_flag = False
        self.scale_factor = scale_factor
        self.position_factor = VMobject().get_center()

        self._save_x: float | None = None
        self._save_y: float | None = None
        self.arrange_function = None

        self.reactive_lock = False
        self.super_init = True
        super().__init__(**kwargs)
        self.super_init = False

        self.mobject_identity: MobjectIdentity | None = None
        self.mobject_identity = MobjectIdentity(self, construct_graph=construct_graph)

        if id is not None:
            self.identity.id = id

        if construct_graph:
            self.begin_edit()
            self.end_edit()

    def has_graph(self):
        try:
            self.graph
            return True
        except:
            return False

    def invalidation_lock(self):
        
        try:
            state = self.graph.manager().state
            if isinstance(state, EditState):
                edit_manager = state.edit_manager
                return edit_manager.invalidation_lock
        except:
            # in partial construction for .become() a DM/Mi setup may not have a graph
            return False
        
        return False
    
    def execute_compose(self):
        
        self.in_compose = True
        self.shift_during_compose_flag = False
        self.scale_during_compose_flag = False

        mobject_encoding = self.compose()
        self.identity.complete_child_registration()
        self.in_compose = False

        if mobject_encoding:
            if isinstance(mobject_encoding, list):
                self.submobjects = mobject_encoding
            elif isinstance(mobject_encoding, Mobject):
                self.submobjects = [ mobject_encoding ]
            else:
                raise TypeError(
                    f"{self.__class__.__name__}.compose() returned unsupported type {type(mobject_encoding)}"
                )
        
        if not self.scale_during_compose_flag:
            self.restore_scale()

        """
        if self.parent is None:
            if not self.shift_during_compose_flag:
                self.move_to(self.identity.mobject_center) """
        
        if self.arrange_function is not None:
            self.arrange_function(VGroup(*self.submobjects))
        
        if not self.shift_during_compose_flag:
            self.move_to(self.identity.mobject_center) 
            
    @abstractmethod
    def compose(self) -> None | Mobject | List[Mobject]:
        pass
    
    def is_current_dynamic_mobject_guard(self):
        if self.identity.current_dynamic_mobject is not self:
            raise Exception(
                f"Cannot modify former handle for mobject-${self.identity.id}"
                f"which has currently represented by {self.identity.current_dynamic_mobject}"
            )
        
    def manager(self) -> GraphStateManager:
        return self.identity.graph.manager()

    def begin_edit(self):

        if self.super_init:
            return
        
        if self.invalidation_lock():
            return

        if self.reactive_lock:
            return
        
        if not self.has_graph():
            return

        #if self.graph.manager.in_invalidation:
        #    raise Exception()
        
        self.is_current_dynamic_mobject_guard()
        self.manager().begin_edit(self.identity)

    def end_edit(self): 

        if self.super_init:
            return
        
        if self.reactive_lock:
            return
        
        if self.invalidation_lock():
            return
        
        if not self.has_graph():
            return

        #but can't invalidate trigger compose
        #if self.graph.edit_manager.in_invalidation:
        #    raise Exception()


        #self.identity.set_dynamic_mobject(self)
        self.manager().end_edit(self.identity)


    def invalidate(self) -> Self:

        raise Exception(
            f"component.invalidate() is deprecated, please switch to",
            f"",
            f"@reactive",
            f"def component_method(self):`",
        )

    def restore_scale(self):
        super().scale(self.scale_factor)

    def accept_submobjects(self, *mobject: Mobject):
        self.submobjects = [ *mobject ]

    @reactive
    def replace(self, current: DynamicMobject, next: DynamicMobject):

        m = { child.id: child for child in self.children }
        
        if current.id not in m:
            raise Exception("In mobject.replace(m1, m2), m1 must be a child of mobject")
        

        self.identity._replace_mobject = m[current.id]
        self.identity._replace_mobject_replacement = next

    def interchange(self, next: DynamicMobject | Callable[[], DynamicMobject]) -> DynamicMobject:

        if isinstance(next, DynamicMobject):
            self.parent.replace(self, next)
        else:
            parent = self.parent
            next = next()
            parent.replace(self, next)

        return next

    def clear_tracking(self) -> Self:
        for mobject in self.get_dynamic_family():
            mobject.source_id = None
            mobject.target_id = None
        
            mobject.identity.tracked_graphs = []
        return self
    def merge(self, other: DynamicMobject):

        def extract_direct_dynamic_mobjects(dm, arr):
            for subm in dm.submobjects:

                is_dm = isinstance(subm, DynamicMobject)
                is_mt = hasattr(subm, "math_tex_flag")

                if is_dm and not is_mt:
                    arr.append(subm)
                else:
                    extract_direct_dynamic_mobjects(subm, arr)
            return arr

        def recursive_extract(dm1, dm2):
            dm2.target_id = dm1.id

            direct1 = extract_direct_dynamic_mobjects(dm1, [])
            direct2 = extract_direct_dynamic_mobjects(dm2, [])

            print("-")
            print(f"comparison on {dm1.__class__.__name__} vs {dm2.__class__.__name__}, with id {dm1.id} vs {dm2.id}")
            print("direct1 ", [ (x, hasattr(x, "math_tex_flag")) for x in direct1 ])
            print("direct2 ", [ (x, hasattr(x, "math_tex_flag")) for x in direct2 ])
            
            print([ f"{x.id}-vs-{y.id}" for (x, y) in zip(direct1, direct2) ])
            print("-")

            if len(direct1) != len(direct2):
                raise Exception(" requires both mobjects to have same tree-structure")

            for s1, s2 in zip(direct1, direct2):
                recursive_extract(s1, s2)

        recursive_extract(self, other)
    """
    def merge_structure(self, other: DynamicMobject):

        def extract_direct_dynamic_mobjects(dm, arr):
            for subm in dm.submobjects:
                if isinstance(subm, DynamicMobject) and not hasattr(dm, "math_tex_flag"):
                    arr.append(subm)                                ^
                else:
                    extract_direct_dynamic_mobjects(subm, arr)
            return arr

        def recursive_extract(dm1, dm2):
            dm2.target_id = dm1.id

            direct1 = extract_direct_dynamic_mobjects(dm1, [])
            direct2 = extract_direct_dynamic_mobjects(dm2, [])

            print("-")
            print(f"comparison on {dm1.__class__.__name__} vs {dm2.__class__.__name__}, with id {dm1.id} vs {dm2.id}")
            print([ f"{x.id}-vs-{y.id}" for (x, y) in zip(direct1, direct2) ])
            print("-")

            if len(direct1) != len(direct2):
                raise Exception("merge_structure requires both mobjects to have same tree-structure")

            for s1, s2 in zip(direct1, direct2):
                recursive_extract(s1, s2)

        #def recursive_extract(dm1, dm2):
        #    
        #    if isinstance(dm1, DynamicMobject):
        #        dm2.target_id = dm1.id
        #
        #    if len(dm1.submobjects) != len(dm2.submobjects):
        #        raise Exception("merge_structure requires both mobjects to have same tree-structure")
        #
        #    for s1, s2 in zip(dm1.submobjects, dm2.submobjects):
        #        recursive_extract(s1, s2)

        recursive_extract(self, other)
    """
    def pop(self):
        self.parent.remove(self)
        return self

    @abstractmethod
    def remove(self, mobject: DynamicMobject):
        raise NotImplementedError()

    def __add__(self, mobject: Mobject) -> DynamicMobjectSubgraph:
        return DynamicMobjectSubgraph.from_dynamic_mobject(self) + mobject
    
    def __sub__(self, mobject: Mobject) -> DynamicMobjectSubgraph:
        return DynamicMobjectSubgraph.from_dynamic_mobject(self) - mobject
    
    def subgraph(self) -> DynamicMobjectSubgraph:
        return DynamicMobjectSubgraph.from_dynamic_mobject(self)

    def direct_submobjects(self) -> Mobject:
        
        def recursive_extract(mobject: Mobject, group: Mobject):

            for submobject in mobject.submobjects:
                if not isinstance(submobject, DynamicMobject):
                    if submobject.has_points():
                        group.add(submobject)
                    else:
                        subgroup = VGroup()
                        recursive_extract(submobject, subgroup)
                        group.add(subgroup)

        group = VGroup()
        recursive_extract(self, group)
        return group

    def get_point_dynamic_mobject(self):
        
        mobject_copy = self.copy()
        center = self.get_center()

        def convert_to_point_mobject(mobject: Mobject):

            def recursive_extract(mobject: Mobject, group):

                for submobject in mobject.submobjects:
                    if submobject.has_points():
                        point_mobject = submobject.get_point_mobject()
                        group.add(point_mobject)
                    else:
                        subgroup = VGroup()
                        recursive_extract(submobject, subgroup)
                        group.add(subgroup)

            group = VGroup()
            recursive_extract(mobject, group)
            return group

        def recursive_extract(mobject: DynamicMobject) -> DynamicMobject:

            direct = convert_to_point_mobject(mobject.direct_submobjects())

            mobject = mobject.become(
                DGroup(direct, *mobject.children)
            )

            for child in mobject.children:
                recursive_extract(child)

            return mobject

        mobject_copy = recursive_extract(mobject_copy)

        restore_submobjects = {}

        for mobject in set(mobject_copy.get_family()):
            restore_submobjects[mobject] = mobject.submobjects
            mobject.submobjects = []
            mobject.move_to(center)
        
        for mobject, submobjects in restore_submobjects.items():
            mobject.submobjects = submobjects

        return mobject_copy

    def has_direct_points(self):
        for mobject in self.direct_submobjects().get_family():
            if mobject.has_points():
                return True
        return False

    def __deepcopy__(self, memo):

        if memo.get("override"):
            return super().__deepcopy__(memo)
            # a recursive_descendant of selected_mobject.copy()
            # or in case of graph.copy(), the graph-linkage is done at the graph-level for each root-mobject

        parent = self.mobject_identity.parent
        self.mobject_identity.parent = None
        copy_mobject = copy.deepcopy(self, memo={ "override": True })
        self.mobject_identity.parent = parent

        copy_graph = DynamicMobjectGraph()
        copy_graph.root_mobjects = { copy_mobject.identity }
        return copy_mobject
        
    def clone(self) -> DynamicMobject:
        copy_mobject = self.copy()

        for mobject in copy_mobject.get_dynamic_family():
            mobject.reactive_lock = True
            mobject.source_id = mobject.id
            mobject.reactive_lock = False
            mobject.id = uuid.uuid4()

        return copy_mobject

    def get_dynamic_family(self) -> List[DynamicMobject]:
        family: Set[DynamicMobject] = set()

        def recursive_extract(mobject: DynamicMobject):
            family.add(mobject)
            for child in mobject.children:
                recursive_extract(child)

        recursive_extract(self)
        return list(family)
    
    def shift(self, *vectors) -> Self:

        self.manager().require_default_if_transform()
        super().shift(*vectors)

        # begin_edit() causes save-mobject-centers, which restores mobject-centers after shift?
        
        if self.in_compose:
            self.shift_during_compose_flag = True

        self.begin_edit()
        self.end_edit()

        return self

    @reactive
    def scale(self, scale_factor: float, **kwargs) -> Self:
        self.scale_factor *= scale_factor
        super().scale(self.scale_factor, **kwargs)
        return self
    
    def register_child(self, mobject: DynamicMobject) -> DynamicMobject:
        return self.identity.register_child(mobject)
    
    @reactive
    def save_x(self):
        self._save_x = self.get_x()

    @reactive
    def save_y(self):
        self._save_y = self.get_y()

    @reactive
    def save_center(self):
        self.save_x()
        self.save_y()

    #@reactive
    def restore_x(self, propagate=True):
        
        self.manager().require_default_if_transform()

        factor = self._save_x - self.get_x()
        if propagate:
            self.root_parent.shift(np.array([ factor, 0, 0 ]))
        else:
            self.shift(np.array([ factor, 0, 0 ]))

        self.begin_edit()
        self.end_edit()
        return self
    
    #@reactive
    def restore_y(self, propagate=True) -> DynamicMobject:

        self.manager().require_default_if_transform()


        factor = self._save_y - self.get_y()
        if propagate:
            self.root_parent.shift(np.array([ 0, factor, 0 ]))
        else:
            self.shift(np.array([ 0, factor, 0 ]))

        self.begin_edit()
        self.end_edit()
        return self
    
    #@reactive
    def restore_center(self, propagate=True):
        self.restore_x(propagate)
        self.restore_y(propagate)

    @property
    def identity(self) -> MobjectIdentity:
        if self.mobject_identity is not None:
            return self.mobject_identity
        
        raise Exception()
    
    @property
    def parent(self) -> DynamicMobject | None:
        if self.identity.parent is not None:
            return self.identity.parent.current_dynamic_mobject
        
        return None
    
    @property
    def children(self) -> List[DynamicMobject]:
        if self.mobject_identity is None:
            raise Exception("MI IS NONE")
        
        if not isinstance(self.mobject_identity.children, set):
            raise Exception("NOT SET")
        return [ identity.current_dynamic_mobject for identity in self.mobject_identity.children ]

    @property
    def root_parent(self) -> DynamicMobject:
        return self.identity.root_parent.current_dynamic_mobject
    
    def is_root(self):
        return self.identity.is_root()

    @property
    def id(self) -> UUID:
        try:
            return self.identity.id
        except:
            raise Exception(type(self), " has not identity")
    
    @id.setter
    def id(self, id: UUID):
        self.identity.id = id

    @property
    def source_id(self) -> UUID | None:
        if not self.identity.source_ids:
            return None
        
        return self.identity.source_ids[-1]
    
    @source_id.setter
    @reactive
    def source_id(self, id: UUID):
        self.identity.source_ids.append(id)

    @property
    def target_id(self) -> UUID | None:
        if not self.identity.target_ids:
            return None
        
        return self.identity.target_ids[-1]
    
    @target_id.setter
    @reactive
    def target_id(self, id: UUID):
        self.identity.target_ids.append(id)

    @property
    def graph(self) -> DynamicMobjectGraph:
        return self.identity.graph
    
    @reactive
    def arrange(self, direction = RIGHT, buff = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER, center = True, **kwargs) -> Self:
        self.arrange_function = lambda mobject: mobject.arrange(direction, buff, center, **kwargs)
        return self

    @reactive
    def clear_arrange_function(self):
        self.arrange_function = None

    @reactive
    def set_color(
        self, color: ParsableManimColor = YELLOW_C, family: bool = True
    ) -> Self:

        super().set_color(color=color, family=family)
        return self
    
    @reactive 
    def set_fill(
        self,
        color: ParsableManimColor | None = None,
        opacity: float | None = None,
        family: bool = True,
    ) -> Self:
        
        super().set_fill(color=color, opacity=opacity, family=family)
        return self

    @reactive
    def set_stroke(
        self,
        color: ParsableManimColor = None,
        width: float | None = None,
        opacity: float | None = None,
        background=False,
        family: bool = True,
    ) -> Self:
        
        super().set_stroke(color=color, width=width, opacity=opacity, background=background, family=family)
        return self
        

    

class DGroup(DynamicMobject):

    def __init__(
        self,
        *mobjects: VMobject,
        **kwargs
    ):
        self._mobjects = list(mobjects)
        super().__init__(**kwargs)

    def compose(self):
        self.dynamic_mobjects: Set[DynamicMobject] = set()

        def recursive_extract(mobject):
            for submobject in mobject.submobjects.copy():
                if isinstance(submobject, DynamicMobject):
                    self.dynamic_mobjects.add(submobject)
                else:
                    recursive_extract(submobject)
            
            mobject.submobjects = [ self.register_child(submobject) for submobject in mobject.submobjects ]
        
        group = VGroup(*self._mobjects)
        recursive_extract(group)
        self._mobjects = group.submobjects
        self.submobjects = group.submobjects
    
    @reactive
    def add(self, *mobjects: VMobject) -> Self:

        for m in mobjects:
            if not isinstance(m, Mobject):
                raise TypeError(f"All submobjects must be of type Mobject")
            if m is self:
                raise ValueError("Mobject cannot contain self")

        unique_mobjects = remove_list_redundancies(mobjects)
        if len(mobjects) != len(unique_mobjects):
            logger.warning(
                "Attempted adding some Mobject as a child more than once, "
                "this is not possible. Repetitions are ignored.",
            )

        self._mobjects = list_update(self._mobjects, unique_mobjects)
        return self

    @reactive
    def remove(self, *mobjects: Mobject) -> Self:
        
        for mobject in mobjects:
            if mobject in self._mobjects:
                self._mobjects.remove(mobject)
        
        return self
    
    @property
    def mobjects(self) -> List[Mobject]:
        return self._mobjects

    @mobjects.setter
    @reactive
    def mobjects(self, mobjects: List[Mobject]):
        self._mobjects = mobjects