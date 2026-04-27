import time
import subprocess
from datetime import datetime

INTERVAL_MINUTES = 5

while True:
    print(f"[SCHEDULER] Sleeping {INTERVAL_MINUTES} minutes...")
    time.sleep(INTERVAL_MINUTES * 60)
    print(f"[SCHEDULER] Running pipeline at {datetime.now()}")
    subprocess.run(["python", "run_pipeline.py"])
