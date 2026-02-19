import time
from datetime import datetime
import pymem

PROCESS_NAME = "hollow_knight.exe"
HEALTH_ADDR  = 0x1DD24552198
RESET_VALUE  = 9
POLL_INTERVAL = 0.01

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}")

def main():
    log("Waiting for game process...")
    pm = None
    while pm is None:
        try:
            pm = pymem.Pymem(PROCESS_NAME)
        except:
            time.sleep(1)
    log("Attached to process")
    last_value = None

    while True:
        try:
            current = pm.read_int(HEALTH_ADDR)
            if last_value is None:
                last_value = current
            if current != last_value:
                log(f"Health changed: {last_value} -> {current}")
                pm.write_int(HEALTH_ADDR, RESET_VALUE)
                last_value = RESET_VALUE
            else:
                last_value = current

        except Exception as e:
            log(f"Memory read failed: {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
