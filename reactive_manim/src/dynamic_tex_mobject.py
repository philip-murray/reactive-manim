from __future__ import annotations
from abc import abstractmethod
from typing_extensions import *
from typing import List, Dict
import math

import manim
from manim import *
from .dynamic_mobject import DynamicMobject, reactive
from .numpy_mobject_array import NumpyMobjectArray, map_2d

config.tex_template.add_to_preamble("\\let\\originalleft\\left \\let\\originalright\\right \\renewcommand{\\left}{\\mathopen{}\\mathclose\\bgroup\\originalleft} \\renewcommand{\\right}{\\aftergroup\\egroup\\originalright}")

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
        color = None,
        font_size = None,
        adapter = False,
        *args,
        **kwargs
    ):
        self.adapter = adapter
        self.in_compose = False
        self._tex_string = None

        self.math_encodable_init = True
        self.math_encodable_init_color = color
        
        if font_size is not None:
            scale_factor = font_size / 48
        else:
            scale_factor = 1

        super().__init__(scale_factor=scale_factor, *args, **kwargs)
        if color is not None:
            self.set_color(self.math_encodable_init_color)
        self.math_encodable_init = False

    def execute_compose(self):
        
        math_encoding = self.compose_tex_string()
        self.identity.complete_child_registration()

        if isinstance(math_encoding, list):
            self.child_components = math_encoding
            self.tex_string = self.arg_separator.join([ child.tex_string for child in math_encoding ])
        else:
            self.tex_string = math_encoding

        if self.parent and isinstance(self.parent, MathEncodable):# and not self.parent.adapter:
            # ManimMatrix uses an MobjectMatrix to position math components, 
            # The scale of the math components is determined by the ManimMatrix's scaling factor, and not superscript level. 
            # We do not use component.accept_mobject(...) to inject latex submobjects into the component, since we disregard prior superscript context.
            # Therefore, we must render as if the component were the root, however, it can still pull render_tex_string() from the root context. 
            pass
        else:
            math_tex = self.render_tex_string(self.tex_string)
            math_tex.scale(self.scale_factor)

            self.accept_mobject_from_rendered_tex_string(math_tex)

            #if not isinstance(self.parent, MathEncodable):
            #    self.restore_scale()

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

        if self.math_encodable_init and self.math_encodable_init_color is not None and False:
            return SingleStringMathTex(tex_string, color=self.math_encodable_init_color)
        else:
            return SingleStringMathTex(tex_string)

    def __str__(self) -> str:
        if self.tex_string is None:
            return f"{self.__class__.__name__}(pre-init)"
        else:
            return f"{self.__class__.__name__}({self.tex_string})"
    
    def find_root_encodable(self):
        parent = self.parent
        if parent is not None and isinstance(parent, MathEncodable):
            return parent.find_root_encodable()
        else:
            return self

    """ 
    @abstractmethod
    def is_equation(self):
        if isinstance(self, MathTex) and self.equation_guard():
            return self
        
    @abstractmethod
    def is_expression(self):
        pass
        
    def find_root_expression(self):
        pass

    def contains_tex(self, tex):
        pass
        
    def sign() -> Optional[MathEncodable]:
        if self.is_expression():
    """

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
        self.math_tex_flag = True
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
    #@reactive
    def terms(self, terms: List[Any]):
        self._terms = self.adapt_terms(terms)
        self.begin_edit()
        self.end_edit()

    @reactive
    def insert(self, index: int, term):
        self._terms.insert(index, self.adapt_input(term))
    

    @reactive
    def append(self, term):
        self._terms.append(self.adapt_input(term))
        

    @reactive
    def remove(self, term):
        self._terms.remove(term)
        

    def __len__(self) -> int:
        return len(self._terms)

    def __getitem__(self, index: int):
        return self._terms[index]
    

    @reactive
    def __setitem__(self, index: int, term):
        self._terms[index] = self.adapt_input(term)
        

    def __iter__(self):
        return iter(self._terms)
    
    def equation_guard(self):
        if len(self._terms) != 3:
            raise Exception("LHS/RHS properties require len(tex.terms) == 3, where tex[0] is LHS, tex[1] is comparison-symbol, and tex[2] is RHS")
    
    @property
    def LHS(self):
        self.equation_guard()
        return self._terms[0]
    
    @LHS.setter
    def LHS(self, term):
        self.equation_guard()
        self._terms[0] = self.adapt_input(term)
        self.begin_edit()
        self.end_edit()

    @property
    def RHS(self):
        self.equation_guard()
        return self._terms[2]
    
    @RHS.setter
    def RHS(self, term):
        self.equation_guard()
        self._terms[2] = self.adapt_input(term)
        self.begin_edit()
        self.end_edit()

