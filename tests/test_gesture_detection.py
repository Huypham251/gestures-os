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
