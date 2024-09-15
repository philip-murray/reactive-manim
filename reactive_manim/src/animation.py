from __future__ import annotations
from abc import abstractmethod
from typing import Dict
from uuid import UUID

from reactive_manim.src.dynamic_mobject import List
from .helpers import *

from manim import Scene
from .manim_src.composition import PreviousAnimationGroup
from .dynamic_mobject import *



class RecoverMobject():

    def __init__(self):
        self.recover_points = {}
        self.recover_submobjects = {}

    def save_recover_point(self, mobject: MobjectIdentity):
        self.recover_points[mobject] = mobject.current_dynamic_mobject.points.copy()
        self.recover_submobjects[mobject] = mobject.current_dynamic_mobject.submobjects.copy()
    
    def recover_mobject(self, mobject: MobjectIdentity):
        mobject.current_dynamic_mobject.points = self.recover_points[mobject]
        mobject.current_dynamic_mobject.submobjects = self.recover_submobjects[mobject]



"""
The DynamicTransformManager (ADTM) is a class that assits with running multiple partial transforms,

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
        self.source_graph = source_graph
        self.target_graph = target_graph
        self.scene_progress_manager = SceneProgressManager.scene_progress_manager()


        self.subscription_id = uuid.uuid4()
        # target-graph is used as graph-of-interest, where
        # invalidation of graph-of-interest is used as a proxy for end_transforms() to reduce user notation

        self.graph = graph
        self.graph.subscribe(lambda: self.end_transforms(), self.subscription_id)
        self.begin_transforms()

    def begin_transforms(self):

        # This is run on the first scene.play(TransformInStages.some_constructor(tex)) in a series of some_constructor-partial-transforms
        
        self.transform_observers = self.observers()
        self.save_recover_point()
        self.revert_mobjects()

        self.transform_descriptor = GraphTransformDescriptor(self.source_graph, self.target_graph)
        self.transform_containers = { id: VMobject() for id in self.transform_descriptor.ids() }

        self.create_transform_containers()
        self.restructure_mobjects()

    @abstractmethod
    def observers(self) -> List[MobjectIdentity]:
        pass
        # these are the user's mobjects declared on the stack, that are used to connect the scene to the transform_containers
        # Scene -> root_mobject -> transform_container[root]
        # Scene -> root_mobject -> root_mobject.child[i] -> transform_container[child[i]]
        # The transform_container[id] contain's graph[id]'s direct submobjects, that does not include graph[id]'s children which are also apart of graph[some-id]

    def save_recover_point(self):
        self.recover_mobjects = RecoverMobject()

        for mobject in self.transform_observers:
            self.recover_mobjects.save_recover_point(mobject)

    @abstractmethod
    def revert_mobjects(self):
        pass

    def create_transform_containers(self):

        for id in self.transform_descriptor.ids():
            if self.transform_descriptor.has_source(id):
                self.transform_containers[id].points = self.source_graph.get_dynamic_mobject(id).copy().points
                self.transform_containers[id].submobjects = [ self.source_graph.get_dynamic_mobject(id).direct_submobject_tree().copy() ]

    def restructure_mobjects(self):

        for mobject in self.transform_observers:
            children = self.transform_descriptor.child_union_ids(mobject.id)
            mobject.submobjects = [ self.transform_containers[mobject.id], *[ self.transform_containers[id] for id in children ] ]

        
    def end_transforms(self):

        # ID-POLICY
        # this acts on graph-of-interest, which in the case of a progress transform, does not include remover mobject identities
        # what about auto disconncet removers
                
        for mobject in self.graph.dynamic_mobjects:
            mobject.source_id = None
            mobject.target_id = None

        # Introduction via scene.add() creates a progress manager,
        # for progress, create_progress_manager() returns the existing manager
        # for from_copy/replacement_transform, it creates one since none exists, as these are introductory transforms for the graph-of-interest (target_graph)

        self.graph.unsubscribe(self.subscription_id)
        self.scene_progress_manager.create_progress_manager(self.graph).create_progress_point()
        


"""
The proper notation for partial-transformations should look like this:

animation = TransformInStages.progress(tex)
scene.play(animation.animate_subgraph(tex[0]))
scene.play(animation.animate_subgraph(tex[1]))
scene.play(animation.animate_subgraph(tex[2]))

But that is too far removed from the understood notation of ManimCE,
Therefore, we need a way to do:

scene.play(TransformInStages.progress(tex[0]))
scene.play(TransformInStages.progress(tex[1]))
scene.play(TransformInStages.progress(tex[2]))

The first progress(tex[0]) constructor checks to see if there is a ProgressTransformManager associated with tex.graph,
It will construct one since it does not exist, this thereby enters transform-mode, 
This will revert `tex` to its prior state found in the source_graph, which is done for each dynamic-mobject by reverting to source_graph[dynamic-mobject.id]
It will fade-out dynmaic-mobjects that are being introduced (not found in the source_graph)

Then each progress(tex[i]) can animate the subgraph constructed by tex[i], 
for each dynamic-mobject, animating each (dynamic-mobject, id) between source_graph[id] and target_graph[id]

