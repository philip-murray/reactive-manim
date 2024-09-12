from __future__ import annotations
from abc import abstractmethod
from typing_extensions import *
from typing import List, Dict
import uuid
import math

import manim
from manim import *
from .dynamic_mobject import DynamicMobject
from .numpy_mobject_array import NumpyMobjectArray, map_2d

def pairwise(iterable):
    
    iterator = iter(iterable)
    try:
        prev = next(iterator)
    except StopIteration:
        return
    for item in iterator:
        yield prev, item
        prev = item


class MathEncodable(DynamicMobject):

    def __init__(
        self,
        *args,
        **kwargs
    ):
        self.in_compose = False
        self._tex_string = None
        super().__init__(*args, **kwargs)

    def execute_compose(self):
        
        math_encoding = self.compose_tex_string()
        self.identity.complete_child_registration()

        if isinstance(math_encoding, list):
            self.child_components = math_encoding
            self.tex_string = self.arg_separator.join([ child.tex_string for child in math_encoding ])
        else:
            self.tex_string = math_encoding

        if self.parent and isinstance(self.parent, MathEncodable):
            pass
        else:
            math_tex = self.render_tex_string(self.tex_string)
            self.accept_mobject_from_rendered_tex_string(math_tex)

        if not isinstance(self.parent, MathEncodable):
            self.restore_scale()

        #if self.parent is None:
        self.move_to(self.identity.mobject_center)

    @abstractmethod
    def compose_tex_string() -> str | List[MathEncodable]:
        pass

    @abstractmethod
    def get_tex_string(self) -> str:
        return self.tex_string

    """
    @abstractmethod
    def rendered_tex_string_submobject_count(self, mobject: VMobject) -> int:
        return len(SingleStringMathTex(self.get_tex_string()))
    """

    @abstractmethod
    def accept_mobject_from_rendered_tex_string(self, mobject: VMobject) -> int:
        pass
    
    def render_tex_string(self, tex_string: str) -> SingleStringMathTex:
        return SingleStringMathTex(tex_string)

    def __str__(self) -> str:
        if self.tex_string is None:
            return f"{self.__class__.__name__}(pre-init)"
        else:
            return f"{self.__class__.__name__}({self.tex_string})"


class MathComponent(MathEncodable):

    def adapt_input(self, term: Any) -> Any:

        if isinstance(term, MathEncodable):
            return term
        
        if isinstance(term, (str, int, float)):
            return MathString(str(term))
        
        if isinstance(term, List):
            return MathTex(*term) 
        
        """
        if isinstance(term, Mobject):
            return DefaultMobjectAdapter(term)
        
        return TypeError("term passed into MathComponent recieved type ", type(term))
        """
        return term

    def register_child(self, term: Any, ignore_type: bool = False) -> MathEncodable:
        
        if term is None:
            if self.permit_none_children:
                return term
            
            raise Exception()

        if not isinstance(term, MathEncodable) and not ignore_type:
            if isinstance(term, manim.MathTex):
                raise Exception("Use reactive_manim.MathTex instead of manim.MathTex")
            raise Exception("Recieved non-MathEncodble input of type ", type(term))
        
        term = super().register_child(term)
        return term

    def __init__(
        self,
        permit_none_children: bool = False,
        **kwargs,
    ):
        self.arg_separator = " "
        self.permit_none_children = permit_none_children
        super().__init__(**kwargs)
    
    @abstractmethod
    def compose_tex_string(self) -> str | List[MathEncodable]:
        pass

    def accept_mobject_from_rendered_tex_string(self, mobject: VMobject) -> int:
        submobject_count = self.distribute_rendered_tex_string_to_child_components(mobject)
        self.set_submobjects()
        return submobject_count

    def distribute_rendered_tex_string_to_child_components(self, mobject: VMobject) -> int:

        total_change_in_width = 0
        curr_index = 0

        for _, term in enumerate(self.child_components):
            
            #if isinstance(term, MathStringFragment):
            #    term_submobject_count = term.submobject_count
            #else:
            #    term_submobject_count = len(SingleStringMathTex(term.tex_string)) 

            """
            term_submobject_count = term.rendered_tex_string_submobject_count()

            new_index = curr_index + term_submobject_count + len("".join(self.arg_separator.split()))
            rendered_tex_string_portion = math_tex[curr_index:new_index]
            """

            term_submobject_count = term.accept_mobject_from_rendered_tex_string(mobject[curr_index:])
            new_index = curr_index + term_submobject_count + len("".join(self.arg_separator.split()))
            rendered_tex_string_portion = mobject[curr_index:new_index]

            if term.family_members_with_points():

                shift = term.get_left()[0] - rendered_tex_string_portion.get_left()[0]
                term.set_x(term.get_x() - shift)

                self.align_child(term, rendered_tex_string_portion)

                #term.align_to(rendered_tex_string_portion.get_left(), LEFT)
                #term.align_to(rendered_tex_string_portion.get_bottom(), DOWN)

                change_in_width = term.width - rendered_tex_string_portion.width # change_in_width=0 in standard cases
                terms_right = VGroup(*mobject[new_index:]) 
                terms_right.shift(RIGHT * change_in_width)
                total_change_in_width += change_in_width
            
            curr_index = new_index

        """
        center_displacement = total_change_in_width / 2
        
        for term in self.child_components:
            term.shift(LEFT * center_displacement)"""

        return curr_index

    def set_submobjects(self):
        
        submobjects = []
        for term in self.child_components:
            if term.has_no_points() and not term.submobjects:
                continue

            submobjects.append(term)
        self.submobjects = submobjects
    
    def align_child(self, term: VMobject, rendered_tex_string: VMobject):
        term.set_y(rendered_tex_string.get_y())
    

