from __future__ import annotations
from abc import abstractmethod
from typing import Dict, List, Set, Any, Tuple, Any


from .helpers import *

from manim import Scene, VMobject, Transform, Animation, linear, Mobject
from .manim_src.composition import PreviousAnimationGroup
from .dynamic_mobject import *



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
        progress_manager: GraphProgressManager
    ):
        self.progress_manager = progress_manager 

        super().__init__(
            graph=self.progress_manager.graph,
            source_graph=self.progress_manager.source_graph,
            target_graph=self.progress_manager.target_graph
        )

        self.source_graph = None
        self.target_graph = None

    def begin_transforms(self):

        self.progress_manager.save_target_graph()
        self.source_graph = self.progress_manager.source_graph
        self.target_graph = self.progress_manager.target_graph # to fix

        super().begin_transforms()

    def observers(self) -> List[DynamicMobject]:

        # Consider tex = MathTex(a, b, c); scene.add(tex); tex.terms = [ b, c, d ]; scene.play(TransformInStages.progress(tex))
        # MathString(a) would no longer be apart of the graph-of-interest after tex.terms = [ b, c, d ], 
        # but we still want MathString(a).submobjects[0] -> animated transform_container for MathString(a).id
        # the mobject_union will contain all the stack mobjects, including a, b, c, d

        self.mobject_union = { **self.progress_manager.source_mobjects, **self.progress_manager.target_mobjects }
        return [ mobject.current_dynamic_mobject for mobject in self.mobject_union.values() ]
    
    def constructor_name(self) -> str:
        return "progress"

class ReplacementTransformManager(AbstractDynamicTransformManager):
    
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

    def observers(self):

        """
        tex1 = MathTex(x, y)
        tex2 = MathTex(z, y)

        scene.play(ADT.replacement_transform(tex1, tex2))

        Here, we want to have x, y, y, z observe the transform, both y-mobjects will share the same transform_container in their submobjects
        
        scene -> tex1[y] --submobjects[0]-> transform_containers[y]
        scene -> tex2[y] --submobjects[0]-> transform_containers[y]
        """

        return [ *self.source_graph.dynamic_mobjects, *self.target_graph.dynamic_mobjects ]
    
    def constructor_name(self) -> str:
        return "replacement_transform"
    
    def restore_participant_observers(self, participant_observers: Set[UUID]):

        # maybe we should only be restoring target_observers?
        for mobject in self.observers():
            if mobject.id in participant_observers:
                if mobject in self.target_graph.dynamic_mobjects:
                    self.mobject_recovery.recover_mobject(mobject)

class FromCopyTransformManager(AbstractDynamicTransformManager):

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

    def observers(self):
        return self.target_graph.dynamic_mobjects

    def create_source_mobject_for_container(self, container, id):
        super().create_source_mobject_for_container(container, id)

        for container in self.transform_containers.values():
            container.set_opacity(0)

    def constructor_name(self) -> str:
        return "from_copy"







