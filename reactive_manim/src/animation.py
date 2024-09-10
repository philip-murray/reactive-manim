from __future__ import annotations
from abc import abstractmethod
from typing import Dict
from uuid import UUID

from manim import Scene
from .manim_src.composition import PreviousAnimationGroup
from .dynamic_mobject import *


class GraphProgressManager():

    def __init__(
        self,
        graph: DynamicMobjectGraph,
        scene: Scene
    ):
        self.scene = scene
        self.graph = graph
        self.graph.subscribe(lambda graph: self.end_transforms())
        self.is_transforming = False

        self.source_graph: DynamicMobjectGraph | None = None
        self.target_graph: DynamicMobjectGraph | None = None

        self.source_mobjects: Dict[UUID, MobjectIdentity] = {}
        self.target_mobjects: Dict[UUID, MobjectIdentity] = {}
        self.mobject_union: Dict[UUID, MobjectIdentity] = {}

        self.active_mobjects = []


    def begin_transforms(self):
        
        if self.is_transforming == True:
            return
        
        self.is_transforming = True
        
        for mobject in self.graph.root_mobjects:
            self.scene.scene_add(mobject.current_dynamic_mobject)
        
        self.target_graph = self.graph.copy() 
        self.target_mobjects = { mobject.id: mobject for mobject in self.graph.mobjects }
        
        for mobject in self.graph.mobjects:
            if mobject not in self.active_mobjects:
                self.active_mobjects.append(mobject)

        id_union = { id for id in self.source_mobjects.keys() }.union({ id for id in self.target_mobjects.keys() })
        self.mobject_union = {}

        for id in id_union:
            if id in self.target_mobjects:
                self.mobject_union[id] = self.target_mobjects[id]
            else:
                self.mobject_union[id] = self.source_mobjects[id]

        for mobject in self.mobject_union.values():
            mobject = mobject.current_dynamic_mobject
            if mobject.target_id is not None and self.source_graph.contains(mobject.id):
                self.source_graph.find_dynamic_mobject(mobject.id).target_id = mobject.target_id

        self.recover_points = {}
        self.recover_submobjects = {}
        for id in self.mobject_union:
            self.recover_points[id] = self.mobject_union[id].current_dynamic_mobject.points.copy()
            self.recover_submobjects[id] = self.mobject_union[id].current_dynamic_mobject.submobjects.copy()

        for id, mobject in self.target_mobjects.items():
            if id not in self.source_mobjects:
                mobject.current_dynamic_mobject.points = VMobject().points
                mobject.current_dynamic_mobject.submobjects = []
            else:
                mobject.current_dynamic_mobject.points = self.target_graph.find_dynamic_mobject(id).points
                mobject.current_dynamic_mobject.submobjects = self.target_graph.find_dynamic_mobject(id).direct_submobject_tree().copy().submobjects

        for id, mobject in self.source_mobjects.items():
            mobject.current_dynamic_mobject.points = self.source_graph.find_dynamic_mobject(id).points
            mobject.current_dynamic_mobject.submobjects = self.source_graph.find_dynamic_mobject(id).direct_submobject_tree().copy().submobjects
            self.scene.scene_add(mobject)

    def end_transforms(self):
        
        if self.is_transforming == False:
            return
        
        self.is_transforming = False

        for mobject in self.graph.root_mobjects:
            self.scene.scene_add(mobject.current_dynamic_mobject)
            #self.scene.scene_remove(mobject.current_dynamic_mobject)
            #self.scene.scene_add(mobject.current_dynamic_mobject)

        for id, mobject in self.mobject_union.items():
            mobject.current_dynamic_mobject.points = self.recover_points[mobject.id]
            mobject.current_dynamic_mobject.submobjects = self.recover_submobjects[mobject.id]
        
        self.create_progress_point()
        
    def create_progress_point(self):
        self.source_graph = self.graph.copy()
        self.target_graph = None
        self.source_mobjects = { mobject.id: mobject for mobject in self.graph.mobjects }
        self.active_mobjects = [ *self.graph.mobjects ]


