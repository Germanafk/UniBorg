"""Upload local Files to gDrive
Syntax:
.ugdrive"""

# The entire code given below is verbatim copied from
# https://github.com/cyberboysumanjay/Gdrivedownloader/blob/master/gdrive_upload.py
# there might be some changes made to suit the needs for this repository
# Licensed under MIT License

import asyncio
import os
import time
import math
from datetime import datetime
from telethon import events
from uniborg.util import admin_cmd, progress
#
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from apiclient.errors import ResumableUploadError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from oauth2client import file, client, tools
from mimetypes import guess_type
import httplib2


# Path to token json file, it should be in same directory as script
G_DRIVE_TOKEN_FILE = Config.TMP_DOWNLOAD_DIRECTORY + "/auth_token.txt"
# Copy your credentials from the APIs Console
CLIENT_ID = Config.G_DRIVE_CLIENT_ID
CLIENT_SECRET = Config.G_DRIVE_CLIENT_SECRET
# Check https://developers.google.com/drive/scopes for all available scopes
OAUTH_SCOPE = "https://www.googleapis.com/auth/drive.file"
# Redirect URI for installed apps, can be left as is
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
parent_id = Config.GDRIVE_FOLDER_ID


@borg.on(admin_cmd(pattern="ugdrive ?(.*)", allow_sudo=True))
async def _(event):
    if event.fwd_from:
        return
    mone = await event.reply("Processing ...")
    if CLIENT_ID is None or CLIENT_SECRET is None:
        await mone.edit("This module requires credentials from https://da.gd/so63O. Aborting!")
        return
    if Config.PRIVATE_GROUP_BOT_API_ID is None:
        await event.edit("Please set the required environment variable `PRIVATE_GROUP_BOT_API_ID` for this plugin to work")
        return
    input_str = event.pattern_match.group(1)
    if not os.path.isdir(Config.TMP_DOWNLOAD_DIRECTORY):
        os.makedirs(Config.TMP_DOWNLOAD_DIRECTORY)
    required_file_name = None
    start = datetime.now()
    if event.reply_to_msg_id and not input_str:
        reply_message = await event.get_reply_message()
        try:
            c_time = time.time()
            downloaded_file_name = await borg.download_media(
                reply_message,
                Config.TMP_DOWNLOAD_DIRECTORY,
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(d, t, mone, c_time, "trying to download")
                )
            )
        except Exception as e:  # pylint:disable=C0103,W0703
            await mone.edit(str(e))
            return False
        else:
            end = datetime.now()
            ms = (end - start).seconds
            required_file_name = downloaded_file_name
            await mone.edit("Downloaded to `{}` in {} seconds.".format(downloaded_file_name, ms))
    elif input_str:
        input_str = input_str.strip()
        if os.path.exists(input_str):
            end = datetime.now()
            ms = (end - start).seconds
            required_file_name = input_str
            await mone.edit("Found `{}` in {} seconds.".format(input_str, ms))
        else:
            await mone.edit("File Not found in local server. Give me a file path :((")
            return False
    # logger.info(required_file_name)
    if required_file_name:
        #
        if Config.G_DRIVE_AUTH_TOKEN_DATA is not None:
            with open(G_DRIVE_TOKEN_FILE, "w") as t_file:
                t_file.write(Config.G_DRIVE_AUTH_TOKEN_DATA)
        # Check if token file exists, if not create it by requesting authorization code
        if not os.path.isfile(G_DRIVE_TOKEN_FILE):
            storage = await create_token_file(G_DRIVE_TOKEN_FILE, event)
            http = authorize(G_DRIVE_TOKEN_FILE, storage)
        # Authorize, get file parameters, upload file and print out result URL for download
        http = authorize(G_DRIVE_TOKEN_FILE, None)
        file_name, mime_type = file_ops(required_file_name)
        # required_file_name will have the full path
        # Sometimes API fails to retrieve starting URI, we wrap it.
        try:
            g_drive_link = upload_file(http, required_file_name, file_name, mime_type)
            await mone.edit(f"Here is your Google Drive link: {g_drive_link}")
        except Exception as e:
            await mone.edit(f"Exception occurred while uploading to gDrive {e}")
    else:
        await mone.edit("File Not found in local server. Give me a file path :((")


