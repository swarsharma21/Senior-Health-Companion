from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
import requests
import csv
import os
from reminder import start_scheduler
from shared import pending_reminders

app = FastAPI()

# Configuration
VERIFY_TOKEN = "swar_health_bot_123"
ACCESS_TOKEN = "EAAdPF5RRGGcBQ0iImJKji9HMkVORHg45bVqaU303Lip96fJZB3JczpPBVDof320hZBvaUOekKOQc2RWhvFmeGTsmZACqJXxz6ZBbEZB8E1Q0J55cepK4lS0S2XTwqNnHFC7unsde7XVCr1bfM62ahkjkgDwVKH6BUiOJcrztdlcDbeePMDu17daDkZBZAtCXtBUiWmhYjUXjxRmbJxZCgQZC8fkspP703FOgoMMSZA7RAgFtrgPf3CeZCKB9HVk7IbdyuGKhTNU9cRYOiktbcPUlH0Qkw83"
PHONE_NUMBER_ID = "954859211055275"

# States
LANGUAGE, NAME, AGE, CAREGIVER, MEDICINE, TIME, DONE = "language", "name", "age", "caregiver", "medicine", "time", "done"

user_states = {}
user_data = {}

# CSV Setup
if not os.path.exists("users.csv"):
    with open("users.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["phone", "name", "age", "language", "caregiver", "medicine", "time"])

def send_message(to, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def alert_caretaker(caregiver_phone, user_name):
    send_message(caregiver_phone, f"⚠️ Alert: {user_name} may have missed their medicine!")

@app.api_route("/webhook", methods=["GET", "POST"])
async def webhook(request: Request):

    # ---------------------------
    # 1. VERIFICATION (GET)
    # ---------------------------
    if request.method == "GET":
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        print("VERIFY HIT:", mode, token, challenge)  # 👈 ADD THIS

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return PlainTextResponse(content=challenge, status_code=200)

        return PlainTextResponse(content="error", status_code=403)

    # ---------------------------
    # 2. MESSAGE HANDLING (POST)
    # ---------------------------
    if request.method == "POST":
        print("🔥 WEBHOOK HIT")

        data = await request.json()
        print("RAW:", data)

        try:
            # Extract message safely
            value = data.get("entry", [])[0].get("changes", [])[0].get("value", {})

            if "messages" not in value:
                return JSONResponse({"status": "no message"})

            message = value["messages"][0]
            phone = message["from"]
            text = message.get("text", {}).get("body", "").lower().strip()

            print("USER SAID:", text)

            # Get current state
            state = user_states.get(phone)

            # ---------------------------
            # STATE MACHINE LOGIC
            # ---------------------------

            # Start
            if text == "hi" or text == "hello":
                user_states[phone] = LANGUAGE
                user_data[phone] = {}

                send_message(phone,
                    "👋 Welcome to Senior Health Companion\n\n"
                    "Select Language:\n1️⃣ English\n2️⃣ Hindi"
                )

            elif state == LANGUAGE:
                user_data[phone]["language"] = "English" if text == "1" else "Hindi"
                user_states[phone] = NAME
                send_message(phone, "Please enter your name")

            elif state == NAME:
                user_data[phone]["name"] = text
                user_states[phone] = AGE
                send_message(phone, "Enter your age")

            elif state == AGE:
                user_data[phone]["age"] = text
                user_states[phone] = CAREGIVER
                send_message(phone, "Enter caregiver phone number (with country code)")

            elif state == CAREGIVER:
                user_data[phone]["caregiver"] = text
                user_states[phone] = MEDICINE
                send_message(phone, "Enter medicine name")

            elif state == MEDICINE:
                user_data[phone]["medicine"] = text
                user_states[phone] = TIME
                send_message(phone, "Enter time (HH:MM in 24-hour format)")

            elif state == TIME:
                user_data[phone]["time"] = text

                # Save to CSV
                with open("users.csv", "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        phone,
                        user_data[phone]["name"],
                        user_data[phone]["age"],
                        user_data[phone]["language"],
                        user_data[phone]["caregiver"],
                        user_data[phone]["medicine"],
                        user_data[phone]["time"]
                    ])

                user_states[phone] = DONE

                send_message(phone,
                    f"✅ Registered!\n\n"
                    f"Medicine: {user_data[phone]['medicine']}\n"
                    f"Time: {user_data[phone]['time']}"
                )

            elif state == DONE:

                if text == "1":
                    pending_reminders.pop(phone, None)
                    send_message(phone, "✅ Great! Stay healthy")

                elif text == "2":
                    pending_reminders.pop(phone, None)

                    caregiver = user_data.get(phone, {}).get("caregiver")
                    name = user_data.get(phone, {}).get("name", "The patient")

                    if caregiver:
                        alert_caretaker(caregiver, name)
                        send_message(phone, "⚠️ Caregiver has been notified")
                    else:
                        send_message(phone, "Error: Caregiver info not found.")

                else:
                    send_message(phone, "Reply:\n1️⃣ Taken\n2️⃣ Not yet")

            else:
                send_message(phone, "Send *Hi* to start the registration.")

        except Exception as e:
            print("❌ Error:", e)

        return JSONResponse({"status": "ok"})

# Start the background scheduler
start_scheduler()