class SceneProgressManager():

    def __init__(
        self,
        scene: Scene
    ):
        self.scene = scene
        self.progress_managers: Dict[Graph, GraphProgressManager] = {}

    def get_progress_manager(self, graph: DynamicMobjectGraph):

        if graph in self.progress_managers:
            return self.progress_managers[graph]
        
        raise Exception()
    
    def get_progress_manager_from_mobject(self, mobject: DynamicMobject):
        
        manager_from_graph = None
        if mobject.graph in self.progress_managers:
            manager_from_graph = self.progress_managers[mobject.graph]
        
        manager_from_active_mobject = None
        for progress_manager in self.progress_managers.values():
            if mobject.identity in progress_manager.active_mobjects:
                if manager_from_active_mobject is not None:
                    if manager_from_graph is None:
                        raise Exception()
                    
                manager_from_active_mobject = progress_manager
                
        if manager_from_graph is None and manager_from_active_mobject is None:
            raise Exception()
        
        if manager_from_graph is not None:
            return manager_from_graph
        
        if manager_from_active_mobject is not None:
            return manager_from_active_mobject

        raise Exception()

    def add_graph(self, graph: DynamicMobjectGraph):
        if not graph in self.progress_managers:
            self.progress_managers[graph] = GraphProgressManager(graph, self.scene)

        self.progress_managers[graph].create_progress_point()
    
    def add(self, mobject: DynamicMobject):
        self.add_graph(mobject.graph)

    def wait(self):
        for progress_manager in self.progress_managers.values():
            if not progress_manager.is_transforming:
                progress_manager.create_progress_point()


def attach_progress_interceptors(scene: Scene) -> SceneProgressManager:

    if hasattr(scene, "ATTACH_PROGRESS_INTERCEPTORS_FLAG"):
        return scene
    
    scene.ATTACH_PROGRESS_INTERCEPTORS_FLAG = True

    scene_progress_manager = SceneProgressManager(scene)
    AbstractDynamicTransform._scene_progress_manager = scene_progress_manager

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


class AbstractDynamicTransform(Animation):

    _scene_progress_manager: SceneProgressManager | None = None
    _scene: Scene | None = None

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

    @staticmethod
    def extract_subgraph(mobject: DynamicMobject | List[DynamicMobject] | DynamicMobjectSubgraph) -> DynamicMobjectSubgraph:

        if isinstance(mobject, DynamicMobjectSubgraph):
            return mobject

        if isinstance(mobject, DynamicMobject):
            return DynamicMobjectSubgraph.from_dynamic_mobject(mobject)
        
        mobjects: List[DynamicMobject] = []
        for item in mobject:
            mobjects.extend(AbstractDynamicTransform.extract_subgraph(item).dynamic_mobjects)

        return DynamicMobjectSubgraph(*mobjects)
    
    @classmethod
    def progress(
        cls,
        mobject: DynamicMobject | DynamicMobjectSubgraph | List[DynamicMobject | DynamicMobjectSubgraph | Any],
        **kwargs
    ):
        _scene_progress_manager = cls._scene_progress_manager
        
        if _scene_progress_manager is None:
            raise Exception("Missing attach_progress_interceptors(self) in the body of `def construct(self)`")
        

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
        source_graph = source_mobject.graph
        target_graph = target_mobject.graph

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
        if not isinstance(source_mobject, DynamicMobjectGraph):
            source_graph = cls.extract_subgraph(source_mobject).graph
        else:
            source_graph = source_mobject

        target_subgraph = cls.extract_subgraph(target_mobject)
        target_graph = target_subgraph.graph

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
        source_graph: DynamicMobjectGraph, 
        target_graph: DynamicMobjectGraph,
        ids: Set[UUID]
    ):
        self.source_graph = source_graph
        self.target_graph = target_graph

        for id in ids:
            if not (source_graph.contains(id) or target_graph.contains(id)):
                raise Exception()

        self.root_track = AnimationTrack(config=self, run_time=1, is_root_track=True, name="root_track")
        self.transform_descriptor = GraphTransformDescriptor(source_graph, target_graph)
        self.prevent_ids: Set[UUID] = set()
        
        self.ids = ids.copy()
        for id in ids:
            if self.transform_descriptor.is_remover(id):
                for mobject in self.target_graph.mobjects:
                    if mobject.current_dynamic_mobject.source_id is not None and mobject.current_dynamic_mobject.source_id == id:
                        if id in self.ids:
                            self.prevent_ids.add(id)
        

        self.transform_containers = { id: VMobject() for id in self.ids }
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