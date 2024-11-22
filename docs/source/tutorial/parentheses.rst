Parentheses
============


.. raw:: html
    
    <img class="manim-image" width="808" height="454.5" src="../_static/media/paren-scene-1.png">

.. code:: python

    class Parentheses1(Scene):
        def construct(self):

            paren = Parentheses("x")
            self.add(paren)

            paren.input.set_color(BLUE)
            paren.parentheses.set_color(WHITE)

|
|

Distributive Property
^^^^^^^^^^^^^^^^^^^^^

.. raw:: html
    
    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/distribution-scene-1.mp4"></video>

.. code:: python

    class DistributiveProperty(Scene):
        def construct(self):

            a, x, m, y = MathTex("a", "x", "-", "y")

            tex = MathTex(a, Parentheses([ x, m, y ]))
            self.add(tex)

            m.save_y()
            tex.terms = [[a, x], m, [a, y]]
            m.restore_y()
            self.play(TransformInStages.progress(tex, lag_ratio=0))
