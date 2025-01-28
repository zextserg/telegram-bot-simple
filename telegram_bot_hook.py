import telebot
from telebot import types
from datetime import datetime
from fastapi import FastAPI
# from fastapi_cache import caches
# from fastapi_cache.backends.memory import InMemoryCacheBackend, CACHE_KEY
from socket  import error as SocketError
import errno
import logging
import sys
import uvicorn
import uuid
from apiclient import discovery
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseUpload
import io
import base64
import os

# ------------------------------------------ Initial setup and Instructions ----------------------------------------------------------
# First of all - in GooglrCloudPlatform (GCP) create ServiceAccount and generate ServiceAccountKey (JSON)
# Download this JSON from GCP and here set a path to that file
SECRET_KEY = os.path.join('./', 'service_acc_token_key.json')

# Next you should create 3 things and share access to these things to service_accout email (email is inside service account JSON token): 
# - create folder in your GoogleDrive and Enable DriveAPI in GCP
# - create Google Sheet Table and Enable SheetAPI in GCP
# - create Google Form and Enable FormsAPI in GCP
# After creating all 3 things and sharing access - you can set const variables for each in this code below:

# in this directory will be saved all files (photos, audio etc.) that user send to the bot
# Don't forget to Share Full Access in this GoogleDrive Folder to service_accout email (email is inside service account JSON token)
GDRIVE_PARENT_DIR = '123abc' # put here your actual values

# in this table script will write all logs for all users interactions with bot
SHEET_LOG_ID = '123abc' # put here your actual values
SHEET_LOG_SHEET_NAME = 'bot_auto_log' # put here your actual values

# bot will ask user to fill out this form and later check by Telegram username if user really filled it
# so you need to create 1 required field in this Form - "Telegram username" field
# and here you should set key_id for this excat field in your Form as GFORM_USERNAME_KEY (key_id you can check by GoogleFormsAPI)
# Don't forget to Share Full Access in your GoogleForm to service_accout email (email is inside service account JSON token)
GFORM_ID = '123abc' # put here your actual values
GFORM_URL = 'https://forms.gle/123abc' # put here your actual values
GFORM_USERNAME_KEY = '123abc' # put here your actual values

# If you create all 3 things, share access to them and set correct values above - next code for making CREDS should works fine
# If you forget something - here you can see an Error with link to Enabling API on GCP or with message of incorrect access
SCOPES = ["https://www.googleapis.com/auth/forms.responses.readonly", 
          'https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/spreadsheets']
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"

CREDS = Credentials.from_service_account_file(SECRET_KEY, scopes=SCOPES)

# Next you should create bot in Telegram - ask BotFather for that. 
# After creting - set your actual name and Telegram token for that bot (values from BotFather)
TELEGRAM_BOT = {
    'name': 'bot-name', # put here your actual values
    'token': '123:123abc' # put here your actual values
}

# Next you should find a server where this bot will be up and run
# This server should have an External static IP address and should be available from internet on port 443 or 8443.
# You can buy or rent server somewhere for this purpose, but it can not be just your laptop with localhost.
# I prefer to create a VM instance on GCP with External sctatip IP. Instruction how to do it (in russian) can be found here - https://habr.com/ru/companies/ods/articles/462141/
# Anyway - you need a working IP with port 443 or 8443. Set these values here:
WEBHOOK_HOST = 'XXX.XXX.XXX.XXX' # put here your actual values
WEBHOOK_PORT = 443  # 443, 8443 put here your actual values
WEBHOOK_LISTEN = '0.0.0.0'

# Next you should create ssl certificate for your IP.
# You can do it from any terminal after making your IP available.
# Here is a command for creating ssl certificate and example how to respond to terminal prompts
# (when prompt asks "Common Name (e.g. server FQDN or YOUR name)" - insert your actual IP numbers): 
# - Command:
# openssl req -newkey rsa:2048 -sha256 -nodes -keyout url_private.key -x509 -days 3560 -out url_cert.pem
# - Example prompt:
# Country Name (2 letter code) [AU]:GB
# State or Province Name (full name) [Some-State]:London
# Locality Name (eg, city) []:London
# Organization Name (eg, company) [Internet Widgits Pty Ltd]:TEST
# Organizational Unit Name (eg, section) []:director
# Common Name (e.g. server FQDN or YOUR name) []:XXX.XXX.XXX.XXX
# Email Address []:test@test.com

# After that prompt you should get 2 files for ssl certificate: .pem and .key. 
# Save them somewhere and put them in repository and set names of files below:
WEBHOOK_SSL_CERT = 'url_cert.pem'  # put here your actual values - Path to the ssl certificate
WEBHOOK_SSL_PRIV = 'url_private.key'  # put here your actual values - Path to the ssl private key

# Next you should setup your webhook in Telegram. 
# For that you should run next command from folder with your ssl certificate files.
# And of course replace XXX with your actual IP values and YOUR-TOKEN with your Telegram token (word "bot" just before it - leave as is)
# - Command:
# curl -F "url=https://XXX.XXX.XXX.XXX:443" -F "certificate=@url_cert.pem" https://api.telegram.org/botYOUR-TOKEN/setWebhook

# After that in terminal you should receive response from Telegram like:
# "{"ok":true,"result": ...}"

# So now setup final Webhook url 
WEBHOOK_URL = f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}/{TELEGRAM_BOT['token']}/"

# Next you should set your actual values for your Wallet (in text and picture formats):
WALLET_STR = '123' # put here your actual values
WALLET_PIC = 'wallet.png' # put here your actual values

