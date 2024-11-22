Term
============


.. raw:: html
    
    <img class="manim-image" id="asdf-image" width="808" height="454.5" src="../_static/media/term-scene-1.png">

.. code:: python

    class Term1(Scene):
        def construct(self):

            term = Term("x", "n")
            self.add(term)

            term.term.set_color(BLUE)
            term.superscript.set_color(RED)


|
|

Power Rule
^^^^^^^^^^

.. raw:: html
    
    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/term-scene-2.mp4"></video>

.. code:: python

    class PowerRule(Scene):
        def construct(self):

            x = MathTex("x", color=BLUE)
            n = MathTex("n", color=GREEN)

            tex = MathTex(Term(x, n))
            self.add(tex).wait(1)

            tex.terms = [ n, Term(x, [ n, "-", 1 ]) ]
            self.play(TransformInStages.progress(tex))