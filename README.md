#if you run this project u can create our own environment in vs.code
# Save-Life
#🩸BloodNeed - Smart Blood Donation Platform

*BloodNeed* is a smart and responsive blood donation web application built using *Flask* and *MySQL, aimed at saving lives by connecting blood donors and patients efficiently. It enables users to register, update medical details, request blood in emergencies via **SMS, and receive timely responses using **Twilio* and *Telegram* integration.

---

## 🚀 Features

- ✅ *User Registration & Login* – Secure registration with session-based login.
- 🔐 *Forgot Password with OTP* – Reset password using Twilio OTP via SMS.
- 🧾 *Donor Details Update* – Capture personal info, blood group, location, and health conditions.
- 📲 *Emergency SMS Request* – Patients can request blood via Twilio SMS.
- 🤝 *Donor Response via SMS* – Donors can respond YES to confirm willingness.
- 💬 *Direct Donor-Patient Chat* – Chat/contact info is shared once the donor confirms.
- 📡 *Telegram Notification* – Donors are notified on Telegram for urgent requests.
- 📊 *Admin View (Optional)* – Easily manage requests and donor database (can be added).
- 📁 Modular codebase with Flask Blueprints for clean development.

---

## 💻 Tech Stack

| Component         | Technology Used                       |
|------------------|----------------------------------------|
| *Frontend*     | HTML5, CSS3,                           |
| *Backend*      | Python 3, Flask                        |
| *Database*     | MySQL                                  |
| *APIs*         | Twilio SMS API, Telegram Bot API       |
| *Auth*         | Session-based login                    |
| *Hosting*      | Localhost / Render / Heroku (optional) |

---



## 🔧 Setup Instructions

1. *Clone the repository*
   ```bash
   git clone https://github.com/yourusername/bloodneed.git
   cd bloodneed

2.Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

3.Install dependencies
pip install -r requirements.txt

4.Structure
bloodneed/
│
├── static/                # CSS, JS, images
├── templates/             # HTML templates
├── routes/                # Flask Blueprints (register, login, details, sms, reset)
│   ├── auth.py
│   ├── details.py
│   ├── reset_password.py
│   └── sms_handler.py
│
├── db.py                  # Database connection logic
├── telegram_notify.py     # Telegram Bot function
├── run.py                 # Entry point for the app
├── .env                   # Environment variables
├── requirements.txt
└── README.md# Safe-Life
