from setuptools import setup, find_packages

setup(
    name='dynamic-manim-components',
    version='0.1.0',
    description='A ManimCE component library, supporting component composition and automatic animation',
    author='Philip Murray',
    author_email='philipmurray.code@gmail.com',
    url='https://github.com/philip-murray/dynamic-manim-components',
    packages=find_packages(where='.'),
    package_dir={'': 'dynamic_manim_components'},
    install_requires=[
        'manim>=18.1.0', 
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)
