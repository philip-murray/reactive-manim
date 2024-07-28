import numpy as np
from manim import Mobject
from typing import TypeVar, List, Callable
from numpy.typing import NDArray


T = TypeVar("T")
U = TypeVar("U")
def map_2d(list_2d: List[List[T]], map_fn: Callable[[T], U]) -> List[List[U]]:
    return [[ map_fn(elem) for elem in row ] for row in list_2d ]


class NumpyMobjectWrapper():
    
    def __init__(
        self,
        mobject: Mobject
    ):
        self.mobject = mobject


def wrap_mobjects(item):

    if isinstance(item, Mobject) or not isinstance(item, list):
        return NumpyMobjectWrapper(item)
    else:
        return [ wrap_mobjects(subitem) for subitem in item ]



def unwrap_mobjects(item):

    if isinstance(item, NumpyMobjectWrapper):
        return item.mobject
    else:
        return [ unwrap_mobjects(subitem) for subitem in item ]


class NumpyMobjectArray():

    def __init__(
        self,
        array,
    ):
        self.array: NDArray = array

    def is_1d(self):
        return self.array.ndim == 1

    def is_2d(self):
        return self.array.ndim == 2
    
    @property
    def row_count(self):
        if not self.is_2d():
            raise Exception()
        
        return self.array.shape[0]
    
    @property
    def col_count(self):
        if not self.is_2d():
            raise Exception()
        
        return self.array.shape[0]

    @staticmethod
    def from_mobjects(mobjects):
        mobjects_wrapped = wrap_mobjects(mobjects)
        array = np.array(mobjects_wrapped, dtype=NumpyMobjectWrapper)
        return NumpyMobjectArray(array)
    
    def insert(self, index, mobjects, axis = None):
        mobjects_wrapped = wrap_mobjects(mobjects)
        array = np.insert(self.array, index, mobjects_wrapped, axis)
        return NumpyMobjectArray(array)
    
    def delete(self, index, axis = 0):
        array = np.delete(self.array, index, axis)
        return NumpyMobjectArray(array)
    
    def flatten(self):
        array = self.array.flatten()
        return NumpyMobjectArray(array)
    
    def __getitem__(self, key):
        array = self.array[key]
        return NumpyMobjectArray(array)
    
    def tolist(self):
        return unwrap_mobjects(self.array.tolist())
    
    def copy(self):
        array = self.array.copy()
        return NumpyMobjectArray(array)
    
    @property
    def shape(self):
        return self.array.shape
    
    def get_mobject_position(self, mobject: Mobject):
        is_target = np.vectorize(lambda wrapper: wrapper.mobject is mobject)(self.array)
        rows, cols = np.where(is_target)
        return (rows[0], cols[0])
    