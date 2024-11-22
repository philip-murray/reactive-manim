Matrix
======

- `MathMatrix`_ renders a bmatrix ``(...) -> \begin{bmatrix} ... \end{bmatrix}``
- `ManimMatrix`_ renders a MobjectMatrix that can be placed inside a math component [in development]. 

|
|

MathMatrix
----------

.. raw:: html

    <img class="manim-image" width="808" height="454.5" src="../_static/media/math-matrix-1.png">

.. code-block:: python

    class MathMatrix1(Scene):
        def construct(self):

            mat = MathMatrix([[ 1, 0 ], [ 0, 1 ]])
            self.add(mat)

            mat[0][0].set_color(BLUE)
            mat[1][1].set_color(BLUE)

            mat.brackets.set_color(LIGHT_BROWN)

|
|

Linear Equations
^^^^^^^^^^^^^^^^

.. raw:: html

    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/math-matrix-2.mp4"></video>

.. code-block:: python

    class LinearEquations(Scene):
        def construct(self):

            x0, x1, y0, y1 = MathTex("x_0", "x_1", "y_0", "y_1")
            w00, w01, w10, w11 = MathTex("w_{00}", "w_{01}", "w_{10}", "w_{11}")
            

            tex1 = MathTex(y0, "=", w00, x0, "+", w01, x1)
            tex2 = MathTex(y1, "=", w10, x0, "+", w11, x1)

            group = DGroup(tex1, tex2).arrange(DOWN).shift(UP)
            self.add(group).wait(1)

            tex3 = MathTex(
                MathMatrix([
                    [ y0 ],
                    [ y1 ]
                ]), 
                "=",
                MathMatrix([
                    [ w00, w01 ],
                    [ w10, w11 ]
                ]),
                MathMatrix([
                    [ x0 ],
                    [ x1 ]
                ])
            )
            tex3.shift(DOWN)
            
            self.play(TransformInStages.from_copy(group, tex3[0],      lag_ratio=0.4, run_time=2.5))
            self.play(TransformInStages.from_copy(group, tex3[1],      lag_ratio=0.4, run_time=1.4))
            self.play(TransformInStages.from_copy(group, tex3[2],      lag_ratio=0.4, run_time=2.5))
            self.play(TransformInStages.from_copy(group, tex3[3] - x0, lag_ratio=0.4, run_time=2.5))
            self.play(TransformInStages.from_copy(group, x0,           lag_ratio=0.4, run_time=2.5))


|
|

ManimMatrix
-----------
in development