import subprocess
from unittest.mock import Mock, patch

import pytest

import actions


@pytest.fixture(autouse=True)
def reset_permission_warning(monkeypatch):
    monkeypatch.setattr(actions, "_warned_permission_error", False)


def test_dispatch_swipe_left_sends_left_arrow_keycode():
    key_sender = Mock()
    actions.dispatch("SWIPE_LEFT", key_sender=key_sender)
    key_sender.assert_called_once_with(123)  # kVK_LeftArrow


def test_dispatch_swipe_right_sends_right_arrow_keycode():
    key_sender = Mock()
    actions.dispatch("SWIPE_RIGHT", key_sender=key_sender)
    key_sender.assert_called_once_with(124)  # kVK_RightArrow


def test_dispatch_swipe_up_sends_up_arrow_keycode():
    key_sender = Mock()
    actions.dispatch("SWIPE_UP", key_sender=key_sender)
    key_sender.assert_called_once_with(126)  # kVK_UpArrow


def test_dispatch_swipe_down_sends_down_arrow_keycode():
    key_sender = Mock()
    actions.dispatch("SWIPE_DOWN", key_sender=key_sender)
    key_sender.assert_called_once_with(125)  # kVK_DownArrow


def test_dispatch_unknown_gesture_is_noop():
    key_sender = Mock()
    actions.dispatch("NOT_A_GESTURE", key_sender=key_sender)
    key_sender.assert_not_called()


def test_dispatch_prints_instructive_message_once_on_subprocess_failure(capsys):
    key_sender = Mock(side_effect=subprocess.CalledProcessError(1, ["osascript"]))

    actions.dispatch("SWIPE_LEFT", key_sender=key_sender)
    actions.dispatch("SWIPE_RIGHT", key_sender=key_sender)

    output = capsys.readouterr().out
    assert output.count("Automation") == 1


def test_dispatch_raises_on_programming_error():
    """A bug in key_sender itself (not an OS/permission failure) must
    propagate, not be swallowed and misreported as a permission issue."""
    key_sender = Mock(side_effect=AttributeError("boom"))

    with pytest.raises(AttributeError):
        actions.dispatch("SWIPE_LEFT", key_sender=key_sender)


def test_send_ctrl_arrow_invokes_osascript_with_control_and_keycode():
    """actions._send_ctrl_arrow is the real, default key_sender. Mock only
    subprocess.run - the actual OS boundary - to verify it constructs the
    correct AppleScript command without actually shelling out."""
    with patch("actions.subprocess.run") as mock_run:
        actions._send_ctrl_arrow(123)

    mock_run.assert_called_once()
    (command,), kwargs = mock_run.call_args
    assert command[0] == "osascript"
    assert "key code 123" in command[2]
    assert "control down" in command[2]
    assert kwargs.get("check") is True
