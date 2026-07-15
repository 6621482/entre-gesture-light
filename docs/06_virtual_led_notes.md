# 가상 LED 시뮬레이터 구현
제스처 인식(`gesture.py`, `gesture_demo.py`) → 조명 제어 로직을 먼저 테스트하기 위해 가상 LED 모듈(`virtual_led.py`)을 추가

## 1. 목표
- 하드웨어 없이도 ON/OFF, 밝기 조절 결과를 화면으로 확인
- 나중에 실제 하드웨어가 오면 로직(제스처 인식, 상태 머신)은 그대로 두고, 값을 적용하는 부분만 교체 가능하도록 설계

## 2. 설계

### 상태 (`VirtualLight`)
```python
class VirtualLight:
    def __init__(self):
        self.is_on = False
        self.brightness = 50

    def turn_on(self):
        self.is_on = True

    def turn_off(self):
        self.is_on = False

    def set_brightness(self, value):
        self.brightness = max(0, min(100, value))
```

`is_on`, `brightness` 두 값만 들고 있고, 이 값을 바꾸는 함수 3개(`turn_on`, `turn_off`, `set_brightness`)를 제공

### 시각화 (`LEDVisualizer`)
`threading.Thread`를 상속받아 별도 스레드에서 Tkinter 창을 띄우고, `VirtualLight`의 상태를 0.05초 간격으로 읽어서 원(LED)의 색을 갱신

**별도 스레드로 만든 이유**: `gesture_demo.py`의 웹캠 루프(`while cap.isOpened():`)와 Tkinter의 `mainloop()`는 둘 다 무한루프이므로 한 스레드에서 둘 다 돌릴 수 없음. 그래서 시각화 창만 별도 스레드로 분리하고, `daemon=True`로 만들어서 메인 프로그램(웹캠 루프) 종료 시 별도 `join()` 없이 자동으로 같이 정리되게 함

**Tkinter 갱신 방식**: `after(ms, 함수)`로 자기 자신을 반복 예약하는 방식 (Tkinter엔 "N초마다 반복" 기능이 따로 없어서, 함수 끝에서 스스로를 다시 예약하는 패턴을 사용)

## 3. `gesture_demo.py` 연동
기존 확장 지점(`apply_brightness`)을 그대로 활용하고, ON/OFF용 `apply_power`를 새로 추가
```python
from virtual_led import VirtualLight, LEDVisualizer

light = VirtualLight()
visualizer = LEDVisualizer(light)
visualizer.start()

_last_applied = None
_last_power = None

def apply_brightness(value: int):
    global _last_applied
    if value != _last_applied:
        light.set_brightness(value)
        _last_applied = value

def apply_power(gesture_name: str):
    global _last_power
    if gesture_name == "ON" and _last_power != "ON":
        light.turn_on()
        _last_power = "ON"
    elif gesture_name == "OFF" and _last_power != "OFF":
        light.turn_off()
        _last_power = "OFF"
```

`main()`의 밝기 모드가 아닐 때(`else` 블록)에 `apply_power(gesture_name)` 호출 추가. `finger_state.py`, `gesture.py`의 인식 로직은 수정하지 않음

### 설계 결정: 밝기조절 진입 시 자동으로 켜지게 할지
밝기조절 모드에 진입해도 조명이 꺼진 상태면 자동으로 켜지게 할지(매끄러운 데모) vs. ON 제스처로 먼저 켠 뒤에만 밝기 조절이 보이게 할지(실제 전구와 동일한 동작, 기존 ON/OFF·밝기조절 상태 머신을 독립적으로 유지하는 설계 원칙과 일관성) 고민 후, **후자로 결정**. 코드 변경 없이 기존 구조 그대로 유지

## 4. 오늘 이해한 개념

### 스레드(threading)
- 같은 프로세스 안에서 실행 흐름만 하나 더 만드는 것
    - 힙에 있는 객체는 두 스레드가 그대로 공유하지만, 함수 호출 시 쌓는 스택은 스레드마다 별개
- 객체 생성과 시작은 분리된 두 단계:
    1. `LEDVisualizer(light)`: 객체만 만들어짐 (아직 새 스레드/스택 없음)
    2. `.start()`: 이 시점에 OS에 실재로 새 스레드 생성을 요청함(리눅스면 내부적으로 `pthread_create()`에 해당하는 동작) 새로 새긴 스레드가 우리가 정의한 `run()`을 실행하기 시작 
    - `start()`는 `threading.Thread`를 상속받으면 있는 기능 
- `start()`는 새 스레드가 끝나길 기다리지 않고 바로 다음줄로 넘어감 (비동기)
- `damon=True`: 메인 스레드(웹캠 루프) 종료 시 자동으로 같이 정리됨

### 상속(inheritance)
- `class LEDVisualizer(threading.Thread)`: 괄호는 부모 클래스를 선언함 -> 이 클래스는 `threading.Thread`의 기능을 물려받는다는 뜻
- `super().__init__(damon=True)`: 부모(threading.Thread)가 원래 하던 초기화를 먼저 실행하라는 의미. 스레드를 만들 때 필요한 내부 준비는 파이썬이 알아서 하게 두고, 우리는 `damon=True` 같은 옵션만 넘겨줌
- `self`는 이 메서드를 호출한 객체 자기 자신을 가리킴

### Tkinter
- `tk.Tk()`: 실제 OS 창 하나를 생성 
- `tk.Canvas()`: 도형을 그릴 수 있는 도화지 위젯 (`.pack()`을 호출해야 실제로 창에 배치되어 보임 -> 만들기만 하고 `pack()`안 하면 화면에 안 뜸)
- `canvas.create_oval(x0, y0, x1, y1, ...)`: 원(타원)을 그리고, 그 도형을 가리키는 ID를 반환
- `canvas.itemconfig(id, fill=색)`: ID로 이미 그려진 도형을 찾아서 속성(색 등)만 갱신 (다시 그리는 게 아니라 기존 도형을 수정하는 것)
- `root.after(ms, 함수)`: Tkinter에는 N초마다 반복실행하는 기능이 없어서 함수 끝에서 자기 자신을 다시 `after`로 예약하는 방식으로 반복을 구현 
- `root.mainloop()`: 창 이벤트(클릭, `after`타이머 등)를 계속 감시하는 무한 루프. 호출하면 여기서 멈춰서 창이 닫힐 때까지 다음 코드로 안 넘어감 -> 웹캠 루프와 동시에 돌리려면 별도 스레드가 필요한 이유 

## 5. 확장 지점 (실제 하드웨어 연결 시)
`virtual_led.py`의 `VirtualLight`/`LEDVisualizer` 대신 실제 `neopixel` 라이브러리로 교체하고, `apply_brightness`/`apply_power` 내부에서 실제 GPIO 제어 코드를 호출하도록 교체. 제스처 인식, 상태 머신 로직은 그대로 유지