# Last preparing thing - set your chat_id as ADMIN chat, but for that you may need a first interaction with this bot.
# So just start this script first, find it in Telegram, start conversation with message "/start" to the bot.
# And then - you can find your chat_id in GoogleSheet log table.
# Then replace value for ADMIN chat with your actual value:
ADMIN_CHAT = '123' # put here your actual values

# So now - you're ready to move this script to your server and RUn it!
# Of course you should install all libs from requirements.txt in the envirenment on your server and then RUN this script.
# You should be able to RUN it with just command:
# "python telegram_bot_hook.py" 
# or if you want to run it at background to be able to close terminal after: 
# "nohup python telegram_bot_hook.py &" 
# But sometimes Google can prevent run commands like these without sudo and gives Errors about permissions. So you can try: 
# "sudo python telegram_bot_hook.py" or "sudo env "PATH=$PATH" python telegram_bot_hook.py"
# Now you set up all needed values and below is just code which should work without any additional settings!
# ------------------------------------------------------------------------------------------------------------------------

# Logging to STDOUT section
# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# create console handler and set level to debug
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)

# create logger
logger = logging.getLogger(f'{TELEGRAM_BOT["name"]}_logger')
logger.setLevel('INFO')

# add handlers to logger
logger.addHandler(stdout_handler)

SERVICE_NAME_FOR_LOGS = 'bot_service'

# Creating telebot and FastAPI instannces section
bot = telebot.TeleBot(TELEGRAM_BOT['token'])
app = FastAPI()
FASTAPI_PORT = 443

# Configuring possible formats
PHOTO_TYPES = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff', '.raw', '.svg']
VIDEO_TYPES = ['.mov', '.mpeg', '.mpg', '.mp4', '.wmv', '.mkv', '.avi']
AUDIO_TYPES = ['.mp3', '.aac', '.flac', '.ogg', '.wma', '.wav', '.amr']

# Configuring messages and buttons texts
WRONG_TYPE_MSG = 'Unfortunately, we can not get this type of message'
ERR_MSG = f'something goes wrong, you have to go back and start again!'

GREETING_MSG = "*Hello! It's Greeting message!*"
BTN_HOME = {'txt': 'Home', 'next_node': '1'}

MSG_1 = '''It's our very first message #1! Want to know about our service? Just click next button!'''
BTN_1 = {'txt': 'Btn1 About Our Service', 'next_node': '2'}

MSG_2 = '''It's a message #2 Our service - is the best service!
Want to hear about our benefits?'''
BTN_2 = {'txt': 'Btn2 About Our Benefits', 'next_node': '3'}

MSG_3 = '''It's a message #3 Our Benefits are incredible!
Well, now you may want to know about Support?'''
BTN_3 = {'txt': 'Btn3 About Our Support', 'next_node': '4'}

MSG_4 = '''It's a message #4 Support - is our care!
Can we tell you about Our people?'''
BTN_4 = {'txt': 'Btn4 About Our Support', 'next_node': '5'}

MSG_5 = '''It's a message #5 Glad you ask! Our people are beatiful!
Want to know about our goals?'''
BTN_5 = {'txt': 'Btn5 About Our Goals', 'next_node': '6'}

MSG_6 = ''''It's a message #6 Our goals - be the best of the best!
Should we decsribe you our products?'''
BTN_6 = {'txt': 'Btn6 About Our Products', 'next_node': '7'}

MSG_7 = '''It's a message #7 Good question! Our products move Earth spinning!
Want to know more reviews?'''
BTN_7 = {'txt': 'Btn7 About Our Reviews', 'next_node': '8'}

MSG_8 = '''It's a message #8 Reviews tell that we are the power, for sure!
You can ask about our vision if you want!'''
BTN_8 = {'txt': 'Btn8 About Our Vision', 'next_node': '9'}

MSG_9 = '''It's a message #9 Our vision - just like marvel!
If you're ready to join us - click next button and we will give you a link to applying form!'''
BTN_9 = {'txt': "Btn9 I'm ready to join!", 'next_node': '10'}

# Here you can put a link to your google form.
# Here you can tell user that after filling out form he can return back to bot and continue!
# Here you should ask user to fill out his Telegram username, becase we will match it with actual username by the bot, later in code!
# If you want to make this message more persdonolised - you can leave the key word here and 
# below (in line 284 of code) you can replace key with username. 
# For example you can write:
# "He, username mr_xxx, fill this form for me, please and don't forget to fill out your TG username - mr_xxx!"
# Now look below and find replacing "mr_xxx" in this code:
MSG_10 = f'''It's a message #10. Happy that you want join us! 
First of all fill this form for me -  {GFORM_URL}, and please don't forget to fill your TG username - mr_xxx!
After filling form - return to me and click next Button "I fiiled out the form"'''
BTN_10_filled_form = {'txt': 'Btn10 - I fiiled out the form!', 'next_node': '11'}
MSG_TO_ADMIN_ABOUT_FORM = 'user: mr_xxx (id=id_xxx) filled form!'
# After click that Btn10 - bot will send message to ADMIN: "user: {user_id} filled form!". 

MSG_11 = '''It's a message #11 Checking your filled form...'''
# After user said that he filled the form - bot will check it by Telegram username and if't really done - send next message:
# Here you can tell user to send pictures to the bot and then click to the button "I sent photo!"
MSG_11_1 = '''It's a message #11-1. We found your filled form! 
Now please send me your photo! And after that - click to the button "I sent photo!"'''
MSG_11_2 = '''We don't found your filled form :( Make sure that you correctly fill out you TG username - for you it's: mr_xxx"'''
BTN_11_sent_photo = {'txt': 'Btn11 - I sent photo!', 'next_node': '12'}
MSG_TO_ADMIN_ABOUT_PHOTO = 'user: mr_xxx (id=id_xxx) sended photos!'
# After click that Btn11 - bot will send message to ADMIN: "user: {user_id} sended photo!". 
# And Photo from user will appear in your GoogleDrive directory with name starts with user_id.

