.. reactive-manim documentation master file, created by
   sphinx-quickstart on Sun Oct 13 13:12:11 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

reactive-manim documentation
============================

Add your content using ``reStructuredText`` syntax. See the
`reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_
documentation for details.


.. toctree::
   :maxdepth: 2
   :caption: Contents:

.. raw:: html

    <video class='manim-video' width="808" height="454.5" controls loop autoplay src="_static/natural-log-animation.mp4">
    </video>


.. code-block:: python

    from manim import Scene, Square

    class MyScene(Scene):
        def construct(self):
            square = Square()
            self.play(Create(square))