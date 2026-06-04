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
