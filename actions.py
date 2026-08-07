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
    except (OSError, RuntimeError):
        if not _warned_permission_error:
            print(
                "Could not simulate a keypress for gesture "
                f"'{gesture}'. On macOS this usually means the running "
                "process needs Accessibility permission: System Settings "
                "-> Privacy & Security."
            )
            _warned_permission_error = True
