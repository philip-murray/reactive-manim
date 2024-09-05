"""Tools for displaying multiple animations at once."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable, Sequence

import numpy as np

from manim._config import config
from manim.animation.animation import Animation, prepare_animation
from manim.constants import RendererType
from manim.mobject.mobject import Group, Mobject
from manim.mobject.opengl.opengl_mobject import OpenGLGroup
from manim.scene.scene import Scene
from manim.utils.iterables import remove_list_redundancies
from manim.utils.rate_functions import linear

if TYPE_CHECKING:
    from manim.mobject.opengl.opengl_vectorized_mobject import OpenGLVGroup
    from manim.mobject.types.vectorized_mobject import VGroup

__all__ = ["AnimationGroup", "Succession", "LaggedStart", "LaggedStartMap"]


DEFAULT_LAGGED_START_LAG_RATIO: float = 0.05



class PreviousAnimationGroup(Animation):
    """Plays a group or series of :class:`~.Animation`.

    Parameters
    ----------
    animations
        Sequence of :class:`~.Animation` objects to be played.
    group
        A group of multiple :class:`~.Mobject`.
    run_time
        The duration of the animation in seconds.
    rate_func
        The function defining the animation progress based on the relative
        runtime (see :mod:`~.rate_functions`) .
    lag_ratio
        Defines the delay after which the animation is applied to submobjects. A lag_ratio of
        ``n.nn`` means the next animation will play when ``nnn%`` of the current animation has played.
        Defaults to 0.0, meaning that all animations will be played together.

        This does not influence the total runtime of the animation. Instead the runtime
        of individual animations is adjusted so that the complete animation has the defined
        run time.
    """

    def __init__(
        self,
        *animations: Animation,
        group: Group | VGroup | OpenGLGroup | OpenGLVGroup = None,
        run_time: float | None = None,
        rate_func: Callable[[float], float] = linear,
        lag_ratio: float = 0,
        **kwargs,
    ) -> None:
        self.animations = [prepare_animation(anim) for anim in animations]
        self.rate_func = rate_func
        self.group = group
        if self.group is None:
            mobjects = remove_list_redundancies(
                [anim.mobject for anim in self.animations if not anim.is_introducer()],
            )
            if config["renderer"] == RendererType.OPENGL:
                self.group = OpenGLGroup(*mobjects)
            else:
                self.group = Group(*mobjects)
        super().__init__(
            self.group, rate_func=self.rate_func, lag_ratio=lag_ratio, **kwargs
        )
        self.run_time: float = self.init_run_time(run_time)

    def get_all_mobjects(self) -> Sequence[Mobject]:
        return list(self.group)

    def begin(self) -> None:
        if self.suspend_mobject_updating:
            self.group.suspend_updating()
        for anim in self.animations:
            anim.begin()

    def _setup_scene(self, scene) -> None:
        for anim in self.animations:
            anim._setup_scene(scene)

    def finish(self) -> None:
        for anim in self.animations:
            anim.finish()
        if self.suspend_mobject_updating:
            self.group.resume_updating()

    def clean_up_from_scene(self, scene: Scene) -> None:
        self._on_finish(scene)
        for anim in self.animations:
            if self.remover:
                anim.remover = self.remover
            anim.clean_up_from_scene(scene)

    def update_mobjects(self, dt: float) -> None:
        for anim in self.animations:
            anim.update_mobjects(dt)

    def init_run_time(self, run_time) -> float:
        """Calculates the run time of the animation, if different from ``run_time``.

        Parameters
        ----------
        run_time
            The duration of the animation in seconds.

        Returns
        -------
        run_time
            The duration of the animation in seconds.
        """
        self.build_animations_with_timings()
        if self.anims_with_timings:
            self.max_end_time = np.max([awt[2] for awt in self.anims_with_timings])
        else:
            self.max_end_time = 0
        return self.max_end_time if run_time is None else run_time

    def build_animations_with_timings(self) -> None:
        """Creates a list of triplets of the form (anim, start_time, end_time)."""
        self.anims_with_timings = []
        curr_time: float = 0
        for anim in self.animations:
            start_time: float = curr_time
            end_time: float = start_time + anim.get_run_time()
            self.anims_with_timings.append((anim, start_time, end_time))
            # Start time of next animation is based on the lag_ratio
            curr_time = (1 - self.lag_ratio) * start_time + self.lag_ratio * end_time

    def interpolate(self, alpha: float) -> None:
        # Note, if the run_time of AnimationGroup has been
        # set to something other than its default, these
        # times might not correspond to actual times,
        # e.g. of the surrounding scene.  Instead they'd
        # be a rescaled version.  But that's okay!
        time = self.rate_func(alpha) * self.max_end_time
        for anim, start_time, end_time in self.anims_with_timings:
            anim_time = end_time - start_time
            if anim_time == 0:
                sub_alpha = 0
            else:
                sub_alpha = np.clip((time - start_time) / anim_time, 0, 1)
            anim.interpolate(sub_alpha)