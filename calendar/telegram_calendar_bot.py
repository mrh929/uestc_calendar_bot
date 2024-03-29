import telegram
import google
import logging
import base64
import io
#from telegram.ext import MessageHandler, Filters, Updater, CommandHandler
from requests_html import HTMLSession
from google.cloud import firestore
from bs4 import BeautifulSoup
from PIL import Image








def course_print(mycourse, bot, update):#构造一个好看的字符串发送给用户
    week={
        "0":"Monday",
        "1":"Tuesday",
        "2":"Wednsday",
        "3":"Thirsday",
        "4":"Friday",
        "5":"Saturday",
        "6":"Sunday",
    }

    for course in mycourse:
        info = course[0]
        time = course[1]

        out = "{}\n{} {}\nweek:".format(info[0],info[1],info[2])

        i = 0
        while(i <= 20):
            if(info[3][i] == 1):
                out = out + " {}".format(i)
            i += 1

        out = out + '\n' + week[str(time[0][0])] + " "
        out = out + "class no."
        for classes in time:
            out = out + " {}".format(classes[1]+1)

        #print(out)
        bot.send_message(chat_id=update.message.chat_id, text=out)
        """
        print(info)
        #out = out + str(info) + "\n"
        out = out + str(info[0]) + '\n' + str(info[1]) + str(info[2]) +'\n' + str(info[3]) + "\n"
        for t in time:
            out = out + str(t) + "\n"
        out = out + "\n"
        """

    bot.send_message(chat_id=update.message.chat_id, text="Demo version. To be continued....")
    #bot.send_message(chat_id=update.message.chat_id, text=out)




def func_start(bot, update):
    print("{} just started".format(update.message.chat_id))
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    doc_ref.set({
    'user_id': update.message.chat_id,
    'status': 0
    })
    #setstatus = 0

    #bot.send_message(chat_id=update.message.chat_id, text="plz input your ID and passwd:")

def func_login(bot, update):
    print("{} just login".format(update.message.chat_id))
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    doc_ref.set({
    'status': 1
    }, merge=True)
    #setstatus = 1
    bot.send_message(chat_id=update.message.chat_id, text="plz input your student ID:")

def func_login_account(bot, update):
    print("{} just input account {}".format(update.message.chat_id,update.message.text))
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    doc_ref.set({
    'account': update.message.text,
    'status': 2
    }, merge=True)
    #setstatus = 2
    bot.send_message(chat_id=update.message.chat_id, text="plz input your password:")

def func_login_passwd(bot, update):
    print("{} just input passwd {}".format(update.message.chat_id,update.message.text))
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    doc = doc_ref.get().to_dict()
    account = doc['account']
    passwd = update.message.text
    bot.send_message(chat_id=update.message.chat_id, text="plz input your captcha below:")
    bot.send_message(chat_id=update.message.chat_id, text="Pulling captcha photo...")
    form, img, new_session = get_captcha(account, passwd)

    #test
    img_b64encode = base64.b64encode(img)  # base64编码
    img_b64decode = base64.b64decode(img_b64encode)  # base64解码
    image = io.BytesIO(img_b64decode)
    bot.send_photo(chat_id=update.message.chat_id, photo=image)


    doc_ref.set({
    'form': form,
    'cookies': new_session.cookies.get_dict(),
    'status': 3
    }, merge=True)

    #bot.send_photo(chat_id=update.message.chat_id, photo=img)

def func_login_captcha(bot, update):
    print("{} just input captcha".format(update.message.chat_id))
    bot.send_message(chat_id=update.message.chat_id, text="Attempting to login...")
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    doc = doc_ref.get().to_dict()
    cookies = doc['cookies']
    form = doc['form']

    captcha = update.message.text
    new_session, res = login(form, captcha, cookies)

    if(res == 0):
        bot.send_message(chat_id=update.message.chat_id, text="Login success! Pulling data...")

        mycourse = get_all_course(new_session)
        course_print(mycourse, bot, update)


    elif(res == 1):
        bot.send_message(chat_id=update.message.chat_id, text="Password wrong!")
    elif(res == 2):
        bot.send_message(chat_id=update.message.chat_id, text="Captcha wrong!")
    elif(res == 3):
        bot.send_message(chat_id=update.message.chat_id, text="Student ID wrong!")

    doc_ref.set({
    'form': form,
    'cookies': new_session.cookies.get_dict(),
    'status': 0
    }, merge=True)

def func_message(bot, update):
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    try:#如果之前没有记录，自动跳转到start菜单
        doc = doc_ref.get().to_dict()
    except google.cloud.exceptions.NotFound:
        func_start(bot, update)
        return

    status = doc[u'status']
    if(status == 0):
        func_start(bot, update)
    elif(status == 1):
        func_login_account(bot, update)
    elif(status == 2):
        func_login_passwd(bot, update)
    elif(status == 3):
        func_login_captcha(bot, update)
    #elif(status == 4):
        #func_login_captcha(bot, update)
        #print(4)


if(__name__ == "__main__"):
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)

    f = open("token.txt","r")
    token = f.read()
    f.close()

    bot = telegram.Bot(token = token)#bot
    print(bot.get_me())
    updater = Updater(token = token)#updater
    db = firestore.Client()#google filestore


    dispatcher = updater.dispatcher
    handler = CommandHandler('start', func_start)
    dispatcher.add_handler(handler)
    handler = CommandHandler('login', func_login)
    dispatcher.add_handler(handler)
    handler = MessageHandler(Filters.text, func_message)
    dispatcher.add_handler(handler)


    updater.start_polling()

#$env:GOOGLE_APPLICATION_CREDENTIALS="G:\github\telebot\key\My First Project-2035ff2d3024.json"