class MathTex(MathComponent):

    def __init__(
        self, 
        *terms: Any,
        **kwargs
    ):
        self._terms = self.adapt_terms(terms)
        super().__init__(**kwargs)

    def compose_tex_string(self):
        self._terms = [ self.register_child(term) for term in self._terms ]
        return self._terms
    
    def adapt_terms(self, terms):
        return [ self.adapt_input(term) for term in terms ]

    @property
    def terms(self):
        return self._terms

    @terms.setter
    def terms(self, terms: List[Any]):
        self._terms = self.adapt_terms(terms)
        self.invalidate()

    def insert(self, index: int, term):
        self._terms.insert(index, self.adapt_input(term))
        self.invalidate()

    def append(self, term):
        self._terms.append(self.adapt_input(term))
        self.invalidate()

    def remove(self, term):
        self._terms.remove(term)
        self.invalidate()

    def __len__(self) -> int:
        return len(self._terms)

    def __getitem__(self, index: int):
        return self._terms[index]

    def __setitem__(self, index: int, term):
        self._terms[index] = self.adapt_input(term)
        self.invalidate()

    def __iter__(self):
        return iter(self._terms)

class MathString(MathEncodable):

    def __init__(self, tex_string: str, **kwargs):
        self.tex_string = tex_string
        
        mobject = SingleStringMathTex(tex_string)
        self.submobject_group = mobject
        self.submobjects = mobject.submobjects
        super().__init__(**kwargs)

    def compose_tex_string(self) -> str:
        return self.tex_string

    def set_tex_string(self, tex_string: str) -> Self:
        self.tex_string = tex_string
        self.invalidate()
        return self

    def accept_mobject_from_rendered_tex_string(self, mobject: VMobject) -> int:

        submobject_count = len(SingleStringMathTex(self.tex_string))
        submobjects = mobject.submobjects[:submobject_count]
        self.submobject_group = VGroup(*submobjects).match_style(self.submobject_group)

        self.submobjects =  [ *submobjects ]
        return submobject_count


class MathStringFragment(MathEncodable):

    def __init__(self, tex_string: str, submobject_count: int = 0):
        self.tex_string = tex_string
        self.submobject_count = submobject_count
        self.first = True

        super().__init__()

    def execute_compose(self):

        if self.parent:
            super().execute_compose()

    def compose_tex_string(self):
        return self.tex_string
    
    def accept_mobject_from_rendered_tex_string(self, mobject: VMobject) -> int:

        if self.submobject_count == 0:
            self.submobjects = [ ]
        else:
            group = mobject[:self.submobject_count]

            if self.first == False:
                group.match_style(self)
            else:
                self.first = False
            
            self.submobjects = group.submobjects
        
        return self.submobject_count

class HSpaceTex(MathString):

    def __init__(self, buff):
        if isinstance(buff, (float, int)):
            super().__init__(f"\\hspace{{{buff}em}}")
        else:
            super().__init__(f"\\hspace{{{buff}}}")