MSG_12 = '''It's a message #12 Checking your sended photo...'''
MSG_12_1 = '''It's a message #12-1 After successfully checked photo - wait, we will send you info for payment...'''
MSG_12_2 = '''We don't found any photo :( Send me photo one more time in this chat, just like regular photo and then again click on Button "I sent photo!"'''

# While user reads message about successfully checked photos - admin should check new photo on GoogleDrive
# Then ADMIN can check it and decide which sum should be sended to this user.
# Then ADMIN should send command to bot with the sum that should be sended to that user by bot.
# ADMIN should send to the bot message in format: send-from-admin-to-user-payment-info {user_id} <sum of money>
# For example ADMIN can send command as a message to the bot like this: "send-from-admin-to-user-payment-info {123} <150>"
# Then bot will ask ADMIN to Confirm it with button by message:
# "We will send to that user: 123 the sum = 150 and that wallet for payment: 123. Confirm by button:"
MSG_TO_ADMIN_ABOUT_SENDING_PAYINFO_BEFORE_CONFIRM = f'We will send to that user: user_id=id_xxx the sum = coins_xxx and that wallet for payment: {WALLET_STR}. Confirm by button:'
BTN_12_admin_confirm =  {'txt': 'ADMIN Btn#12 Confirm Sending ToPayInfo', 'next_node': '13'}
MSG_TO_ADMIN_ABOUT_SENT_PAYINFO_TO_USER = 'we sended user: mr_xxx (id=id_xxx) msg about payment!'
# After ADMIN approval bot will send ADMIN message that he send user nedded info: 
# "we sended user: 123 msg about payment!""

# Here you can tell user credentials about service for paying. 
# Leave some key word, like "coins_xxx" in the message - so that later in code it can be replaced with sum from ADMIN. 
# And next bot will send user your picture from repository (it can be QR code or something else).
# And here you can tell user that after his payment he can click on button "I paid!" and continue.
MSG_13 = f'''It's a message #13. Good work! Here is picture of our wallet and his numer - {WALLET_STR}.
If you want to use our service please pay coins_xxx money!
After that click next button - "I paid!"'''
BTN_13_paid = {'txt': 'Btn13 - I paid!', 'next_node': '14'}
MSG_TO_ADMIN_ABOUT_PAY = 'user: mr_xxx (id=id_xxx) paid money! Check it and send him new steps.'
# After user said that he paid - bot will send to ADMIN messgae about it like: 
# "user username paid money! Check it and send him new steps."

MSG_14 = '''It's a message #14 After successfull payment. You are great! 
Here is next steps - you can finish our discussion by clicking Finish Button!'''
BTN_14_finish = {'txt': 'Btn14 - Finish', 'next_node': '15'}

MSG_15 = '''It's a message #15 - Finish message - see you soon!'''

# Also ADMIN can send some text messgae to user using special command - "send-from-admin-to-user-text"
# Inside message you should avoid special characters like #,/,{,},<,>, etc. 
# ADMIN should send to bot a message in format: "send-from-admin-to-user-text {user_id} <text>"
# For example: "send-from-admin-to-user-text {123} <Hi user! It's admin and I write to you directly using my bot!>"

# Configuring nodes of conversation schema
HOME_NODE = '1'
BEFORE_FILL_FORM_NODE = '10'
I_FILLED_FORM_NODE = '11'
I_SEND_PHOTO_NODE = '12'
I_PAID_NODE = '14'
SEND_USER_PAY_NODE = '13'

TREE = {
    '1': {'btn_to_this': BTN_HOME, 'msg': MSG_1, 'btns': [BTN_1]},
    '2': {'btn_to_this': BTN_1, 'msg': MSG_2, 'btns': [BTN_2]},
    '3': {'btn_to_this': BTN_2, 'msg': MSG_3, 'btns': [BTN_3]},
    '4': {'btn_to_this': BTN_3, 'msg': MSG_4, 'btns': [BTN_4]},
    '5': {'btn_to_this': BTN_4, 'msg': MSG_5, 'btns': [BTN_5]},
    '6': {'btn_to_this': BTN_5, 'msg': MSG_6, 'btns': [BTN_6]},
    '7': {'btn_to_this': BTN_6, 'msg': MSG_7, 'btns': [BTN_7]},
    '8': {'btn_to_this': BTN_7, 'msg': MSG_8, 'btns': [BTN_8]},
    '9': {'btn_to_this': BTN_8, 'msg': MSG_9, 'btns': [BTN_9]},
    '10': {'btn_to_this': BTN_9, 'msg': MSG_10, 'btns': [BTN_10_filled_form]},
    '11': {'btn_to_this': BTN_10_filled_form, 'msg': MSG_11, 'btns': [BTN_11_sent_photo]},
    '12': {'btn_to_this': BTN_11_sent_photo, 'msg': MSG_12, 'btns': []},
    '13': {'btn_to_this': BTN_12_admin_confirm, 'msg': MSG_13, 'btns': [BTN_13_paid]},
    '14': {'btn_to_this': BTN_13_paid, 'msg': MSG_14, 'btns': [BTN_14_finish]},
    '15': {'btn_to_this': BTN_14_finish, 'msg': MSG_15, 'btns': []},
}

