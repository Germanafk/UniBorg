import random
import requests
from uniborg.util import admin_cmd

@borg.on(admin_cmd(pattern="quote ?(.*)"))
async def quote_search(event):
    if event.fwd_from:
        return
    await event.edit("Processing...")
    search_string = event.pattern_match.group(1)
    input_url = "https://bots.shrimadhavuk.me/Telegram/GoodReadsQuotesBot/?q={}".format(search_string)
    headers = {"USER-AGENT": "UniBorg"}
    response = requests.get(input_url, headers=headers).json()
    result = random.choice(response).get("input_message_content").get("message_text")
    if result:
        await event.edit(result.replace("<code>", "`").replace("</code>", "`"))
    else:
        await event.edit("Zero results found")
