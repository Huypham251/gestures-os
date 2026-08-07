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
