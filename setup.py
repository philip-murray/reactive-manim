from setuptools import setup, find_packages

setup(
    name='dynamic-manim-components',
    version='0.1.3',
    description='A ManimCE component library, supporting component composition and automatic animation',
    author='Philip Murray',
    author_email='philipmurray.code@gmail.com',
    url='https://github.com/philip-murray/dynamic-manim-components',
    packages=['dynamic_manim_components', 'dynamic_manim_components.src', 'dynamic_manim_components.src.manim_src'],
    install_requires=[
        'manim>=0.18.1', 
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)