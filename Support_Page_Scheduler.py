import schedule
import time
from Support_Page_Run import run_support_page_test

schedule.every().day.at("09:00").do(run_support_page_test)

print("Scheduler is running... Test will run at 9:00 AM daily")
print("Do not close this window!")

while True:
    schedule.run_pending()
    time.sleep(60)