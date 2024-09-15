from __future__ import annotations
from abc import abstractmethod
from typing_extensions import *
from typing import List, Dict, overload
import copy
import uuid
from uuid import UUID
import numpy as np

from manim import *


class DynamicMobjectGraph():

    def __init__(self):
        self.root_mobjects: Set[MobjectIdentity] = []
        self.subscriptions: Dict[UUID, Callable[[DynamicMobjectGraph], None]] = {}
        self.id = None
    
    @property
    def mobjects(self) -> List[MobjectIdentity]:
        mobjects: Set[MobjectIdentity] = set()

        for root_mobject in self.root_mobjects:
            connected_mobjects = self.connected_from_root(root_mobject)
            for mobject in connected_mobjects:
                mobjects.add(mobject)
        
        return list(mobjects)

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


    def subscribe(self, function: Callable[[DynamicMobjectGraph], None], id: UUID | None = None) -> UUID:
        if id is None:
            id = uuid.uuid4()
        self.subscriptions[id] = function
        return id
    
    def unsubscribe(self, id: UUID):
        del self.subscriptions[id]

    def copy(self) -> DynamicMobjectGraph:
        subscriptions = self.subscriptions
        self.subscriptions = {}
        graph = copy.deepcopy(self)
        self.subscriptions = subscriptions
        return graph
    

    def begin_invalidation(self):
        for function in list(self.subscriptions.values()).copy():
            function(self)

    def begin_state_invalidation(self):

        for function in list(self.subscriptions.values()).copy():
            function(self)

        for mobject in self.mobjects:
            try:
                center = mobject.current_dynamic_mobject.get_center()
                mobject.mobject_center = center
            except:
                pass
    
    
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
                
                curr_root.graph = graph
        
        for next_root in root_mobjects:
            if next_root not in self.root_mobjects:
                
                next_root.graph.root_mobjects.remove(next_root)

                self.root_mobjects.add(next_root)

                next_root.graph = self

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

            for mobject in root_connected_mobjects2:
                if mobject.id in m:
                    raise Exception(
                        "Mobject graph cannot contain duplicate ids."
                        "Use mobject.clone() instead of mobject.copy() for duplication."
                    )
            
            graph2_root_mobjects = graph2.root_mobjects.copy()
            graph2.root_mobjects = set()
            graph1.root_mobjects = graph1.root_mobjects.union(graph2_root_mobjects)

        graph1.root_mobjects.remove(child) ###
        child.graph = None

        parent.children.add(child)
        child.parent = parent

    def disconnect_parent_child(self, parent: MobjectIdentity, child: MobjectIdentity):

        parent.children.remove(child)
        child.parent = None

        graph = DynamicMobjectGraph()
        graph.root_mobjects = { child }
        child.graph = graph


