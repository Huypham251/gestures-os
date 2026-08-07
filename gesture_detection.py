import math
from collections import deque

HISTORY_SIZE = 8
MOVEMENT_THRESHOLD = 120  # pixels the fingertip must travel to count as "far"
MAX_SWIPE_DURATION = 0.6  # seconds that travel must happen within to count as "fast"
GESTURE_COOLDOWN = 1.0  # seconds to wait before recognizing another gesture

# NOTE: elapsed vs. required fps, once the history buffer is full.
# Once the position-history deque is full, `elapsed` (the time between the
# oldest and newest buffered point) is always exactly `history_size - 1`
# frame intervals, i.e. elapsed ~= (history_size - 1) / fps. Since a gesture
# only fires when `elapsed <= max_swipe_duration`, this implicitly requires
# the camera/processing loop to sustain at least
# (history_size - 1) / max_swipe_duration frames per second, or no swipe can
# ever satisfy the "fast enough" check. At the defaults above
# (HISTORY_SIZE=8, MAX_SWIPE_DURATION=0.6), that's roughly (8 - 1) / 0.6 ~=
# 11.7 fps minimum. Worth remembering if gestures mysteriously stop firing
# on a loaded machine - it may just be dropped frame rate, not a detection
# bug.


class SwipeDetector:
    """Classifies index-fingertip motion into swipe gestures.

    Judges each swipe against the oldest point in a rolling history buffer
    (not the previous frame), so a single frame of jitter can't flip the
    detected direction. A gesture only fires if the movement is both FAR
    (distance) and FAST (within max_swipe_duration) - a slow drift covering
    the same distance over more time is ignored.
    """

    def __init__(
        self,
        history_size: int = HISTORY_SIZE,
        movement_threshold: float = MOVEMENT_THRESHOLD,
        max_swipe_duration: float = MAX_SWIPE_DURATION,
        gesture_cooldown: float = GESTURE_COOLDOWN,
    ):
        self.history_size = history_size
        self.movement_threshold = movement_threshold
        self.max_swipe_duration = max_swipe_duration
        self.gesture_cooldown = gesture_cooldown
        self._position_history = deque(maxlen=history_size)
        self._last_gesture_time = -gesture_cooldown

    def reset(self) -> None:
        """Clear position history, e.g. when hand tracking is lost."""
        self._position_history.clear()

    def update(self, x: int, y: int, t: float) -> str | None:
        """Feed the latest fingertip position; return a gesture name or None."""
        self._position_history.append((x, y, t))

        cooldown_elapsed = t - self._last_gesture_time > self.gesture_cooldown
        if len(self._position_history) < self.history_size:
            return None

        old_x, old_y, old_t = self._position_history[0]
        dx, dy = x - old_x, y - old_y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        elapsed = t - old_t

        if not (
            cooldown_elapsed
            and distance > self.movement_threshold
            and elapsed <= self.max_swipe_duration
        ):
            return None

        # atan2(dy, dx): 0 deg = right, 90 deg = down (y grows downward in
        # image coordinates), +/-180 deg = left, -90 deg = up.
        angle = math.degrees(math.atan2(dy, dx))
        if -45 <= angle < 45:
            gesture = "SWIPE_RIGHT"
        elif 45 <= angle < 135:
            gesture = "SWIPE_DOWN"
        elif angle >= 135 or angle < -135:
            gesture = "SWIPE_LEFT"
        else:
            gesture = "SWIPE_UP"

        self._last_gesture_time = t
        self._position_history.clear()  # require a fresh swipe before firing again
        return gesture
