Function
============


.. raw:: html
    
    <img class="manim-image" width="808" height="454.5" src="../_static/media/function-scene-1.png">

.. code:: python

    class Function1(Scene):
        def construct(self):

            func = Function("\text{sin}", "\theta")
            self.add(func)

            func.function.set_color(GREEN)
            func.input.set_color(LIGHT_BROWN)
            func.parentheses.set_color(WHITE)

|
|
|

Function Equation Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. raw:: html
    
    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/function-scene-2.mp4"></video>

.. code:: python

    class Function2(Scene):
        def construct(self):

            a = MathTex("a", color=RED)
            b = MathTex("b", color=BLUE)

            tex = MathTex(a, "=", b)
            self.add(tex)

            tex.LHS = Function("\\sin", tex.LHS)
            tex.RHS = Function("\\sin", tex.RHS)

            self.play(TransformInStages.progress(tex))

            tex.LHS = tex.LHS.input
            tex.RHS = tex.RHS.input
            
            self.play(TransformInStages.progress(tex))


|
|
|

Log of Exponent
^^^^^^^^^^^^^^^

.. raw:: html
    
    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/function-scene-3.mp4"></video>

.. code:: python

    class LogOfExponent(Scene):
        def construct(self):

            a = MathTex("a", color=RED)
            k = MathTex("k", color=BLUE)

            log = Function("\log", Term(a, k))
            tex = MathTex(log)

            self.add(tex)
            
            log.input = a
            tex.terms = [ k, log ]

            self.play(TransformInStages.progress(tex))