@borg.on(admin_cmd(pattern="drivesch ?(.*)", allow_sudo=True))
async def sch(event):
    if event.fwd_from:
        return
    if CLIENT_ID is None or CLIENT_SECRET is None:
        await mone.edit("This module requires credentials from https://da.gd/so63O. Aborting!")
        return False    
    try:
        with open(G_DRIVE_TOKEN_FILE) as f:
            pass
    except IOError:
        storage = await create_token_file(G_DRIVE_TOKEN_FILE, event)
        http = authorize(G_DRIVE_TOKEN_FILE, storage)
        # Authorize, get file parameters, upload file and print out result URL for download
    http = authorize(G_DRIVE_TOKEN_FILE, None)    
    input_str = event.pattern_match.group(1).strip()
    await event.edit("Searching for {} in G-Drive.".format(input_str))
    query = "'{}' in parents and (title contains '{}')".format(parent_id,input_str)#search_query(parent_id,input_str)
    msg = await gsearch(http,query,input_str)
    await event.edit(str(msg))


async def gsearch(http,query,filename):
    drive_service = build("drive", "v2", http=http)
    page_token = None
    msg = "**G-Drive Search Query**\n`"+filename+"`\n**Results**\n"
    while True:
        response = drive_service.files().list(q=query,
                                          spaces='drive',
                                          fields='nextPageToken, items(id, title, mimeType)',
                                          pageToken=page_token).execute()
        for file in response.get('items',[]):
            if file.get('mimeType') == "application/vnd.google-apps.folder":
                msg +="⁍ [{}](https://drive.google.com/drive/folders/{}) (folder)".format(file.get('title'),file.get('id'))+"\n"
            # Process change
            else:
                msg += "⁍ [{}](https://drive.google.com/uc?id={}&export=download)".format(file.get('title'),file.get('id'))+"\n"
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return msg        






@borg.on(admin_cmd(pattern="gdrivedir ?(.*)", allow_sudo=True))
async def _(event):
    if event.fwd_from:
        return
    try:
        with open(G_DRIVE_TOKEN_FILE) as f:
            pass
    except IOError:
        storage = await create_token_file(G_DRIVE_TOKEN_FILE, event)
        http = authorize(G_DRIVE_TOKEN_FILE, storage)
        # Authorize, get file parameters, upload file and print out result URL for download
    http = authorize(G_DRIVE_TOKEN_FILE, None)    
    input_str = event.pattern_match.group(1).strip()
    if os.path.exists(input_str):
        await event.edit("`Directory Found. Started Upload..Please Wait`")
        folder_link,new_folder_id = create_folder(http=http,folder_name=input_str.replace("."," "),parent_folder_id=parent_id)
        up_files = walk_fs(input_str)
        await event.edit("`Uploading {} Files To G-Drive.`".format(len(up_files)))
        for file in walk_fs(input_str):
            file_name,mime_type =file_ops(file)
            await upload_file(http,file,file_name,mime_type,event,new_folder_id)
        await event.edit("__Successfully Uploaded Folder To G-Drive:__\n⁍ [{}]({}) ".format(input_str,folder_link))   
    else:
        await event.edit("`404 : Folder Not Found !!`")
        return



def walk_fs(folder_path):
    file_paths = []
    for root, dirs, files in os.walk(folder_path):
        for name in files:
            file_paths.append(os.path.join(root, name))
    return file_paths        


