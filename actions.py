import subprocess

# macOS virtual keycodes (kVK_*) for the arrow keys.
_GESTURE_KEYCODES = {
    "SWIPE_LEFT": 123,   # kVK_LeftArrow  -> move to Space on the left
    "SWIPE_RIGHT": 124,  # kVK_RightArrow -> move to Space on the right
    "SWIPE_DOWN": 125,   # kVK_DownArrow  -> App Exposé
    "SWIPE_UP": 126,     # kVK_UpArrow    -> Mission Control
}


def _send_ctrl_arrow(vk: int) -> None:
    """Send Ctrl+<arrow> via AppleScript's System Events.

    Plain CGEventPost-based keyboard simulation (e.g. pynput's default
    backend) does NOT trigger macOS's Mission Control Space-switch handler,
    even from a process with Accessibility trust - verified empirically:
    neither pynput's default event construction nor a variant tagging the
    event with an explicit HID event source switched Spaces, while both a
    real physical keypress and AppleScript's System Events pathway did.
    System Events is used here for that reason.
    """
    subprocess.run(
        [
            "osascript",
            "-e",
            f'tell application "System Events" to key code {vk} using {{control down}}',
        ],
        check=True,
        capture_output=True,
    )


_warned_permission_error = False


def _warn_permission_error_once(gesture: str) -> None:
    """Print the instructive Automation-permission message, at most once."""
    global _warned_permission_error
    if not _warned_permission_error:
        print(
            "Could not send the keypress for gesture "
            f"'{gesture}' via System Events - check System Settings -> "
            "Privacy & Security -> Automation and grant this app "
            "permission to control System Events."
        )
        _warned_permission_error = True


def dispatch(gesture: str, key_sender=_send_ctrl_arrow) -> None:
    """Look up gesture's macOS virtual keycode and send Ctrl+<that key>.

    Unknown gestures are a no-op. An OS/subprocess-level failure (e.g.
    missing 'Automation' permission for controlling System Events) is
    reported once instead of crashing the caller's loop or being silently
    retried every frame; a programming error in key_sender itself (a bug,
    not an OS-permission issue) propagates normally.
    """
    vk = _GESTURE_KEYCODES.get(gesture)
    if vk is None:
        return

    try:
        key_sender(vk)
    except (subprocess.CalledProcessError, OSError):
        _warn_permission_error_once(gesture)
