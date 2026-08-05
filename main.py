import cv2
import mediapipe as mp

camera = cv2.VideoCapture(0)
hands = mp.solutions.hands.Hands()
mp_draw = mp.solutions.drawing_utils

while True:
    ret, frame = camera.read()

    if not ret:
        break

    results = hands.process(frame)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp.solutions.hands.HAND_CONNECTIONS
            )

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()