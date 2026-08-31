from manim import *
from reactive_manim import *





# SECTION 3, 
# FACTORING 


class Quad3(Scene):
    def construct(self):
        
        a = MathTex("a", color=RED)
        b = MathTex("b", color=BLUE)
        c = MathTex("c", color=GREEN)

        frac = Fraction(b, [ 2, a ])

        LHS = MathTex(
            Term("x", "2"), "+", [frac, "x"], "+", [frac, "x"], "+", Term(frac, "2", paren=True)
        )

        RHS = Fraction(
            [ Term(b, 2), "-", [4, a, c] ], 
            [ 4, Term(a, 2) ]
        )
        
        tex = MathTex(LHS, "=", RHS)
        self.add(tex)

        factoring(self, tex)


class Factor_xh(Scene):
    def construct(self):

        LHS = MathTex(Term("x", 2), "+", ["h", "x"], "+", ["h", "x"], "+", Term("h", 2))
        RHS = MathTex("0")

        tex = MathTex(LHS, "=", RHS)
        self.add(tex)

        factoring(self, tex)


def factoring(scene: Scene, tex: MathTex):
    
    [ xs, _, xh, _, xh, _, hs ] = tex.LHS

    tex[1].save_y()

    xx = xs.swap(lambda: MathTex(xs.base.clone(), xs.base.clone()))
    hh = hs.swap(lambda: MathTex(hs.base.clone(), hs.base.clone()))

    tex[1].restore_y()
    scene.play(TransformInStages.progress(tex))



    [A, B], _1, [C, D], _2, [E, F], _3, [G, H] = tex.LHS

    def create_phantom(term):
        return term.clone().clear_tracking().set_opacity(0)
    
    phantom_x_outer = create_phantom(A)
    phantom_h_outer = create_phantom(E)

    left  = MathTex([A, B], _1, [C, D])
    right = MathTex([E, F], _3, [G, H])

    paren1 = Parentheses(left)
    paren2 = Parentheses(right)

    tex.LHS = MathTex([ phantom_x_outer, paren1 ], _2, [ phantom_h_outer, paren2 ])

    scene.play(TransformInStages.progress(tex))

    phantom_B = B.swap(lambda: create_phantom(B))
    phantom_D = D.swap(lambda: create_phantom(D))
    phantom_E = E.swap(lambda: create_phantom(E))
    phantom_G = G.swap(lambda: create_phantom(G))

    phantom_x_outer.swap(B)
    B.merge(D)

    phantom_h_outer.swap(E)
    E.merge(G)
    tex[1].restore_y()

    scene.play(TransformInStages.progress(tex))
    
    phantom_B.pop()
    phantom_D.pop()
    phantom_E.pop()
    phantom_G.pop()

    scene.play(TransformInStages.progress(tex))

    phantom_paren_outer = create_phantom(paren1)
    paren_inner = Parentheses(tex.LHS)

    tex.LHS = MathTex(paren_inner, phantom_paren_outer)

    scene.play(TransformInStages.progress(tex))

    phantom_paren1 = paren1.swap(lambda: create_phantom(paren1))
    phantom_paren2 = paren2.swap(lambda: create_phantom(paren2))
    phantom_paren_outer.swap(paren1)
    paren1.merge(paren2)

    scene.play(TransformInStages.progress(tex))

    phantom_paren1.pop()
    phantom_paren2.pop()

    scene.play(TransformInStages.progress(tex))

    tex.LHS = Term(paren_inner, "2")
    paren_inner.merge(paren1)

    scene.play(TransformInStages.progress(tex))