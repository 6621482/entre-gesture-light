import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("웹캠을 열 수 없습니다.")
else:
    print("웹캠 연결 성공! 'q'를 누르면 종료됩니다.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow('Webcam Test', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()