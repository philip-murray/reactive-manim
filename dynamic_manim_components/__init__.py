from .src.animation import *
from .src.dynamic_mobject import *
from .src.dynamic_tex_mobject import *


from manim import config, logger
import atexit
from importlib.metadata import version
__components_version__ = version("dynamic-manim-components")

import http.client
import json
#import sys
import urllib.error
import urllib.request
#from pathlib import Path
from typing import cast


def on_atexit():

    if not config.notify_outdated_version:
        return

    components_info_url = "https://pypi.org/pypi/dynamic-manim-components/json"
    warn_prompt = "Cannot check if latest release of dynamic-manim-components is installed"

    try:
        with urllib.request.urlopen(
            urllib.request.Request(components_info_url),
            timeout=10,
        ) as response:
            response = cast(http.client.HTTPResponse, response)
            json_data = json.loads(response.read())
    except urllib.error.HTTPError:
        logger.debug("HTTP Error: %s", warn_prompt)
    except urllib.error.URLError:
        logger.debug("URL Error: %s", warn_prompt)
    except json.JSONDecodeError:
        logger.debug(
            "Error while decoding JSON from %r: %s", components_info_url, warn_prompt
        )
    except Exception:
        logger.debug("Something went wrong: %s", warn_prompt)
    else:
        pypi_version = json_data["info"]["version"]
        if pypi_version != __components_version__:
            console.print(
                f"You are using dynamic-manim-components [bright_magenta]v{__components_version__}[/bright_magenta], but version [bright_cyan]v{pypi_version}[/bright_cyan] is available.",
            )
            console.print(
                "You can upgrade via [yellow]pip install -U dynamic-manim-components[/yellow]",
            )

        console.print(
            ""
        )
        console.print(
            "dynamic-manim-components has been renamed to reactive-manim, you can install it via [bright_magenta]pip install -U reactive-manim[/bright_magenta]"
        )
        console.print(
            "and using the import statement [bright_cyan]from reactive_manim import *[bright_cyan]"
        )

atexit.register(on_atexit)