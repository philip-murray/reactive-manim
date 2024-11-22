Mobject Controls
================

pop and swap
~~~~~~~~~~~~

..
    ``term.pop()`` disconnects a term from it's parent. 
    ``term1.swap(lambda: term2)`` replaces ``term1`` with ``term2`` with respect to ``term1``'s parent.

.. raw:: html

    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/quad-scene-1.mp4"></video>

.. code-block:: python


    class QuadScene(Scene):
        def construct(self):

            a = MathTex("a", color=RED)
            b = MathTex("b", color=BLUE)
            c = MathTex("c", color=GREEN)

            tex = MathTex([[ a, "x^2" ], "+", [ b, "x" ], "+", [ c ]], "=", 0)
            self.add(tex).wait(1)

            a.pop()

            b.swap(lambda: Fraction(b, a))
            c.swap(lambda: Fraction(c, a))

            self.play(TransformInStages.progress(tex))


In this example:

- ``a.pop()`` disconnects :math:`a` from :math:`ax^2` and returns :math:`a`.
- ``b.swap(lambda: Fraction(b, a))`` replaces :math:`b` with :math:`\frac{b}{a}` and returns :math:`\frac{b}{a}`.
- ``c.swap(lambda: Fraction(c, a))`` replaces :math:`c` with :math:`\frac{c}{a}` and returns :math:`\frac{c}{a}`.

|
|
|

merge
~~~~~

``term1.merge(term2)``, directs the animation generator to use a clone of ``term1`` as the target mobject for ``term2``. 

.. raw:: html

    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/merge-scene-1.mp4"></video>

.. code-block:: python

    class QuadraticMerge(Scene):
        def construct(self):

            a = MathTex("a", color=RED)
            b = MathTex("b", color=BLUE)

            paren1 = Paren([ "x", "+", Fraction(b, [ 2, a ])])
            paren2 = Paren([ "x", "+", Fraction(b, [ 2, a ])])

            tex = MathTex(paren1, paren2)
            self.add(tex)

            tex.terms = [ Term(paren1, 2) ] # paren2 is removed, but merges onto paren1 for remover-animation
            paren1.merge(paren2)

            self.play(TransformInStages.progress(tex, lag_ratio=0.5))


|
|
|

.. raw:: html

    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/merge-scene-2.mp4"></video>

.. code-block:: python

    class FractionMerge(Scene):
        def construct(self):
            
            a = MathTex("a", color=RED)
            b = MathTex("b", color=BLUE)
            c = MathTex("c", color=GREEN)
            
            frac1 = Fraction(
                Term(b, 2), 
                [ 4, Term(a, 2) ]
            )

            frac2 = Fraction(
                [ 4, a, c ], 
                [ 4, Term(a, 2) ]
            )

            tex = MathTex(frac1, "+", frac2)
            self.add(tex)


            frac1.numerator = MathTex(frac1.numerator, tex[1], frac2.numerator)
            frac1.denominator.merge(frac2.denominator)
            tex.terms = [ frac1 ]

            self.play(TransformInStages.progress(tex, lag_ratio=0.5))

|
|
|

