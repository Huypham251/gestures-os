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

        # Mirror the frame so it matches the user's real-world sense of
        # left/right, like a normal camera app. Without this, a swipe to the
        # user's right moves toward decreasing x in the raw frame, so every
        # detected direction (and the on-screen preview) would be backwards.
        frame = cv2.flip(frame, 1)

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
