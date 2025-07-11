from manim import *
from reactive_manim import *


class LimitDerivScene(Scene):
    def construct(self):

        
        x, p, h = MathTex("x", "+", "h")

        x.set_color(GREEN)
        h.set_color(BLUE)
        

        func1 = Function("f", x)
        func2 = Function("f", [ x, p, h ])

        frac = Fraction(
            [ func2, "-", func1 ],
            h
        )
        
        tex = MathTex("\\lim_{h \\to 0}", frac)
        self.play(FadeIn(tex))

        
        h.save_y()
        term1 = Term(func1.input, "2", paren=func1.paren)
        term2 = Term(func2.input, "2", paren=func2.paren)

        frac.numerator[0] = term2
        frac.numerator[2] = term1
        h.restore_y()

        self.play(TransformInStages.progress(tex, lag_ratio=0.25))


        term1.paren = None

        term2 = Term(
            [ Term(x, term2.exponent), "+", [ 2, x, h ], "+", Term(h, term2.exponent) ],
            paren=term2.paren
        )
        
        frac.numerator[0] = term2   

        self.play(TransformInStages.progress(tex))


        frac.numerator.terms = [ *frac.numerator[0].base, frac.numerator[1], frac.numerator[2] ]
        self.play(TransformInStages.progress(tex, lag_ratio=0.7))


        frac.numerator.terms = frac.numerator[2:5]
        self.play(TransformInStages.progress(tex))


        frac.numerator[0][2].pop()
        frac.numerator[2].exponent.pop()
        tex[1] = tex[1].numerator
        self.play(TransformInStages.progress(tex))

        
        tex.terms = [ tex[1][0] ]
        self.play(TransformInStages.progress(tex))