def create_folder(http, folder_name, parent_folder_id):
    """ 
        Create folder on Google Drive
    """
    drive_service = build("drive", "v2", http=http)
    permissions = {
        "role": "reader",
        "type": "anyone",
        "value": None,
        "withLink": True
    }
    file_metadata = {
    'title': folder_name,
    'mimeType': 'application/vnd.google-apps.folder',
    }
    if parent_id:
        file_metadata[ 'parents' ] = [{'id': parent_id}]
    file = drive_service.files().insert(body=file_metadata).execute()
    drive_service.permissions().insert(fileId=file["id"], body=permissions).execute()
    print("Created Gdrive Folder:\nName: {}\nID: {} ".format(file.get('title'),file.get('id')))
    folder_link = "https://drive.google.com/folderview?id={}".format(file.get('id'))
    return folder_link,file.get('id')

# Get mime type and name of given file
def file_ops(file_path):
    mime_type = guess_type(file_path)[0]
    mime_type = mime_type if mime_type else "text/plain"
    file_name = file_path.split("/")[-1]
    return file_name, mime_type


async def create_token_file(token_file, event):
    # Run through the OAuth flow and retrieve credentials
    flow = OAuth2WebServerFlow(
        CLIENT_ID,
        CLIENT_SECRET,
        OAUTH_SCOPE,
        redirect_uri=REDIRECT_URI
    )
    authorize_url = flow.step1_get_authorize_url()
    async with event.client.conversation(Config.PRIVATE_GROUP_BOT_API_ID) as conv:
        await conv.send_message(f"Go to the following link in your browser: {authorize_url} and reply the code")
        response = conv.wait_event(events.NewMessage(
            outgoing=True,
            chats=Config.PRIVATE_GROUP_BOT_API_ID
        ))
        response = await response
        code = response.message.message.strip()
        credentials = flow.step2_exchange(code)
        storage = Storage(token_file)
        storage.put(credentials)
        return storage


def authorize(token_file, storage):
    # Get credentials
    if storage is None:
        storage = Storage(token_file)
    credentials = storage.get()
    # Create an httplib2.Http object and authorize it with our credentials
    http = httplib2.Http()
    credentials.refresh(http)
    http = credentials.authorize(http)
    return http


async def upload_file(http, file_path, file_name, mime_type, event, parent_id):
    # Create Google Drive service instance
    drive_service = build("drive", "v2", http=http, cache_discovery=False)
    # File body description
    media_body = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    body = {
        "title": file_name,
        "description": "Uploaded using @UniBorg gDrive v2",
        "mimeType": mime_type,
    }
    if parent_id is not None:
        body["parents"] = [{"id": parent_id}]
    # Permissions body description: anyone who has link can upload
    # Other permissions can be found at https://developers.google.com/drive/v2/reference/permissions
    permissions = {
        "role": "reader",
        "type": "anyone",
        "value": None,
        "withLink": True
    }
    # Insert a file
    file = drive_service.files().insert(body=body, media_body=media_body)
    response = None
    display_message = ""
    while response is None:
        status, response = file.next_chunk()  #Credits: https://github.com/AvinashReddy3108/PaperplaneExtended/commit/df65da55d16a6563aa9023cac2bedf43248379f5
        await asyncio.sleep(1)
        if status:
            percentage = int(status.progress() * 100)
            progress_str = "[{0}{1}]\nProgress: {2}%\n".format(
                "".join(["█" for i in range(math.floor(percentage / 5))]),
                "".join(["░" for i in range(20 - math.floor(percentage / 5))]),
                round(percentage, 2)
            )
            current_message = f"Uploading to G-Drive\nFile Name: `{file_name}`\n{progress_str}"
            if display_message != current_message:
                try:
                    await event.edit(current_message)
                    display_message = current_message
                except Exception as e:
                    logger.info(str(e))
                    pass
    file_id = response.get("id")
    # Insert new permissions
    drive_service.permissions().insert(fileId=file_id, body=permissions).execute()
    # Define file instance and get url for download
    file = drive_service.files().get(fileId=file_id).execute()
    download_url = file.get("webContentLink")
    return download_url


@borg.on(admin_cmd(pattern="gfolder ?(.*)", allow_sudo=True))
async def _(event):
    if event.fwd_from:
        return
    folder_link = "https://drive.google.com/folderview?id="+parent_id    
    await event.edit("`Here is Your G-Drive Folder link : `\n"+folder_link)    
