# Telegram bot with connnect to Google Drive/Sheet/Form

This script can deploy a simple Telegram Bot with pre-defined conversation of 15 messages and with Buttons for each step of conversation.
It's designed like a bot for some service. 
On some steps of conversation there are additional possibilities for users and some checking of them:  
- On one step bot ask user to fill the Google Form and give link to that. And later bot can check if user really filled this form.
- On other step bot ask user to send a photo. And recieved photo will be saved on your Google Drive. And later bot can check if user really sent photo.
- On other step Admin can send user a message via bot (like from bot to user) with some payment credentials or other important information.
- All interactions from all users will be send as log to your Google Sheet Table.

## Schema of Bot Conversation
![alt text](https://github.com/zextserg/telegram-bot-simple/blob/main/tg-bot-schema.png?raw=true)