class MobjectIdentity(VMobject):

    def __init__(self, mobject: DynamicMobject):

        super().__init__()
        self.id = uuid.uuid4()
        self.source_ids: List[UUID] = []
        self.target_ids: List[UUID] = [] 


        self.parent: MobjectIdentity | None = None
        self.children: Set[MobjectIdentity] = set()

        self.incorporated = False

        self.mobject_graph: DynamicMobjectGraph | None = None
        self.mobject_graph = DynamicMobjectGraph()
        self.mobject_graph.root_mobjects = { self }

        self.terminate_propogation_mobject: MobjectIdentity | None = None
        self.permit_propogation: bool = True
        self.change_parent_mobject: MobjectIdentity | None = None
        self.change_parent_mobject_replacement: DynamicMobject | None = None
    
        self.mobject_center = VMobject().get_center()
        
        self.current: DynamicMobject | None = None
        self.set_dynamic_mobject(mobject)

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
        graph = self.root_parent.mobject_graph
        if graph is None:
            raise Exception()
        return graph

    @graph.setter
    def graph(self, graph: DynamicMobjectGraph):
        if self.root_parent is not self:
            raise Exception()
        self.mobject_graph = graph
    

    def set_dynamic_mobject(self, mobject: DynamicMobject):

        if mobject.mobject_identity is not None and mobject.mobject_identity is not self:
            raise Exception()
        
        if self.current is not None:
            self.graph.begin_state_invalidation()
        
        if self.current is not None and self.current is not mobject:
            #self.graph.begin_state_invalidation()
            self.current.submobjects = [ self ]

        #self.graph.begin_invalidation()
        #self.graph.begin_state_invalidation()

        self.current = mobject
        self.current.mobject_identity = self
        self.submobjects = [ self.current ]

        self.begin_entrance_invalidation()

    def begin_entrance_invalidation(self):
        self.invalidate(terminate_propogation_mobject=self.terminate_propogation_mobject)
        self.terminate_propogation_mobject = None

    def complete_child_registration(self):
        self.set_children(self.next_children)

    def invalidate(
            self, 
            terminate_propogation_mobject: MobjectIdentity | None = None
        ):
        self.next_children: List[MobjectIdentity] = []
        self.current_dynamic_mobject.execute_compose()

        if self.parent is not None and self.parent is terminate_propogation_mobject:
            # terminate propogation
            pass
        else:
            self.invalidate_parent()

    def invalidate_parent(self):
        if self.parent is not None:
            self.parent.invalidate()
        else:
            pass
    
    def conditional_clone(self, mobject: DynamicMobject) -> DynamicMobject:

        if mobject.identity in self.next_children:
            return mobject.clone()
        
        if mobject.identity is self.change_parent_mobject:
            replacement = self.change_parent_mobject_replacement
            self.change_parent_mobject = None
            self.change_parent_mobject_replacement = None
            return replacement
        
        return mobject

    def register_child(self, mobject: Mobject):

        if isinstance(mobject, DynamicMobject):
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
        
        if child.parent is not None:
            child.graph.begin_invalidation()
            child.parent.change_parent_mobject = child
            child.parent.change_parent_mobject_replacement = child.current_dynamic_mobject.clone()
            child.parent.terminate_propogation_mobject = parent
            child.parent.graph.begin_state_invalidation()

            child_parent = child.parent
            child.parent.invalidate()
            child_parent.terminate_propogation_mobject = None
        
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
        self.submobjects = [ mobject.direct_submobject_tree() for mobject in self.dynamic_mobjects ]

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
        **kwargs
    ):
        self.shift_flag = False
        self.scale_flag = False
        self.scale_factor = 1
        self.position_factor = VMobject().get_center()

        self._save_x: float | None = None
        self._save_y: float | None = None
        self.arrange_function = None

        self.in_composite_edit = False

        super().__init__(**kwargs)
        self.mobject_identity: MobjectIdentity | None = None
        
        MobjectIdentity(self)

        if id is not None:
            self.identity.id = id
    
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

    def invalidate(self) -> Self:
        self.is_current_dynamic_mobject_guard()  
        self.identity.set_dynamic_mobject(self)
        return self

    def restore_scale(self):
        super().scale(self.scale_factor)

    def accept_submobjects(self, *mobject: Mobject):
        self.submobjects = [ *mobject ]

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

    def direct_submobject_tree(self) -> Mobject:
        
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

            direct = convert_to_point_mobject(mobject.direct_submobject_tree())

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

    def __disconnect_graph_objects(self):

        mobject_graph = self.mobject_identity.mobject_graph

        self.mobject_identity.mobject_graph = None

        def restore_graph_objects():
            self.mobject_identity.mobject_graph = mobject_graph

        self.restore_graph_objects_function = restore_graph_objects

    def __restore_graph_objects(self):
        self.restore_graph_objects_function()

    
    def copy(self) -> DynamicMobject:
        
        dynamic_family = self.get_dynamic_family()

        for mobject in dynamic_family:
            mobject.__disconnect_graph_objects()

        parent = self.mobject_identity.parent
        self.mobject_identity.parent = None

        copy_mobject = super().copy()
        
        if not isinstance(copy_mobject, DynamicMobject):
            raise Exception()

        self.mobject_identity.parent = parent

        for mobject in dynamic_family:
            mobject.__restore_graph_objects()
        
        copy_graph = DynamicMobjectGraph()
        copy_graph.root_mobjects = { copy_mobject.identity }
        copy_mobject.identity.mobject_graph = copy_graph

        return copy_mobject
        
    def clone(self) -> DynamicMobject:
        copy_mobject = self.copy()

        for mobject in copy_mobject.get_dynamic_family():
            mobject.source_id = mobject.id
            mobject.id = uuid.uuid4()

        return copy_mobject
    
    def become(self, mobject: DynamicMobjectType) -> DynamicMobjectType:
        self.is_current_dynamic_mobject_guard()

        if not isinstance(mobject, DynamicMobject):
            raise TypeError(
                f"{type(self).__name__}.become() recieved a standard mobject."
                f"To use a standard mobject, for example, a Square(), try using `${type(self).__name__}.become(Dynamic(Square()))`"
            )

        mobject_centers = {}
        for vertex in mobject.get_dynamic_family():
            mobject_centers[vertex] = vertex.get_center()

        mobject1, mobject2 = mobject, mobject.clone()

        children1 = mobject1.children.copy()
        children2 = mobject2.children.copy()

        m = {}
        for child in children2:
            b = False
            for mobject in children1:
                if mobject.id == child.source_id:
                    m[child] = mobject
                    b = True
            if not b:
                raise Exception()

        for child in children1:
            mobject1.identity.change_parent_mobject = child.identity
            mobject1.identity.change_parent_mobject_replacement = child.clone()
            mobject1.identity.invalidate()

        for child in children2:
            mobject2.identity.change_parent_mobject = child.identity
            mobject2.identity.change_parent_mobject_replacement = m[child]
            mobject2.identity.invalidate()
        
        empty = DynamicMobject()
        empty.mobject_identity = None

        mobject2.identity.set_dynamic_mobject(empty)
        mobject2.mobject_identity = None
        mobject2.mobject_identity = self.mobject_identity

        for child in children1:
            child.identity.mobject_center = mobject_centers[child]

        self.mobject_identity.set_dynamic_mobject(mobject2)

        for child in children1:
            child.identity.mobject_center = mobject_centers[child]
        return mobject2

    def get_dynamic_family(self) -> List[DynamicMobject]:
        family: Set[DynamicMobject] = set()

        def recursive_extract(mobject: DynamicMobject):
            family.add(mobject)
            for child in mobject.children:
                recursive_extract(child)

        recursive_extract(self)
        return list(family)
        
 
    def shift(self, *vectors) -> Self:
        super().shift(*vectors)
        
        if self.in_compose:
            self.shift_during_compose_flag = True

        return self

    def scale(self, scale_factor: float, **kwargs) -> Self:
        self.scale_factor *= scale_factor
        super().scale(self.scale_factor, **kwargs)
        return self
    
    def register_child(self, mobject: DynamicMobject) -> DynamicMobject:
        return self.identity.register_child(mobject)

    def save_x(self):
        self._save_x = self.get_x()

    def save_y(self):
        self._save_y = self.get_y()

    def save_center(self):
        self.save_x()
        self.save_y()

    def restore_x(self, propogate=True):
        factor = self._save_x - self.get_x()
        if propogate:
            self.root_parent.shift(np.array([ factor, 0, 0 ]))
        else:
            self.shift(np.array([ factor, 0, 0 ]))
        return self
    
    def restore_y(self, propogate=True) -> DynamicMobject:
        factor = self._save_y - self.get_y()
        if propogate:
            self.root_parent.shift(np.array([ 0, factor, 0 ]))
        else:
            self.shift(np.array([ 0, factor, 0 ]))
        return self
    
    def restore_center(self, propogate=True):
        self.restore_x(propogate)
        self.restore_y(propogate)

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
        return [ identity.current_dynamic_mobject for identity in self.mobject_identity.children ]

    @property
    def root_parent(self) -> DynamicMobject:
        return self.identity.root_parent.current_dynamic_mobject
    
    def is_root(self):
        return self.identity.is_root()

    @property
    def id(self) -> UUID:
        return self.identity.id
    
    @id.setter
    def id(self, id: UUID):
        self.identity.id = id

    @property
    def source_id(self) -> UUID | None:
        if not self.identity.source_ids:
            return None
        
        return self.identity.source_ids[-1]
    
    @source_id.setter
    def source_id(self, id: UUID):
        self.identity.source_ids.append(id)

    @property
    def target_id(self) -> UUID | None:
        if not self.identity.target_ids:
            return None
        
        return self.identity.target_ids[-1]
    
    @target_id.setter
    def target_id(self, id: UUID):
        self.identity.target_ids.append(id)

    @property
    def graph(self) -> DynamicMobjectGraph:
        return self.identity.graph
    
    def arrange(self, direction = RIGHT, buff = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER, center = True, **kwargs) -> Self:
        self.arrange_function = lambda mobject: mobject.arrange(direction, buff, center, **kwargs)
        self.invalidate()
        return self

    def clear_arrange_function(self):
        self.arrange_function = None
        self.invalidate()

    def begin_composite_edit(self):
        for mobject in self.get_dynamic_family():
            mobject.in_composite_edit = True

    def end_composite_edit(self):
        for mobject in self.get_dynamic_family():
            mobject.in_composite_edit = False

    
    def set_color(
        self, color: ParsableManimColor = YELLOW_C, family: bool = True
    ) -> Self:
        
        if not self.in_composite_edit:
            self.begin_composite_edit()
            self.invalidate()
            super().set_color(color=color, family=family)
            self.invalidate()
            self.end_composite_edit()
        else:
            super().set_color(color=color, family=family)

        return self

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
        self.invalidate()
        return self

    def remove(self, *mobjects: Mobject) -> Self:
        
        for mobject in mobjects:
            if mobject in self._mobjects:
                self._mobjects.remove(mobject)
        
        self.invalidate()
        return self
    
    @property
    def mobjects(self) -> List[Mobject]:
        return self._mobjects

    @mobjects.setter
    def mobjects(self, mobjects: List[Mobject]):
        self._mobjects = mobjects
        self.invalidate()