# Configuring which buttons should be catched when pressed and which buttons should be at Menu at bottom keyboard
BTNS_TXTS = {key: val for key,val  in [(TREE[key]['btn_to_this']['txt'],key) for key in TREE]}
BNTS_MENU = [BTN_HOME, BTN_1, BTN_2, BTN_3, BTN_4, BTN_5, BTN_6, BTN_7, BTN_8, BTN_9]

# Func to make inline keyboard button by the current node
def make_keyboard(msg_session, node, payment=''):
    markup = None
    try:
        markup = types.InlineKeyboardMarkup()
        if payment:
            markup.add(types.InlineKeyboardButton(text=BTN_12_admin_confirm['txt'],
                                                  callback_data=f'pay={payment}'))
        else:
            buttons_dicts = TREE[node]['btns']
            for button in buttons_dicts:
                markup.add(types.InlineKeyboardButton(text=button.get('txt'),
                                                    callback_data=f'command={button.get("next_node")}')
                        )
            if node != HOME_NODE: # Here we add a HOME button to every message from bot, except first message (node 1)
                markup.add(types.InlineKeyboardButton(text='HOME',
                                                    callback_data=f'command=1')
                            )
    except Exception as e:
        err_msg = Exception(f'Session {msg_session}: TOTAL ERROR in make_keyboard: {e}')
        logger.info(err_msg)

    return markup

# Func to make a message by the current node
def make_message(msg_session, node):
    msg_res = None
    try:
        msg_res = TREE[node]['msg']
    except Exception as e:
        err_msg = Exception(f'Session {msg_session}: TOTAL ERROR in make_message: {e}')
        logger.info(err_msg)

    return msg_res

# Func for inserting log data to Google Sheet. 
# Don't forget to Share Full Access in your GoogleSheet Table to service_accout email (email is inside service account JSON token)
def inserting_to_sheet(msg_session, user_name, user_id, msg, err=False):
    res = None
    try:
        service = discovery.build('sheets', 'v4', credentials=CREDS, cache_discovery=False)
        sheet = service.spreadsheets()

        values = [[
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            msg_session,
            user_name,
            user_id,
            str(msg),
        ]]
        if err:
            values[0].append('error')
        
        body = {
             'values': values
        }
        res = sheet.values().append(spreadsheetId=SHEET_LOG_ID, range=f"'{SHEET_LOG_SHEET_NAME}'",
                                        valueInputOption='RAW', body=body).execute()
    except Exception as e:
        err_msg = Exception(f'Session {msg_session}: ERROR in inserting_to_sheet: {e}')
        logger.info(err_msg)

    return res


# Process webhook calls - to interaction with Telegram requests
@app.get(f'/')
def index():
    return {'status': f'{TELEGRAM_BOT["name"]} start page'}


# Process webhook calls - to interaction with Telegram requests
@app.post(f"/{TELEGRAM_BOT['token']}/")
def process_webhook(update: dict):
    if update:
        update = telebot.types.Update.de_json(update)
        bot.process_new_updates([update])
    else:
        return

