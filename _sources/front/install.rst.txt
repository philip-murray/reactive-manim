Install
============

.. note::

   Requires Manim Community v0.18 or v0.19 
   the OpenGL renderer is not supported.



.. code:: shell

    $ pip install reactive-manim

|

Quickstart
==========

.. raw:: html

    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/quad-scene-1.mp4"></video>

.. code-block:: python


    from manim import *
    from reactive_manim import *


    class Quickstart(Scene):
        def construct(self):

            a = MathTex("a", color=RED)
            b = MathTex("b", color=BLUE)
            c = MathTex("c", color=GREEN)

            tex = MathTex([[ a, "x^2" ], "+", [ b, "x" ], "+", [ c ]], "=", 0)
            self.add(tex).wait(1)


            b.swap(lambda: Fraction(b, a.pop()))
            c.swap(lambda: Fraction(c, a))

            self.play(TransformInStages.progress(tex))


    
      