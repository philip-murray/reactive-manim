Fast Showcase
============

.. raw:: html

    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/root-to-fraction.mp4"></video>

.. code-block:: python

    class RootToFrac(Scene):
        def construct(self):
            
            frac = Fraction("x-1", "x+1")
            root = Root(frac)

            tex = MathTex(root)
            self.add(tex).wait(1)

            root_n = Root(frac.numerator,   symbol=root.symbol)
            root_d = Root(frac.denominator, symbol=root.symbol)

            tex[0] = Fraction(root_n, root_d, vinculum=frac.vinculum)
            
            self.play(TransformInStages.progress(tex))

|
|

.. raw:: html

    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/integral-scene-2.mp4"></video>

.. code-block:: python

    class FundementalTheorem(Scene):
        def construct(self):

            a = MathTex("0", color=GREEN)
            b = MathTex("\pi", color=GREEN)

            integral = Integral("\cos(x) \: dx", a, b)

            tex = MathTex(integral)
            self.add(tex).wait(1)
            

            tex.terms = [
                integral,
                "=",
                [ Function("\sin", b), "-", Function("\sin", a) ]
            ]

            self.play(TransformInStages.progress(tex))

|
|

.. raw:: html

    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/distribution-scene-1.mp4"></video>
    
.. code-block:: python

    class DistributionScene(Scene):
        def construct(self):

            a, x, m, y = MathTex("a", "x", "-", "y")

            tex = MathTex(a, Parentheses([ x, m, y ]))
            self.add(tex).wait(1)

            m.save_y()
            tex.terms = [[a, x], m, [a, y]]
            m.restore_y()
            self.play(TransformInStages.progress(tex, lag_ratio=0))

|
|

.. raw:: html

    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/quad-scene-1.mp4"></video>
    

.. code-block:: python

    class QuadraticScene(Scene):
        def construct(self):

            a = MathTex("a", color=RED)
            b = MathTex("b", color=BLUE)
            c = MathTex("c", color=GREEN)

            tex = MathTex([[ a, "x^2" ], "+", [ b, "x" ], "+", [ c ]], "=", 0)
            self.add(tex).wait(1)

            b.swap(lambda: Fraction(b, a.pop()))
            c.swap(lambda: Fraction(c, a))

            self.play(TransformInStages.progress(tex))