class MathString(MathEncodable):

    def __init__(self, tex_string: str, **kwargs):
        self.tex_string = tex_string
        self.store_sm_count = 8
        
        mobject = SingleStringMathTex(tex_string)
        self.submobject_group = mobject
        self.submobjects = mobject.submobjects
        super().__init__(**kwargs)

    def compose_tex_string(self) -> str:
        return self.tex_string
    
    @reactive
    def set_tex_string(self, tex_string: str) -> Self:
        self.tex_string = tex_string
        
        return self

    def accept_mobject_from_rendered_tex_string(self, mobject: VMobject) -> int:
        
        #if self.tex_string != "" and len(mobject) == 0:
        #    raise Exception("zero on ", self.tex_string)


        submobject_count = len(SingleStringMathTex(self.tex_string))
        #self.store_sm_count = submobject_count
        submobjects = mobject.submobjects[:submobject_count]

        #if self.id == "Y":
        #    AR.append(VGroup(*submobjects).copy())

        if False:
            # don't match style
            pass
        else:
            self.submobject_group = VGroup(*submobjects).match_style(self.submobject_group)

        self.submobjects =  [ *submobjects ]

        #if self.id == "Y":
        #    BR.append(self.submobject_group.copy())

        return submobject_count

    def __repr__(self):
        return f"MathString({self.id, self.tex_string})"

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
    @reactive
    def terms(self, terms: List[Any]):
        self.sequence_terms = self.adapt_terms(terms)

    @reactive
    def remove(self, term):

        for index, _term in enumerate(self.sequence_terms):
            if _term is term:
                break

        self.sequence_terms.pop(index)
        
        if self.commas:
            if index == len(self.commas):
                index -= 1
            self.commas.pop(index)
        
    @reactive
    def insert(self, index, term):
        term = self.adapt_input(term)

        if self.sequence_terms:
            self.commas.insert(index, MathString(","))

        self.sequence_terms.insert(index, term)

    def append(self, term):
        self.insert(len(self), term)

    def __len__(self) -> int:
        return len(self.sequence_terms)

    def __getitem__(self, index: int):
        return self.sequence_terms[index]

    @reactive
    def __setitem__(self, index: int, term):
        self.sequence_terms[index] = self.adapt_input(term)

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
            paren: bool = False
        ):
        
        self._term = self.adapt_input(term)
        self._subscript = self.adapt_input(subscript)
        self._superscript = self.adapt_input(superscript)
        self._parentheses = paren

        super().__init__(permit_none_children=True)

    def compose_tex_string(self):

        if self._parentheses == False:
            self._parentheses = None

        if self._parentheses == True:
            self._parentheses = ParenSymbol()

        if self._parentheses is None or self._parentheses is False:
            
            self._term = self.register_child(self._term)
            self._subscript = self.register_child(self._subscript)
            self._superscript = self.register_child(self._superscript)
            
            if self._superscript is None and self._subscript is None:
                self.child_components = [ self._term ]
                return self._term.get_tex_string()

            if self._superscript is None:
                self.child_components = [ self._term, self._subscript ]
                return f"{{{self._term.get_tex_string()}}}_{{{self._subscript.get_tex_string()}}}"

            if self._subscript is None:
                self.child_components = [ self._term, self._superscript ]
                return f"{{{self._term.get_tex_string()}}}^{{{self._superscript.get_tex_string()}}}"
            
            self.child_components = [ self._term, self._superscript, self._subscript ]
            return f"{{{self._term.get_tex_string()}}}^{{{self._superscript.get_tex_string()}}}_{{{self._subscript.get_tex_string()}}}"
        
        else:
            
            if self._subscript is not None:
                raise Exception("Cannot use subscript alongside parentheses in Term component")
            
            self._term = self.register_child(self._term)
            self._superscript = self.register_child(self._superscript)
            self._parentheses = self.register_child(self._parentheses)
            
            if self._superscript is not None:

                self.child_components = [ self._term, self._superscript, self._parentheses ]
                return f"{{ \\left({ self._term.get_tex_string() }\\right) }}^{{{self._superscript.get_tex_string()}}}"
            else:

                self.child_components = [ self._term, self._parentheses ]
                return f"{{ \\left({ self._term.get_tex_string() }\\right) }}"
        
    def accept_mobject_from_rendered_tex_string(self, mobject):

        if self._parentheses is None or self._parentheses is False:
            return super().accept_mobject_from_rendered_tex_string(mobject)


        submobject_count_1 = bracket_length(mobject)
        bracket_l = mobject[0:submobject_count_1]

        submobject_count_2 = self._term.accept_mobject_from_rendered_tex_string(mobject[submobject_count_1:])

        submobject_count_3 = bracket_length(mobject[submobject_count_1+submobject_count_2:])
        bracket_r = mobject[submobject_count_1+submobject_count_2:submobject_count_1+submobject_count_2+submobject_count_3]

        self._parentheses.accept_mobject_override(bracket_l, bracket_r)

        submobject_count_4 = 0

        if self._superscript is not None:
            submobject_count_4 = self._superscript.accept_mobject_from_rendered_tex_string(mobject[submobject_count_1+submobject_count_2+submobject_count_3:])
            self.submobjects = [ self._term, self._superscript, self._parentheses ]
        else:
            self.submobjects = [ self._term, self._parentheses ]

        return submobject_count_1 + submobject_count_2 + submobject_count_3 + submobject_count_4

    def align_child(self, term, rendered_tex_string):

        if term is self.superscript:
            delta = term.get_bottom()[1] - rendered_tex_string.get_bottom()[1]
            term.set_y(term.get_y() - delta)

        if term is self.subscript:
            delta = term.get_top()[1] - rendered_tex_string.get_top()[1]
            term.set_y(term.get_y() - delta)

    @property
    def term(self):
        return self._term
    
    @term.setter
    @reactive
    def term(self, term: Any):
        self._term = self.adapt_input(term)
        
    @property
    def superscript(self):
        return self._superscript
    
    @superscript.setter
    @reactive
    def superscript(self, superscript: Any):
        self._superscript = self.adapt_input(superscript)
    
    @property
    def subscript(self):
        return self._subscript
    
    @subscript.setter
    @reactive
    def subscript(self, subscript: Any):
        self._subscript = self.adapt_input(subscript)
    
    @property
    def base(self):
        return self._term
    
    @base.setter
    @reactive
    def base(self, term: Any):
        self._term = self.adapt_input(term)
    
    @property
    def exponent(self):
        return self._superscript
    
    @exponent.setter
    @reactive
    def exponent(self, exponent: Any):
        self._superscript = self.adapt_input(exponent)

    @property
    def paren(self):
        return self._parentheses
    
    @paren.setter
    @reactive
    def paren(self, paren):
        self._parentheses = paren

    @property
    def parentheses(self):
        return self._parentheses
    
    @parentheses.setter
    @reactive
    def parentheses(self, parentheses):
        self._parentheses = parentheses
        
    
    @reactive
    def remove(self, mobject):

        if mobject is self.term:
            self._term = MathString("")

        if mobject is self._superscript:
            self._superscript = None

        if mobject is self._subscript:
            self._subscript = None
        
        


