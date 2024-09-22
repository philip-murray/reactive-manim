from __future__ import annotations
from abc import abstractmethod
from typing_extensions import *
from typing import List, Dict, overload, Tuple
import copy
import numpy as np
from .helpers import *

from manim import *
import functools

def reactive(dynamic_mobject_method):
    @functools.wraps(dynamic_mobject_method)
    def interceptor(self: DynamicMobject, *args, **kwargs):
        self.begin_edit()
        result = dynamic_mobject_method(self, *args, **kwargs)
        self.end_edit()
        return result
    return interceptor




class DynamicMobjectGraph():
    
    def in_edit(self):
        return self.edit_manager.in_edit() 

    def __init__(self):
        self.root_mobjects: Set[MobjectIdentity] = []
        self.subscriptions: Dict[UUID, Callable[[DynamicMobjectGraph], None]] = {}
        self.id = None

        self.prevent_match_style_update = False
        self.edit_manager = GraphEditManager(self)


        self.auto_disconnect_queue: List[Tuple[MobjectIdentity, MobjectIdentity]] = []
        self.composite_invalidation_queue = []
    
    
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

        #for function in list(self.subscriptions.values()).copy():
        #    function(self)

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

        if child in graph1.root_mobjects:
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

    def verify(self, mobject):

        #print(self.current_parent.id, self.next_parent.id, self.child.id, self.child_clone.id)
        #print(self.child.parent.id)

        #print(self.child.parent)
        #print(self.current_parent)

        if self.child.parent is not self.current_parent:
            raise Exception()
        if self.child_clone.parent is not self.next_parent:
            raise Exception()
        if self.next_parent is not mobject:
            raise Exception()

    def extract(self):
        return (self.current_parent, self.next_parent, self.child, self.child_clone)
    

