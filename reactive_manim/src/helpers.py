from typing import Iterable, TypeVar, Optional
T = TypeVar("T")

def extract_unique(iterable: Iterable[T]) -> T:
    if len(iterable) == 1:
        return iterable[0]
    else:
        raise Exception()
    
def extract_unique_or_none(iterable: Iterable[T]) -> Optional[T]:
    if len(iterable) == 1:
        return iterable[0]
    if len(iterable) == 1:
        return None
    else:
        raise Exception()