class ParenSymbol(MathComponent):

    def __init__(
        self,
    ):
        self.bracket_l = MathStringFragment("", 1)
        self.bracket_r = MathStringFragment("", 1)
        super().__init__()

    #def execute_compose(self):
    #
    #    if self.parent:
    #        super().execute_compose()

    def compose_tex_string(self):
        
        self.bracket_l = self.register_child(self.bracket_l)
        self.bracket_r = self.register_child(self.bracket_r)
        self.child_components = [ self.bracket_l, self.bracket_r ]

        return "()"

    def accept_mobject_override(self, bracket_l, bracket_r):

        self.bracket_l.submobject_count = len(bracket_l.submobjects)
        self.bracket_r.submobject_count = len(bracket_r.submobjects)
        self.bracket_l.accept_mobject_from_rendered_tex_string(bracket_l)
        self.bracket_r.accept_mobject_from_rendered_tex_string(bracket_r)

        self.submobjects = [ self.bracket_l, self.bracket_r ]

    


class Parentheses(MathComponent):

    def __init__(
        self,
        interior,
        paren = None,
        *args,
        **kwargs
    ):
        self._interior = self.adapt_input(interior)

        if paren is None:
            paren = ParenSymbol()

        self._parentheses = paren

        super().__init__(*args, **kwargs)

    def compose_tex_string(self):
        self._parentheses = self.register_child(self._parentheses)
        self._interior = self.register_child(self._interior)

        self.child_components = [ self._parentheses, self._interior ]
        return f"\\left( {self._interior.get_tex_string()} \\right)"

    def accept_mobject_from_rendered_tex_string(self, mobject):

        submobject_count_1 = bracket_length(mobject)
        bracket_l = mobject[0:submobject_count_1]

        submobject_count_2 = self._interior.accept_mobject_from_rendered_tex_string(mobject[submobject_count_1:])

        submobject_count_3 = bracket_length(mobject[submobject_count_1+submobject_count_2:])
        bracket_r = mobject[submobject_count_1+submobject_count_2:submobject_count_1+submobject_count_2+submobject_count_3]

        self._parentheses.accept_mobject_override(bracket_l, bracket_r)
        self.submobjects = [ self._parentheses, self._interior ]

        return submobject_count_1 + submobject_count_2 + submobject_count_3

    @property
    def interior(self):
        return self._interior
    
    @interior.setter
    @reactive
    def interior(self, interior: Any):
        self._interior = self.adapt_input(interior)

    @property
    def paren(self):
        return self._parentheses

    @property
    def parentheses(self):
        return self._parentheses

    @property
    def symbol(self):
        return self._parentheses




    @property
    def inner(self):
        return self._interior
    
    @inner.setter
    @reactive
    def inner(self, inner: Any):
        self._interior = self.adapt_input(inner)

    # inner alias
    @property
    def input(self):
        return self._interior

    @input.setter
    def input(self, input: Any):
        self._interior = self.adapt_input(input)
    #

    #@property
    #def parentheses(self):
    #    return VGroup(self.bracket_l, self.bracket_r)

    #@property
    #def paren(self):
    #    return VGroup(self.bracket_l, self.bracket_r)

    def __len__(self) -> int:
        return len(self._interior)

    def __getitem__(self, index: int):
        return self._interior[index]

    @reactive
    def __setitem__(self, index: int, term):
        self._interior[index] = self.adapt_input(term)
        


