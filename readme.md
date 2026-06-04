# 🤖 Anu Bot

<div align="center">

### Messenger Group Assistant

AI Chat • Anime Search • Group Management • Telegram Forwarder

Created by **Arafat Hoshen Zihad**

[Facebook](https://www.facebook.com/arafat.hosen.zihad) • [Instagram](https://www.instagram.com/agen_t0919/) • [GitHub](https://github.com/2byts) • [LinkedIn](https://www.linkedin.com/pub/dir/Arafat/Hoshen)

</div>

---

## 🌸 About

Anu Bot is a Facebook Messenger assistant built with Python and fbchat-muqit.

It includes AI conversations, anime utilities, group moderation tools, welcome/bye plugins, Telegram-to-Messenger forwarding, and various automation features.

This project was created for learning, experimentation, and personal use.

---

## ✨ Features

### 🤖 AI Features

* AI chat using `/anu`
* Fast response handling
* Custom roleplay personalities

### 🎌 Anime Features

* Anime information lookup
* Anime episode search
* Anime poster support

### 🛡️ Group Management

* Ban users
* Unban users
* Remove users
* Group settings system
* Leave group command

### 🎉 Group Plugins

* Welcome messages
* Goodbye messages
* Join notifications
* Startup admin notifications

### 📡 Telegram Forwarder

* Telegram → Messenger forwarding
* Multiple Telegram sources
* Route management
* Enable/Disable forwarding
* Persistent route settings

### ⚙️ Admin Tools

* Reload modules
* Maintenance mode
* Stop bot command
* User information tools

---

## 📂 Project Structure

```text
.
├── main.py
├── bot_config.py
├── config.example.json
├── requirements.txt
│
├── commands/
│   ├── admin/
│   ├── group_control/
│   ├── roleplay/
│   ├── anime.py
│   └── help.py
│
├── plugins/
│   ├── assets/
│   ├── join.py
│   ├── bye.py
│   ├── welcome.py
│   ├── telegram.py
│   └── telegram_forwarder.py
│
└── fbchat_muqit/
```

---

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/2byts/anu.git
cd anu
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create configuration:

```bash
cp config.example.json config.json
```

Add your settings:

* Facebook Admin IDs
* API Keys
* Telegram Credentials
* Forwarding Routes

Add Facebook cookies:

```text
cookies.json
```

---

## 🧩 Run Options

You can run Anu Bot in several ways depending on where you want to host it.

### Option 1: PC / Local Python

Best for testing on your own computer.

Requirements:

* Python 3.10+
* `pip`
* `config.json`
* `cookies.json`

Run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
python plugins/telegram.py
python main.py
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy config.example.json config.json
python plugins/telegram.py
python main.py
```

### Option 2: Python Server / VPS / Hosting Panel

Best for 24/7 hosting on a Python server, VPS, or panel like HidenCloud.

Upload these files/folders:

```text
main.py
bot_config.py
commands/
plugins/
fbchat_muqit/
requirements.txt
config.json
cookies.json
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python main.py
```

If Telegram is not logged in yet:

```bash
python plugins/telegram.py
```

Then restart the bot.

### Option 3: Replit

Best for simple cloud testing.

1. Create a new Python Replit.
2. Upload or import this repository.
3. Add `config.json` and `cookies.json` manually.
4. Open the Shell and install dependencies:

```bash
pip install -r requirements.txt
```

5. Run Telegram login once if needed:

```bash
python plugins/telegram.py
```

6. Set the Replit run command to:

```bash
python main.py
```

Note: Replit may sleep on free plans, so forwarding may stop when the repl sleeps.

### Option 4: Docker

Best for VPS or container hosting.

Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Build:

```bash
docker build -t anu-bot .
```

Run:

```bash
docker run -it --name anu-bot \
  -v $(pwd)/config.json:/app/config.json \
  -v $(pwd)/cookies.json:/app/cookies.json \
  -v $(pwd)/telegram_session.session:/app/telegram_session.session \
  anu-bot
```

For first Telegram login in Docker:

```bash
docker run -it --rm \
  -v $(pwd)/config.json:/app/config.json \
  -v $(pwd)/telegram_session.session:/app/telegram_session.session \
  anu-bot python plugins/telegram.py
```

---

## ▶️ Run

Start the bot:

```bash
python main.py
```

Telegram login:

```bash
python plugins/telegram.py
```

---

## 📜 Commands

### 🌷 General

```text
/help
/ping
/time
/anu <message>
```

### 🎌 Anime

```text
/ anime <name>
/ aniget <name> <episode>
```

Example:

```text
/ anime Naruto
/ aniget Naruto 5
```

### 🛡️ Group Control

```text
/ban
/unban
/remove
/settings
/settings <key> <on/off>
/out
```

### 📡 Telegram

```text
/tgstatus
/tgstart
/tgstop

/tgadd <telegram_source> <thread_id>
/tgremove <telegram_source>

/tgon <telegram_source>
/tgoff <telegram_source>
```

### ⚙️ Admin

```text
/reload

/maintain run
/maintain end

/stop
```

---

## 📡 Telegram Route Example

```json
{
  "source": "-1001234567890",
  "target_thread_id": "9876543210",
  "enabled": true
}
```

---

## 👨‍💻 Developer

### Arafat Hoshen Zihad

🇧🇩 Bangladeshi Developer

#### Social Links

🌐 Facebook
https://www.facebook.com/arafat.hosen.zihad

📸 Instagram
https://www.instagram.com/agen_t0919/

💻 GitHub
https://github.com/2byts

💼 LinkedIn
https://www.linkedin.com/pub/dir/Arafat/Hoshen

---

## ❤️ Credits

Huge thanks to **Muhammad MuQiT (togashigreat)** for creating and maintaining the amazing **fbchat-muqit** library.

Without this library, Messenger integration for Anu Bot would not have been possible.

GitHub:
https://github.com/togashigreat/fbchat-muqit

PyPI:
https://pypi.org/project/fbchat-muqit/

Thank you for your hard work and contribution to the community ❤️

---

## ⚠️ Disclaimer

This project is not affiliated with Facebook, Meta, Messenger, Telegram, AniList, or any third-party service.

Using automation on Messenger may violate platform policies and could result in restrictions on your account.

Use responsibly and preferably with a secondary account.

The developer is not responsible for any misuse of this software.

---

<div align="center">

### ⭐ Star the repository if you find it useful!

Made with ❤️ by Arafat Hoshen Zihad

</div>
