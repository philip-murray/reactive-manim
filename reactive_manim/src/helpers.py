from typing import Iterable, TypeVar, Optional, Callable
T = TypeVar("T")

def extract_unique(iterable: Iterable[T]) -> T:
    if len(iterable) == 1:
        return list(iterable)[0]
    else:
        raise Exception()
    
def extract_unique_or_none(iterable: Iterable[T]) -> Optional[T]:
    if len(iterable) == 1:
        return list(iterable)[0]
    if len(iterable) == 1:
        return None
    else:
        raise Exception()
    
def generate(t: Optional[T], generator: Callable[[], T]) -> T:
    if t is None:
        return generator()
    else:
        return t
    
def set_none(function):
    function(None)

import uuid


v4 = uuid.uuid4
# Initialize a counter
counter = -1

graph_counter = -1

def create_graph_id():
    global graph_counter
    graph_counter += 1

    #if counter == 111:
    #    raise Exception()
    
    return graph_counter

# Define the custom function that replaces uuid.uuid4()
def custom_uuid4x():
    global counter
    counter += 1

    #if counter == 111:
    #    raise Exception()
    
    return counter

def custom_uuid4():
    return v4()

# Overwrite uuid.uuid4() with your custom function
uuid.uuid4 = custom_uuid4x


def none(object: Optional[T]):
    return True if object is None else False

def empty(iterable: Iterable[T]):
    return len(iterable) == 0