# Main func for bot working 
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    counter = 0
    msg_session = f'{TELEGRAM_BOT["name"]}_{str(datetime.now().isoformat())[:22]}_{str(uuid.uuid4().hex)[:10]}'
    good_request = False
    user_name = str(call.message.chat.username).lower() if call.message.chat.username and str(call.message.chat.username).lower != 'none' \
                                                        else f'user_{str(call.message.chat.id).lower()}'
    user_id = str(call.message.chat.id)
    try:
        while counter < 5 and not good_request: # if there is some troubles or network errors - we make 5 tries to deal with it
            try:
                if call.data.startswith("command="):
                    command_node = call.data.replace('command=', '')

                    if command_node not in TREE.keys():
                        command_node = HOME_NODE
                        bad_txt = ERR_MSG
                        bot.answer_callback_query(callback_query_id=call.id, show_alert=True,
                                                  text=bad_txt)
                        good_request = True
                        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'command_node not in TREE.keys()! {bad_txt}', err=True)
                elif call.data.startswith("pay="): # Here we catch ADMIN push Confirm Button for sending user message with payment info with exact sum
                    pay_command = call.data.replace('pay=', '')
                    pay_user_id = pay_command[:pay_command.find(':')]
                    pay_sum = pay_command[pay_command.find(':')+1:]
                    adm_txt = f'admin push button: SEND USER PAY for user: {pay_user_id} with sum: {pay_sum} and wallet: {WALLET_STR}'
                    inserting_to_sheet(msg_session=msg_session, user_name=SERVICE_NAME_FOR_LOGS, user_id=SERVICE_NAME_FOR_LOGS, msg=adm_txt)
                    command_node = SEND_USER_PAY_NODE
                else:
                    command_node = HOME_NODE
                    bad_txt = ERR_MSG
                    bot.answer_callback_query(callback_query_id=call.id, show_alert=True,
                                              text=bad_txt)
                    good_request = True
                    inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'call.data.startswith("command=") == False! {bad_txt}', err=True)
                
                message_item = make_message(msg_session=msg_session, node=command_node)

                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'user push button: {TREE[command_node]["btn_to_this"]["txt"]}')
                if command_node == BEFORE_FILL_FORM_NODE:
                    message_item = message_item.replace('mr_xxx', f'{user_name}!')
                elif command_node == I_FILLED_FORM_NODE: # Here bot check if user_name really filled a GoogleForm by requesting it by API
                    form_service = discovery.build('forms', 'v1', credentials=CREDS, 
                                                discoveryServiceUrl=DISCOVERY_DOC, static_discovery=False)

                    get_result = form_service.forms().responses().list(formId=GFORM_ID).execute()
                    resp_list = get_result['responses']
                    resps = []

                    for item  in resp_list: # Here bot parse all answers and find all usernames by GFORM_USERNAME_KEY
                        resps.append({'id': item['responseId'], 
                            'user_name': item['answers'][GFORM_USERNAME_KEY]['textAnswers']['answers'][0]['value'].replace('@','').lower(),
                            })
                    cur = None
                    for u in resps:
                        if user_name == u['user_name']: # Here bot try to find this exact current user_name in all answers usernames
                            cur = u
                    if cur:
                        message_item = f'{message_item} {MSG_11_1}'
                        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'we found filled form and will try to send msg about it to user: {cur["user_name"]}!')
                        adm_msg = MSG_TO_ADMIN_ABOUT_FORM.replace('mr_xxx', user_name).replace('id_xxx', str(user_id))
                        bot.send_message(chat_id=ADMIN_CHAT,
                                    text=adm_msg,
                                    disable_web_page_preview=True)
                        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'we sended info that user: {user_name} (id={user_id}) filled form to ADMIN!')
                    else:
                        message_item = f"{message_item} {MSG_11_2.replace('mr_xxx', user_name)}"
                        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'we DONT found filled form and will try to send msg about it to user!')
                elif command_node == I_SEND_PHOTO_NODE: # Here bot check if user really send photo and it appears inn your GoogleDrive Folder
                    service = discovery.build('drive', 'v3', credentials=CREDS)
                    drive_files = service.files().list(pageSize=1000, fields="nextPageToken, files(id, name)").execute()
                    found_photo = False
                    for item in drive_files['files']:
                        if user_name in item['name']: # for every file in folder bot looks if filename contains user_name
                            found_photo = True
                    if found_photo:
                        message_item = f'{message_item} {MSG_12_1}'
                        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'we found sended photos and will try to send msg about it to user!')
                        bot.send_message(chat_id=ADMIN_CHAT,
                                    text=MSG_TO_ADMIN_ABOUT_PHOTO.replace('mr_xxx', user_name).replace('id_xxx', str(user_id)),
                                    disable_web_page_preview=True)
                        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'we sended info that user: {user_name} sended photos to ADMIN!')
                    else:
                        message_item = f'{message_item} '
                        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'we DONT found sended photos and will try to send msg about it to user!')
                elif command_node == I_PAID_NODE: # Here we catch that user click button "I paid" and send msg about it to ADMIN
                    adm_msg = MSG_TO_ADMIN_ABOUT_PAY.replace('mr_xxx', user_name).replace('id_xxx', str(user_id))
                    bot.send_message(chat_id=ADMIN_CHAT,
                                text=adm_msg,
                                disable_web_page_preview=True)
                    inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'we sended info that user: {user_name} (id={user_id}) paid money to ADMIN!')
                elif command_node == SEND_USER_PAY_NODE: # Here bot send user message about Payment Info and also send picture
                    message_item = f'{make_message(msg_session=msg_session, node=command_node)}'.replace("coins_xxx", f"{pay_sum}")
                    user_id = pay_user_id
                    with open(WALLET_PIC, "rb") as f:
                        wallet_encoded = base64.b64encode(f.read())
                    wallet_pic = io.BytesIO(base64.decodebytes(wallet_encoded))
                    bot.send_photo(chat_id=user_id, photo=wallet_pic)

                markup = make_keyboard(msg_session=msg_session, node=command_node)

                bot.send_message(chat_id=user_id,
                                    text=message_item,
                                    reply_markup=markup,
                                    disable_web_page_preview=True)
                good_request = True
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'we sended this msg to user: {message_item}!')
                if command_node == SEND_USER_PAY_NODE:
                    bot.send_message(chat_id=ADMIN_CHAT,
                                    text=MSG_TO_ADMIN_ABOUT_SENT_PAYINFO_TO_USER.replace('mr_xxx', user_name).replace('id_xxx', str(user_id)),
                                    disable_web_page_preview=True)
            except SocketError as se:
                bad_txt = f'Session {msg_session}: ERROR in callback_query_handler: catch socket error! errno={se.errno}, test_no={errno.ECONNRESET}. On counter={counter}'
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=bad_txt, err=True)
                logger.info(bad_txt)
                counter += 1
            except Exception as e:
                counter += 1
                bad_txt = f'Session {msg_session}: ERROR in callback_query_handler: {e}. On counter={counter}'
                logger.info(bad_txt)
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=bad_txt, err=True)
        
        if not good_request:
            raise Exception(f'Session {msg_session}: can\'t send msg in callback_query_handler to user: {user_id}.')
    except Exception as  e:
        err_msg = Exception(f'Session {msg_session}: ERROR in callback_query_handler: {e}')
        logger.info(err_msg)
        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=err_msg, err=True)

