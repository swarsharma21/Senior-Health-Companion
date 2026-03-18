import schedule
import time
import threading
import csv
import requests
from shared import pending_reminders
ACCESS_TOKEN = "EAAdPF5RRGGcBQ0iImJKji9HMkVORHg45bVqaU303Lip96fJZB3JczpPBVDof320hZBvaUOekKOQc2RWhvFmeGTsmZACqJXxz6ZBbEZB8E1Q0J55cepK4lS0S2XTwqNnHFC7unsde7XVCr1bfM62ahkjkgDwVKH6BUiOJcrztdlcDbeePMDu17daDkZBZAtCXtBUiWmhYjUXjxRmbJxZCgQZC8fkspP703FOgoMMSZA7RAgFtrgPf3CeZCKB9HVk7IbdyuGKhTNU9cRYOiktbcPUlH0Qkw83"
PHONE_NUMBER_ID = "954859211055275"

def send_message(to, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=payload)

def send_reminders():
    with open("users.csv", "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            phone = row["phone"]
            medicine = row["medicine"]

            send_message(phone,
                f"💊 Reminder: Take your {medicine}\n\n"
                "Reply:\n1️⃣ Taken\n2️⃣ Not yet"
            )
            pending_reminders[phone] = True
def check_missed():

    with open("users.csv", "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            phone = row["phone"]

            if phone in pending_reminders:
                name = row["name"]
                caregiver = row["caregiver"]

                send_message(
                    caregiver,
                    f"🚨 ALERT: {name} did NOT respond to medicine reminder!"
                )

                # remove after alert
                pending_reminders.pop(phone, None)
def schedule_reminders():
    # Example: runs every minute (for testing)
    schedule.every(1).minutes.do(send_reminders)
    schedule.every(2).minutes.do(check_missed)
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler():
    thread = threading.Thread(target=schedule_reminders)
    thread.daemon = True
    thread.start()
