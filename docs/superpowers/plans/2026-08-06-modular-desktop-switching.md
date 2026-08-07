# Modular Architecture + macOS Desktop Switching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `main.py` into focused, independently testable modules and wire detected swipe gestures to real macOS Space-switching / window-management actions.

**Architecture:** Extract `SwipeDetector` (pure gesture classification, no I/O deps) and `HandTracker` (MediaPipe wrapper) out of the camera loop, add an `actions.py` that simulates the relevant Ctrl+Arrow shortcut via `pynput` for each gesture, then rewire the slimmed-down `main.py` loop to use all three.

**Tech Stack:** Python 3.11, OpenCV (`cv2`), MediaPipe, `pynput`, pytest (new dev dependency).

## Global Constraints

- Gesture names are exactly: `SWIPE_LEFT`, `SWIPE_RIGHT`, `SWIPE_UP`, `SWIPE_DOWN`.
- Default detection thresholds (from the existing implementation, keep as constructor defaults): `HISTORY_SIZE = 8`, `MOVEMENT_THRESHOLD = 120`, `MAX_SWIPE_DURATION = 0.6`, `GESTURE_COOLDOWN = 1.0`.
- `gesture_detection.py` must not import `cv2`, `mediapipe`, or `pynput` — it must be pure and camera-free so it's unit-testable.
- Gesture-to-shortcut mapping: `SWIPE_LEFT` → Ctrl+Left, `SWIPE_RIGHT` → Ctrl+Right, `SWIPE_UP` → Ctrl+Up, `SWIPE_DOWN` → Ctrl+Down.
- `actions.dispatch` must accept an injectable `controller` parameter so tests never drive the real OS.
- A failed keypress simulation (e.g. missing macOS Accessibility permission) must print an instructive message once, not crash the caller or spam on every frame.

---

### Task 1: Extract `SwipeDetector` into `gesture_detection.py`, with pytest set up

**Files:**
- Create: `gesture_detection.py`
- Create: `tests/test_gesture_detection.py`
- Create: `pytest.ini`
- Modify: `requirements.txt` (add `pytest==9.1.1`)

**Interfaces:**
- Produces: `SwipeDetector(history_size=8, movement_threshold=120, max_swipe_duration=0.6, gesture_cooldown=1.0)` with methods `update(x: int, y: int, t: float) -> str | None` and `reset() -> None`.

- [ ] **Step 1: Add pytest to the project and configure it to find top-level modules**

Append to `requirements.txt`:

```
pytest==9.1.1
```

Create `pytest.ini`:

```ini
[pytest]
pythonpath = .
```

Install it:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_gesture_detection.py`:

```python
from gesture_detection import SwipeDetector


def make_detector(**overrides):
    defaults = dict(
        history_size=2,
        movement_threshold=10,
        max_swipe_duration=1.0,
        gesture_cooldown=0.5,
    )
    defaults.update(overrides)
    return SwipeDetector(**defaults)


def test_swipe_right():
    detector = make_detector()
    assert detector.update(0, 0, 0.0) is None
    assert detector.update(50, 0, 0.1) == "SWIPE_RIGHT"


def test_swipe_down():
    detector = make_detector()
    assert detector.update(0, 0, 0.0) is None
    assert detector.update(0, 50, 0.1) == "SWIPE_DOWN"


def test_swipe_left():
    detector = make_detector()
    assert detector.update(0, 0, 0.0) is None
    assert detector.update(-50, 0, 0.1) == "SWIPE_LEFT"


def test_swipe_up():
    detector = make_detector()
    assert detector.update(0, 0, 0.0) is None
    assert detector.update(0, -50, 0.1) == "SWIPE_UP"


def test_no_gesture_when_too_slow():
    detector = make_detector(max_swipe_duration=0.05)
    detector.update(0, 0, 0.0)
    assert detector.update(50, 0, 0.1) is None


