# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'reactive-manim'
copyright = '2024, Philip Murray'
author = 'Philip Murray'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

github_username = 'philip-murray'
github_repository = 'reactive-manim'

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

html_css_files = [
    'styles.css',
]
html_js_files = [
    "custom.js", 
]

html_theme_options = {
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

html_context = {
    "display_github": True,  # Enable GitHub link
    "github_user": "philip-murray",
    "github_repo": "reactive-manim",
    "github_version": "main",
    "github_url": "https://github.com/philip-murray/reactive-manim",  # GitHub repo link
    "conf_py_path": "/docs/",
    'navigation_exclusions': ['github'], 
}

pygments_style = 'tango' 