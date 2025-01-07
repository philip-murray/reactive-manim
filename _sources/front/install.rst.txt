Install
============

.. note::

   Requires Manim Community v0.18.1, 
   the OpenGL renderer is not supported.



.. code:: shell

    $ pip install reactive-manim

|

Quickstart
==========

.. raw:: html

    <video class='manim-video' name="asdf" id="asdf" width="808" height="454.5" controls loop autoplay muted src="../_static/media/natural-log-partial.mp4"></video>

.. code-block:: python

    from manim import *
    from reactive_manim import *


    class NaturalLogScene(Scene):
        def construct(self):

            tex = MathTex("a", "=", "b")
            self.add(tex).wait(1)


            tex[0] = Term("e", tex[0])
            tex[2] = Term("e", tex[2])
            self.play(TransformInStages.progress(tex, lag_ratio=0.6))

            tex[0] = Function(r"\ln", tex[0])
            tex[2] = Function(r"\ln", tex[2])
            self.play(TransformInStages.progress(tex, lag_ratio=0.6))



    
      