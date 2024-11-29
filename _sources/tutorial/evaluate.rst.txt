Evaluate
========

.. raw:: html
    
    <img class="manim-image" width="808" height="454.5" src="../_static/media/evaluate-1.png">

.. code:: python

    class Evaluate1(Scene):
        def construct(self):

            eval = Evaluate("\\frac{1}{x} \mspace{4mu} ", "1", "e")
            self.add(eval)
            
            eval.a.set_color(RED)
            eval.b.set_color(BLUE)
            eval.symbol.set_color(LIGHT_BROWN)
