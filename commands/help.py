HELP_TEXT = """🌸✨ 𝐀𝐍𝐔 𝐁𝐎𝐓 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 ✨🌸
╭─────────────────────╮
│ 🤖 Your Friendly AI Assistant │
╰─────────────────────╯

🌷 👤 𝐔𝐒𝐄𝐑 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒
━━━━━━━━━━━━━━━━━━━━

🌼 /help
➜ Show this command menu

🌼 /ping
➜ Check if the bot is online

🌼 /time
➜ Show current Bangladesh time 🇧🇩🕒

🌼 /anu <message>
➜ Chat with Anu AI 💖

🌼 /anu give me your photo
➜ Request a photo from Anu 📸🌹

💡 𝐓𝐢𝐩:
🌸 Reply to any Anu message and continue chatting without using /anu.

━━━━━━━━━━━━━━━━━━━━

🌺 🎌 𝐀𝐍𝐈𝐌𝐄 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒
━━━━━━━━━━━━━━━━━━━━

🌸 /anime <name>
➜ Search anime information and poster 🖼️

🌸 /aniget <name> <episode>
➜ Get anime episode video 🎥

🌷 Example:
➜ /aniget Naruto 5

━━━━━━━━━━━━━━━━━━━━

🛡️🌻 𝐆𝐑𝐎𝐔𝐏 𝐌𝐀𝐍𝐀𝐆𝐄𝐌𝐄𝐍𝐓
━━━━━━━━━━━━━━━━━━━━

🌹 /ban
➜ Reply to a user or use /ban <user_id>
➜ Ban and remove the user 🚫

🌹 /unban
➜ Reply to a user or use /unban <user_id>
➜ Remove ban status ✅

🌹 /remove
➜ Reply to a user to remove them 👢

🌹 /settings
➜ View group settings ⚙️

🌹 /settings <setting> <on/off>
➜ Enable or disable a setting 🔧

🌹 /out
➜ Make the bot leave the group 👋

━━━━━━━━━━━━━━━━━━━━

📡✨ 𝐓𝐄𝐋𝐄𝐆𝐑𝐀𝐌 𝐅𝐎𝐑𝐖𝐀𝐑𝐃𝐄𝐑
━━━━━━━━━━━━━━━━━━━━

🌼 /tgstatus
➜ Check Telegram forwarder status 📊

🌼 /tgstart
➜ Start Telegram ➜ Messenger forwarding ▶️

🌼 /tgstop
➜ Stop Telegram forwarding 🛑

🌼 /tgadd <tg_id> <messenger_thread_id>
➜ Forward one Telegram channel/group to one Messenger group 🔁

🌼 /tgadd <tg_id>
➜ Add source using default Messenger target

🌼 /tgremove <tg_id>
➜ Remove a Telegram source route ❌

🌼 /tgon <tg_id>
➜ Turn a saved Telegram route ON ✅

🌼 /tgoff <tg_id>
➜ Turn a saved Telegram route OFF without deleting it ⏸️

🌷 Example:
➜ /tgadd -1001234567890 1234567890

━━━━━━━━━━━━━━━━━━━━

⚙️🌻 𝐀𝐃𝐌𝐈𝐍 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒
━━━━━━━━━━━━━━━━━━━━

🌹 /info
➜ Reply to a user to see profile info 👤

🌹 /delet
➜ Reply to a bot message to unsend it 🧹

🌹 /see_req
➜ Show pending friend requests 📋

🌹 /maintain run
➜ Turn maintenance mode on 🔧

🌹 /maintain end
➜ Turn maintenance mode off ✅

🌹 /reload
➜ Reload commands/plugins without full restart 🔄

🌹 /stop
➜ Shut down the bot 🛑

━━━━━━━━━━━━━━━━━━━━

🌸💖 𝐀𝐍𝐔 𝐁𝐎𝐓 💖🌸
🌷 Smart • Friendly • Helpful 🌷

🌹 Made with ❤️ by
✨ Arafat Hoshen Zihad ✨

🌺 Have a wonderful day! 🌺
"""


async def handle_help(client, message):
    await client.send_message(HELP_TEXT, message.thread_id)