class MathSequence(MathComponent):

    def __init__(
        self, 
        *sequence_terms,
        include_commas = True,
        extra_buff = 1,
    ):
        self.sequence_terms = [ self.adapt_input(term) for term in sequence_terms ]
        self.include_commas = include_commas
        self.extra_buff = extra_buff

        self.commas = []
        if self.include_commas:
            for _ in range(1, len(self.sequence_terms)):
                self.commas.append(MathString(","))

        super().__init__()

    def compose_tex_string(self):

        self.sequence_terms = [ self.register_child(term) for term in self.sequence_terms ]
        self.commas = [ self.register_child(comma) for comma in self.commas ]
        spacers = []

        components = []
        if self.include_commas:
            if self.sequence_terms:
                components.append(self.sequence_terms[0])
            for comma, term in zip(self.commas, self.sequence_terms[1:]):
                x = HSpaceTex(self.extra_buff)
                components += [ comma, x, term ]
                spacers += [x]
        else:
            if self.sequence_terms:
                components.append(self.sequence_terms[0])
            for term in self.sequence_terms[1:]:
                x = HSpaceTex(self.extra_buff)
                components += [ x, term ]
                spacers += [x]
        
        self.spacers = spacers
        return components

    def adapt_terms(self, terms):
        return [ self.adapt_input(term) for term in terms ]

    @property
    def terms(self):
        return self.sequence_terms

    @terms.setter
    def terms(self, terms: List[Any]):
        self.sequence_terms = self.adapt_terms(terms)
        self.invalidate()

    def remove(self, term):

        for index, _term in enumerate(self.sequence_terms):
            if _term is term:
                break

        self.sequence_terms.pop(index)
        
        if self.commas:
            if index == len(self.commas):
                index -= 1
            self.commas.pop(index)

        self.invalidate()

    def insert(self, index, term):
        term = self.adapt_input(term)

        if self.sequence_terms:
            self.commas.insert(index, MathString(","))

        self.sequence_terms.insert(index, term)
        self.invalidate()

    def append(self, term):
        self.insert(len(self), term)

    def __len__(self) -> int:
        return len(self.sequence_terms)

    def __getitem__(self, index: int):
        return self.sequence_terms[index]

    def __setitem__(self, index: int, term):
        self.sequence_terms[index] = self.adapt_input(term)
        self.invalidate()

    def __iter__(self):
        return iter(self.sequence_terms)


class MathList(MathSequence):

    def __init__(
        self,
        *sequence_terms,
        include_commas = True,
        extra_inner_buff = 0.5,
        extra_outer_buff = 0.35,
        bracket_l = "[",
        bracket_r = "]"
    ):
        self.bracket_l = MathString(bracket_l)
        self.bracket_r = MathString(bracket_r)
        self.extra_inner_buff = extra_inner_buff
        self.extra_outer_buff = extra_outer_buff
        
        super().__init__(*sequence_terms, include_commas=include_commas, extra_buff=extra_inner_buff)

    def compose_tex_string(self):

        self.sequence_terms = [ self.register_child(term) for term in self.sequence_terms ]
        self.commas = [ self.register_child(comma) for comma in self.commas ]
        spacers = []

        self.bracket_l = self.register_child(self.bracket_l)
        self.bracket_r = self.register_child(self.bracket_r)
        
        components = []
        components.append(self.bracket_l)
        components.append(HSpaceTex(self.extra_outer_buff))
        if self.include_commas:
            if self.sequence_terms:
                components.append(self.sequence_terms[0])
            for comma, term in zip(self.commas, self.sequence_terms[1:]):
                x = HSpaceTex(self.extra_inner_buff)
                components += [ comma, x, term ]
                spacers += [x]
        else:
            if self.sequence_terms:
                components.append(self.sequence_terms[0])
            for term in self.sequence_terms[1:]:
                x = HSpaceTex(self.extra_inner_buff)
                components += [ x, term ]
                spacers += [x]
        
        components.append(HSpaceTex(self.extra_outer_buff))
        components.append(self.bracket_r)
        self.spacers = spacers
        return components


