# Telegram bot with connnect to Google Drive/Sheet/Form

This script can deploy a simple Telegram Bot with pre-defined conversation of 15 messages and with Buttons for each step of conversation.
It's designed like a bot for some service. 
On some steps of conversation there are additional possibilities for users and some checking of them:  
- On one step bot ask user to fill the Google Form and give link to that. And later bot can check if user really filled this form.
- On other step bot ask user to send a photo. And recieved photo will be saved on your Google Drive. And later bot can check if user really sent photo.
- On other step Admin can send user a message via bot (like from bot to user) with some payment credentials or other important information.
- All interactions from all users will be send as log to your Google Sheet Table.

## Short instruction how to run bot
1. In GooglrCloudPlatform (GCP) create ServiceAccount and generate ServiceAccountKey (JSON)
2. Create folder in your GoogleDrive and Enable DriveAPI in GCP and share access to ServiceAccountEmail
3. Create Google Sheet Table and Enable SheetAPI in GCP and share access to ServiceAccountEmail
4. Create Google Form and Enable FormsAPI in GCP and share access to ServiceAccountEmail
5. Create bot in Telegram - ask BotFather for that and take from it Telegram token
6. Get access to some Server where application with this bot will be running. Rent server or start a VM instance on GCP. The server should have an External Static IP with open port 8443 or 443 so Telegram can reach it by requests.
7. For IP of that Server generate SSL certificates using command:  
`openssl req -newkey rsa:2048 -sha256 -nodes -keyout url_private.key -x509 -days 3560 -out url_cert.pem`
8. Setup your webhook in Telegram using certificates files and IP of your server:  
`curl -F "url=https://XXX.XXX.XXX.XXX:443" -F "certificate=@url_cert.pem" https://api.telegram.org/botYOUR-TOKEN/setWebhook`
9. Set all CONST variables inside the script file **telegram_bot_hook.py**
10. Move script to server, install all dependencies from requirements.txt and run script with command:  
`python telegram_bot_hook.py` or for background run `nohup python telegram_bot_hook.py &`  
if you catch errors with permissions or get troubles on GCP VM yu can try:  
`sudo python telegram_bot_hook.py` or `sudo env "PATH=$PATH" python telegram_bot_hook.py`  

