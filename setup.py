from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='dynamic-manim-components',
    version='0.1.5',
    description='A ManimCE component library, supporting component composition and automatic animation',
    author='Philip Murray',
    author_email='philipmurray.code@gmail.com',
    url='https://github.com/philip-murray/dynamic-manim-components',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=['dynamic_manim_components', 'dynamic_manim_components.src', 'dynamic_manim_components.src.manim_src'],
    install_requires=[
        'manim>=0.18.1', 
    ],
    python_requires='>=3.8',
)