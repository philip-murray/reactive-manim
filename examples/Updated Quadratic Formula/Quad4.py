from manim import *
from reactive_manim import *


# SECTION 4,
# ISOLATE X


class Quad4(Scene):
    def construct(self):

        a = MathTex("a", color=RED)
        b = MathTex("b", color=BLUE)
        c = MathTex("c", color=GREEN)

        LHS = Term(
            [ "x", "+", Fraction(b, [ 2, a ]) ],
            "2",
            paren=True
        )

        RHS = Fraction(
            [ Term(b, 2), "-", [4, a, c] ],
            [ 4, Term(a, 2) ]
        )

        tex = MathTex(LHS, "=", RHS)
        self.add(tex).wait(1)


        tex[1].save_y()

        # take square root both sides
        tex.RHS = MathTex("\\pm", Root(tex.RHS, LHS.exponent.set_opacity(0)))
        tex.LHS.swap(lambda: tex.LHS.base)
        tex[1].restore_y()
        self.play(TransformInStages.progress(tex))


        # split √(num/den) into √num / √den
        root = tex.RHS[1]
        frac = root.radicand
        fr = Fraction(
            Root(frac.numerator, symbol=root.symbol),
            Root(frac.denominator, symbol=root.symbol),
            vinculum=frac.vinculum
        )
        root.swap(fr)
        tex[1].restore_y()
        self.play(TransformInStages.progress(tex))


        # simplify √(4a²) → 2a
        [four, a_squared] = fr.denominator.radicand
        two = four.set_tex_string("2")
        a = a_squared.base
        fr.denominator = MathTex(two, a)
        tex[1].restore_y()
        self.play(TransformInStages.progress(tex))


        # move b/2a from LHS to RHS (denominator now matches)
        x, p, frac_b2a = tex.LHS
        m = MathTex("-")
        tex.RHS = MathTex(m, frac_b2a.pop(), *tex.RHS)
        p.pop()
        tex[1].restore_y()
        self.play(TransformInStages.progress(tex))


        # merge -b/2a and ±√(b²-4ac)/2a → (-b ± √(b²-4ac)) / 2a
        # m.pop() moves "-" into the numerator and removes it from tex.RHS,
        # leaving tex.RHS as [frac_b2a, ±, fr] so frac1/pm/frac2 unpack cleanly.
        frac_b2a.numerator = MathTex(m.pop(), frac_b2a.numerator)
        frac1, pm, frac2 = tex.RHS[0], tex.RHS[1], tex.RHS[2]
        frac1.pop()
        pm.pop()
        frac2.denominator.merge(frac1.denominator)
        frac2.numerator = MathTex(frac1.numerator, pm, frac2.numerator)
        tex[1].restore_y()
        self.play(TransformInStages.progress(tex))