class Function(MathComponent):

    def __init__(
        self,
        name,
        input,
        paren = None,
    ):
        self._name = self.adapt_input(name)
        self._input = self.adapt_input(input)

        if paren is None:
            self._parentheses = ParenSymbol()
        else:
            self._parentheses = paren

        super().__init__()

    def compose_tex_string(self):

        self._name = self.register_child(self._name)
        self._input = self.register_child(self._input)
        self._parentheses = self.register_child(self._parentheses)

        self.child_components = [ self._name, self._input, self._parentheses ]
        return f"{self._name.get_tex_string()} \\left( {self._input.get_tex_string()} \\right)"
    
    def accept_mobject_from_rendered_tex_string(self, mobject):

        submobject_count_0 = self._name.accept_mobject_from_rendered_tex_string(mobject)
        mobject = mobject[submobject_count_0:]

        submobject_count_1 = bracket_length(mobject)
        bracket_l = mobject[0:submobject_count_1]

        submobject_count_2 = self._input.accept_mobject_from_rendered_tex_string(mobject[submobject_count_1:])

        submobject_count_3 = bracket_length(mobject[submobject_count_1+submobject_count_2:])
        bracket_r = mobject[submobject_count_1+submobject_count_2:submobject_count_1+submobject_count_2+submobject_count_3]

        self._parentheses.accept_mobject_override(bracket_l, bracket_r)
        self.submobjects = [ self._name, self._parentheses, self._input ]

        return submobject_count_0 + submobject_count_1 + submobject_count_2 + submobject_count_3
    
    @property
    def parentheses(self):
        return self._parentheses
    
    @property
    def paren(self):
        return self._parentheses


    @property
    def input(self):
        return self._input
    
    @input.setter
    def input(self, input: Any):
        self._input = self.adapt_input(input)
    

    @property
    def function_name(self):
        return self._name

    @function_name.setter
    @reactive
    def function_name(self, name):
        self._name = self.adapt_input(name)

    # function_name alias
    @property
    def function(self):
        return self._name

    @function.setter
    @reactive
    def function(self, name):
        self._name = self.adapt_input(name)
        


class Fraction(MathComponent):

    def __init__(
        self,
        numerator,
        denominator,
        vinculum = None
    ):
        self._numerator = self.adapt_input(numerator)

        if vinculum is None:
            self._vinculum = MathStringFragment("", submobject_count=1)
        else: 
            self._vinculum = vinculum

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
    @reactive
    def numerator(self, numerator):
        self._numerator = self.adapt_input(numerator)
        
    
    @property
    def vinculum(self):
        return self._vinculum
    
    @vinculum.setter
    @reactive
    def vinculum(self, vinculum):
        self._vinculum = vinculum
    
    @property
    def denominator(self):
        return self._denominator

    @denominator.setter
    @reactive
    def denominator(self, denominator):
        self._denominator = self.adapt_input(denominator)
        


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

