from fbchat_muqit import ParticipantsAdded


async def notify_admin_group_join(client, event: ParticipantsAdded, admin_ids):

    client_was_added = any(
        str(p.user_id) == str(client.uid)
        for p in event.added_participants
    )

    if not client_was_added:
        return

    thread_id = event.messageMetadata.thread_id

    # FIXED
    adder_id = event.messageMetadata.sender_id

    member_count = len(event.participants)

    try:

        users = await client.fetch_user_info(str(adder_id))

        adder = users.get(str(adder_id))

        adder_name = adder.name if adder else f"Unknown ({adder_id})"

    except Exception as e:

        print("FETCH ERROR:", e)

        adder_name = f"Unknown ({adder_id})"

    msg = (
        f"⚠️ Bot was added to a group!\n"
        f"👤 Added by: {adder_name}\n"
        f"🆔 Adder ID: {adder_id}\n"
        f"💬 Group Thread ID: {thread_id}\n"
        f"👥 Members: {member_count}"
    )

    for admin_id in admin_ids:

        try:
            await client.send_message(msg, admin_id)

        except Exception as e:
            print(f"Notify failed: {e}")