class GraphEditManager():

    def in_edit(self):
        return self.in_edit()

    # INVALIDATION SYSTEM

    def require_edit_mode(self, mobject):

        if self.mode == "edit":
            return 

        self.mode = "edit"
        self.graph.begin_invalidation() # NOTIFY
        self.graph.begin_state_invalidation()

        self.primary_mobject = mobject
        self.composite_stack = []
        self.composite_queue = []
        self.composite_depth = {}

        self.auto_disconnect_queue = []
        
    def queue_composite(self, mobject):
        self.composite_stack.append(mobject)
        self.composite_queue.append(mobject)
        self.composite_depth[mobject] = len(self.composite_stack)   

    def begin_edit(self, mobject: MobjectIdentity):
        self.require_edit_mode(mobject)
        self.queue_composite(mobject)

    def run_composite_invalidation(self, mobject: MobjectIdentity):
        
        self.in_invalidation = True
        mobject.invalidate(propogate=False)
        self.in_invalidation = False

        if len(self.auto_disconnect_queue) > 0:
            raise Exception("Cannot use auto-disconnect in nested-level composite-edit")

    def process_composite_queue(self):

        sorted_composite_queue = sorted(set(self.composite_queue), key=lambda mobject: self.composite_depth[mobject], reverse=True)

        for mobject in sorted_composite_queue:
            if mobject is not self.primary_mobject:
                self.run_composite_invalidation(mobject)

        self.composite_queue = []
        self.composite_stack = []
        self.composite_depth = {}

    def queue_auto_disconnect(self, packet):
        self.auto_disconnect_queue.append(packet)

    def process_auto_disconnect_queue(self):
            
        invalidation_queue = []

        for (placeholder, child, next_parent) in self.auto_disconnect_queue:

            # next_parent.graph is GIM.graph
            # child.graph and current_parent.graph is/is-not GIM.graph

            current_parent = child.parent
            current_parent.prepare_auto_disconnect(child)

            if current_parent.graph is next_parent.graph:
                current_parent.invalidate(propogate=False)
                invalidation_queue.append(current_parent)
            else:
                current_parent.begin_entrance_invalidation()

            next_parent.prepare_auto_disconnect()
                

        #this all relies in the assumption that only on begin_entrance_invalidation, is auto-disconnect potentially required
            inv_q = []

            for (old_parent, child, new_parent, child_clone) in self.auto_disconnect_replacements:
                
                temp = child_clone
                temp_dm = child_clone.current_dynamic_mobject
                
                if old_parent.graph is not self.graph:
                #   old_parent.graph.begin_invalidation()
                    #old_parent.graph.begin_state_invalidation() # this will save_centers()
                    old_parent.begin_entrance_invalidation() # this will call old_parent.graph.notify_subscribers()
                    
                    """
                    begin_state_invalidation is SAVE_CENTERS
                    begin_entrance_invalidation will call old_parent.graph.NOTIFY_SUBSCRIBERS

                    SAVE_CENTERS is called by set_dynamic_mobject() prior to begin_entrance_invalidation() handoff, 
                    because set_dynamic_mobject is checking for (MobjectIdentity.current == None) condition on first construction
                    therefore, we need to change DynamicMobject -> MobjectIdentity -> Graph construction to just create an initial empty state
                    and then DynamicMobject will call begin_entrance_invalidation() to render
                    """
                    
                    # will not call save_centers() 
                
                old_parent.change_parent_mobject = child #MI
                old_parent.change_parent_mobject_replacement = child.current_dynamic_mobject.clone() #DM

                if old_parent.graph is self.graph:
                    old_parent.invalidate(propogate=False) # alrady in entrance_invalidation
                    inv_q.append(old_parent)
                else:
                    # Attempt to un-restructure terms in tex2, prior to handoff to tex3.
                    #old_parent.graph.begin_invalidation()
                    #old_parent.graph.begin_state_invalidation()
                    #print(old_parent, child, new_parent, child_clone)
                    #print(old_parent, old_parent.graph, old_parent.graph.edit_manager.in_invalidation)
                    old_parent.begin_entrance_invalidation()

                if child.graph is old_parent.graph or child.graph is new_parent.graph:
                    raise Exception()
                
                new_parent.change_parent_mobject = child_clone
                new_parent.change_parent_mobject_replacement = child.current_dynamic_mobject

                next_parent.change_parent_mobject = temp
                
                new_parent.invalidate(propogate=False)

            

            mobject.invalidate()
            for m in inv_q:
                m.invalidate() 

            self.auto_disconnect_replacements = [] 

    
    def __init__(
        self,
        graph
    ):
        self.mode = "default"
        self.in_invalidation = False

        self.graph = graph
        self.auto_disconnect_queue: List[AutoDisconnectPacket] = []
        self.composite_stack: List[MobjectIdentity] = []
        self.composite_queue: List[MobjectIdentity] = []
        self.composite_depth: Dict[MobjectIdentity, int] = {}
    
    
    def process_mobject(self, mobject: MobjectIdentity):

        self.in_invalidation = True
        mobject.invalidate()
        self.in_invalidation = False

        same_graph_parent_queue: Set[MobjectIdentity] = set()

        for packet in self.auto_disconnect_queue:
            packet.verify(mobject)
            current_parent, next_parent, child, child_clone = packet.extract()

            # NEED OLD PARENT NOTIFY/SAVE_CENTERS

            

            if current_parent.graph is self.graph:
                #print("A")
                # with .replace(), this is only used for same-graph handling
                current_parent.change_parent_mobject = child
                current_parent.change_parent_mobject_replacement = child.current_dynamic_mobject.clone().identity
                current_parent.invalidate(propogate=False)
                same_graph_parent_queue.append(current_parent)
            else:
                # INVALIDATE OLD PARENT BEGIN ENTRANCE IVNAL
                #print("B")
                current_parent.current_dynamic_mobject.replace(child.current_dynamic_mobject, child.current_dynamic_mobject.clone())
                

            # the child belongs to neither curr nor next
            if child.graph is current_parent.graph or child.graph is next_parent.graph:
                #print(child.graph)
                #print(current_parent.graph)
                #print(next_parent.graph)
                raise Exception()

            next_parent.change_parent_mobject = child_clone
            next_parent.change_parent_mobject_replacement = child.current_dynamic_mobject.identity
            next_parent.invalidate(propogate=False)
        
        for mobject in same_graph_parent_queue:
            mobject.invalidate()

        mobject.invalidate()
        self.auto_disconnect_queue = []




    def end_edit(self, mobject: MobjectIdentity):

        if self.in_invalidation:
            raise Exception()

        if len(self.composite_stack) == 0 or self.composite_stack[-1] is not mobject:
                #print(len(self.composite_stack) == 0)
                #print(self.composite_stack[-1] is not mobject)
                #print(self.composite_stack[-1], mobject)
                raise Exception()

        self.composite_stack.pop()

        if len(self.composite_stack) > 0:
            return
        
        if mobject is not self.primary_mobject:
            raise Exception()
        
        self.process_composite_queue()
        self.process_mobject(mobject)

        self.mode = "default"

"""
class GraphManager():
    
    def __init__(
        self:
    ):
        self.managers: Dict[DynamicMobjectGraph, GraphUpdateManager] = {}

    def begin(self, mobject: MobjectIdentity):
        if mobject.graph not in self.managers:
"""
            
            

        



