Root
============


.. raw:: html
    
    <img class="manim-image" width="808" height="454.5" src="../_static/media/root-scene-1.png">

.. code:: python

    class Root1(Scene):
        def construct(self):

            root = Root("x", "n")
            self.add(root)

            root.index.set_color(RED)
            root.symbol.set_color(LIGHT_BROWN)
            root.radicand.set_color(BLUE)

|
|

Root Equation Operation
^^^^^^^^^^^^^^^^^^^^^^^

.. raw:: html
    
    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/root-scene-2.mp4"></video>

.. code:: python

    class Root2(Scene):
        def construct(self):

            tex = MathTex(Term("A", 2), "=", "B")
            self.add(tex).wait(1)
            
            tex.RHS = MathTex("\pm", Root(tex.RHS))
            tex.LHS = tex.LHS.term
            
            self.play(TransformInStages.progress(tex, lag_ratio=0.25))

|
|

Quotient Property of Roots
^^^^^^^^^^^^^^^^^^^^^^^^^^

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

            tex.terms = [ Fraction(root_n, root_d, vinculum=frac.vinculum) ]
            
            self.play(TransformInStages.progress(tex))