# Func to catch when user send some files to the bot (photos, audio, pdf etc.)
@bot.message_handler(content_types=['photo', 'document', 'audio', 'video', 'voice'])
def handle_content(message):
    counter = 0
    good_request = False
    msg_session = f'{TELEGRAM_BOT["name"]}_{str(datetime.now().isoformat())[:22]}_{str(uuid.uuid4().hex)[:10]}'
    logger.info(f'Session {msg_session}: START handle_content')
    try:
        while counter < 3 and not good_request:
            logger.info(f'Session {msg_session}: IN handle_content: Try counter={counter}')
            # we want to make sure user has user_name - we will use it for naming file when upload it to our GoogleDrive
            # if user don't have user_name (it's possible in Telegram) - we take his user_id (chat_id) and generate user_name with it
            user_name = str(message.chat.username).lower() if message.chat.username and str(message.chat.username).lower != 'none' \
                                                           else f'user_{str(message.chat.id).lower()}'
            user_id = str(message.chat.id)
            inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg='trying to send something')
            try:
                external_id = f"{user_name}_{user_id}"
                if message.content_type == 'photo':
                    file_id = getattr(message, message.content_type)[-1].file_id
                else:
                    file_id = getattr(message, message.content_type).file_id
                file_info = bot.get_file(file_id)
                file_name_full = str(file_info.file_path)
                file_name = file_name_full[file_name_full.find('/')+1:]
                # final filename will be user_name + user_id + first 10 symbols of actual file + last 10 symbols of actual file
                file_name_str = f'{external_id}_{str(file_id)[:10]}_{str(file_id)[-10:]}_{file_name}'
                downloaded_file = bot.download_file(file_info.file_path)

                service = discovery.build('drive', 'v3', credentials=CREDS)
                if message.content_type == 'photo':
                    mime_type = 'image/jpeg'
                elif message.content_type == 'document':
                    mime_type = 'application/pdf'
                elif message.content_type == 'audio':
                    mime_type = 'audio/mpeg'
                elif message.content_type == 'video':
                    mime_type = 'video/mp4'
                elif message.content_type == 'voice':
                    mime_type = 'audio/ogg'
                else:
                    mime_type = 'text/plaine'

                # Uploading file to our GoogleDrive Folder
                # Don't forget to Share Full Access in this GoogleDrive Folder to service_accout email (email is inside service account JSON token)
                file_metadata = {'name': file_name_str, 'parents': [GDRIVE_PARENT_DIR]}
                media = MediaIoBaseUpload(io.BytesIO((downloaded_file)),mime_type)
                file = service.files().create(body=file_metadata, media_body=media,
                                            fields='id').execute()
                if file and file.get("id"):
                    good_request = True
                    good_txt = f'Session {msg_session}: GOOD sended content in handle_content from {user_id}: {file_name_str}. On counter={counter}'
                    logger.info(good_txt)
                    inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=good_txt)
                else:
                    raise Exception(f'Session {msg_session}: error from handle_content: {err_msg}. On counter={counter}')
            except SocketError as se:
                bad_txt = f'Session {msg_session}: ERROR in handle_content from {user_id}: catch socket error! errno={se.errno}, test_no={errno.ECONNRESET}. On counter={counter}'
                logger.info(bad_txt)
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=bad_txt, err=True)
                counter += 1
            except Exception as e:
                counter += 1
                bad_txt = f'Session {msg_session}: ERROR in handle_content: {e}. On counter={counter}'
                logger.info(bad_txt)
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=bad_txt, err=True)

        if not good_request:
            raise Exception(f'Session {msg_session}: can\'t receive content from {user_id} - file: {file_name}. Error: {err_msg}')
    except Exception as  e:
        err_msg = Exception(f'Session {msg_session}: ERROR in handle_content: {e}')
        logger.info(err_msg)
        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=err_msg, err=True)

# Func for very first interaction with bot
@bot.message_handler(commands=['start'])
def handle_start_command(message):
    counter = 0
    good_request = False
    msg_session = f'{TELEGRAM_BOT["name"]}_{str(datetime.now().isoformat())[:22]}_{str(uuid.uuid4().hex)[:10]}'
    logger.info(f'Session {msg_session}: START command "start"')
    try:
        while counter < 3 and not good_request:
            logger.info(f'Session {msg_session}: IN handle_start_command: Try counter={counter}')
            user_name = str(message.chat.username).lower() if message.chat.username and str(message.chat.username).lower != 'none' \
                                                           else f'user_{str(message.chat.id).lower()}'
            user_id = str(message.chat.id)
            inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg='command start')
            try:
                markup = types.ReplyKeyboardMarkup()

                for btn in BNTS_MENU:
                    markup.row(btn['txt'])
                bot.send_message(chat_id=user_id,
                                 text=GREETING_MSG,
                                 reply_markup=markup,
                                 parse_mode='Markdown',
                                 disable_web_page_preview=True)
                good_txt = f'Session {msg_session}: GOOD sended greeting msg in command "start". On counter={counter}'
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=good_txt)
                logger.info(good_txt)

                markup = make_keyboard(msg_session=msg_session, node=HOME_NODE)
                message_item = make_message(msg_session=msg_session, node=HOME_NODE)
                bot.send_message(chat_id=user_id,
                                    text=message_item,
                                    reply_markup=markup,
                                    disable_web_page_preview=True)
                good_txt = f'Session {msg_session}: GOOD sended home msg in command "start". On counter={counter}'
                good_request = True
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=good_txt)
                logger.info(good_txt)
            except SocketError as se:
                bad_txt = f'Session {msg_session}: ERROR in handle_start_command: catch socket error! errno={se.errno}, test_no={errno.ECONNRESET}. On counter={counter}'
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=bad_txt, err=True)
                logger.info(bad_txt)
                counter += 1
            except Exception as e:
                counter += 1
                bad_txt = f'Session {msg_session}: ERROR in handle_start_command: {e}. On counter={counter}'
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=bad_txt, err=True)
                logger.info(bad_txt)
        if not good_request:
            raise Exception(f'Session {msg_session}: can\'t send start message to {user_id}')
    except Exception as e:
        err_msg = Exception(f'Session {msg_session}: TOTAL ERROR in handle_start_command: {e}')
        logger.info(err_msg)
        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=err_msg, err=True)

