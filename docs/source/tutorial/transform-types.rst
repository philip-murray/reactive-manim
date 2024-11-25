Transform Types
===============


from_copy
^^^^^^^^^

.. raw:: html
    
    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/transform-type-1.mp4"></video>

.. code:: python

    class EquationScene1(Scene):
        def construct(self):

            x, y, _1, _3, eq, mn = MathTex("x", "y", "1", "3", "=", "-")

            x.set_color(BLUE)
            y.set_color(GREEN)

            tex1 = MathTex(       x,                 eq,  [ Term(y, _3), "+", _1 ]); eq.save_x()
            tex2 = MathTex(     [ x, mn, _1 ],       eq,    Term(y, _3)           )
            tex3 = MathTex(Root([ x, mn, _1 ], _3),  eq,         y                )
            tex4 = MathTex(     tex3.RHS,            eq,    tex3.LHS              )

            group = VGroup(tex1, tex2, tex3, tex4).arrange(DOWN, buff=MED_LARGE_BUFF)
            [ tex[1].restore_x() for tex in group ]
            
            self.add(tex1)
            self.play(TransformInStages.from_copy(tex1, tex2))
            self.play(TransformInStages.from_copy(tex2, tex3))
            self.play(TransformInStages.from_copy(tex3, tex4))

|
|


replacement_transform
^^^^^^^^^^^^^^^^^^^^^

.. raw:: html
    
    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/transform-type-2.mp4"></video>

.. code:: python

    class EquationScene2(Scene):
        def construct(self):

            x, y, _1, _3, eq, mn = MathTex("x", "y", "1", "3", "=", "-")

            x.set_color(BLUE)
            y.set_color(GREEN)

            tex1 = MathTex(       x,                 eq,  [ Term(y, _3), "+", _1 ]); eq.save_x()
            tex2 = MathTex(     [ x, mn, _1 ],       eq,    Term(y, _3)           )
            tex3 = MathTex(Root([ x, mn, _1 ], _3),  eq,         y                )
            tex4 = MathTex(     tex3.RHS,            eq,    tex3.LHS              )

            group = VGroup(tex1, tex2, tex3, tex4)
            [ tex[1].restore_x() for tex in group ]
            
            self.add(tex1)
            self.play(TransformInStages.replacement_transform(tex1, tex2))
            self.play(TransformInStages.replacement_transform(tex2, tex3))
            self.play(TransformInStages.replacement_transform(tex3, tex4))

|
|


progress
^^^^^^^^

.. raw:: html
    
    <video class='manim-video' width="808" height="454.5" controls loop autoplay muted src="../_static/media/transform-type-3.mp4"></video>

.. code:: python

    class EquationScene3(Scene):
        def construct(self):

            x, y, _1, _3, eq, mn = MathTex("x", "y", "1", "3", "=", "-")

            x.set_color(BLUE)
            y.set_color(GREEN)


            tex = MathTex(       x,                  eq,  [ Term(y, _3), "+", _1 ]); eq.save_x()
            self.add(tex)

            tex.terms =  [      [ x, mn, _1 ],       eq,    Term(y, _3)           ]; eq.restore_x()
            self.play(TransformInStages.progress(tex))

            tex.terms =  [ Root([ x, mn, _1 ], _3),  eq,         y                ]; eq.restore_x()
            self.play(TransformInStages.progress(tex))

            tex.terms =  [      tex.RHS,              eq,     tex.LHS             ]; eq.restore_x()
            self.play(TransformInStages.progress(tex))