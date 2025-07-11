Integral
========


.. raw:: html

    <img class="manim-image" width="808" height="454.5" src="../_static/media/integral-scene-1.png">

.. code-block:: python

    class Integral1(Scene):
        def construct(self):
            
            integral = Integral("f(x) \: dx", "a", "b")
            self.add(integral)

            integral.a.set_color(RED)
            integral.b.set_color(BLUE)

            integral.symbol.set_color(WHITE)
            integral.function.set_color(WHITE)

|
|
|


Fundemental Theorem
^^^^^^^^^^^^^^^^^^^

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