# Func to prevent user for sending other stuff to bot
@bot.message_handler(content_types=['sticker', 'video_note', 'location', 'contact', 'new_chat_members', 
                                    'left_chat_member', 'new_chat_title', 'new_chat_photo', 'delete_chat_photo', 
                                    'group_chat_created', 'supergroup_chat_created', 'channel_chat_created', 
                                    'migrate_to_chat_id', 'migrate_from_chat_id', 'pinned_message'])
def handle_wrong_type(message):
    counter = 0
    good_request = False
    msg_session = f'{TELEGRAM_BOT["name"]}_{str(datetime.now().isoformat())[:22]}_{str(uuid.uuid4().hex)[:10]}'
    logger.info(f'Session {msg_session}: START handle_wrong_type')
    try:
        while counter < 3 and not good_request:
            logger.info(f'Session {msg_session}: IN handle_wrong_type: Try counter={counter}')
            user_name = str(message.chat.username).lower() if message.chat.username and str(message.chat.username).lower != 'none' \
                                                           else f'user_{str(message.chat.id).lower()}'
            user_id = str(message.chat.id)
            inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'handle wrong type: {message.content_type}')
            try:
                bot.send_message(chat_id=user_id,
                                text=WRONG_TYPE_MSG)
                good_request = True
                good_txt = f'Session {msg_session}: GOOD sended msg in handle_wrong_type from {user_id}. On counter={counter}'
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=good_txt)
                logger.info(good_txt)
            except SocketError as se:
                bad_txt = f'Session {msg_session}: ERROR in handle_wrong_type from {user_id}: catch socket error! errno={se.errno}, test_no={errno.ECONNRESET}. On counter={counter}'
                logger.info(bad_txt)
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=bad_txt, err=True)
                counter += 1
            except Exception as e:
                counter += 1
                bad_txt = f'Session {msg_session}: ERROR in handle_wrong_type: {e}. On counter={counter}'
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=bad_txt, err=True)
                logger.info(bad_txt)
        if not good_request:
            raise Exception(f'Session {msg_session}: can\'t send handle_wrong_type message to {user_id}')
    except Exception as e:
        err_msg = Exception(f'Session {msg_session}: TOTAL ERROR in handle_wrong_type: {e}')
        logger.info(err_msg)
        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=err_msg, err=True)