def test_no_gesture_when_too_short():
    detector = make_detector(movement_threshold=100)
    detector.update(0, 0, 0.0)
    assert detector.update(50, 0, 0.1) is None


def test_cooldown_suppresses_second_gesture():
    detector = make_detector(gesture_cooldown=1.0)
    detector.update(0, 0, 0.0)
    assert detector.update(50, 0, 0.1) == "SWIPE_RIGHT"
    # A second swipe right away, still within the cooldown window.
    detector.update(50, 0, 0.15)
    assert detector.update(100, 0, 0.2) is None


def test_reset_clears_history():
    detector = make_detector()
    detector.update(0, 0, 0.0)
    detector.reset()
    # Only one point buffered since reset; history_size=2 needs two.
    assert detector.update(50, 0, 0.1) is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_gesture_detection.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gesture_detection'`

- [ ] **Step 4: Write the implementation**

Create `gesture_detection.py`:

```python
import math
from collections import deque

HISTORY_SIZE = 8
MOVEMENT_THRESHOLD = 120  # pixels the fingertip must travel to count as "far"
MAX_SWIPE_DURATION = 0.6  # seconds that travel must happen within to count as "fast"
GESTURE_COOLDOWN = 1.0  # seconds to wait before recognizing another gesture


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
        self._last_gesture_time = 0.0

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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_gesture_detection.py -v`
Expected: PASS (8 tests)

- [ ] **Step 6: Commit**

```bash
git add gesture_detection.py tests/test_gesture_detection.py pytest.ini requirements.txt
git commit -m "Extract SwipeDetector into gesture_detection.py with tests"
```

---

### Task 2: Extract `HandTracker` into `hand_tracking.py`

**Files:**
- Create: `hand_tracking.py`

**Interfaces:**
- Produces: `HandResult` (dataclass with `x: int`, `y: int`, `landmarks`) and `HandTracker` with `process(frame) -> HandResult | None` and `draw(frame, hand_result: HandResult) -> None`.