## Schema of Bot Conversation
![alt text](https://github.com/zextserg/telegram-bot-simple/blob/main/tg-bot-schema.png?raw=true)

## Detailed instruction how to run bot (same as in comments inside script)
1. First of all - in GooglrCloudPlatform (GCP) create ServiceAccount and generate ServiceAccountKey (JSON)
2. Download this JSON from GCP and here set a path to that file  
`SECRET_KEY = os.path.join('./', 'service_acc_token_key.json')`

3. Next you should create 3 things and share access to these things to service_accout email (email is inside service account JSON token): 
- create folder in your GoogleDrive and Enable DriveAPI in GCP
- create Google Sheet Table and Enable SheetAPI in GCP
- create Google Form and Enable FormsAPI in GCP
After creating all 3 things and sharing access - you can set const variables for each in this code below:  

In this directory will be saved all files (photos, audio etc.) that user send to the bot (bot will ask for it on **step #12**).  
Don't forget to Share Full Access in this GoogleDrive Folder to service_accout email (email is inside service account JSON token).  
`GDRIVE_PARENT_DIR = '123abc'` - put here your actual values  

In this table script will write all logs for all users interactions with bot  
`SHEET_LOG_ID = '123abc'` - put here your actual values  
`SHEET_LOG_SHEET_NAME = 'bot_auto_log'` - put here your actual values  

On **step #10** bot will ask user to fill out your Google Form and later check by Telegram username if user really filled it.  
So you need to create 1 required field in this Form - *"Telegram username"* field and here you should set **key_id** for this excat field in our Form as `GFORM_USERNAME_KEY` (**key_id** you can check by GoogleFormsAPI).  
Don't forget to Share Full Access in your GoogleForm to service_accout email (email is inside service account JSON token)  
`GFORM_ID = '123abc'` - put here your actual values  
`GFORM_URL = 'https://forms.gle/123abc'` - put here your actual values  
`GFORM_USERNAME_KEY = '123abc'` - put here your actual values  

 4. If you create all 3 things, share access to them and set correct values above - next code for making CREDS should works fine.
If you forget something - here you can see an Error with link to Enabling API on GCP or with message of incorrect access:  
```
SCOPES = ["https://www.googleapis.com/auth/forms.responses.readonly", 
          'https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/spreadsheets']
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"
CREDS = Credentials.from_service_account_file(SECRET_KEY, scopes=SCOPES)
```  

5. Next you should create bot in Telegram - ask BotFather for that.  
After creting - set your actual name and Telegram token for that bot (values from BotFather):  
```
TELEGRAM_BOT = {
    'name': 'bot-name', # put here your actual values
    'token': '123:123abc' # put here your actual values
}
```

6. Next you should find a server where this bot will be up and run.  
This server should have an External static IP address and should be available from internet on port 443 or 8443.  
You can buy or rent server somewhere for this purpose, but it can not be just your laptop with localhost.  
I prefer to create a VM instance on GCP with External sctatip IP. Instruction how to do it (in russian) can be found   
[here](https://habr.com/ru/companies/ods/articles/462141/).  
Anyway - you need a working IP with port 443 or 8443. Set these values here:  
`WEBHOOK_HOST = 'XXX.XXX.XXX.XXX'` - put here your actual values  
`WEBHOOK_PORT = 443`  - put here your actual values  
`WEBHOOK_LISTEN = '0.0.0.0'`  

7. Next you should create ssl certificate for your IP.  
You can do it from any terminal after making your IP available.  
Here is a command for creating ssl certificate and example how to respond to terminal prompts  
(when prompt asks "Common Name (e.g. server FQDN or YOUR name)" - insert your actual IP numbers):  
`openssl req -newkey rsa:2048 -sha256 -nodes -keyout url_private.key -x509 -days 3560 -out url_cert.pem`  

Example prompt:  
```
# Country Name (2 letter code) [AU]:GB
# State or Province Name (full name) [Some-State]:London
# Locality Name (eg, city) []:London
# Organization Name (eg, company) [Internet Widgits Pty Ltd]:TEST
# Organizational Unit Name (eg, section) []:director
# Common Name (e.g. server FQDN or YOUR name) []:XXX.XXX.XXX.XXX
# Email Address []:test@test.com
```  

After that prompt you should get 2 files for ssl certificate: **.pem** and **.key.**  
Save them somewhere and put them in repository and set names of files below:  
`WEBHOOK_SSL_CERT = 'url_cert.pem'`  - put here your actual values - Path to the ssl certificate  
`WEBHOOK_SSL_PRIV = 'url_private.key'`  - put here your actual values - Path to the ssl private key  

8. Next you should setup your webhook in Telegram.  
For that you should run next command from folder with your ssl certificate files.  
And of course replace XXX with your actual IP values and YOUR-TOKEN with your Telegram token (word "bot" just before it - leave as is)  
`curl -F "url=https://XXX.XXX.XXX.XXX:443" -F "certificate=@url_cert.pem" https://api.telegram.org/botYOUR-TOKEN/setWebhook`  

After that in terminal you should receive response from Telegram like:  
`{"ok":true,"result": ...}`  

9. So now setup final Webhook url  
`WEBHOOK_URL = f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}/{TELEGRAM_BOT['token']}/"`  

10. Next you should set your actual values for your Wallet (in text and picture formats) - bot will use it on **step #13**:  
`WALLET_STR = '123'` - put here your actual values  
`WALLET_PIC = 'wallet.png'` - put here your actual values  

11. Last preparing thing - set your **chat_id** as ADMIN chat, but for that you may need a first interaction with this bot.  
So just start this script first, find it in Telegram, start conversation with message `/start` to the bot.  
And then - you can find your **chat_id** in GoogleSheet log table.  
Then replace value for ADMIN chat with your actual value:  
`ADMIN_CHAT = '123'` - put here your actual values  

12. So now - you're ready to move this script to your server and Run it!  
Of course you should install all libs from requirements.txt in the envirenment on your server and then RUN this script.  
You should be able to RUN it with just command:  
`python telegram_bot_hook.py`  
or if you want to run it at background to be able to close terminal after:  
`nohup python telegram_bot_hook.py &`  

But sometimes Google can prevent run commands like these without sudo and gives Errors about permissions. So you can try:  
`sudo python telegram_bot_hook.py` or `sudo env "PATH=$PATH" python telegram_bot_hook.py`  

Now you set up all needed values and below is just code which should work without any additional settings!