class Term(MathComponent):

    def __init__(
            self, 
            term, 
            superscript = None, 
            subscript = None,
        ):
        
        self.base = self.adapt_input(term)
        self._subscript = self.adapt_input(subscript)
        self._superscript = self.adapt_input(superscript)

        self.bracket1 = MathString(r"{")
        self.bracket2 = MathString(r"}^")
        self.bracket3 = MathString(r"{")
        self.bracket4 = MathString(r"}_")
        self.bracket5 = MathString(r"{")
        self.bracket6 = MathString(r"}")

        super().__init__(permit_none_children=True)

    def compose_tex_string(self):

        self.base = self.register_child(self.base)
        self._subscript = self.register_child(self._subscript)
        self._superscript = self.register_child(self._superscript)

        if self._superscript is None and self._subscript is None:
            return [ self.base ]
        
        if self._superscript is None:
            return ([ 
                self.bracket1, 
                self.base, 
                self.bracket2, 
                self.bracket3, 
                self.bracket4, 
                self.bracket5, 
                self._subscript, 
                self.bracket6 
            ])

        if self._subscript is None:
            return ([ 
                self.bracket1, 
                self.base, 
                self.bracket2, 
                self.bracket3, 
                self._superscript, 
                self.bracket4, 
                self.bracket5, 
                self.bracket6 
            ])
        
        return ([ 
            self.bracket1, 
            self.base, 
            self.bracket2, 
            self.bracket3, 
            self._superscript, 
            self.bracket4, 
            self.bracket5, 
            self._subscript, 
            self.bracket6 
        ])

    def align_child(self, term, rendered_tex_string):

        if term is self.superscript:
            delta = term.get_bottom()[1] - rendered_tex_string.get_bottom()[1]
            term.set_y(term.get_y() - delta)

        if term is self.subscript:
            delta = term.get_top()[1] - rendered_tex_string.get_top()[1]
            term.set_y(term.get_y() - delta)

    @property
    def term(self):
        return self.base
    
    @term.setter
    def term(self, term: Any):
        self.base = self.adapt_input(term)
        self.invalidate()
    
    @property
    def subscript(self):
        return self._subscript
    
    @subscript.setter
    def subscript(self, subscript: Any):
        self._subscript = self.adapt_input(subscript)
        self.invalidate()
    
    @property
    def superscript(self):
        return self._superscript
    
    @superscript.setter
    def superscript(self, superscript: Any):
        self._superscript = self.adapt_input(superscript)
        self.invalidate()

    def remove(self, mobject):

        if mobject is self.term:
            self.term = MathString("")

        if mobject is self._superscript:
            self._superscript = None

        if mobject is self._subscript:
            self._subscript = None
        
        self.invalidate()


class Parentheses(MathComponent):

    def __init__(
        self,
        inner
    ):
        self._inner = self.adapt_input(inner)
        self.spacer = MathString("\mspace{-3mu}")
        self.bracket_l = BracketMathStringFragment(r"\left(")
        self.bracket_r = BracketMathStringFragment(r"\right)")
        super().__init__()

    def compose_tex_string(self):

        self._inner = self.register_child(self._inner)
        self.spacer = self.register_child(self.spacer)
        self.bracket_l = self.register_child(self.bracket_l)
        self.bracket_r = self.register_child(self.bracket_r)

        return ([
            self.spacer,
            self.bracket_l,
            self._inner,
            self.bracket_r
        ])
    
    @property
    def inner(self):
        return self._inner
    
    @inner.setter
    def inner(self, inner: Any):
        self._inner = self.adapt_input(inner)
        self.invalidate()


    def __len__(self) -> int:
        return len(self._inner)

    def __getitem__(self, index: int):
        return self._inner[index]

    def __setitem__(self, index: int, term):
        self._inner[index] = self.adapt_input(term)
        self.invalidate()
        

class Function(MathComponent):

    def __init__(
        self,
        name,
        input
    ):
        self._name = self.adapt_input(name)
        self._input = self.adapt_input(input)
        self._parentheses = Parentheses(self._input)
        super().__init__()

    def compose_tex_string(self):
        self._name = self.register_child(self._name)
        self._parentheses = self.register_child(self._parentheses)
        self._input = self._parentheses._inner

        return ([
            self._name,
            self._parentheses
        ])
    
    @property
    def parentheses(self):
        return self._parentheses

    @property
    def input(self):
        return self._input
    
    @input.setter
    def input(self, input: Any):
        self._input = self.adapt_input(input)
        self.invalidate()

    @property
    def function_name(self):
        return self._name

    @function_name.setter
    def function_name(self, name):
        self._name = self.adapt_input(name)
        self.invalidate()


