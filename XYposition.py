# live_xy.py
import time, pyautogui
try:
    while True:
        x, y = pyautogui.position()
        print(f"\rX={x:4d} Y={y:4d}", end="", flush=True)
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nStopped.")