def bracket_length(mobject: VMobject):

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
    @reactive
    def lines(self, lines: List[Any]):
        self._lines = self.adapt_lines(lines)
        

    @reactive
    def insert(self, index: int, line):
        self._lines.insert(index, self.adapt_input(line))
        

    @reactive
    def append(self, line):
        self._lines.append(self.adapt_input(line))
        

    @reactive
    def remove(self, line):
        self._lines.remove(line)
        
    
    def __len__(self) -> int:
        return len(self._lines)

    def __getitem__(self, index: int):
        return self._lines[index]

    @reactive
    def __setitem__(self, index: int, line):
        self._lines[index] = self.adapt_input(line)
        

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
    @reactive
    def output(self, output):
        self._output = self.adapt_input(output)
        

    @property
    def condition(self):
        return self._condition

    @condition.setter
    @reactive
    def condition(self, condition):
        self._condition = self.adapt_input(condition)
        
    

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
    def brackets(self):
        return VGroup(self.bracket_l, self.bracket_r)

    @property
    def matrix(self):
        return self._matrix.tolist()
    
    @matrix.setter
    def matrix(self, matrix: List[List[Any]]):
        self._matrix = NumpyMobjectArray.from_mobjects(
            map_2d(matrix, lambda elem: self.adapt_input(elem))
        )

    def __len__(self) -> int:
        return len(self._matrix.tolist())

    def __getitem__(self, key):
        return self._matrix.tolist().__getitem__(key)

    def __iter__(self):
        return iter(self._matrix.tolist())
    

class ManimMatrix(MathComponent):

    def __init__(
        self,
        matrix: List[List[Any]],
    ):
        #self.a = matrix[0][0]
        #self.b = matrix[0][1]
        self.first = True
        self.bracket_l = MathStringFragment("", submobject_count=1)
        self.bracket_r = MathStringFragment("", submobject_count=1)

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
        #self.a = self.register_child(self.a)
        #self.b = self.register_child(self.b)
        self.bracket_r = self.register_child(self.bracket_r)


        #self.mobject_matrix = MobjectMatrix([[ SingleStringMathTex("a") ]]) #MobjectMatrix(self._matrix.tolist())
        #self.child_components = [ self.bracket_l, self.a, self.b, self.bracket_r ] #[ self.bracket_l, *self._matrix.flatten().tolist(), self.bracket_r ]
        self.child_components = [ self.bracket_l, *self._matrix.flatten().tolist(), self.bracket_r ]
        return "x"
        

    def accept_mobject_from_rendered_tex_string(self, mobject: VMobject) -> int:
        
        if self.first == False:
            for mobject in self._matrix.flatten().tolist():
                mobject.reactive_lock = True
                mobject.scale(1/self.scale_factor)
                mobject.reactive_lock = False

        

        self.mobject_matrix = MobjectMatrix(self._matrix.tolist())
        self.mobject_matrix.scale(self.scale_factor)

        if self.first == True:
            self.copy_mobject_matrix = self.mobject_matrix.copy()


        self.first = False

        self.bracket_l.accept_mobject_from_rendered_tex_string(self.mobject_matrix[1])
        self.bracket_r.accept_mobject_from_rendered_tex_string(self.mobject_matrix[2])

        #self.submobjects = [ self.bracket_l, self.a, self.b, self.bracket_r ]
        self.submobjects = [ self.bracket_l, *self._matrix.flatten().tolist(), self.bracket_r ]
        

        #root_math = self.find_root_encodable()
        #if root_math is not self:
        #    self.scale(1 / root_math.scale_factor)
        #    self.scale(self.scale_factor)

        """
        if submobject_count == 0:
            self.submobjects = []
        else:
            group = mobject[:submobject_count]

            if not self.first_render:
                group.match_style(self)
            else:
                self.first_render = False
        
            self.submobjects = [ *group ]
        """
        return 1

