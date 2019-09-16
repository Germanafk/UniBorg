from telethon import events
from uniborg.util import admin_cmd


async def tcoing(event):
    tcoin = event.get_entity("@counting123")
    @borg.on(events.NewMessage(chats=tcoin, incoming=True))
    async def _(event):
        m = int(event.raw_text) + 1
        event.client.send_message(
            tcoin.id,
            m,
            reply_to=event.message.id
        )

@borg.on(events.NewMessage(incoming=True))
async def test(event):
    tcoing(event)
