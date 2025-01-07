from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='reactive-manim',
    version='0.0.4',
    description='A component library for ManimCE, supporting component composition and automatic animation. Supports declarative syntax for writing components inspired by React.js.',
    author='Philip Murray',
    author_email='philipmurray.code@gmail.com',
    url='https://github.com/philip-murray/reactive-manim',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=['reactive_manim', 'reactive_manim.src', 'reactive_manim.src.manim_src'],
    install_requires=[
        'manim>=0.18.1', 
    ],
    python_requires='>=3.8',
)