class MobjectIdentity():

   

    def composite_edit(self):
        self.graph.edit_manager.composite_edit(self)

    def __init__(self, mobject: DynamicMobject):


        super().__init__()
        self.id = uuid.uuid4()
        self.source_ids: List[UUID] = []
        self.target_ids: List[UUID] = [] 


        self.match_style_invalidate_flag = False


        self.parent: MobjectIdentity | None = None
        self.children: Set[MobjectIdentity] = set()

        self.incorporated = False

        self.mobject_graph: DynamicMobjectGraph | None = None
        self.mobject_graph = DynamicMobjectGraph()
        self.mobject_graph.root_mobjects = { self }
        
        self.permit_propogation: bool = True
        self._change_parent_mobject: MobjectIdentity | None = None
        self._change_parent_mobject_replacement: MobjectIdentity | None = None
    
        #self.mobject_center = VMobject().get_center()
        
        self.current: DynamicMobject | None = mobject
        self.mobject_center = mobject.get_center()
        #self.set_dynamic_mobject(mobject)

        self._replace_mobject: DynamicMobject | None = None
        self._replace_mobject_replacement: DynamicMobject | None = None 

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
        
        """
        So, begin_state_invalidation SAVE_CENTERS must be called prior to setting the new dynamic-mobject? 
        If GraphInvalidationManager.begin_entrance_invalidation() does SAVE_CENTERS, 
        then by that point, the Mi already has a new DM with a new center? 
        """
        
        self.current = mobject
        self.current.mobject_identity = self

    def begin_entrance_invalidation(self):

        self.graph.edit_manager.begin_entrance_invalidation(self)


    def complete_child_registration(self):
        self.set_children(self.next_children)

    def invalidate(self, propogate=True):

        self.next_children: List[MobjectIdentity] = []
        self.current_dynamic_mobject.execute_compose()

        """
        dynmaic_mobject.execute_compose() runs compose() which adds children to next_children
        dynamic_mobject.execute_compose() then runs complete_child_registration() prior to returning
        this process enables for downscaling ManimMatrix in e^ManimMatrix, 
        since ManimMatrix, upon accepting new submobjects, will have the information that,
        ManimMatrix.parent = Term and Term.superscript = ManimMatrix
        """

        if propogate:
            self.invalidate_parent()
        
    def invalidate_parent(self):
        if self.parent is not None:
            self.parent.invalidate()
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

        if mobject.identity in self.next_children:
            return mobject.clone()
        
        
        #if mobject.identity.parent is not None and mobject.identity.parent is self:
        #    raise Exception("CAN THIS HAPPEN?")
        # yes, because while every mobject a graph, not every mobject has a parent. 
        
        # mobject has another parent
        if mobject.identity.parent is not None and mobject.identity.parent is not self:

            clone = mobject.clone()

            self.graph.edit_manager.queue_auto_disconnect(
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
        **kwargs
    ):
        self.shift_flag = False
        self.scale_flag = False
        self.scale_factor = 1
        self.position_factor = VMobject().get_center()

        self._save_x: float | None = None
        self._save_y: float | None = None
        self.arrange_function = None


        self.super_init = True
        super().__init__(**kwargs)
        self.super_init = False

        self.mobject_identity: MobjectIdentity | None = None
        self.mobject_identity = MobjectIdentity(self)

        if id is not None:
            self.identity.id = id

        self.begin_edit()
        self.end_edit()
    
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
        
    def begin_edit(self):

        if self.super_init:
            return

        if self.graph.edit_manager.in_invalidation:
            raise Exception()
        
        self.is_current_dynamic_mobject_guard()
        self.identity.graph.edit_manager.begin_edit(self.identity)

    def end_edit(self): 

        if self.super_init:
            return
        
        #but can't invalidate trigger compose
        if self.graph.edit_manager.in_invalidation:
            raise Exception()


        #self.identity.set_dynamic_mobject(self)
        self.identity.graph.edit_manager.end_edit(self.identity)


    def invalidate(self) -> Self:
        
        if self.super_init: # During DynamicMobject().VMobject().__init__, the MobjectIdentity is not yet initialized
            return
        
        if self.graph.edit_manager.in_invalidation:
            #print("WE ARE ATTEMPTIGN TO INVALIDATE DURIGN COMPOSE!")
            return 

        self.is_current_dynamic_mobject_guard()  
        self.identity.set_dynamic_mobject(self)
        return self

    def restore_scale(self):
        super().scale(self.scale_factor)

    def accept_submobjects(self, *mobject: Mobject):
        self.submobjects = [ *mobject ]

    @reactive
    def replace(self, current: DynamicMobject, next: DynamicMobject):
        self.identity._replace_mobject = current
        self.identity._replace_mobject_replacement = next

    
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
    
    @reactive
    def arrange(self, direction = RIGHT, buff = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER, center = True, **kwargs) -> Self:
        self.arrange_function = lambda mobject: mobject.arrange(direction, buff, center, **kwargs)
        return self

    @reactive
    def clear_arrange_function(self):
        self.arrange_function = None


    
    def composite_edit(self):
        
        if self.super_init:
            return
        
        if self.graph.edit_manager.in_invalidation:
            #print("WE ARE ATTEMPTIGN TO INVALIDATE DURIGN COMPOSE!")
            return 
        
        self.identity.composite_edit()

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