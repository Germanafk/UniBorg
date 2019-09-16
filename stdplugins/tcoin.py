from telethon import events
from uniborg.util import admin_cmd


@borg.on(events.NewMessage(incoming=True))
async def test(event):
    tcoin = await event.client.get_entity('@counting123')
    if tcoin.id == int(str(event.chat_id).replace("-100", "")):
        try:
            tcoin_int = int(event.raw_text)
            tcoin_message = tcoin_int + 1
            tcoin_id = int("-100" + str(tcoin.id))
            event.client.send_message(
                tcoin_id,
                tcoin_message,
            )
        except:
            return
    else:
        print("false alarm")
                
                
        