class Root(MathComponent):

    def __init__(
        self,
        radicand,
        index = None, 
        symbol = None
    ):
        self._radicand = self.adapt_input(radicand)

        if symbol is None:
            self._radical_symbol = MathStringFragment("", submobject_count=2)
        else:
            self._radical_symbol = symbol
        
        self._index = self.adapt_input(index)
        super().__init__(permit_none_children=True)

    def compose_tex_string(self):

        self._radicand = self.register_child(self._radicand)
        self._radical_symbol = self.register_child(self._radical_symbol)
        self._index = self.register_child(self._index)
        
        if self.index is not None:
            self.child_components = [ self._index, self._radical_symbol, self._radicand ]
            return f"\\sqrt[{self._index.get_tex_string()}]{{{self._radicand.get_tex_string()}}}"
        else:
            self.child_components = [ self._radical_symbol, self._radicand ]
            return f"\\sqrt{{{self._radicand.get_tex_string()}}}"
    
    @property 
    def radicand(self):
        return self._radicand

    @radicand.setter
    @reactive
    def radicand(self, radicand):
        self._radicand = self.adapt_input(radicand)
        

    @property
    def index(self):
        return self._index
    
    @index.setter
    @reactive
    def index(self, index):
        self._index = self.adapt_input(index)
        
    
    @property
    def radical_symbol(self):
        return self._radical_symbol
    
    @property
    def symbol(self):
        return self._radical_symbol
    
    @symbol.setter
    def symbol(self, symbol):
        self._radical_symbol = symbol
    


Paren = Parentheses



class Int(MathComponent):

    def __init__(
        self,
        a = None,
        b = None,
    ):
        self._a = self.adapt_input(a)
        self._b = self.adapt_input(b)
        self._symbol = MathStringFragment("", submobject_count=1)
        super().__init__(permit_none_children=True)

    def compose_tex_string(self):

        self._a = self.register_child(self._a)
        self._b = self.register_child(self._b)
        self._symbol = self.register_child(self._symbol)

        if self._a is not None and self._b is not None:
            self.child_components = [ self._symbol, self._b, self._a ]
            return f"\int_{{{self._a.get_tex_string()}}}^{{{self._b.get_tex_string()}}}"
        
        if self._a is not None:
            self.child_components = [ self._symbol, self._a ]
            return f"\int_{{{self._a.get_tex_string()}}}"
        
        if self._b is not None:
            self.child_components = [ self._symbol, self._b ]
            return f"\int^{{{self._b.get_tex_string()}}}"

        if self._a is None and self._b is None:
            self.child_components = [ self._symbol ]
            return "\int "
        
    @property
    def symbol(self):
        return self._symbol
    
    @property
    def a(self):
        return self._a
    
    @a.setter
    @reactive
    def a(self, a):
        self._a = self.adapt_input(a)

    @property
    def b(self):
        return self._b
    
    @b.setter
    @reactive
    def b(self, b):
        self._b = self.adapt_input(b)

class Integral(MathComponent):

    def __init__(
        self,
        function,
        a = None,
        b = None
    ):
        self._function = self.adapt_input(function)
        self._int = Int(a, b)
        super().__init__()

    def compose_tex_string(self):
        
        self._function = self.register_child(self._function)
        self._int = self.register_child(self._int)

        return [ self._int, self._function ]
    
    @property
    def symbol(self):
        return self._int.symbol

    @property
    def a(self):
        return self._int.a
    
    @a.setter
    def a(self, a):
        self._int.a = a

    @property
    def b(self):
        return self._int.b
    
    @b.setter
    def b(self, b):
        self._int.b = b

    @property
    def function(self):
        return self._function
    
    @function.setter
    def function(self, function):
        self._function = self.adapt_input(function)

class Evaluate(MathComponent):
    
    def __init__(
        self,
        function,
        a = None,
        b = None
    ):
        self._function = self.adapt_input(function)
        self._bracket = BracketMathStringFragment("")
        self._a = self.adapt_input(a)
        self._b = self.adapt_input(b)
        super().__init__()

    def compose_tex_string(self):
        
        self._function = self.register_child(self._function)
        self._bracket = self.register_child(self._bracket)
        self._a = self.register_child(self._a)
        self._b = self.register_child(self._b)
        
        self.child_components = [ self._function, self._bracket, self._b, self._a ]
        return f"\\left. {{{self._function.get_tex_string()}}} \\right|_{{{self._a.get_tex_string()}}}^{{{self._b.get_tex_string()}}}"
    
    @property
    def symbol(self):
        return self._bracket

    @property
    def a(self):
        return self._a
    
    @a.setter
    @reactive
    def a(self, a):
        self._a = self.adapt_input(a)

    @property
    def b(self):
        return self._b
    
    @b.setter
    @reactive
    def b(self, b):
        self._b = self.adapt_input(b)
        
        
