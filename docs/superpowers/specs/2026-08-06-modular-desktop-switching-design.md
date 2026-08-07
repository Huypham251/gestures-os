# Gesture OS: Modular Architecture + macOS Desktop Switching

**Date:** 2026-08-06
**Status:** Approved

## Purpose

Today, `main.py` is a single-file script that detects hand-swipe gestures via
MediaPipe/OpenCV but only prints the detected gesture and overlays it on the
video window — it doesn't actually control macOS. This design:

1. Restructures the script into focused, independently testable modules.
2. Wires detected swipe gestures to real macOS Space-switching / window
   management actions, using `pynput` (already an unused dependency in
   `requirements.txt`).

## Module layout

```
gesture-os/
├── main.py                # camera loop; wires the pieces together; overlay/UI
├── hand_tracking.py       # HandTracker: MediaPipe wrapper
├── gesture_detection.py   # SwipeDetector: pure swipe-classification state machine
├── actions.py             # gesture name -> macOS action (key simulation)
├── requirements.txt
├── docs/superpowers/specs/
└── tests/
    ├── test_gesture_detection.py
    └── test_actions.py
```

### `hand_tracking.py`

Owns the `mediapipe.solutions.hands.Hands()` instance — the only module that
imports `mediapipe`. Exposes:

```python
class HandTracker:
    def process(self, frame) -> HandResult | None
```

`HandResult` carries the index fingertip's pixel `(x, y)` plus the raw
landmarks (needed only so `main.py` can call `mp_draw.draw_landmarks` for the
on-screen skeleton overlay). Returns `None` when no hand is detected.

### `gesture_detection.py`

The `SwipeDetector` class, ported from today's `main.py` loop body (rolling
deque, distance/duration thresholds, `atan2`-based direction classification,
cooldown). Constructor takes the four tunable constants
(`history_size`, `movement_threshold`, `max_swipe_duration`,
`gesture_cooldown`) as defaults, overridable for tests.

```python
class SwipeDetector:
    def update(self, x: int, y: int, t: float) -> str | None
    def reset(self) -> None
```

**No cv2/mediapipe/pynput imports.** Inputs are plain `(x, y, t)` values,
output is a gesture-name string (`"SWIPE_LEFT"`, `"SWIPE_RIGHT"`,
`"SWIPE_UP"`, `"SWIPE_DOWN"`) or `None`. This isolation is what makes the
detection logic unit-testable without a camera or MediaPipe.

Behavior carried over unchanged from today's implementation:

- A swipe is judged against the *oldest* buffered point, not the previous
  frame, so single-frame jitter can't flip the detected direction.
- A gesture only fires if movement is both far (> `movement_threshold` px)
  and fast (within `max_swipe_duration` seconds).
- `gesture_cooldown` seconds must elapse since the last recognized gesture.
- After a gesture fires, or tracking is lost (`reset()`), history clears —
  a fresh swipe is required before the next gesture can fire.

### `actions.py`

Maps each gesture name to a macOS action, simulated as a keyboard shortcut
via `pynput.keyboard.Controller`:

| Gesture | Shortcut simulated | Effect |
|---|---|---|
| `SWIPE_LEFT` | Ctrl + ← | Move to Space on the left |
| `SWIPE_RIGHT` | Ctrl + → | Move to Space on the right |
| `SWIPE_UP` | Ctrl + ↑ | Mission Control |
| `SWIPE_DOWN` | Ctrl + ↓ | App Exposé |

All four combos share one helper, `_send_combo(controller, key)`, which
presses `Key.ctrl`, presses `key`, then releases both in reverse order —
rather than four copy-pasted press/release blocks.

```python
def dispatch(gesture: str, controller: pynput.keyboard.Controller | None = None) -> None
```

`dispatch` looks up `gesture` in the mapping and calls it, injecting a
`Controller` (real by default, or a mock in tests) so the OS is never
actually driven from a test. Unknown gesture names are a no-op.

### `main.py`

Shrinks to the camera loop, wiring the above together:

```
camera.read() → frame
  → hand_tracking.process(frame) → (x, y) fingertip or None
      → if None: detector.reset()
      → else: detector.update(x, y, time.time()) → gesture or None
          → if gesture: actions.dispatch(gesture)
  → draw overlay (fingertip dot, coords, last-gesture text)
  → cv2.imshow
```

This is the same control flow as today's script — the restructure changes
*where* the logic lives, not the loop's runtime behavior.

## Error handling

- **Accessibility permission (macOS-specific gotcha):** simulating keypresses
  via `pynput` on macOS requires the running process to have Accessibility
  permission (System Settings → Privacy & Security → Accessibility). Without
  it, `pynput` may silently no-op or raise depending on version. `dispatch`
  wraps the simulated keypress in a try/except; on failure it prints a
  one-time instructive message telling the user to grant Accessibility
  access, rather than crashing the camera loop or failing silently on every
  frame.
- **Camera open/read failure:** unchanged from today — if `camera.read()`
  returns `ret=False`, the loop breaks.
- **No hand detected:** unchanged — `SwipeDetector.reset()` clears history,
  same as today's `else: position_history.clear()`.

## Testing

- `tests/test_gesture_detection.py`: feeds synthetic `(x, y, t)` sequences
  into `SwipeDetector.update()`, using small constructor-injected thresholds
  so tests run instantly with few points. Covers: each of the 4 directions,
  no-gesture when movement is too slow, no-gesture when movement is too
  short, cooldown suppression of a second gesture, and history reset on lost
  tracking.
- `tests/test_actions.py`: injects a mock `Controller` into `dispatch()` and
  asserts the correct press/release sequence was called for each gesture
  name; asserts unknown gesture names are a no-op.
- `hand_tracking.py` and the `main.py` loop remain untested — exercising them
  would require mocking a real camera, MediaPipe, and the OS, which isn't
  valuable for this project.

## Out of scope

- Registry/plugin-style gesture or action registration (considered as an
  alternative approach; deferred as premature for a fixed 4-gesture set —
  see rejected approaches below).
- Threaded producer/consumer split between detection and action dispatch
  (deferred — key simulation is near-instant, so there's no latency problem
  to solve).
- Any gestures beyond the existing 4 swipe directions.
- A configuration file for the tunable thresholds (they remain constructor
  defaults in `gesture_detection.py`).

## Rejected approaches

1. **Registry/plugin-style gesture and action registration** (e.g.
   `@register_gesture("SWIPE_LEFT")` decorators instead of a plain dict) —
   more extensible if the gesture set grows substantially, but is
   speculative abstraction for a project with 4 known gestures today.
2. **Threaded producer/consumer** (capture+detection on one thread pushing
   gesture events to a queue, consumed by a separate action-dispatch
   thread) — solves a concurrency/latency problem this app doesn't have,
   at the cost of thread-safety complexity.
