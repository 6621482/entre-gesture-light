# 제스처 인식 프로토타입 작업 
ON/OFF 제스처 인식 + FPS 측정 

## 1. 오늘 만든 파일 
| 파일 | 역할 |
|---|---|
| `finger_state.py` (신규) | 손가락별 펴짐/굽힘 판정 로직<br> `finger_extension_test.py`에서 검증된 로직을 분리 |
| `finger_extension_test.py` (리팩터링) | `finger_state.py`를 import해서 씀<br> 재보정/디버깅용 웹캠 테스트 스크립트로 역할 유지 |
| `gesture.py` (신규) | 제스처 패턴 정의(config) + `classify_gesture()` 판정 함수 |
| `gesture_demo.py` (신규) | 웹캠 + 위 모듈들을 연결한 실제 데모<br> 화면에 제스처/FPS 표시 |

## 2. 설계 결정과 이유
### 2.1 `finger_state.py`를 측정(`get_finger_ratios`)과 판단(`get_finger_states`) 두 함수로 분리 
하나로 합치면 판정 결과(True/False)만 남고 원본 비율 숫자가 사라짐. 원본 비율을 봐야 threshold를 어떻게 조정할지 판단할 수 있음. 그래서 "측정"과 "판단"을 분리해서, 판단 함수는 이미 계산된 비율 딕셔너리를 입력으로 받게 만듦.

### 2.2 `gesture.py`의 패턴 매칭을 리스트 위치 비교가 아니라 딕셔너리 비교(`==`)로 구현
처음엔 `finger_states`를 `[0,1,1,0,0]`같은 리스트로 변환해서 비교하려 했는데, 이러면 "몇 번째가 어느 손가락이냐"가 암묵적으로 딕셔너리 순서에 의존하게 됨 -> 순서가 다르면 인식 오류가 생길 위험이 있음.
딕셔너리끼리 `==`로 비교하면 파이썬에서 키 순서와 무관하게 값만 비교하므로 이 위험이 없어지고, 패턴 자체도 읽기 쉬워짐.

### 2.3 FPS는 `time.perf_counter()`로, 손 감지 여부와 상관없이 매 프레임 계산
`time.time()`은 시스템 시계 보정에 영향받을 수 있어서 경과 시간 측정엔 부적합  
`perf_counter()`는 monotonic이라 안전함.  
처음엔 FPS 계산이 `if hand_world_landmarks:` 블록 안에 있어서 손이 안 잡힌 첫 프레임에 `UnboundLocalError`가 나는 버그가 있었음 -> `detect_for_video` 호출 직후, 조건문 밖으로 빼서 수정 

## 3. 실습 결과
- `gesture_demo.py` 로컬(venv-win) 실행 결과 - ON(보자기), OFF(주먹) 둘 다 정확히 인식됨
- 실측 FPS: OFF 39.36 / ON 39.51 (PC 웹캠 기준, VIDEO 모드)
![gesture_demo_result1](./images/gesture_demo_result(ON).png)
![gesture_demo_result2](./images/gesture_demo_result(OFF).png)

## 4. 실측 재보정
- `THUMB_EXTENDED_THRESHOLD`: `1` → `1.25`
- 이유: 주먹을 쥘 때 엄지를 완전히 구부리지 않는 습관이 있어서, 실측 비율이 1~1.2대로 나와 OFF로 판정되지 않고 "알 수 없음"이 나왔음. 실제 웹캠 테스트로 발견 → `finger_extension_test.py`로 재보정.

## 5. FPS
### 5.1 추가한 이유
지금 노트북/PC 웹캠 기준 성능을 기록해두면, 나중에 최적화 단계에서 LIVE_STREAM 모드로 바꾸거나 라즈베리파이로 하드웨어를 옮겼을 때 "그때보다 빨라졌는지/느려졌는지"를 비교할 수 있는 기준점이 됨

### 5.2 계산 방법
1. 프레임 처리 시작 직전에 시각을 기록 (`fps_start_time`)
2. 처리(웹캠 캡처 + 색공간 변환 + MediaPipe 추론)가 끝난 직후 시각을 또 기록 (`fps_end_time`)
3. 두 값의 차이가 "이 프레임 하나 처리하는 데 걸린 시간"(초 단위)
4. `FPS = 1 / 처리시간` → "1초에 이만큼의 프레임을 처리할 수 있다"는 값으로 환산

### 5.3 `time.time()` 대신 `time.perf_counter()`를 쓴 이유
오늘 처음 알게 된 부분이라 자세히 정리:

- `time.time()`은 "1970년 1월 1일부터 몇 초 지났는가"를 나타내는 실제 시각(wall clock)임. 이 값은 OS가 NTP로 시스템 시계를 보정하거나 사용자가 수동으로 시계를 바꾸면 순간적으로 튈 수 있음. 극단적인 경우 두 시점의 차이가 음수로 나올 수도 있음.
- `time.perf_counter()`는 애초에 "경과 시간 측정" 전용으로 만들어진 함수. 시스템에서 쓸 수 있는 가장 정밀한 시계를 사용하고, **모노토닉(monotonic)** — 즉 절대 거꾸로 가지 않고, 시스템 시계가 조정돼도 영향을 안 받음.
- `perf_counter()`가 반환하는 값 자체는 "지금 몇 시인지"와 무관한 임의의 기준점부터 잰 숫자라 그 자체로는 의미가 없음. 오직 두 번 호출한 값의 **차이**만 믿고 쓰면 됨.
  ```python
  start = time.perf_counter()
  # ... 처리 ...
  end = time.perf_counter()
  elapsed = end - start  # 이 차이값만 의미 있음
  ```
- 결론: 실제 날짜/시각이 필요 없고 순수하게 "경과 시간"만 필요한 성능 측정 상황엔 `perf_counter()`가 더 안전하고 정밀함.

## 6. 오늘 이해한 것
- `time.perf_counter()`는 경과 시간 측정 전용, `time.time()`은 실제 시각(wall clock) —> 성능 측정엔 `perf_counter()`가 맞음 (모노토닉이라 시스템 시계 보정에 안 흔들림)
- 타입힌트(`: dict[str, bool]`, `-> str`)는 실행에 전혀 영향 없는 문서화용 문법 — 없어도 코드는 똑같이 동작함
- 파이썬 `if`문은 별도 스코프를 안 만들어서, 조건문 안에서만 정의된 변수를 밖에서 참조하면 `UnboundLocalError`가 날 수 있음 (오늘 FPS 코드에서 직접 겪음 — `fps_value`가 if 블록 안에서만 계산되고 있었음)
- 딕셔너리 비교(`==`)는 키 순서 상관없이 값만 같으면 True — 리스트로 순서에 암묵적으로 의존해서 비교하는 것보다 안전함
- "측정"과 "판단"을 분리해두면(`get_finger_ratios`/`get_finger_states`) 나중에 threshold만 바꿔서 재적용하기 쉬워짐 — 재사용성 있는 설계 원칙

## 7. 다음에 해야할 것 
- 밝기 조절 제스처 추가
- 제스처 오탐(Midas touch problem) 대응
    - 손 인식이 항상 켜져 있으면 사용자가 무심코 취한 손 모양도 명령으로 오인식할 수 있음. "이 프레임이 무슨 제스처인가"(classifiy_gesture)와 "언제 그 판정을 실제로 실행할지"(트리거/디바운스)가 서로 다른 레이어라서, classify_gesture를 stateless하게 만들어두면 나중에 트리거 레이어만 얹으면 됨 -> Github 이슈로 등록 예정 