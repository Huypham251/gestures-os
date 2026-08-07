# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Gesture OS: a Python app that uses computer vision hand-gesture recognition to control macOS desktops (e.g. switching Spaces via swipe gestures). Tech stack: OpenCV, MediaPipe, pynput.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py     # run; press 'q' in the camera window to quit
pytest              # run the unit test suite (gesture_detection.py, actions.py)
```

## Architecture

The app is split into four modules:

1. **`hand_tracking.py`** — `HandTracker` wraps MediaPipe Hands to detect and track the index fingertip in each video frame. It converts frames from OpenCV's BGR to MediaPipe's RGB internally (leaving the original frame BGR for display), extracts the index fingertip landmark from the first detected hand, and provides a `draw()` method to render hand landmarks on the frame.

2. **`gesture_detection.py`** — `SwipeDetector` classifies index-fingertip motion into swipe gestures. It maintains a rolling `deque(maxlen=HISTORY_SIZE)` of `(x, y, timestamp)` positions and judges each swipe against the oldest point in the buffer (not the previous frame), so single-frame jitter can't flip the detected direction. A gesture only fires if movement is both **far** (euclidean distance > `MOVEMENT_THRESHOLD` px) and **fast** (distance covered within `MAX_SWIPE_DURATION` seconds). Direction is classified from `atan2(dy, dx)` into `SWIPE_LEFT/RIGHT/UP/DOWN`. `GESTURE_COOLDOWN` seconds must elapse between recognized gestures. When hand tracking is lost, the detector's history is cleared.

3. **`actions.py`** — Maps gestures to macOS keyboard shortcuts, sent via AppleScript's System Events (`osascript -e 'tell application "System Events" to key code <vk> using {control down}'`):
   - `SWIPE_LEFT` → switch Space left (Ctrl+Left)
   - `SWIPE_RIGHT` → switch Space right (Ctrl+Right)
   - `SWIPE_UP` → Mission Control (Ctrl+Up)
   - `SWIPE_DOWN` → App Exposé (Ctrl+Down)

   **This is AppleScript-based, not `pynput`-based, and that's deliberate**: `pynput`'s `CGEventPost`-based keyboard simulation does NOT trigger macOS's Mission Control Space-switch handler, even from a process with Accessibility trust — verified empirically (neither pynput's default event construction nor one tagging the event with an explicit HID event source worked, while both a real physical keypress and AppleScript's System Events pathway did). Do not revert this to `pynput` without re-verifying live against Mission Control.

   The `dispatch(gesture, key_sender=...)` function looks up the gesture's virtual keycode in `_GESTURE_KEYCODES` and calls `key_sender` (the real `_send_ctrl_arrow` by default; injectable for tests). It requires macOS's **Automation** permission (System Settings → Privacy & Security → Automation) for this app to control System Events — not Accessibility. A failure is reported once via a printed message instead of crashing the caller's loop or being silently retried every frame.

4. **`main.py`** — The main event loop:
   - Captures frames from the webcam and processes them through `HandTracker`, `SwipeDetector`, and `actions` modules in sequence.
   - Draws hand landmarks and the fingertip position on each frame.
   - Displays recognized gestures as an overlay on the video window.
   - Exits on 'q' key press.

When tuning gesture detection, adjust the constants in `gesture_detection.py` (`HISTORY_SIZE`, `MOVEMENT_THRESHOLD`, `MAX_SWIPE_DURATION`, `GESTURE_COOLDOWN`) rather than rewriting the detection logic.
