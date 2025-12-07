import schedule
import time
from main import DisclosureClass

# wait for selenium container ready
print("Start search_disclosure/start.py")

# define class instance
Disclosure = DisclosureClass()

# DEV : run once immediately
# Disclosure.main_process()

# PROD : set run schedule
schedule.every().monday.at("19:10").do(lambda:Disclosure.main_process())
schedule.every().tuesday.at("19:10").do(lambda:Disclosure.main_process())
schedule.every().wednesday.at("19:10").do(lambda:Disclosure.main_process())
schedule.every().thursday.at("19:10").do(lambda:Disclosure.main_process())
schedule.every().friday.at("19:10").do(lambda:Disclosure.main_process())
while True:
    schedule.run_pending()
    time.sleep(20)