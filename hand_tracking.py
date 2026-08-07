from dataclasses import dataclass
from typing import Any

import cv2
import mediapipe as mp


@dataclass
class HandResult:
    x: int
    y: int
    landmarks: Any  # mediapipe NormalizedLandmarkList, needed only for drawing


class HandTracker:
    """Wraps MediaPipe Hands to track the index fingertip in a video frame."""

    def __init__(self):
        self._hands = mp.solutions.hands.Hands()

    def process(self, frame) -> HandResult | None:
        # MediaPipe expects RGB, but OpenCV captures in BGR - convert just for
        # detection and leave `frame` itself untouched (still BGR for imshow).
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb_frame)

        if not results.multi_hand_landmarks:
            return None

        hand_landmarks = results.multi_hand_landmarks[0]
        height, width, _ = frame.shape
        index_tip = hand_landmarks.landmark[
            mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP
        ]
        x, y = int(index_tip.x * width), int(index_tip.y * height)
        return HandResult(x=x, y=y, landmarks=hand_landmarks)

    def draw(self, frame, hand_result: HandResult) -> None:
        mp.solutions.drawing_utils.draw_landmarks(
            frame,
            hand_result.landmarks,
            mp.solutions.hands.HAND_CONNECTIONS,
        )