class Fraction(MathComponent):

    def __init__(
        self,
        numerator,
        denominator
    ):
        self._numerator = self.adapt_input(numerator)
        self._vinculum = MathStringFragment("", submobject_count=1)
        self._denominator = self.adapt_input(denominator)
        super().__init__()

    def compose_tex_string(self):
        self._numerator = self.register_child(self._numerator)
        self._vinculum = self.register_child(self._vinculum)
        self._denominator = self.register_child(self._denominator)

        self.child_components = [ self._numerator, self._vinculum, self._denominator ]
        return r"\frac{" + self._numerator.get_tex_string() + r"}{" + self._denominator.get_tex_string() + r"}"

    @property
    def numerator(self):
        return self._numerator

    @numerator.setter
    def numerator(self, numerator):
        self._numerator = self.adapt_input(numerator)
        self.invalidate()
    
    @property
    def vinculum(self):
        return self._vinculum
    
    @property
    def denominator(self):
        return self._denominator

    @denominator.setter
    def denominator(self, denominator):
        self._denominator = self.adapt_input(denominator)
        self.invalidate()


class BracketMathStringFragment(MathStringFragment):

    def __init__(
        self,
        tex_string: str = ""
    ):
        self.first_render = True
        super().__init__(tex_string)

    def bracket_length(self, mobject: VMobject):

        if len(mobject.submobjects) == 1:
            return 1
        
        bracket_submobjects = []
        
        for submobject1, submobject2 in pairwise(mobject.submobjects):
            bracket_submobjects.append(submobject1)

            bottom_points = []
            top_points = []

            for point in submobject1[0].points:
                if math.isclose(point[1], submobject1.get_bottom()[1]):
                    bottom_points.append(point)

            for point in submobject2[0].points:
                if math.isclose(point[1], submobject2.get_top()[1]):
                    top_points.append(point)

            min_bx = min(bottom_points, key=lambda point: point[0])[0]
            max_bx = max(bottom_points, key=lambda point: point[0])[0]
            min_tx = min(top_points, key=lambda point: point[0])[0]
            max_tx = max(top_points, key=lambda point: point[0])[0]

            def overlap(interval1, interval2):
                a1, a2 = interval1
                b1, b2 = interval2

                overlap_start = max(a1, b1)
                overlap_end = min(a2, b2)

                overlap_length = max(0, overlap_end - overlap_start)

                total_length = max(a2, b2) - min(a1, b1)

                if total_length == 0:
                    return 0.0 
                percentage_overlap = (overlap_length / total_length)

                return percentage_overlap

            ov = overlap([min_bx, max_bx], [min_tx, max_tx])
            if ov < 0.99:
                break

            dist_y = submobject2.get_top()[1] - submobject1.get_bottom()[1]
            dist_x = max_bx - min_bx 
            
            if dist_y < 0:
                if -dist_y/dist_x > 0.15:
                    break

            if submobject2 is mobject.submobjects[-1]:
                bracket_submobjects.append(submobject2)

        return len(bracket_submobjects)
    
    def accept_mobject_from_rendered_tex_string(self, mobject: VMobject) -> int:
        submobject_count = self.bracket_length(mobject)

        if submobject_count == 0:
            self.submobjects = []
        else:
            group = mobject[:submobject_count]

            if not self.first_render:
                group.match_style(self)
            else:
                self.first_render = False
        
            self.submobjects = [ *group ]

        return submobject_count


class MathCases(MathComponent):

    def __init__(
        self,
        *lines: MathEncodable
    ):
        self._lines = self.adapt_lines(lines)
        self.begin_cases_fragment = BracketMathStringFragment(r"\begin{cases}") #MathStringFragment(r"\begin{cases}", 1)
        self.end_cases_fragment = MathStringFragment(r"\end{cases}", 0)
        self.replacement_bracket = None
        super().__init__()

    def compose_tex_string(self):
        self._lines = [ self.register_child(line) for line in self._lines ]
        self.begin_cases_fragment = self.register_child(self.begin_cases_fragment)

        space = r"\left\{ \vphantom{\begin{cases}"
        for line in self._lines:
            space += r"\\"
        space += r"\end{cases}} \right."

        self.replacement_bracket = self.render_tex_string(space)

        processed_lines = []

        for index, line in enumerate(self._lines):
            processed_lines.append(line)
            if index < len(self.lines) - 1:
                fragment = MathStringFragment(r"\\", 0)
                processed_lines.append(fragment)

        return ([
            self.begin_cases_fragment,
            *processed_lines,
            self.end_cases_fragment
        ])
    
    def adapt_lines(self, lines):
        return [ self.adapt_input(line) for line in lines ]
    
    @property
    def bracket(self) -> MathEncodable:
        return self.begin_cases_fragment
    
    @property
    def lines(self) -> List[MathEncodable]:
        return self._lines
    
    @lines.setter
    def lines(self, lines: List[Any]):
        self._lines = self.adapt_lines(lines)
        self.invalidate()

    def insert(self, index: int, line):
        self._lines.insert(index, self.adapt_input(line))
        self.invalidate()

    def append(self, line):
        self._lines.append(self.adapt_input(line))
        self.invalidate()

    def remove(self, line):
        self._lines.remove(line)
        self.invalidate()
    
    def __len__(self) -> int:
        return len(self._lines)

    def __getitem__(self, index: int):
        return self._lines[index]

    def __setitem__(self, index: int, line):
        self._lines[index] = self.adapt_input(line)
        self.invalidate()

    def __iter__(self):
        return iter(self._lines)
    