# Func to catch when user or admin push some button 
# or when admin want to send user payInfo or when admin want to send user some other message
@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    counter = 0
    good_request = False
    err_msg = ''
    msg_session = f'{TELEGRAM_BOT["name"]}_{str(datetime.now().isoformat())[:22]}_{str(uuid.uuid4().hex)[:10]}'
    logger.info(f'Session {msg_session}: START handle_text_messages')
    try:
        while counter < 5 and not good_request:
            logger.info(f'Session {msg_session}: IN handle_text_messages: Try counter={counter}')
            user_name = str(message.chat.username).lower() if message.chat.username and str(message.chat.username).lower != 'none' \
                                                           else f'user_{str(message.chat.id).lower()}'
            user_id = str(message.chat.id)
            
            try:
                if message.text in BTNS_TXTS: # if user or admin push some button
                    inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'user push button: {message.text}')
                    msg = make_message(msg_session=msg_session, node=BTNS_TXTS[message.text])
                    markup  = make_keyboard(msg_session=msg_session, node=BTNS_TXTS[message.text])
                    bot.send_message(chat_id=user_id,
                                 text=msg,
                                 reply_markup=markup,
                                 disable_web_page_preview=True)
                    good_request = True
                elif message.text.startswith('send-from-admin-to-user-text'): # if admin want to send user some other message
                    if user_id == ADMIN_CHAT:
                        msg_txt = message.text
                        # in ADMIN message - user_id should be inside {}. Here we grab it. 
                        # and message to user should be inside <>. Here we grab it. For exapmle:
                        # "send-from-admin-to-user-text {123} <Hi user! It's admin and I write to you directly using my bot!>"
                        to_user_id = msg_txt[msg_txt.find('{')+1:msg_txt.find('}',msg_txt.find('{'))].replace(' ', '')
                        to_user_txt = msg_txt[msg_txt.find('<')+1:msg_txt.find('>',msg_txt.find('<'))]
                        inserting_to_sheet(msg_session=msg_session, user_name=SERVICE_NAME_FOR_LOGS, user_id=SERVICE_NAME_FOR_LOGS, msg=f'we will try to send text msg for: {to_user_id} with text: {to_user_txt}')
                        
                        if to_user_id and to_user_txt:
                            inserting_to_sheet(msg_session=msg_session, user_name=SERVICE_NAME_FOR_LOGS, user_id=SERVICE_NAME_FOR_LOGS, msg=f'we checked text data for: {to_user_id} with text: {to_user_txt}')
                            bot.send_message(chat_id=to_user_id,
                                    text=to_user_txt,
                                    disable_web_page_preview=True)
                            inserting_to_sheet(msg_session=msg_session, user_name=SERVICE_NAME_FOR_LOGS, user_id=SERVICE_NAME_FOR_LOGS, msg=f'we sended text msg to user: {to_user_id} with text: {to_user_txt}')
                            bot.send_message(chat_id=ADMIN_CHAT,
                                    text=f'we sended user: {to_user_id} msg with text: {to_user_txt}',
                                    disable_web_page_preview=True)
                            good_request = True
                            inserting_to_sheet(msg_session=msg_session, user_name=SERVICE_NAME_FOR_LOGS, user_id=SERVICE_NAME_FOR_LOGS, msg=f'we sended info that we sended text msg user: {to_user_id} to ADMIN!')
                        else:
                            msg = f'we DONT found user_id OR text for sending text to: {to_user_id}. Maybe empty text?: {to_user_txt}?'
                            inserting_to_sheet(msg_session=msg_session, user_name=SERVICE_NAME_FOR_LOGS, user_id=SERVICE_NAME_FOR_LOGS, msg=msg)
                            bot.send_message(chat_id=ADMIN_CHAT,
                                        text=msg,
                                        disable_web_page_preview=True)
                            good_request = True
                    else:
                        msg = f'this command is only for admin!'
                        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=msg)
                        bot.send_message(chat_id=user_id,
                                        text=msg,
                                        disable_web_page_preview=True)
                        good_request = True
                elif message.text.startswith('send-from-admin-to-user-payment-info'): # if admin want to send user payInfo
                    if user_id == ADMIN_CHAT:
                        pay_txt = message.text.replace(' ', '')
                        # in ADMIN message - user_id should be inside {}. Here we grab it. 
                        # and payment sum to user should be inside <>. Here we grab it. For exapmle:
                        # "send-from-admin-to-user-payment-info {123} <150>"
                        to_user_id = pay_txt[pay_txt.find('{')+1:pay_txt.find('}',pay_txt.find('{'))]
                        to_user_sum = pay_txt[pay_txt.find('<')+1:pay_txt.find('>',pay_txt.find('<'))]
                        inserting_to_sheet(msg_session=msg_session, user_name=SERVICE_NAME_FOR_LOGS, user_id=SERVICE_NAME_FOR_LOGS, msg=f'we will try to send payment info for: {to_user_id} with sum: {to_user_sum}')
                        
                        if to_user_id and to_user_sum and float(to_user_sum) > 0:
                            inserting_to_sheet(msg_session=msg_session, user_name=SERVICE_NAME_FOR_LOGS, user_id=SERVICE_NAME_FOR_LOGS, msg=f'we checked payment info for: {to_user_id} with sum: {to_user_sum}')
                            msg = MSG_TO_ADMIN_ABOUT_SENDING_PAYINFO_BEFORE_CONFIRM.replace('id_xxx', to_user_id).replace('coins_xxx', to_user_sum)
                            markup  = make_keyboard(msg_session=msg_session, node=HOME_NODE, payment=f'{to_user_id}:{to_user_sum}')
                            bot.send_message(chat_id=ADMIN_CHAT,
                                        text=msg,
                                        reply_markup=markup,
                                        disable_web_page_preview=True)
                            good_request = True
                            inserting_to_sheet(msg_session=msg_session, user_name=SERVICE_NAME_FOR_LOGS, user_id=SERVICE_NAME_FOR_LOGS, msg=f'we sended msg for admin to approve sending payment info to user: {to_user_id} with sum: {to_user_sum} and wallet: {WALLET_STR}')
                        else:
                            msg = f'we DONT found payment data for: {to_user_id}. Maybe incorrect sum: {to_user_sum}?'
                            inserting_to_sheet(msg_session=msg_session, user_name=SERVICE_NAME_FOR_LOGS, user_id=SERVICE_NAME_FOR_LOGS, msg=msg)
                            bot.send_message(chat_id=ADMIN_CHAT,
                                        text=msg,
                                        disable_web_page_preview=True)
                            good_request = True
                    else: # if user just send some text to bot
                        msg = f'this command is only for admin!'
                        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=msg)
                        bot.send_message(chat_id=user_id,
                                        text=msg,
                                        disable_web_page_preview=True)
                        good_request = True
                else:
                    inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=f'get text msg: {message.text}')
                    good_request = True
            except SocketError as se:
                bad_txt = f'Session {msg_session}: catch socket error in handle_all_messages from {user_id}! errno={se.errno}, test_no={errno.ECONNRESET}. On counter={counter}'
                logger.info(bad_txt)
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=bad_txt, err=True)
                counter += 1
            except Exception as e:
                bad_txt = f'Session {msg_session}: ERROR in handle_all_messages: {e}. On counter={counter}'
                logger.info(bad_txt)
                inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=bad_txt, err=True)
                counter += 1
        
        if not good_request:
            raise Exception(f'Session {msg_session}: can\'t send text message to {user_id}. Error: {err_msg}')
    except Exception as e:
        err_msg = Exception(f'Session {msg_session}: TOTAL ERROR in handle_all_messages: {e}')
        inserting_to_sheet(msg_session=msg_session, user_name=user_name, user_id=user_id, msg=err_msg, err=True)
        logger.info(err_msg)


if __name__ == '__main__':
    """
        Start of script.
        Create telegram bot pool instance
    """
    logger.info(f'Starting {TELEGRAM_BOT["name"]}! Time: {datetime.now()}')
    try:
        # Remove webhook, it fails sometimes the set if there is a previous webhook
        bot.remove_webhook()

        # Set webhook
        bot.set_webhook(url=WEBHOOK_URL,
                        certificate=open(WEBHOOK_SSL_CERT, 'r'))

        uvicorn.run(
            app,
            host=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
            ssl_keyfile=WEBHOOK_SSL_PRIV,
            ssl_certfile=WEBHOOK_SSL_CERT
        )
    except Exception as e:
        logger.info(f'ERROR in __main__: {e}')