class AbstractDynamicTransform(Animation):

    @staticmethod
    def extract_graph(subgraph: DynamicMobjectSubgraph):

        graphs = { mobject.graph for mobject in subgraph.mobjects }
        return extract_unique(graphs)
    
    @staticmethod
    def extract_subgraph(mobject: DynamicMobject | DynamicMobjectSubgraph | List[DynamicMobject]) -> DynamicMobjectSubgraph:

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
        config = None,
        **kwargs
    ):
        scene_manager = SceneManager.scene_manager()
        subgraph = cls.extract_subgraph(mobject)
        primary = { mobject.graph for mobject in subgraph.mobjects if scene_manager.graph_manager(mobject.graph).has_progress_manager() }

        if len(primary) > 1:
            raise Exception("Cannot progress selection of multiple DynamicMobjectGraph(s)")
        
        if len(primary) == 0:
            raise Exception("DynamicMobjectGraph does not have progress-point, missing scene.add(mobject) or scene.play(Introducer(mobject))")
        
        graph = extract_unique(primary)
        graph_manager = scene_manager.graph_manager(graph)
        progress_manager = graph_manager.progress_manager

        transform_manager = graph_manager.accept_transform_manager(
            ProgressTransformManager(progress_manager).set_abstract_dynamic_transform(cls) # discarded on subsequent partial-transforms
        ) 
        
        participants = set()
        
        for mobject in subgraph.mobjects:
            for descendant in transform_manager.mobject_union.values():
                if transform_manager.transform_descriptor.is_continuous_ancestor(mobject.id, descendant.id):
                    participants.add(descendant.id)

        animation = cls(transform_manager, participants, param=config, **kwargs)

        def begin_scene(scene: Scene):
            # in case otherwise empty composite is configured to have direct submobjects. 
            transform_manager.restructure_participant_observers(participants)

        def clean_scene(scene: Scene):
            transform_manager.restore_participant_observers(participants)

        animation.begin_functions = [ begin_scene ]
        animation.clean_functions = [ clean_scene ]
        return animation

    
    @classmethod
    def replacement_transform(
        cls,
        source_mobject: DynamicMobject | DynamicMobjectSubgraph | List[DynamicMobject | DynamicMobjectSubgraph | Any],
        target_mobject: DynamicMobject | DynamicMobjectSubgraph | List[DynamicMobject | DynamicMobjectSubgraph | Any],
        config = None,
        **kwargs
    ):
        source_subgraph = cls.extract_subgraph(source_mobject)
        target_subgraph = cls.extract_subgraph(target_mobject)
        source_graph = cls.extract_graph(source_subgraph)
        target_graph = cls.extract_graph(target_subgraph)


        scene_manager = SceneManager.scene_manager()

        transform_manager = scene_manager.graph_manager(target_graph).accept_transform_manager(
            ReplacementTransformManager(source_graph, target_graph).set_abstract_dynamic_transform(cls) # discarded on subsequent partial-transforms
        )

        #transform_manager = scene_manager.add_transform_manager(
        #    target_graph, 
        #    ReplacementTransformManager(source_graph, target_graph).set_abstract_dynamic_transform(cls) # discarded on subsequent partial-transforms
        #)

        participants = { mobject.id for mobject in source_subgraph.dynamic_mobjects }.union({ mobject.id for mobject in target_subgraph.dynamic_mobjects })
        animation = cls(transform_manager, participants, param=config, **kwargs)

        def begin_scene(scene: Scene):
            # in case otherwise empty composite is configured to have direct submobjects. 
            transform_manager.restructure_participant_observers(participants)

        def clean_scene(scene: Scene):
            transform_manager.restore_participant_observers(participants)

        animation.begin_functions = [ begin_scene ]
        animation.clean_functions = [ clean_scene ]
        return animation
    

    @classmethod
    def from_copy(
        cls,
        source_mobject: DynamicMobject | DynamicMobjectSubgraph | List[DynamicMobject | DynamicMobjectSubgraph | Any],
        target_mobject: DynamicMobject | DynamicMobjectSubgraph | List[DynamicMobject | DynamicMobjectSubgraph | Any],
        config = None,
        **kwargs
    ):
        source_subgraph = cls.extract_subgraph(source_mobject)
        target_subgraph = cls.extract_subgraph(target_mobject)
        source_graph = cls.extract_graph(source_subgraph)
        target_graph = cls.extract_graph(target_subgraph)

        scene_manager = SceneManager.scene_manager()

        transform_manager = scene_manager.graph_manager(target_graph).accept_transform_manager(
            FromCopyTransformManager(source_graph, target_graph).set_abstract_dynamic_transform(cls)
        )

        #transform_manager = scene_manager.add_transform_manager(
        #    target_graph, 
        #    FromCopyTransformManager(source_graph, target_graph).set_abstract_dynamic_transform(cls)
        #)
        
        """
        ID-POLICY

        required due to auto-disconnect, where instead of x -> x' we have x' -> x
        x' -> x, means that x'.source_id = x.id """

        """
        extra_ids = set()
        for mobject in source_graph.dynamic_mobjects:
            #if transform_manager.transform_descriptor.find_target_dynamic_mobject(mobject.id) is not None:

        
            if target_subgraph.contains(mobject.current_dynamic_mobject.target_id):
                extra_ids.add(mobject.id)
            if target_subgraph.contains(mobject.current_dynamic_mobject.source_id):
                extra_ids.add(mobject.id)
        """

        participants = { mobject.id for mobject in target_subgraph.mobjects }
        participants_extra = set()

        for mobject in source_graph.dynamic_mobjects:
            if mobject.id not in participants:
                mobject_target = transform_manager.transform_descriptor.find_target_dynamic_mobject(mobject.id)
                if not none(mobject_target) and mobject_target.id in participants:
                    participants_extra.add(mobject.id)

        participants = participants.union(participants_extra)
        animation = cls(transform_manager, participants, param=config, **kwargs)

        def begin_scene(scene: Scene):
            # in case otherwise empty composite is configured to have direct submobjects. 
            transform_manager.restructure_participant_observers(participants)

        def clean_scene(scene: Scene):
            transform_manager.restore_participant_observers(participants)
            
        animation.begin_functions = [ begin_scene ]
        animation.clean_functions = [ clean_scene ]
        return animation

        
    
    def __init__(
        self,
        transform_manager: AbstractDynamicTransformManager,
        ids: Set[UUID],
        run_time: float | None = None, 
        param = None,
        **kwargs
    ):
        self.param = param
        if self.param is None:
            self.param = {}

        self.provided_run_time = run_time
        if run_time is None:
            run_time = 1
        
        self.transform_manager = transform_manager
        self.config = DynamicTransformConfiguration(transform_manager, ids)
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

        #scene.scene_remove(self.super_mobject)

        for container in self.config.transform_containers.values():
            scene.scene_add(container).scene_remove(container)

        scene.scene_add(self.animation.mobject)
        self.super_mobject.submobjects = [ self.animation.mobject ]
        
        
        if self.provided_run_time is not None:
            self.run_time = self.provided_run_time
        else:
            self.run_time = self.animation.run_time
                

        # having this causes thicker-overlay appearence, even on independent mobjects. 
        #scene.add(self.animation.mobject)

        for function in self.setup_functions:
            function(scene)

    def begin(self):
        self.animation.begin()
        
    def finish(self):
        self.animation.finish()

    def clean_up_from_scene(self, scene: Scene) -> None:
        self.animation.clean_up_from_scene(scene)

        scene.scene_add(self.super_mobject).scene_remove(self.super_mobject)
        scene.scene_add(self.animation.mobject).scene_remove(self.animation.mobject)

        for container in self.config.transform_containers.values():
            scene.scene_add(container)

        # scene add remove animation.mobject may remove parts of the GOC.
        # I am going to do .restructure_scene() on the clean_scene() to try to add it back

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



        



