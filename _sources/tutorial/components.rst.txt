Components
============

.. toctree::
    :caption: Section 1
    :maxdepth: 5
    :hidden:


    
    term
    root
    fraction
    function
    parentheses
    matrix
    cases
    integral
    evaluate



.. raw:: html

    <div class="component-grid">
        
        <div class="component-button">
            <a href="./term.html" class="component-image-container tex-small">
                <img src="https://latex.codecogs.com/svg.image?x^n">
            </a>
            <p>Term</p>
        </div>

        <div class="component-button">
            <a href="./root.html" class="component-image-container tex-small">
                <img src="https://latex.codecogs.com/svg.image?\sqrt[n]{x}">
            </a>
            <p>Root</p>
        </div>

        <div class="component-button">
            <a href="./fraction.html" class="component-image-container tex-small">
                <img src="https://latex.codecogs.com/svg.image?\frac{a}{b}" style="padding: 16px !important;">
            </a>
            <p>Fraction</p>
        </div>

        <div class="component-button">
            <a href="./function.html" class="component-image-container tex-small">
                <img src="https://latex.codecogs.com/svg.image?f(x)">
            </a>
            <p>Function</p>
        </div>

        <div class="component-button">
            <a href="./parentheses.html" class="component-image-container tex-small">
                <img src="https://latex.codecogs.com/svg.image?(x)">
            </a>
            <p>Parentheses</p>
        </div>

        <div class="component-button">
            <a href="./matrix.html" class="component-image-container tex-small">
                <img src="https://latex.codecogs.com/svg.image?\begin{bmatrix} a \\ b \end{bmatrix}" style="padding: 12px !important;">
            </a>
            <p>Matrix</p>
        </div>

        <div class="component-button">
            <a href="./cases.html" class="component-image-container tex-small">
                <img src="https://latex.codecogs.com/svg.image?f(x)=\begin{cases} a \\ b \end{cases}" style="padding: 9px !important;">
            </a>
            <p>Piecewise</p>
        </div>

        <div class="component-button">
            <a href="./integral.html" class="component-image-container tex-large">
                <img src="https://latex.codecogs.com/svg.image?\int_a^b">
            </a>
            <p>Integral</p>
        </div>

        <div class="component-button">
            <a href="./evaluate.html" class="component-image-container tex-medium">
                <img src="https://latex.codecogs.com/svg.image?\Big|_a^b" style="padding: 9px !important;">
            </a>
            <p>Evaluate</p>
        </div>


    </div>

.. raw:: html

   <style>
        .component-button {
            text-align: center;
            text-decoration: none;
        }

        .component-button p {
            font-size: 0.9em; /* Slightly smaller font size */
            font-weight: bold;
            color: #333;
            margin-top: 4px;
            margin-bottom: 0px !important;
        }

        .component-image-container {
            display: flex;
            justify-content: center; /* Centers horizontally */
            align-items: center; /* Centers vertically */
            text-align: center;
            text-decoration: none;
            color: inherit;
            width: 140px;
            height: 80px;
            padding: 5px; /* Reduced padding to make it less tall */
            border: 2px solid #ccc;
            border-radius: 8px;
            background-color: #f9f9f9;
            box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .component-image-container:hover {
            transform: scale(1.05);
            box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.2);
            cursor: pointer;
        }

       .component-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr); /* 3 columns */
            gap: 20px;
            justify-items: center;
            align-items: center;
        }

        .tex-small img {
            padding: 18px;
            width: 100%;
            height: 100%;
        }

        .tex-medium img {
            padding: 12px;
            width: 100%;
            height: 100%;
        }


        .tex-large img {
            padding: 8px;
            width: 100%;
            height: 100%;
        }

   </style>

.. raw:: html

    <div style="margin-top: 50px; margin-bottom: 50px">
    <img class="manim-image" style="border-radius: 4px" width="808" height="454.5" src="../_static/media/components_grid.png" alt="Component Composition">

..
    <div style="margin-top: 100px; margin-bottom: 100px">
    <video class='manim-video' id="component-composition" style="border-radius: 4px" width="808" height="454.5" controls loop autoplay muted src="../_static/media/composition.mp4"></video>

..
    <script>
        const video = document.getElementById('component-composition');
        video.playbackRate = 1.25; 
    </script>

..
    |
    |
    |
    |
    |
    |