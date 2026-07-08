import cv2  # 이미지 표시, 텍스트 그리기용 OpenCV
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

mp_hands = mp.tasks.vision.HandLandmarksConnections  # 손 랜드마크 연결 정보
mp_drawing = mp.tasks.vision.drawing_utils  # 손 랜드마크 시각화용 유틸리티
mp_drawing_styles = mp.tasks.vision.drawing_styles  # 손 랜드마크 시각화용 스타일

# Left/Right Hand 구분 텍스트 표시용 상수
MARGIN = 10  # pixels
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54)  # 초록색 

def draw_landmarks_on_image(rgb_image, detection_result):
    hand_landmarks_list = detection_result.hand_landmarks
    handedness_list = detection_result.handedness  # 왼손인지 오른손인지 
    annotated_image = np.copy(rgb_image)  # 복사본 만들어서 시각화 (원본 이미지 훼손 방지)

    # Loop through the detected hands to visualize.
    for idx in range(len(hand_landmarks_list)):  # 감지된 손이 여러 개 일 수 있음 
        hand_landmarks = hand_landmarks_list[idx]
        handedness = handedness_list[idx]

        # Draw the hand landmarks.
        mp_drawing.draw_landmarks(
            annotated_image,  # 이미지
            hand_landmarks,  # 랜드마크 좌표
            mp_hands.HAND_CONNECTIONS,  # 연결 정보
            mp_drawing_styles.get_default_hand_landmarks_style(),  # 점 스타일
            mp_drawing_styles.get_default_hand_connections_style(),  # 선 스타일
        )

        # Get the top left corner of the detected hand's bounding box.
        height, width, _ = annotated_image.shape  # 이미지 크기 (_은 지금 안 쓸 변수라는 의미)
        x_coordinates = [landmark.x for landmark in hand_landmarks]
        y_coordinates = [landmark.y for landmark in hand_landmarks]
        text_x = int(min(x_coordinates) * width)  # 텍스트 위치 
        text_y = int(min(y_coordinates) * height) - MARGIN

        # Draw handedness (left or right hand) on the image.
        cv2.putText(
            annotated_image, f"{handedness[0].category_name}",
            (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX,
            FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA,
        )

    return annotated_image


# ── 콜랩 노트북 셀: STEP 1~5 ──

# STEP 1: Import the necessary modules. (이미 위에서 완료)

# STEP 2: Create an HandLandmarker object.
base_options = python.BaseOptions(model_asset_path="../hand_landmarker.task")
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2)
detector = vision.HandLandmarker.create_from_options(options)

# STEP 3: Load the input image.
image = mp.Image.create_from_file("test_hand.jpg")

# STEP 4: Detect hand landmarks from the input image.
detection_result = detector.detect(image)

# STEP 5: Process the classification result. In this case, visualize it.
annotated_image = draw_landmarks_on_image(image.numpy_view(), detection_result)

# 결과 이미지 화면에 띄우기 
cv2.imshow("Hand Landmarker Result", cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
print("아무 키나 누르면 창이 닫힙니다.")
cv2.waitKey(0)
cv2.destroyAllWindows()