No automated tests for this module (per design doc — exercising it needs a real camera/MediaPipe, which isn't valuable here). Verified manually in Task 4.

- [ ] **Step 1: Write the implementation**

Create `hand_tracking.py`:

```python
from dataclasses import dataclass
from typing import Any

import cv2
import mediapipe as mp


@dataclass
class HandResult:
    x: int
    y: int
    landmarks: Any  # mediapipe NormalizedLandmarkList, needed only for drawing


class HandTracker:
    """Wraps MediaPipe Hands to track the index fingertip in a video frame."""

    def __init__(self):
        self._hands = mp.solutions.hands.Hands()

    def process(self, frame) -> HandResult | None:
        # MediaPipe expects RGB, but OpenCV captures in BGR - convert just for
        # detection and leave `frame` itself untouched (still BGR for imshow).
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb_frame)

        if not results.multi_hand_landmarks:
            return None

        hand_landmarks = results.multi_hand_landmarks[0]
        height, width, _ = frame.shape
        index_tip = hand_landmarks.landmark[
            mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP
        ]
        x, y = int(index_tip.x * width), int(index_tip.y * height)
        return HandResult(x=x, y=y, landmarks=hand_landmarks)

    def draw(self, frame, hand_result: HandResult) -> None:
        mp.solutions.drawing_utils.draw_landmarks(
            frame,
            hand_result.landmarks,
            mp.solutions.hands.HAND_CONNECTIONS,
        )
```

- [ ] **Step 2: Sanity-check it imports cleanly**

Run: `python3 -c "import hand_tracking"`
Expected: no output, exit code 0 (full behavioral verification happens in Task 4 once `main.py` uses it)

- [ ] **Step 3: Commit**

```bash
git add hand_tracking.py
git commit -m "Extract HandTracker into hand_tracking.py"
```

---

### Task 3: Build `actions.py` mapping gestures to macOS shortcuts, with tests

**Files:**
- Create: `actions.py`
- Create: `tests/test_actions.py`

**Interfaces:**
- Consumes: gesture name strings produced by `gesture_detection.SwipeDetector.update` (`"SWIPE_LEFT"`, `"SWIPE_RIGHT"`, `"SWIPE_UP"`, `"SWIPE_DOWN"`).
- Produces: `dispatch(gesture: str, controller: pynput.keyboard.Controller | None = None) -> None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_actions.py`:

```python
from unittest.mock import Mock, call

import pytest

import actions


@pytest.fixture(autouse=True)
def reset_permission_warning(monkeypatch):
    monkeypatch.setattr(actions, "_warned_permission_error", False)


def test_dispatch_swipe_left_sends_ctrl_left():
    controller = Mock()
    actions.dispatch("SWIPE_LEFT", controller=controller)
    assert controller.press.call_args_list == [
        call(actions.Key.ctrl), call(actions.Key.left)
    ]
    assert controller.release.call_args_list == [
        call(actions.Key.left), call(actions.Key.ctrl)
    ]


def test_dispatch_swipe_right_sends_ctrl_right():
    controller = Mock()
    actions.dispatch("SWIPE_RIGHT", controller=controller)
    assert controller.press.call_args_list == [
        call(actions.Key.ctrl), call(actions.Key.right)
    ]
    assert controller.release.call_args_list == [
        call(actions.Key.right), call(actions.Key.ctrl)
    ]


def test_dispatch_swipe_up_sends_ctrl_up():
    controller = Mock()
    actions.dispatch("SWIPE_UP", controller=controller)
    assert controller.press.call_args_list == [
        call(actions.Key.ctrl), call(actions.Key.up)
    ]
    assert controller.release.call_args_list == [
        call(actions.Key.up), call(actions.Key.ctrl)
    ]


def test_dispatch_swipe_down_sends_ctrl_down():
    controller = Mock()
    actions.dispatch("SWIPE_DOWN", controller=controller)
    assert controller.press.call_args_list == [
        call(actions.Key.ctrl), call(actions.Key.down)
    ]
    assert controller.release.call_args_list == [
        call(actions.Key.down), call(actions.Key.ctrl)
    ]


def test_dispatch_unknown_gesture_is_noop():
    controller = Mock()
    actions.dispatch("NOT_A_GESTURE", controller=controller)
    controller.press.assert_not_called()
    controller.release.assert_not_called()


def test_dispatch_prints_instructive_message_once_on_failure(capsys):
    controller = Mock()
    controller.press.side_effect = OSError("accessibility permission denied")

    actions.dispatch("SWIPE_LEFT", controller=controller)
    actions.dispatch("SWIPE_RIGHT", controller=controller)

    output = capsys.readouterr().out
    assert output.count("Accessibility") == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_actions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'actions'`

- [ ] **Step 3: Write the implementation**

Create `actions.py`:

```python
from pynput.keyboard import Controller, Key


def _send_combo(controller: Controller, key) -> None:
    controller.press(Key.ctrl)
    controller.press(key)
    controller.release(key)
    controller.release(Key.ctrl)


def switch_space_left(controller: Controller) -> None:
    _send_combo(controller, Key.left)


def switch_space_right(controller: Controller) -> None:
    _send_combo(controller, Key.right)


def mission_control(controller: Controller) -> None:
    _send_combo(controller, Key.up)


def app_expose(controller: Controller) -> None:
    _send_combo(controller, Key.down)


ACTIONS = {
    "SWIPE_LEFT": switch_space_left,
    "SWIPE_RIGHT": switch_space_right,
    "SWIPE_UP": mission_control,
    "SWIPE_DOWN": app_expose,
}

_warned_permission_error = False


def dispatch(gesture: str, controller: Controller | None = None) -> None:
    """Look up gesture in ACTIONS and simulate the mapped keyboard shortcut.

    Unknown gestures are a no-op. On macOS, simulating keypresses requires
    Accessibility permission for the running process; a failure here is
    reported once instead of crashing the caller's loop or being silently
    retried every frame.
    """
    global _warned_permission_error
    action = ACTIONS.get(gesture)
    if action is None:
        return

    if controller is None:
        controller = Controller()

    try:
        action(controller)
    except Exception:
        if not _warned_permission_error:
            print(
                "Could not simulate a keypress for gesture "
                f"'{gesture}'. On macOS this usually means the running "
                "process needs Accessibility permission: System Settings "
                "-> Privacy & Security -> Accessibility."
            )
            _warned_permission_error = True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_actions.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add actions.py tests/test_actions.py
git commit -m "Add actions.py mapping swipe gestures to macOS shortcuts"
```

---

### Task 4: Rewire `main.py` to use the three modules

**Files:**
- Modify: `main.py` (full rewrite of the camera loop)

**Interfaces:**
- Consumes: `hand_tracking.HandTracker.process/draw`, `gesture_detection.SwipeDetector.update/reset`, `actions.dispatch`.

- [ ] **Step 1: Rewrite `main.py`**

Replace the full contents of `main.py`:

```python
import time

import cv2

import actions
import gesture_detection
import hand_tracking


def main() -> None:
    camera = cv2.VideoCapture(0)
    tracker = hand_tracking.HandTracker()
    detector = gesture_detection.SwipeDetector()

    last_gesture = None
    last_gesture_time = 0.0

    while True:
        ret, frame = camera.read()
        if not ret:
            break

        hand_result = tracker.process(frame)

        if hand_result is not None:
            tracker.draw(frame, hand_result)
            cv2.circle(frame, (hand_result.x, hand_result.y), 8, (0, 255, 0), cv2.FILLED)
            cv2.putText(
                frame,
                f"({hand_result.x}, {hand_result.y})",
                (hand_result.x + 15, hand_result.y - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

            gesture = detector.update(hand_result.x, hand_result.y, time.time())
            if gesture:
                actions.dispatch(gesture)
                last_gesture = gesture
                last_gesture_time = time.time()
        else:
            detector.reset()

        if last_gesture and time.time() - last_gesture_time < 1.0:
            cv2.putText(
                frame,
                last_gesture,
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 255),
                3,
            )

        cv2.imshow("Camera", frame)

        if cv2.waitKey(1) == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full automated test suite**

Run: `pytest -v`
Expected: PASS (all 14 tests from Tasks 1 and 3 — `main.py` and `hand_tracking.py` have no automated tests)

- [ ] **Step 3: Manually verify end-to-end behavior**

Run: `python3 main.py`

Check, in front of the webcam:
- A green dot and hand skeleton overlay track your index fingertip.
- A fast, wide swipe right prints/overlays `SWIPE_RIGHT` in the window **and** actually switches to the Space on the right (requires Accessibility permission for your terminal — grant it via System Settings → Privacy & Security → Accessibility if the switch doesn't happen and a message about it is printed in the terminal).
- Repeat for swipe left (Space switch left), swipe up (Mission Control), swipe down (App Exposé).
- Pressing `q` closes the window and exits cleanly.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "Rewire main.py to use hand_tracking, gesture_detection, and actions"
```

---

### Task 5: Update `CLAUDE.md` to reflect the new structure

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update the Architecture and Commands sections**

In `CLAUDE.md`, replace the single-file "Architecture" description with the new module breakdown (`hand_tracking.py`, `gesture_detection.py`, `actions.py`, `main.py`), and add the test command to "Commands":

```
pytest              # run the unit test suite (gesture_detection.py, actions.py)
```

Also remove the now-stale line "There are no tests, linter, or build step configured in this repo" and the note about `pynput`/`pyobjc-framework-Quartz` being unwired, since that gap is now closed.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md for the modular architecture and test command"
```
