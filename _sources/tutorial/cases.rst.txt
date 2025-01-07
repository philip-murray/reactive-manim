MathCases
============

.. raw:: html
    
    <img class="manim-image" width="808" height="454.5" src="../_static/media/cases-scene-1.png" alt="Natural Log Example">

.. code:: python

    class NeuronVoltage(Scene):
        def construct(self):

            cases = MathCases(
                CaseLine("0,",       "t <    0"),
                CaseLine("te^{-t},", "t \geq 0")
            )

            tex = MathTex("v(t) = ", cases)
            self.add(tex)

            tex.set_color(LIGHT_BROWN)
            cases[1].output.set_color(GREEN)
            cases[1].condition.set_color(BLUE)

|
|
|

.. raw:: html
    
    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/cases-scene-2.mp4"></video>

.. code:: python

    class PredicatePartition(Scene):
        def construct(self):

            tex = MathTex("f(x) =", MathCases(
                CaseLine(r"b,     ", r"\text{even}(x)"),
                CaseLine(r"\neg b,", r"\text{odd}(x)"),
                CaseLine(r"?,",      r"\text{otherwise}"),        
            ))
            self.add(tex)

            cases = tex[1]
            cases[1].condition.set_color(ORANGE)
            cases[2].output.set_color(ORANGE)

            self.play(TransformInStages.progress(tex))
            
            cases[1].condition = cases[2].condition
            cases.lines = [ cases[0], cases[1] ]   

            self.play(TransformInStages.progress(tex))