Each progress(tex[i]) relies on the reversion done at progress(tex[0]) when the ProgressTransformManager is constructed
Subsequent progress(tex[i]) calls will not recreate the ProgressTransformManager. 
"""

class ProgressTransformManager(AbstractDynamicTransformManager):

    def __init__(
        self,
        graph_progress_manager: GraphProgressManager
    ):
        self.graph_progress_manager = graph_progress_manager 

        # ID-POLICY
        # If a user sets a target_id for a merge-onto, it will not affect the source-graph, since progress_point is taken before edits, i.e.
        # stack -> source_graph = stack.copy()
        # stack[id].target_id set
        # stack -> target_graph = stack.copy() (with target_id)
        # This tells source-graph[id] that it needs a target_id corresponding to target-graph[id].target_id

        for mobject in self.graph_progress_manager.graph.dynamic_mobjects: # stack-mobjects
            if (mobject.target_id is not None) and self.graph_progress_manager.source_graph.contains(mobject.id):
                self.source_graph.find_dynamic_mobject(mobject.id).target_id = mobject.target_id
        
        self.graph_progress_manager.save_target_graph()

        super().__init__(
            graph=self.graph_progress_manager.graph,
            source_graph=self.graph_progress_manager.source_graph,
            target_graph=self.graph_progress_manager.target_graph
        )

    def observers(self) -> List[MobjectIdentity]:
        pass


    def revert_mobjects(self):

        # Consider tex = MathTex(a, b, c); scene.add(tex); tex.terms = [ b, c, d ]; scene.play(TransformInStages.progress(tex))
        # MathString(a) would no longer be apart of the graph-of-interest after tex.terms = [ b, c, d ], 
        # but we still want MathString(a).submobjects[0] -> animated transform_container for MathString(a).id
        # the mobject_union will contain all the stack mobjects, including a, b, c, d

        self.mobject_union = { **self.graph_progress_manager.source_mobjects, **self.graph_progress_manager.target_mobjects }


        # The mobjects will first be reverted to their source state, then they will be restructured for transformation
        # the recover_mobjects will store the target_state, to undo the restructuring

        self.recover_mobjects = RecoverMobject()
        for mobject in self.mobject_union.values():
            self.recover_mobjects.save_recover_point(mobject)

        def revert_to_empty_mobject(mobject: DynamicMobject):
            mobject.points = VMobject().points
            mobject.submobjects = []

        def revert_to_prior_mobject(mobject: DynamicMobject):
            mobject.points = self.source_graph.find_dynamic_mobject(mobject.id).copy().points
            mobject.submobjects = self.source_graph.find_dynamic_mobject(mobject.id).direct_submobject_tree().copy().submobjects
        
        for mobject in [ mobject.current_dynamic_mobject for mobject in self.mobject_union.values() ]:

            if self.transform_descriptor.is_introducer(mobject.id):
                revert_to_empty_mobject(mobject)
            else:
                revert_to_prior_mobject(mobject)

        for mobject in self.mobject_union.values():
            if not self.transform_descriptor.is_introducer(mobject):
                mobject.current_dynamic_mobject.submobjects = []
                self.scene.scene_add(mobject.current_dynamic_mobject)
        
        

class FromCopyTransformsManager(PartialTransformsManager):

    def __init__(
        self,
        source_graph: DynamicMobjectGraph,
        target_graph: DynamicMobjectGraph
    ):
        super().__init__(
            graph=target_graph,
            source_graph=source_graph, 
            target_graph=target_graph
        )

        self.source_graph = self.source_graph
        self.target_graph = self.target_graph

    def revert_mobject(self, mobject: DynamicMobject):

        # consider tex1 = Term(x, Term(y, z)); tex2 = tex1.shift(DOWN)
        # if we wanted to introduce only y' at first, then the from_copy(tex1, y') would conclude with scene_add(y')
        # then this would consequently introduce z, since y.submobjects includes z.
        # therefore, we set_opacity(0) on all mobjects' in the target_graph

        




class GraphProgressManager():

    def __init__(
        self,
        graph: DynamicMobjectGraph,
        scene: Scene
    ):
        self.scene = scene
        self.graph = graph
        
        self.is_transforming = False
        self.has_progress_point = False

        self.graph.subscribe(lambda graph: self.end_transforms())
        
        # copied mobjects from stack, f(id-carrier)
        self.source_graph: DynamicMobjectGraph | None = None
        self.target_graph: DynamicMobjectGraph | None = None

        # stack mobjects, id-carries
        self.source_mobjects: Dict[UUID, MobjectIdentity] = {}
        self.target_mobjects: Dict[UUID, MobjectIdentity] = {}
        self.mobject_union: Dict[UUID, MobjectIdentity] = {}

    def begin_transforms(self):
        
        if self.is_transforming == True:
            return
        
        self.is_transforming = True
        
        if self.has_progress_point:
            self.begin_transforms_from_progress()

    def end_transforms(self):
        
        if self.is_transforming == False:
            return
        
        self.is_transforming = False
        self.is_progress_transform = False


        self.end_transforms_progress()
        self.create_progress_point()

    def create_progress_point(self):
        self.source_graph = self.graph.copy()
        self.target_graph = None
        self.source_mobjects = { mobject.id: mobject for mobject in self.graph.mobjects }

        self.has_progress_point = True

    def begin_transforms_from_progress(self):

        # scene_add(root) will restructure scene so that scene_remove(root) works correctly, safeguard against corruption
        for mobject in self.graph.root_mobjects:
            self.scene.scene_add(mobject.current_dynamic_mobject)


        self.target_graph = self.graph.copy()
        self.taget_mobjects = { mobject.id: mobject for mobject in self.graph.mobjects }

        self.mobject_union = { **self.source_mobjects, **self.target_mobjects }


        # ID-POLICY
        # If a user sets a target_id for a merge-onto, it will not affect the source-graph, since progress_point is taken before edits, i.e.
        # stack -> source_graph = stack.copy()
        # stack[id].target_id set
        # stack -> target_graph = stack.copy() (with target_id)
        # This tells source-graph[id] that it needs a target_id corresponding to target-graph[id].target_id

        def target_id(mobject):
            return mobject.current_dynamic_mobject.target_id

        for mobject in self.mobject_union.values():
            if target_id(mobject) is not None and self.source_graph.contains(mobject.id):
                self.source_graph.find_dynamic_mobject(mobject.id).target_id = target_id(mobject)


        self.recover_mobjects = RecoverMobject()
        [ self.recover_mobjects.save_recover_point(mobject) for mobject in self.mobject_union.values() ]
        
        
        def set_to_empty_mobject(mobject):
            mobject.current_dynamic_mobject.points = VMobject().points
            mobject.current_dynamic_mobject.submobjects = []

        def set_to_prior_mobject(mobject):
            mobject.current_dynamic_mobject.points = self.source_graph.find_dynamic_mobject(id).copy().points
            mobject.current_dynamic_mobject.submobjects = self.source_graph.find_dynamic_mobject(id).direct_submobject_tree().copy().submobjects

        transform_descriptor = GraphTransformDescriptor(self.source_graph, self.target_graph)

        # add stack mobjects, that are source_mobjects, individually to scene to increase stability
        for mobject in self.mobject_union.values():
            if not transform_descriptor.is_introducer(mobject):
                mobject.current_dynamic_mobject.submobjects = []
                self.scene.scene_add(mobject.current_dynamic_mobject)

        # restructure stack mobjects to source_state
        for mobject in self.mobject_union.values():
            if transform_descriptor.is_introducer(mobject):
                set_to_empty_mobject(mobject)
            else:
                set_to_prior_mobject(mobject)


    def end_transforms_progress(self):
        
        # add root_mobjects to restructure-scene
        for mobject in self.graph.root_mobjects:
            self.scene.scene_add(mobject.current_dynamic_mobject)

        [ self.recover_mobjects.recover_mobject(mobject) for mobject in self.mobject_union.values() ]

class GraphTransformManager():

    def __init__(
        self,
        graph: DynamicMobjectGraph,
        scene: Scene
    ):
        self.scene = scene
        self.graph = graph
        
        self.is_transforming = False
        self.has_progress_point = False

    def begin_transforms(self):

        if self.is_transforming == True:
            return
        
        self.is_transforming = True

    def end_transforms(self):



class SceneProgressManager():

    _scene_progress_manager: SceneProgressManager | None = None
    _scene: Scene | None = None
    
    def scene_progress_manager(self):

        scene_progress_manager = SceneProgressManager._scene_progress_manager
        
        if scene_progress_manager is None:
            raise Exception("Missing attach_progress_interceptors(self) in the body of `def construct(self)`")
        
        return scene_progress_manager
    
    def __init__(
        self,
        scene: Scene
    ):
        self.scene = scene
        self.progress_managers: Dict[Graph, GraphProgressManager] = {}
        self.transforms_managers: Dict[Graph, AbstractDynamicTransformManager] = {}


    def has_transforms_manager(self, graph: DynamicMobjectGraph):
        return graph in self.transforms_managers
    
    def get_transforms_manager(self, graph: DynamicMobjectGraph):

        if graph in self.transforms_managers:
            return self.transforms_managers[graph]
        
        raise Exception()
    
    def create_transforms_manager(self, graph, function):
        
        if graph not in self.transforms_managers[graph]:
            self.transforms_managers[graph] = function()

        return self.transforms_managers[graph] 
        

    def has_progress_manager(self, graph: DynamicMobjectGraph):
        return graph in self.progress_managers

    def get_progress_manager(self, graph: DynamicMobjectGraph):

        if graph in self.progress_managers:
            return self.progress_managers[graph]
        
        raise Exception()
    
    def create_progress_manager(self, graph: DynamicMobjectGraph):

        if graph not in self.progress_managers:
            self.progress_managers[graph] = GraphProgressManager(graph, self.scene)
        
        return self.progress_managers[graph]

    
    def add(self, mobject: DynamicMobject):
        
        manager = self.create_progress_manager(mobject.graph)
        manager.create_progress_point()

    def wait(self):
        for progress_manager in self.progress_managers.values():
            if not progress_manager.is_transforming:
                progress_manager.create_progress_point()


def attach_progress_interceptors_core(scene: Scene) -> SceneProgressManager:

        scene_progress_manager = SceneProgressManager(scene)
        
        scene_add = scene.add
        scene_wait = scene.wait
        scene_remove = scene.remove

        def _add(*mobjects: Mobject) -> Scene:
            
            for mobject in mobjects:
                for m in extract_direct_dynamic_mobjects(mobject):
                    if isinstance(m, DynamicMobject):
                        scene_progress_manager.add(m)

            return scene_add(*mobjects)
        
        def _wait(*args, **kwargs) -> None:
            scene_progress_manager.wait()
            scene_wait(*args, **kwargs)

        scene.add = _add
        scene.wait = _wait

        scene.scene_add = scene_add
        scene.scene_wait = scene_wait
        scene.scene_remove = scene_remove

        return scene_progress_manager

def attach_progress_interceptors(scene: Scene) -> SceneProgressManager:

    if hasattr(scene, "scene_progress_manager"):
        return scene.scene_progress_manager
    
    scene_progress_manager = attach_progress_interceptors_core(scene)

    scene.scene_progress_manager = scene_progress_manager
    AbstractDynamicTransform._scene_progress_manager = scene_progress_manager

    return scene_progress_manager



class PartialAbstractDynamicTransformConstructor():

    def __init__(self):
        scene_progress_manager = SceneProgressManager.scene_progress_manager()
    
    def create_deferred_animation(
            self, 
            cls: type[AbstractDynamicTransform],
            **kwargs
        ) -> AbstractDynamicTransform:
        
        # currently, self.source_graph set until after PADTC.__init__, by PADTC-implementer
        animation = cls(
            self.source_graph,
            self.target_graph,
            self.participants(),
            **kwargs
        )

        self.recover_mobjects = RecoverMobject()

        def begin_scene(scene: Scene):

            # can we have submobjects[1-n] point to actual children from subgraphs (sg1 and sg2), or does it need to be transform_containers

            for mobject in [ mobject.current_dynamic_mobject for mobject in self.observers() ]:
                continuous_child_ids = animation.config.transform_descriptor.child_union_ids(mobject.id)
                mobject.submobjects = [ animation.config.transform_containers[mobject.id], *[ animation.config.transform_containers[id] for id in continuous_child_ids] ]

        def clean_scene(scene: Scene):

            

        def begin_scene(scene: Scene):
            AbstractDynamicTransform._scene = scene

            cls.scene_add(scene, source_mobject)
            cls.scene_remove(scene, source_mobject)
    
            for mobject in subgraph1.dynamic_mobjects:
                
                submobject_saves[mobject] = mobject.submobjects
                points_saves[mobject] = mobject.points
                
                continuous_child_ids = animation.config.transform_descriptor.child_union_ids(mobject.id)
                mobject.submobjects = [ animation.config.transform_containers[mobject.id], *[ animation.config.transform_containers[id] for id in continuous_child_ids ]]

            for mobject in subgraph2.dynamic_mobjects:
                
                submobject_saves[mobject] = mobject.submobjects
                points_saves[mobject] = mobject.points
                
                continuous_child_ids = animation.config.transform_descriptor.child_union_ids(mobject.id)
                mobject.submobjects = [ animation.config.transform_containers[mobject.id], *[ animation.config.transform_containers[id] for id in continuous_child_ids ]]

        def clean_scene(scene: Scene):
            cls.scene_add(scene, target_mobject)

            for mobject in subgraph1.dynamic_mobjects:
                mobject.submobjects = submobject_saves[mobject]
                mobject.points = points_saves[mobject]

            for mobject in subgraph2.dynamic_mobjects:
                mobject.submobjects = submobject_saves[mobject]
                mobject.points = points_saves[mobject]

        def begin_scene(scene: Scene):

            for mobject in progress_mobjects:
                mobject = mobject.current_dynamic_mobject
                submobject_saves[mobject] = mobject.submobjects
                points_saves[mobject] = mobject.points
                
                continuous_child_ids = animation.config.transform_descriptor.child_union_ids(mobject.id)

                child_intersection = []
                for id in continuous_child_ids:
                    if transform_descriptor.is_continuous_ancestor(mobject.id, id):
                        child_intersection.append(find_mobject_from_mobject_union(id))

                mobject.submobjects = [ animation.config.transform_containers[mobject.id], *child_intersection ]

    @abstracmethod
    def participants(self) -> Set[UUID]:
        pass

    @abstractmethod
    def observers(self) -> List[MobjectIdentity]:
        pass

    def extract_subgraph(self, mobject: DynamicMobject | DynamicMobjectSubgraph | List[DynamicMobject]) -> DynamicMobjectSubgraph:

        if isinstance(mobject, DynamicMobjectSubgraph):
            return mobject

        if isinstance(mobject, DynamicMobject):
            return DynamicMobjectSubgraph.from_dynamic_mobject(mobject)
        
        mobjects: List[DynamicMobject] = []

        for item in mobject:
            mobjects.extend(AbstractDynamicTransform.extract_subgraph(item).dynamic_mobjects)

        return DynamicMobjectSubgraph(*mobjects)
        
    
    def extract_graph(self, subgraph: DynamicMobjectSubgraph):

        graphs = { mobject.graph for mobject in subgraph.mobjects }
        return extract_unique(graphs)
    
    
            

    


class ProgressTransformConstructor(PartialAbstractDynamicTransformConstructor):

    def __init__(
            self, 
            mobject
        ):
        super().__init__()

        self.subgraph = self.extract_subgraph(mobject)
        self.graph = self.extract_graph()

    
        if not self.scene_progress_manager.has_progress_manager(self.graph):
            raise Exception("No progress point for DynamicMobjectGraph exists")
        
        self.graph_progress_manager = self.scene_progress_manager.get_progress_manager(self.graph)


        def create_transforms_manager():
            return ProgressTransformsManager(self.graph_progress_manager)

        self.transforms_manager = self.scene_progress_manager.create_transforms_manager(self.graph, create_transforms_manager)
        
    def extract_graph(self):

        primary = { mobject.graph for mobject in self.subgraph.mobjects if self.scene_progress_manager.has_progress_manager(mobject.graph) }

        if len(primary) > 1:
            raise Exception("Cannot progress selection of multiple DynamicMobjectGraph(s)")
        
        if len(primary) == 0:
            raise Exception("DynamicMobjectGraph does not have progress-point, missing scene.add(mobject) or scene.play(Introducer(mobject))")
        
        return extract_unique(primary)

    
    def participants(self) -> Set[UUID]:

        # progress(tex - remover) will still include the remover, because in
        # progress(tex) it is assumed the remover children should be progressed as well

        particpants = set()
        
        for mobject in self.subgraph.mobjects:
            for descendant in self.transforms_manager.mobject_union.values():
                if self.transforms_manager.transform_descriptor.is_continuous_ancestor(mobject.id, descendant.id):
                    particpants.add(descendant.id)
        
        return particpants
    
    def observers(self) -> List[DynamicMobject]:
        return [ self.transforms_manager.mobject_union.get_dynamic_mobject(id) for id in self.participants() ] 
        


class ADTReplacementTransformConstructor(AbstractDynamicTransformConstructor):

    def __init__(
        self,
        source_mobject,
        target_mobject
    ):
        super().__init__()
        self.source_subgraph = self.extract_subgraph(source_mobject)
        self.target_subgraph = self.extract_subgraph(target_mobject)

        self.source_graph = self.extract_graph(self.source_subgraph)
        self.target_graph = self.extract_graph(self.target_subgraph)

        manager = self.scene_progress_manager.create_progress_manager(self.target_graph)
        manager.begin_transforms()

    def participants(self) -> List[UUID]:
        return { mobject.id for mobject in self.source_subgraph.dynamic_mobjects }.union({ mobject.id for mobject in self.target_subgraph.dynamic_mobjects })
    
    def observers(self) -> List[MobjectIdentity]:
        
        source_mobjects = [ self.source_graph.get_dynamic_mobject(id) for id in self.participants() if self.source_graph.contains(id) ] 
        target_mobjects = [ self.target_graph.get_dynamic_mobject(id) for id in self.participants() if self.target_graph.contains(id) ] 
        return [ *source_mobjects, *target_mobjects ]
    


class AbstractDynamicTransform(Animation):

    _scene_progress_manager: SceneProgressManager | None = None
    _scene: Scene | None = None

    @staticmethod
    def get_scene_progress_manager():
        _scene_progress_manager = AbstractDynamicTransform._scene_progress_manager
        if _scene_progress_manager is None:
            raise Exception()
        return _scene_progress_manager

    @staticmethod
    def scene_add(scene: Scene, mobject: Mobject):
        _scene_progress_manager = AbstractDynamicTransform._scene_progress_manager
        if _scene_progress_manager is not None:
            scene.scene_add(mobject)
        else:
            scene.add(mobject)

    @staticmethod
    def scene_remove(scene: Scene, mobject: Mobject):
        _scene_progress_manager = AbstractDynamicTransform._scene_progress_manager
        if _scene_progress_manager is not None:
            scene.scene_remove(mobject)
        else:
            scene.remove(mobject)

 


    @classmethod
    def progress(
        cls,
        mobject: DynamicMobject | DynamicMobjectSubgraph | List[DynamicMobject | DynamicMobjectSubgraph | Any],
        **kwargs
    ):
        
        animation = ADTProgressConstructor(mobject).deferred_animation()
        #return animation
        
        _scene_progress_manager = AbstractDynamicTransform.require_scene_progress_manager()

        mobjects: Set[DynamicMobject] = set()
        def extract_mobjects(mobject):

            if isinstance(mobject, DynamicMobjectSubgraph):
                for connected_mobject in mobject.dynamic_mobjects:
                    mobjects.add(connected_mobject)
                return

            if isinstance(mobject, DynamicMobject):
                for connected_mobject in DynamicMobjectSubgraph.from_dynamic_mobject(mobject).dynamic_mobjects:
                    mobjects.add(connected_mobject)
                return
            
            if isinstance(mobject, list):
                for item in mobject:
                    extract_mobjects(item)
                return
            
            raise Exception()
        
        """
        progress_manager = _scene_progress_manager.get_progress_manager(mobject.graph) """
        extract_mobjects(mobject)

        mobjects = list(mobjects)
        progress_manager, *other_progress_managers = [ _scene_progress_manager.get_progress_manager_from_mobject(mobject) for mobject in mobjects ]

        for other_progress_manager in other_progress_managers:
            if other_progress_manager is not  progress_manager:
                raise Exception()

        progress_manager.begin_transforms()

        source_graph, target_graph = progress_manager.source_graph, progress_manager.target_graph
        mobject_union = progress_manager.mobject_union
        
        progress_mobjects: Set[MobjectIdentity] = set()
        transform_descriptor = GraphTransformDescriptor(source_graph, target_graph)

        def extract_subgraph(mobject):
            return AbstractDynamicTransform.extract_subgraph(mobject)

        progress_subgraph = extract_subgraph(mobject)

        for mobject1 in progress_subgraph.mobjects:
            for id2, mobject2 in mobject_union.items():
                if transform_descriptor.is_continuous_ancestor(mobject1.id, id2):
                    progress_mobjects.add(mobject2)

        animation = cls(
            source_graph,
            target_graph,
            set(mobject.id for mobject in progress_mobjects),
            **kwargs
        )
        
        submobject_saves = {}
        points_saves = {}

        def find_mobject_from_mobject_union(id):
            for mobject in mobject_union.values():
                if mobject.id == id:
                    return mobject
                
            raise Exception()

        def begin_scene(scene: Scene):
            
            for mobject in progress_mobjects:
                mobject = mobject.current_dynamic_mobject
                submobject_saves[mobject] = mobject.submobjects
                points_saves[mobject] = mobject.points
                
                continuous_child_ids = animation.config.transform_descriptor.child_union_ids(mobject.id)

                child_intersection = []
                for id in continuous_child_ids:
                    if transform_descriptor.is_continuous_ancestor(mobject.id, id):
                        child_intersection.append(find_mobject_from_mobject_union(id))

                mobject.submobjects = [ animation.config.transform_containers[mobject.id], *child_intersection ]

        def clean_scene(scene: Scene):

            for mobject in progress_mobjects:
                mobject = mobject.current_dynamic_mobject
                mobject.submobjects = []

                if transform_descriptor.is_scene_remover(mobject.id):
                    scene.scene_add(mobject)
                    scene.scene_remove(mobject)

                if transform_descriptor.is_scene_introducer(mobject.id):
                    scene.scene_add(mobject)

                mobject.points = progress_manager.recover_points[mobject.id]
                mobject.submobjects = progress_manager.recover_submobjects[mobject.id]

        animation.setup_functions = [ begin_scene ]
        animation.clean_functions = [ clean_scene ]


        function_id = uuid.uuid4()

        def create_progress_point(graph: DynamicMobjectGraph):
            _scene_progress_manager = cls._scene_progress_manager

            for mobject in graph.dynamic_mobjects:
                mobject.source_id = None
                mobject.target_id = None

            if _scene_progress_manager is not None:
                _scene_progress_manager.add_graph(graph)

            graph.unsubscribe(function_id)

        progress_manager.graph.subscribe(lambda graph: create_progress_point(graph), function_id)


        return animation

    
    @classmethod
    def replacement_transform(
        cls,
        source_mobject: DynamicMobject,
        target_mobject: DynamicMobject,
        **kwargs
    ):
        _scene_progress_manager = AbstractDynamicTransform.require_scene_progress_manager()

        source_subgraph = AbstractDynamicTransform.extract_subgraph(source_mobject)
        target_subgraph = AbstractDynamicTransform.extract_subgraph(target_mobject)
        
        source_graph = AbstractDynamicTransform.extract_graph(source_subgraph)
        target_graph = AbstractDynamicTransform.extract_graph(target_subgraph)

        subgraph1 = DynamicMobjectSubgraph.from_dynamic_mobject(source_mobject)
        subgraph2 = DynamicMobjectSubgraph.from_dynamic_mobject(target_mobject)
        union = { mobject.id for mobject in subgraph1.dynamic_mobjects }.union({ mobject.id for mobject in subgraph2.dynamic_mobjects })

        animation = cls(
            source_graph,
            target_graph, 
            union, 
            **kwargs
        )

        submobject_saves = {}
        points_saves = {}

        def begin_scene(scene: Scene):
            AbstractDynamicTransform._scene = scene

            cls.scene_add(scene, source_mobject)
            cls.scene_remove(scene, source_mobject)
    
            for mobject in subgraph1.dynamic_mobjects:
                
                submobject_saves[mobject] = mobject.submobjects
                points_saves[mobject] = mobject.points
                
                continuous_child_ids = animation.config.transform_descriptor.child_union_ids(mobject.id)
                mobject.submobjects = [ animation.config.transform_containers[mobject.id], *[ animation.config.transform_containers[id] for id in continuous_child_ids ]]

            for mobject in subgraph2.dynamic_mobjects:
                
                submobject_saves[mobject] = mobject.submobjects
                points_saves[mobject] = mobject.points
                
                continuous_child_ids = animation.config.transform_descriptor.child_union_ids(mobject.id)
                mobject.submobjects = [ animation.config.transform_containers[mobject.id], *[ animation.config.transform_containers[id] for id in continuous_child_ids ]]

        def clean_scene(scene: Scene):
            cls.scene_add(scene, target_mobject)

            for mobject in subgraph1.dynamic_mobjects:
                mobject.submobjects = submobject_saves[mobject]
                mobject.points = points_saves[mobject]

            for mobject in subgraph2.dynamic_mobjects:
                mobject.submobjects = submobject_saves[mobject]
                mobject.points = points_saves[mobject]

        animation.setup_functions = [ begin_scene ]
        animation.clean_functions = [ clean_scene ]


        function_id = uuid.uuid4()

        def create_progress_point(graph: DynamicMobjectGraph):
            _scene_progress_manager = cls._scene_progress_manager

            for mobject in graph.dynamic_mobjects:
                mobject.source_id = None
                mobject.target_id = None

            if _scene_progress_manager is not None:
                _scene_progress_manager.add_graph(graph)

            for root_mobject in graph.root_mobjects:
                cls.scene_add(AbstractDynamicTransform._scene, root_mobject)

            graph.unsubscribe(function_id)

        target_graph.subscribe(lambda graph: create_progress_point(graph), function_id)


        return animation
    

    
    @classmethod
    def from_copy(
        cls,
        source_mobject,
        target_mobject,
        **kwargs
    ):
        _scene_progress_manager = AbstractDynamicTransform.require_scene_progress_manager()
        
        

        if not isinstance(source_mobject, DynamicMobjectGraph):
            source_graph = cls.extract_subgraph(source_mobject).graph
        else:
            source_graph = source_mobject

        target_subgraph = cls.extract_subgraph(target_mobject)
        target_graph = target_subgraph.graph

        # required due to auto-disconnect
        # x' -> x, means that x'.source_id = x.id
        extra_ids = set()
        for mobject in source_graph.mobjects:
            if target_subgraph.contains(mobject.current_dynamic_mobject.target_id):
                extra_ids.add(mobject.id)
            if target_subgraph.contains(mobject.current_dynamic_mobject.source_id):
                extra_ids.add(mobject.id)

        animation = cls(
            source_graph,
            target_graph,
            set(mobject.id for mobject in target_subgraph.mobjects).union(extra_ids),
            **kwargs
        )

        recover_submobjects = {}
        recover_points = {}

        def begin_scene(scene: Scene):
            AbstractDynamicTransform._scene = scene

            for mobject in target_subgraph.dynamic_mobjects:
                
                recover_submobjects[mobject] = mobject.submobjects
                recover_points[mobject] = mobject.points

                id_union = animation.config.transform_descriptor.child_union_ids(mobject.id)
                id_intersection = []

                for id in id_union:
                    if animation.config.transform_descriptor.is_continuous_ancestor(mobject.id, id):
                        id_intersection.append(id)

                mobject.submobjects = [ animation.config.transform_containers[mobject.id], *[ target_graph.find_dynamic_mobject(id) for id in id_intersection ]]

        def clean_scene(scene: Scene):
            
            for mobject in target_subgraph.dynamic_mobjects:
                
                mobject.submobjects = []
                cls.scene_add(scene, mobject)

                mobject.submobjects = recover_submobjects[mobject]
                mobject.points = recover_points[mobject]

        animation.setup_functions = [ begin_scene ]
        animation.clean_functions = [ clean_scene ]


        function_id = uuid.uuid4()

        def create_progress_point(graph: DynamicMobjectGraph):
            _scene_progress_manager = cls._scene_progress_manager

            for mobject in graph.dynamic_mobjects:
                mobject.source_id = None
                mobject.target_id = None

            if _scene_progress_manager is not None:
                _scene_progress_manager.add_graph(graph)

            for root_mobject in graph.root_mobjects:
                cls.scene_add(AbstractDynamicTransform._scene, root_mobject)

            graph.unsubscribe(function_id)

        target_graph.subscribe(lambda graph: create_progress_point(graph), function_id)
            

        return animation
    
    def __init__(
        self,
        source_graph: DynamicMobjectGraph, 
        target_graph: DynamicMobjectGraph,
        ids: Set[UUID],
        run_time: float | None = None, 
        **kwargs
    ):
        self.provided_run_time = run_time
        if run_time is None:
            run_time = 1

        self.config = DynamicTransformConfiguration(source_graph, target_graph, ids)
        self.container_group = VGroup(*self.config.transform_containers.values())

        self.setup_functions: List[Callable[[Scene], None]] = []
        self.clean_functions: List[Callable[[Scene], None]] = []

        self.apply()
        self.super_mobject = VMobject()
        super().__init__(mobject=self.super_mobject, run_time=run_time, **kwargs)

    @abstractmethod
    def apply(self):
        pass

    def intercept(
        self,
        mobject: DynamicMobject | DynamicMobjectSubgraph | UUID | List[Any]
    ) -> ItinerarySelectionInterceptor:

        ids: Set[UUID] = set()

        def recursive_extract(mobject):

            if isinstance(mobject, DynamicMobject):
                connected_ids = set(m.id for m in DynamicMobjectSubgraph.from_dynamic_mobject(mobject).mobjects)
                for connected_id in connected_ids:
                    ids.add(connected_id)
                return

            if isinstance(mobject, DynamicMobjectSubgraph):
                connected_ids = set(m.id for m in mobject.mobjects)
                for connected_id in connected_ids:
                    ids.add(connected_id)
                return

            if isinstance(mobject, UUID):
                ids.add(mobject)
                return

            if isinstance(mobject, list):
                for m in mobject:
                    recursive_extract(m)
                return

            raise Exception(
                f"Recieved {mobject} as input for animation intercept."
                "Only a DynamicMobject, DynamicMobjectSubgraph, UUID, or a list of those types, can be used to define ids to intercept." 
            )

        recursive_extract(mobject)
        return self.config.intercept(list(ids))

    def create_track(
        self,
        parent_track: AnimationTrack | None = None,
        start_time: float = 0,
        run_time: float = 1,
        name: str | None = None
    ) -> AnimationTrack:
        return self.config.create_track(parent_track=parent_track, start_time=start_time, run_time=run_time, name=name)

    def _setup_scene(self, scene):
        self.animation = self.config.build()
        
        if self.provided_run_time is not None:
            self.run_time = self.provided_run_time
        else:
            self.run_time = self.animation.run_time

        scene.add(self.animation.mobject)

        for function in self.setup_functions:
            function(scene)

    def begin(self):
        self.animation.begin()
        
    def finish(self):
        self.animation.finish()

    def clean_up_from_scene(self, scene: Scene) -> None:
        self.animation.clean_up_from_scene(scene)

        scene.remove(self.super_mobject)
        self.scene_add(scene, self.animation.mobject)
        self.scene_remove(scene, self.animation.mobject)

        for function in self.clean_functions:
            function(scene)
    
    def update_mobjects(self, dt: float) -> None:
        self.animation.update_mobjects(dt)

    def init_run_time(self, run_time) -> float:
        pass

    def build_animations_with_timings(self) -> None:
        pass

    def interpolate(self, alpha: float) -> None:
        self.animation.interpolate(alpha)

    
class GraphTransformDescriptor():

    def __init__(
        self, 
        source_graph: DynamicMobjectGraph,
        target_graph: DynamicMobjectGraph
    ):
        self.source_graph = source_graph
        self.target_graph = target_graph

    def ids(self):
        return { id for id in self.source_graph.mobjects }.union({ id for id in self.target_mobjects })

    def find_source_dynamic_mobject(self, id: UUID) -> DynamicMobject | None:

        if self.source_graph.contains(id):
            return self.source_graph.find_dynamic_mobject(id)
        else:
            source_id = self.target_graph.get_dynamic_mobject(id).source_id
            if source_id is not None and self.source_graph.contains(source_id):
                return self.source_graph.find_dynamic_mobject(source_id)
            else:
                for mobject in self.source_graph.dynamic_mobjects:
                    if mobject.source_id == id:
                        return mobject
                
                if self.target_graph.contains(source_id):
                    for mobject in self.source_graph.dynamic_mobjects:
                        if mobject.source_id == source_id:
                            return mobject
                
                return None
    
    def find_target_dynamic_mobject(self, id: UUID) -> DynamicMobject | None:
        
        if self.target_graph.contains(id):
            return self.target_graph.find_dynamic_mobject(id)
        else:
            target_id = self.source_graph.get_dynamic_mobject(id).target_id
            if target_id is not None and self.target_graph.contains(target_id):
                return self.target_graph.find_dynamic_mobject(target_id)
            else:
                source_id = self.source_graph.find_dynamic_mobject(id).source_id
                for mobject in self.target_graph.dynamic_mobjects:
                    if mobject.id == source_id:
                        return mobject

                return None
    
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
        
    def child_union_ids(self, id: UUID) -> List[UUID]:
        children: List[UUID] = set()

        if self.has_source(id):
            children = children.union(set([ mobject.id for mobject in self.find_source_dynamic_mobject(id).children ]))
        if self.has_target(id):
            children = children.union(set([ mobject.id for mobject in self.find_target_dynamic_mobject(id).children ]))

        return children


class ExtractTransform(Animation):

    def __init__(
        self,
        mobject: Mobject,
        animation: Animation
    ):
        self.super_mobject = VMobject()
        self.mobject = mobject
        self.animation = animation
        super().__init__(mobject=self.super_mobject)

    def begin(self):
        self.animation.begin()

    def finish(self):
        self.animation.finish()

    def interpolate(self, alpha: float) -> None:
        self.animation.interpolate(alpha)
        self.mobject.become(self.animation.mobject)

    def get_run_time(self) -> float:
        return self.animation.get_run_time()
        
    def clean_up_from_scene(self, scene: Scene) -> None:
        scene.remove(self.super_mobject)


class DynamicMobjectTransformItinerary():

    def __init__(
        self,
        config: DynamicTransformConfiguration,
        id: UUID
    ):
        self.config = config
        self.id = id

        self.source_mobject: VMobject = VMobject()
        self.target_mobject: VMobject = VMobject()
        self.animation_generator: Callable[[Mobject, Mobject], Animation] = lambda source, target: Transform(source, target)
        self.track = AnimationTrack(config, parent_track=self.config.root_track, run_time=1, is_leaf_track=True, name=self.id, id=self.id)

        if self.config.transform_descriptor.has_source(self.id):
            self.source_mobject = self.config.transform_descriptor.find_source_dynamic_mobject(self.id).direct_submobject_tree().copy()

        if self.config.transform_descriptor.has_target(self.id):
            self.target_mobject = self.config.transform_descriptor.find_target_dynamic_mobject(self.id).direct_submobject_tree().copy()
            
    def set_animation_generator(self, animation_generator):
        self.animation_generator = animation_generator

    def set_track(self, track: AnimationTrack):
        self.track.set_parent(track)

    def is_initialized(self):

        if self.source_mobject is not None and self.target_mobject is not None and self.animation_generator is not None and self.track is not None:
            return True
        
        return False

    def build(self):

        if not self.is_initialized():
            raise Exception()
        
        animation = self.animation_generator(self.source_mobject.copy(), self.target_mobject.copy())
        animation.run_time = self.track.run_time
        container_animation = ExtractTransform(self.config.transform_containers[self.id], animation)
        return container_animation


class ItinerarySelectionInterceptor():
    
    def __init__(
        self,
        config: DynamicTransformConfiguration,
        ids: List[uuid.UUID] 
    ):
        self.config = config

        for id in ids.copy():
            if id not in config.itineraries:
                ids.remove(id)    

        self.itineraries = { id: config.itineraries[id] for id in ids }

    def set_animation(self, animation_generator) -> ItinerarySelectionInterceptor:
        for itinerary in self.itineraries.values():
            itinerary.set_animation_generator(animation_generator)
        return self

    def set_track(self, track: AnimationTrack) -> ItinerarySelectionInterceptor:
        for itinerary in self.itineraries.values():
            itinerary.set_track(track)
        return self

    def set_source(self, mobject: Mobject | DynamicMobject) -> ItinerarySelectionInterceptor:

        if isinstance(mobject, DynamicMobject):
            for descendant in mobject.get_dynamic_family():
                if descendant.id in self.itineraries:
                    self.itineraries[descendant.id].source_mobject = descendant.direct_submobject_tree().copy()
        else:
            for itinerary in self.itineraries.values():
                itinerary.source_mobject = mobject.copy()

        return self

    def set_target(self, mobject: Mobject | DynamicMobject) -> ItinerarySelectionInterceptor:

        if isinstance(mobject, DynamicMobject):
            for mobject in mobject.get_dynamic_family():
                if mobject.id in self.itineraries:
                    self.itineraries[mobject.id].target_mobject = mobject.direct_submobject_tree().copy()
        else:
            for itinerary in self.itineraries.values():
                itinerary.target_mobject = mobject.copy()
                
        return self
    

class AnimationTrack():
    
    def set_run_time(self):
        if self.is_leaf_track and self.parent_track is not None:
            self.run_time = self.parent_track.run_time

    def __init__(
        self, 
        config: DynamicTransformConfiguration,
        start_time: float = 0.0, 
        run_time: float | None = None, 
        require_points: bool = True,
        is_root_track: bool = False,
        is_leaf_track: bool = False,
        parent_track: AnimationTrack | None = None,
        name: str | None = None,
        id: UUID | None = None, 
    ):
        #self.start_time = start_time
        self.run_time = run_time
        self.require_points = require_points

        self.config = config
        self.is_root_track = is_root_track
        self.is_leaf_track = is_leaf_track
        self.id = id

        if is_leaf_track and id is None:
            raise Exception()

        self.children: List[AnimationTrack] = []
        self.parent_track: AnimationTrack | None = None
        
        if parent_track:
            self.set_parent(parent_track)

        self.name = name
        self.start_time = start_time
       
    def set_parent(
        self, 
        parent_track: AnimationTrack | None
    ):
        if parent_track is not None:
            if parent_track.is_leaf_track:
                raise Exception()
        
            if self.config is not parent_track.config:
                raise Exception()

        if self.is_root_track:
            raise Exception()
        
        if self.parent_track:
            self.parent_track.children.remove(self)
        
        self.start_time = 0
        self.parent_track = parent_track

        if self.parent_track is not None:
            self.parent_track.children.append(self)

        self.set_run_time()

    def set_lag_ratio(self, lag_ratio: float):
        
        curr_time: float = 0
        for track in self.children:
            start_time: float = curr_time
            track.start_time = start_time

            end_time: float = start_time + track.run_time
            curr_time = (1 - lag_ratio) * start_time + lag_ratio * end_time

        self.run_time = curr_time

    def get_run_time(self):
        self.set_run_time()

        if not self.children and not self.is_leaf_track:
            return 0
        
        if self.is_leaf_track:
            return self.parent_track.run_time

        if self.run_time:
            return self.run_time

        _max = 0
        for track in self.children:
            _max = max(_max, track.start_time + track.get_run_time())

        return _max
    
    def get_itinerary(self):
        self.set_run_time()
        return self.config.itineraries[self.id]
    
    def has_mobject_with_points(self):
        self.set_run_time()
        if self.is_leaf_track:
            itinerary = self.get_itinerary()
            source_family = itinerary.source_mobject.get_family()
            target_family = itinerary.target_mobject.get_family()

            for mobject in source_family:
                if mobject.has_points():
                    return True
                
            for mobject in target_family:
                if mobject.has_points():
                    return True
                
            return False
        else:
            for track in self.children:
                if track.has_mobject_with_points():
                    return True
            
            return False


class ExactTimingsAnimationGroup(PreviousAnimationGroup):


    def __init__(
        self,
        *animations: Tuple[Animation, float],
        group = None,
        run_time: float | None = None,
        rate_func: Callable[[float], float] = linear,
        lag_ratio: float = 0,
        **kwargs,
    ):
        self.start_times = [ item[1] for item in animations ]     
        super().__init__(*[ item[0] for item in animations ])
        

    def build_animations_with_timings(self) -> None:
        self.anims_with_timings = []

        for start_time, anim in zip(self.start_times, self.animations):
            end_time: float = start_time + anim.get_run_time()
            self.anims_with_timings.append((anim, start_time, end_time))


class DynamicTransformConfiguration():

    def __init__(
        self,
        transform_manager: DynamicTransformManager,
        ids: Set[UUID]
    ):
        self.source_graph = transform_manager.source_graph
        self.target_graph = transform_manager.target_graph
        self.transform_manager = transform_manager

        for id in ids:
            if not (self.source_graph.contains(id) or self.target_graph.contains(id)):
                raise Exception()

        self.root_track = AnimationTrack(config=self, run_time=1, is_root_track=True, name="root_track")
        self.transform_descriptor = transform_manager.transform_descriptor
        self.prevent_ids: Set[UUID] = set()
        
        self.ids = ids.copy()
        for id in ids:
            if self.transform_descriptor.is_remover(id):
                for mobject in self.target_graph.mobjects:
                    if mobject.current_dynamic_mobject.source_id is not None and mobject.current_dynamic_mobject.source_id == id:
                        if id in self.ids:
                            self.prevent_ids.add(id)
        

        self.transform_containers = { id: transform_manager.transform_containers[id] for id in self.ids }
        self.itineraries = { id: DynamicMobjectTransformItinerary(self, id) for id in self.ids }

    def initialized(self):

        for itinerary in self.itineraries.values():
            if not itinerary.initialized():
                return False
            
        return True
    
    def create_track(
        self,
        parent_track: AnimationTrack | None = None,
        start_time: float = 0,
        run_time: float = 1,
        name: str | None = None
    ) -> AnimationTrack:
        
        if parent_track is None:
            parent_track = self.root_track

        return AnimationTrack(config=self, parent_track=parent_track, start_time=start_time, run_time=run_time, name=name)

    def build(self):
        
        def recursive_build(track: AnimationTrack) -> ExactTimingsAnimationGroup:
            

            if track.is_leaf_track:
                subtracks = [ ( track.get_itinerary().build() , 0) ]
            else:
                subtracks = [ ( recursive_build(track), track.start_time ) for track in track.children ]

            animation = ExactTimingsAnimationGroup(*subtracks, run_time=track.get_run_time())
            return animation
        
        animation = recursive_build(self.root_track)
        return animation

    def intercept(
        self, 
        ids: List[UUID]
    ):
        return ItinerarySelectionInterceptor(self, ids)


class TransformInStages(AbstractDynamicTransform):

    def __init__(
        self, 
        source_graph: DynamicMobjectGraph,
        target_graph: DynamicMobjectGraph,
        ids: Set[UUID],
        lag_ratio: float = 1,
        track_run_time: float = 1,
        **kwargs
    ):
        self._lag_ratio = lag_ratio
        self.track_run_time = track_run_time
        super().__init__(source_graph, target_graph, ids, **kwargs)
    
    def apply(self):

        self.default_track = self.config.create_track(name="default")
        self.remover_track = self.config.create_track(parent_track=self.default_track, name="default-remover", run_time=self.track_run_time)
        self.transformer_track = self.config.create_track(parent_track=self.default_track, name="default-transformer", run_time=self.track_run_time)
        self.introducer_track = self.config.create_track(parent_track=self.default_track, name="default-introducer", run_time=self.track_run_time)

        for itinerary in self.config.itineraries.values():
            itinerary.set_animation_generator(lambda source, target: Transform(source, target))

            if self.config.transform_descriptor.is_remover(itinerary.id):
                itinerary.target_mobject = self.config.source_graph.find_dynamic_mobject(itinerary.id).direct_submobject_tree().copy().fade(1)
                itinerary.set_track(self.remover_track)

            if self.config.transform_descriptor.is_introducer(itinerary.id):
                itinerary.source_mobject = self.config.target_graph.find_dynamic_mobject(itinerary.id).direct_submobject_tree().copy().fade(1)
                itinerary.set_track(self.introducer_track)

            if self.config.transform_descriptor.is_transformer(itinerary.id):
                itinerary.set_track(self.transformer_track)

            if itinerary.id in self.config.prevent_ids:
                itinerary.track.set_parent(None)
                itinerary.source_mobject = VMobject()
                itinerary.target_mobject = VMobject()

        if not self.remover_track.has_mobject_with_points():
            self.remover_track.set_parent(None)

        if not self.transformer_track.has_mobject_with_points():
            self.transformer_track.set_parent(None)
        
        if not self.introducer_track.has_mobject_with_points():
            self.introducer_track.set_parent(None)
        
        self.default_track.set_lag_ratio(self._lag_ratio)