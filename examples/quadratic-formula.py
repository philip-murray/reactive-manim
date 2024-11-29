from manim import *
from reactive_manim import *

class QuadraticScene(Scene):
    def construct(self):

        a = MathTex("a", color=RED)
        b = MathTex("b", color=BLUE)
        c = MathTex("c", color=GREEN)

        term_a = MathTex(a, Term("x", 2))
        term_b = MathTex(b, "x")
        term_c = MathTex(c)

        p1, p2 = MathTex("+", "+")

        tex = MathTex([ term_a, p1, term_b, p2, term_c ], "=", 0)
        self.add(tex).wait(1)




        
        # SECTION 1, COMPLETING THE SQUARE
        # ################################

        # ax^2 + bx + c -> x^2 + (b/a)x + (c/a)

        frac_b = b.swap(lambda: Fraction(b, a.pop()))
        frac_c = c.swap(lambda: Fraction(c, a))

        self.play(TransformInStages.progress(tex))


        
        #  [ ... + c/a = 0 ] -> [ ... = -c/a ]
        
        minus = MathTex("-")
        tex.LHS.terms = [ term_a, p1, term_b ]
        tex.RHS = MathTex(minus, frac_c)
        
        self.play(TransformInStages.progress(tex))



        # Frac(b, a)x -> Frac(b, 2a)x + Frac(b, 2a)x
        # term_b            term2          term3

        frac_b.denominator = MathTex(2, frac_b.denominator)
        term1 = term_a
        term2 = term_b.clone()
        term3 = term_b.clone()
        tex.LHS.terms = [ term1, p1, term2, p2, term3 ]

        self.play(TransformInStages.progress(tex))



        # [ ... = ... ]  -> [ ... + (b/2a)^2 = (b/2a)^2 + ... ]

        term4 = Term(Parentheses(Fraction(b, [2, a]), spacer=False), 2).clear_tracking()
        term5 = term4.clone().clear_tracking()
        
        tex[1].save_y()
        p3 = MathTex("+")
        tex.LHS       = [[ term1, p1, term2 ], p2, [ term3, p3, term4 ]]
        tex.RHS.terms = [  term5, minus, frac_c ]
        tex[1].restore_y()
        
        self.play(TransformInStages.progress(tex, lag_ratio=0.6))
        self.wait(1)





        # SECTION 2, COMBINE RIGHT-HAND SIDE
        # ##################################

        coa = frac_c

        _4n, _4d, an, ad = MathTex("4", "4", a, a).clear_tracking()
        c, a = coa.numerator, coa.denominator


        # (b/2a)^2 -> b^2/4a^2

        _2    = term5.superscript
        frac5 = term5.swap(lambda: term5.term.inner)

        frac5.numerator      = Term(frac5.numerator,      _2)
        frac5.denominator[1] = Term(frac5.denominator[1], _2)
        frac5.denominator[0].set_tex_string("4")

        self.play(TransformInStages.progress(tex, lag_ratio=0.4))

        
        # c/a -> [4a c]/[4a a]

        _4n, _4d, an, ad = MathTex("4", "4", a, a).clear_tracking()
        c, a = coa.numerator, coa.denominator

        _4a_frac = Fraction([ _4n, an ], [ _4d, ad ]).clear_tracking()
        tex.RHS.terms = [ frac5, minus, _4a_frac, "\\cdot", frac_c ]

        self.play(TransformInStages.progress(tex))


        # [4a c]/[4a a] -> 4ac / 4a^2

        tex.RHS.terms = [ frac5, minus, frac_c ]

        coa.numerator =   MathTex(_4n, an, c)
        coa.denominator = MathTex(_4d, Term(a, 2))
        a.merge(ad)

        self.play(TransformInStages.progress(tex))


        # [b^2/4a^2] + [4ac/4a^2] -> [b^2 + 4ac]/4a^2

        tex.RHS = frac5
        frac5.numerator = MathTex(frac5.numerator, minus, coa.numerator)
        frac5.denominator.merge(coa.denominator)

        self.play(TransformInStages.progress(tex))
        self.wait(1)





        
        # SECTION 3, FACTOR LEFT-HAND SIDE
        # ################################

        tex[1].save_y()

        x_1 = term1[0].term
        x_2 = x_1.clone()
        term1 = term1.swap(lambda: MathTex(x_1, x_2))

        f_1 = term4.term.inner
        f_2 = f_1.clone()
        term4 = term4.swap(lambda: MathTex(f_1, f_2))

        tex[1].restore_y()

        self.play(TransformInStages.progress(tex, lag_ratio=0.4))



        [A, B], [C, D], [E, F], [G, H] = term1, term2, term3, term4

        def create_phantom(term):
            return term.clone().clear_tracking().set_opacity(0)

        phantom_x_outer = create_phantom(x_1)
        phantom_f_outer = create_phantom(f_1)

        paren_1 = Parentheses(tex.LHS[0])
        paren_2 = Parentheses(tex.LHS[2])

        tex.LHS.terms = [[ phantom_x_outer, paren_1 ], p2, [ phantom_f_outer, paren_2 ]]
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex, lag_ratio=0.6, track_run_time=1.2))



        phantom_B = create_phantom(B)
        phantom_D = create_phantom(D)
        phantom_E = create_phantom(E)
        phantom_G = create_phantom(G)

        B.swap(lambda: phantom_B)
        D.swap(lambda: phantom_D)
        E.swap(lambda: phantom_E)
        G.swap(lambda: phantom_G)

        phantom_x_outer.swap(B)
        B.merge(D)

        phantom_f_outer.swap(E)
        E.merge(G)
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex))


        phantom_B.pop()
        phantom_D.pop()
        phantom_E.pop()
        phantom_G.pop()
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex))
        self.wait(1)


        phantom_p_outer = create_phantom(paren_1)
        root_paren = Parentheses(tex.LHS)
        tex.LHS = MathTex(root_paren, phantom_p_outer)
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex))


        phantom_paren_1 = paren_1.swap(lambda: create_phantom(paren_1))
        phantom_paren_2 = paren_2.swap(lambda: create_phantom(paren_2))

        phantom_p_outer.swap(paren_1)
        paren_1.merge(paren_2)
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex))


        phantom_paren_1.pop()
        phantom_paren_2.pop()
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex))
        
        _2 = MathTex("2")
        tex.LHS = Term(root_paren, _2)
        root_paren.merge(paren_1)
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex))




        # SECTION 4, ISOLATE X
        # ####################

        frac_RHS = tex.RHS

        tex.LHS = tex.LHS.term.inner
        tex.RHS = MathTex("\pm", Root(tex.RHS, _2.set_opacity(0)))

        root = tex.RHS[1]
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex))

        symbol = tex.RHS[1].symbol

        fraction = root.swap(lambda: Fraction(
            Root(frac_RHS.numerator,   symbol=symbol),
            Root(frac_RHS.denominator, symbol=symbol),
            vinculum=frac_RHS.vinculum
        ))
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex))

        denominator = fraction.denominator
        _2 = denominator.radicand[0].set_tex_string("2")
        a  = denominator.radicand[1].term

        denominator.swap(lambda: MathTex(_2, a))
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex))

        x, p, frac = tex.LHS
        frac = frac[0]
        m = MathTex("-")
        tex.RHS = MathTex(m, frac.pop(), *tex.RHS)
        p.pop()
        tex[1].restore_y()

        self.play(TransformInStages.progress(tex))

        frac.numerator = MathTex(m.pop(), frac.numerator)

        frac1, pm, frac2 = tex.RHS[0], tex.RHS[1], tex.RHS[2]
        frac1.pop()
        pm.pop()

        frac2.denominator.merge(frac1.denominator)
        frac2.numerator = MathTex(frac1.numerator, pm, frac2.numerator)
        tex[1].restore_y()
        self.play(TransformInStages.progress(tex))
        self.wait(4)