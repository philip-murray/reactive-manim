from manim import *
from reactive_manim import *





# SECTION 1, 
# COMPLETING THE SQUARE

class Quad1(Scene):
    def construct(self):


        a = MathTex("a", color=RED)
        b = MathTex("b", color=BLUE)
        c = MathTex("c", color=GREEN)

        term_a = MathTex(a, Term("x", 2))
        term_b = MathTex(b, "x")
        term_c = MathTex(c)

        tex = MathTex([ term_a, "+", term_b, "+", term_c ], "=", 0)
        self.add(tex).wait(1)


        ### Recenters for constant height of `=` symbol

        def save_center():
            tex[1].save_y()

        def recenter():
            tex[1].restore_y()

        save_center()


        # Step 1, 
        # ax^2 + bx + c -> x^2 + (b/a)x + (c/a)

        frac_b = b.swap(lambda: Fraction(b, a.pop()))
        frac_c = c.swap(lambda: Fraction(c, a))

        recenter()
        self.play(TransformInStages.progress(tex))




        # Step 2
        # [ ... + c/a = 0 ] -> [ ... = -c/a ]
        
        tex.LHS = MathTex(*tex.LHS.terms[0:3])
        tex.RHS = MathTex("-", frac_c)
        
        recenter()
        self.play(TransformInStages.progress(tex))




        # Step 3
        # (b/a) x -> (b/2a) x + (b/2a) x

        tex.LHS.remove(term_b)
        
        frac_b.denominator.insert(0, "2")

        tex.LHS.append(term_b.clone())
        tex.LHS.append("+")
        tex.LHS.append(term_b.clone())

        recenter()
        self.play(TransformInStages.progress(tex, lag_ratio=0.6))



        # Step 4
        # [ ... = ... ]  -> [ ... + (b/2a)^2 = (b/2a)^2 + ... ]

        b_2a_x_squared = Term(Fraction(b, [2, a]), 2, paren=True)

        square1 = b_2a_x_squared.clone().clear_tracking()
        square2 = b_2a_x_squared.clone().clear_tracking()

        tex.LHS.append("+")
        tex.LHS.append(square1)
        tex.RHS.insert(0, square2)
        
        recenter()
        self.play(TransformInStages.progress(tex, lag_ratio=0.6))   

        print(tex.get_center())