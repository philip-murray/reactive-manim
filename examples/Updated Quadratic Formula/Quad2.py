from manim import *
from reactive_manim import *





# SECTION 2, 
# REARRANGING RHS

class Quad2(Scene):
    def construct(self):
        
        a = MathTex("a", color=RED)
        b = MathTex("b", color=BLUE)
        c = MathTex("c", color=GREEN)

        frac = Fraction(b, [ 2, a ])

        LHS = MathTex(
            Term("x", "2"), "+", [ frac, "x" ], "+", [ frac, "x" ], "+", Term(frac, "2", paren=True)
        )




        b_2a_squared = Term(frac, "2", paren=True)
        coa = Fraction(c, a)

        RHS = MathTex(b_2a_squared, "-", coa)

        tex = MathTex(LHS, "=", RHS)
        tex.set_y(-0.01895107)
        tex.clear_tracking()
        
        self.add(tex).wait(1)



        
        ### Recenters to maintain constant height of `=` symbol

        def save_center():
            tex[1].save_y()

        def recenter():
            tex[1].restore_y()

        save_center()
        
        #

        b, [ t, a ] = frac.numerator, frac.denominator
        exponent = b_2a_squared.exponent
        f = t.set_tex_string("4")

        xr = b_2a_squared.swap(lambda:
          
          Fraction(
                 Term(b, exponent),
            [ f, Term(a, exponent)],
            vinculum=frac.vinculum
          )

        )
        self.play(TransformInStages.progress(tex))


        #

        a = coa.denominator
        a_n = MathTex("a", color=RED)
        a_d = MathTex("a", color=RED)

        frac_4a = Fraction(
            [4, a_n], 
            [4, a_d]
        )

        merge1 = coa.swap(lambda: 
          MathTex(frac_4a, "\\cdot", coa)
        )

        self.play(TransformInStages.progress(tex))

        #

        merge2 = merge1.swap(lambda:

            Fraction(
                [ *frac_4a.numerator, *coa.numerator ],
                MathTex(frac_4a.denominator[0], Term(a_d, MathTex("2"))),
                vinculum=coa.vinculum
            )
        )

        a_d.merge(coa.denominator)

        self.play(TransformInStages.progress(tex))

        #

        minus = tex.RHS[1]
        tex.RHS = xr
        xr.numerator = MathTex(xr.numerator, minus, merge2.numerator)
        xr.denominator.merge(merge2.denominator)

        self.play(TransformInStages.progress(tex))
