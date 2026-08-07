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
```

There are no tests, linter, or build step configured in this repo.

## Architecture

The entire app is currently `main.py`, a single blocking loop:

1. **Capture** — `cv2.VideoCapture(0)` reads webcam frames; MediaPipe requires RGB but OpenCV captures BGR, so frames are converted just for detection (`frame` itself stays BGR for `cv2.imshow`).
2. **Hand detection** — `mediapipe.solutions.hands.Hands()` finds landmarks; only `results.multi_hand_landmarks[0]` (the first detected hand) is used. The index fingertip landmark (`HandLandmark.INDEX_FINGER_TIP`) is the sole tracked point.
3. **Swipe detection** — a rolling `deque(maxlen=HISTORY_SIZE)` of `(x, y, timestamp)` holds recent fingertip positions. A swipe is judged against the *oldest* point in the buffer (not the previous frame), so single-frame jitter can't flip the detected direction. A gesture only fires if movement is both:
   - **far**: euclidean distance since the oldest buffered point > `MOVEMENT_THRESHOLD` px
   - **fast**: that distance covered within `MAX_SWIPE_DURATION` seconds
   - direction is classified from `atan2(dy, dx)` into one of `SWIPE_LEFT/RIGHT/UP/DOWN`, and `GESTURE_COOLDOWN` seconds must have elapsed since the last recognized gesture. After a gesture fires, `position_history` is cleared to require a fresh swipe.
   - Losing hand tracking (no landmarks in a frame) also clears the history.
4. **Output** — currently gestures are only `print()`ed and overlaid on the video window; there is no actual macOS desktop-switching wired up yet, despite `pynput` and `pyobjc-framework-Quartz` being in `requirements.txt` for that purpose. Adding that integration is the natural next step when working in this codebase.

When tuning gesture detection, the constants at the top of `main.py` (`HISTORY_SIZE`, `MOVEMENT_THRESHOLD`, `MAX_SWIPE_DURATION`, `GESTURE_COOLDOWN`) are the primary levers — prefer adjusting them over rewriting the detection logic.
