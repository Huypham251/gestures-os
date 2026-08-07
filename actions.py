from pynput.keyboard import Controller, Key

try:
    from ApplicationServices import AXIsProcessTrusted
except ImportError:  # pragma: no cover - defensive fallback if pyobjc symbol is missing
    def AXIsProcessTrusted() -> bool:
        return True


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


def _warn_permission_error_once(gesture: str) -> None:
    """Print the instructive Accessibility-permission message, at most once."""
    global _warned_permission_error
    if not _warned_permission_error:
        print(
            "Could not simulate a keypress for gesture "
            f"'{gesture}'. On macOS this usually means the running "
            "process needs Accessibility permission: System Settings "
            "-> Privacy & Security."
        )
        _warned_permission_error = True


def dispatch(gesture: str, controller: Controller | None = None) -> None:
    """Look up gesture in ACTIONS and simulate the mapped keyboard shortcut.

    Unknown gestures are a no-op. On macOS, simulating keypresses requires
    Accessibility permission for the running process. pynput's CGEventPost
    backend does NOT raise when that permission is missing - it silently
    discards the event - so we proactively check AXIsProcessTrusted() before
    attempting the keypress and skip it entirely if untrusted. The
    except (OSError, RuntimeError) block remains as a backstop for any other
    unexpected runtime failure during the actual keypress. Either path
    reports the instructive message once instead of crashing the caller's
    loop or being silently retried every frame.
    """
    action = ACTIONS.get(gesture)
    if action is None:
        return

    if controller is None:
        controller = Controller()

    if not AXIsProcessTrusted():
        _warn_permission_error_once(gesture)
        return

    try:
        action(controller)
    except (OSError, RuntimeError):
        _warn_permission_error_once(gesture)