class ExtractTransform(Animation):

    def __init__(
        self,
        container: Mobject,
        animation: Animation
    ):
        self.container = container
        self.animation = animation
        super().__init__(mobject=self.container)
    
    def begin(self):
        self.animation.begin()

    def finish(self):
        self.animation.finish()

    def interpolate(self, alpha: float) -> None:
        self.animation.interpolate(alpha)
        self.container.become(self.animation.mobject.copy())

    def get_run_time(self) -> float:
        return self.animation.get_run_time()


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
            self.source_mobject = self.config.transform_descriptor.find_source_dynamic_mobject(self.id).direct_submobjects().copy()

        if self.config.transform_descriptor.has_target(self.id):
            self.target_mobject = self.config.transform_descriptor.find_target_dynamic_mobject(self.id).direct_submobjects().copy()
            
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
        
        source_mobject = self.source_mobject.copy()
        target_mobject = self.target_mobject.copy()

        if self.id in self.config.transform_descriptor.prevent_ids():
            source_mobject.set_opacity(0)
            target_mobject.set_opacity(0)
        
        animation = self.animation_generator(source_mobject, target_mobject)
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
                    self.itineraries[descendant.id].source_mobject = descendant.direct_submobjects().copy()
        else:
            for itinerary in self.itineraries.values():
                itinerary.source_mobject = mobject.copy()

        return self

    def set_target(self, mobject: Mobject | DynamicMobject) -> ItinerarySelectionInterceptor:

        if isinstance(mobject, DynamicMobject):
            for mobject in mobject.get_dynamic_family():
                if mobject.id in self.itineraries:
                    self.itineraries[mobject.id].target_mobject = mobject.direct_submobjects().copy()
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
        transform_manager: AbstractDynamicTransformManager,
        ids: Set[UUID]
    ):
        self.source_graph = transform_manager.transform_descriptor.source_graph
        self.target_graph = transform_manager.transform_descriptor.target_graph
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
        transform_manager: AbstractDynamicTransformManager,
        ids: Set[UUID],
        lag_ratio: float = 1,
        track_run_time: float = 1,
        **kwargs
    ):
        self._lag_ratio = lag_ratio
        self.track_run_time = track_run_time
        super().__init__(transform_manager, ids, **kwargs)

    def apply_special_intro(self, itinerary: DynamicMobjectTransformItinerary):

        if "intro" in self.param:
            intro = self.param["intro"]
        else:
            return

        if issubclass(intro, Animation):
            itinerary.set_animation_generator(lambda source, target: intro(target))
        else:
            raise Exception("intro-config only supports Introducer(target) syntax")
        
    def apply_special_remover(self, itinerary: DynamicMobjectTransformItinerary):

        if "outro" in self.param:
            intro = self.param["outro"]
        else:
            return
        
        if issubclass(intro, Animation):
            itinerary.set_animation_generator(lambda source, target: intro(source))
        else:
            raise Exception("outro-config only supports Remover(target) syntax")

    
    def apply(self):

        self.default_track = self.config.create_track(name="default")
        self.remover_track = self.config.create_track(parent_track=self.default_track, name="default-remover", run_time=self.track_run_time)
        self.transformer_track = self.config.create_track(parent_track=self.default_track, name="default-transformer", run_time=self.track_run_time)
        self.introducer_track = self.config.create_track(parent_track=self.default_track, name="default-introducer", run_time=self.track_run_time)

        for itinerary in self.config.itineraries.values():
            itinerary.set_animation_generator(lambda source, target: Transform(source, target))

            if self.config.transform_descriptor.is_remover(itinerary.id):
                itinerary.target_mobject = self.config.source_graph.find_dynamic_mobject(itinerary.id).direct_submobjects().copy().fade(1)
                itinerary.set_track(self.remover_track)

                self.apply_special_remover(itinerary)

            if self.config.transform_descriptor.is_introducer(itinerary.id):
                itinerary.source_mobject = self.config.target_graph.find_dynamic_mobject(itinerary.id).direct_submobjects().copy().fade(1)
                itinerary.set_track(self.introducer_track)

                self.apply_special_intro(itinerary)

            if self.config.transform_descriptor.is_transformer(itinerary.id):
                itinerary.set_track(self.transformer_track)

                self

            #if itinerary.id in self.config.prevent_ids:
            #    itinerary.track.set_parent(None)
            #    itinerary.source_mobject = VMobject()
            #    itinerary.target_mobject = VMobject()

        if not self.remover_track.has_mobject_with_points():
            self.remover_track.set_parent(None)

        if not self.transformer_track.has_mobject_with_points():
            self.transformer_track.set_parent(None)
        
        if not self.introducer_track.has_mobject_with_points():
            self.introducer_track.set_parent(None)

        self.default_track.set_lag_ratio(self._lag_ratio)