class CaseLine(MathComponent):

    def __init__(
        self,
        output,
        condition,
    ):
        self._output = self.adapt_input(output)
        self._condition = self.adapt_input(condition)
        super().__init__()

    def compose_tex_string(self):
        self._output = self.register_child(self._output)
        self._condition = self.register_child(self._condition)

        return [ self._output, MathStringFragment(r"&", 0), self._condition ]
    
    @property
    def output(self):
        return self._output

    @output.setter
    def output(self, output):
        self._output = self.adapt_input(output)
        self.invalidate()

    @property
    def condition(self):
        return self._condition

    @condition.setter
    def condition(self, condition):
        self._condition = self.adapt_input(condition)
        self.invalidate()
    

class MathMatrix(MathComponent):

    def __init__(
        self,
        matrix: List[List[Any]]
    ):
        self.bracket_l = BracketMathStringFragment(r"\begin{bmatrix}")
        self.bracket_r = BracketMathStringFragment(r"\end{bmatrix}")

        self._matrix = NumpyMobjectArray.from_mobjects(
            map_2d(matrix, lambda elem: self.adapt_input(elem))
        )
        super().__init__()

    def compose_tex_string(self):

        if not self._matrix.is_2d():
            raise Exception()

        self.bracket_l = self.register_child(self.bracket_l)   
        self._matrix = NumpyMobjectArray.from_mobjects(
            map_2d(self._matrix.tolist(), lambda elem: self.register_child(elem) )
        )
        self.bracket_r = self.register_child(self.bracket_r)

        def mobject_row_encoding(mobject_row):
            encoding = []
            front_mobject, *next_mobjects = mobject_row

            if front_mobject:
                encoding += [ front_mobject ]

            for mobject in next_mobjects:
                encoding += [ MathStringFragment(r"&", 0), mobject ]

            return encoding
        
        encoding = []
        front_row, *next_rows = self._matrix.tolist()

        if front_row:
            encoding += [ *mobject_row_encoding(front_row) ]

        for row in next_rows:
            encoding += [ MathStringFragment(r"\\", 0), *mobject_row_encoding(row) ]

        return ([
            self.bracket_l,
            *encoding,
            self.bracket_r
        ])

    @property
    def matrix(self):
        return self._matrix.tolist()
    
    @matrix.setter
    def matrix(self, matrix: List[List[Any]]):
        self._matrix = NumpyMobjectArray.from_mobjects(
            map_2d(matrix, lambda elem: self.adapt_input(elem))
        )
        self.invalidate()

    def __len__(self) -> int:
        return len(self._matrix.tolist())

    def __getitem__(self, key):
        return self._matrix.tolist().__getitem__(key)

    def __iter__(self):
        return iter(self._matrix.tolist())
    

class Root(MathComponent):

    def __init__(
        self,
        radicand,
        index = None
    ):
        self._radicand = radicand
        self._radical_symbol = MathStringFragment("", submobject_count=2)
        self._index = index
        super().__init__(permit_none_children=True)

    def compose_tex_string(self):

        self._radicand = self.register_child(self._radicand)
        self._radical_symbol = self.register_child(self._radical_symbol)
        self._index = self.register_child(self._index)
        
        if self.index is None:
            self.child_components = [ self._index, self._radical_symbol, self._radicand ]
            return f"\\sqrt[{self._index.get_tex_string()}]{{{self._radicand.get_tex_string()}}}"
        else:
            self.child_components = [ self._radical_symbol, self._radicand ]
            return f"\\sqrt[{self._index.get_tex_string()}]{{{self._radicand.get_tex_string()}}}"
    
    @property
    def radicand(self):
        return self._radicand

    @radicand.setter
    def radicand(self, radicand):
        self._radicand = self.adapt_input(radicand)
        self.invalidate()

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, index):
        self._index = self.adapt_input(index)
        self.invalidate()

    @property
    def radical_symbol(self):
        return self._radical_symbol