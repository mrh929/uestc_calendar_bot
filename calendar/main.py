import telegram
import google
import logging
import base64
import io
from requests_html import HTMLSession
from google.cloud import firestore
from bs4 import BeautifulSoup
from PIL import Image
from time import sleep
from Spider import get_all_course
from UESTC_Login import _login, get_captcha

def __Bot_token():
    f = open("token.txt","r")
    token = f.read()
    f.close()
    return token

def course_print(mycourse, update):#构造一个好看的字符串发送给用户
    chat_id = update.message.chat_id
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
        _bot_send_text(chat_id, out)
        """
        print(info)
        #out = out + str(info) + "\n"
        out = out + str(info[0]) + '\n' + str(info[1]) + str(info[2]) +'\n' + str(info[3]) + "\n"
        for t in time:
            out = out + str(t) + "\n"
        out = out + "\n"
        """

    _bot_send_text(chat_id, "Demo version. To be continued....")
    #bot.send_message(chat_id=update.message.chat_id, text=out)


def _bot_send_text(chat_id, text):
    global bot
    bot.send_message(chat_id = chat_id, text = text)

def _firestore_update(chat_id ,dict):
    #将字典中的内容放入google firestore
    global db
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(chat_id))
    doc_ref.set(dict, merge=True)

def _firestore_read(chat_id):
    global db
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(chat_id))
    doc = doc_ref.get().to_dict()
    return doc

def _Process_Start(update):
    #打印欢迎界面
    chat_id = update.message.chat_id
    dicts = {
        'user_id': chat_id,
        'status': 0
    }
    _firestore_update(chat_id, dicts)
    _bot_send_text(chat_id,
        text="""    Welcome to YouESTC alarm clock!

    This bot is used to query your timetable and alarm you before class.

    Commands:
    /login : to login into uestc""")

def _Process_Login(update):
    chat_id = update.message.chat_id
    dicts = {'status': 1}
    _firestore_update(chat_id, dicts)
    _bot_send_text(chat_id, "please input your UESTC student number:")

def _Process_Account(update):
    #处理输入的帐号
    chat_id = update.message.chat_id
    dicts = {
        'status': 2,
        'account': update.message.text
    }
    _firestore_update(chat_id, dicts)
    _bot_send_text(chat_id, "please input your password:")

def _Process_Password(update):
    #处理输入的密码
    chat_id = update.message.chat_id
    doc = _firestore_read(chat_id)
    account = doc['account']
    passwd = update.message.text
    dicts = {'passwd': base64.b64encode(passwd.encode('utf-8'))}
    _firestore_update(chat_id, dicts)

    bot.send_message(chat_id=update.message.chat_id, text="please input your captcha below:")
    bot.send_message(chat_id=update.message.chat_id, text="Pulling captcha photo...")
    form, img, new_session = get_captcha(account, passwd) #请求验证码图片

    #f = open("captcha.png", "wb")
    #f.write(img)
    #f.close()

    img_b64encode = base64.b64encode(img.encode('utf-8'))  # base64编码
    img_b64decode = base64.b64decode(img_b64encode)  # base64解码
    image = io.BytesIO(img_b64decode)
    #f = open("captcha.png", "rb")
    bot.send_photo(chat_id=chat_id, photo=image)
    # 发送验证码图片给用户

    dicts = {
        'form': form,
        'cookies': new_session.cookies.get_dict(),
        'status': 3
    }
    _firestore_update(chat_id, dicts)

def _Process_Captcha(update):
    #处理输入的验证码
    chat_id = update.message.chat_id
    _bot_send_text(chat_id, "Attempting to login...")
    doc = _firestore_read(chat_id)
    cookies = doc['cookies']
    form = doc['form']
    captcha = update.message.text

    new_session, res = _login(form, captcha, cookies)

    if(res == 0):
        _bot_send_text(chat_id, "Login success! Pulling data...")
        mycourse = get_all_course(new_session)
        course_print(mycourse, update)
    elif(res == 1):
        _bot_send_text(chat_id, "Password wrong!")
    elif(res == 2):
        _bot_send_text(chat_id, "Captcha wrong!")
    else:
        _bot_send_text(chat_id, "Student number wrong!")

    dicts = {'status': 0}
    _firestore_update(chat_id, dicts)

def Text_Process(update):
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    try:#如果之前没有记录，自动跳转到start菜单
        doc = doc_ref.get().to_dict()
    except google.cloud.exceptions.NotFound:
        _Process_Start(update)
        return

    status = doc['status']
    if(status == 0):
        _Process_Start(update)
    elif(status == 1):
        _Process_Account(update)
    elif(status == 2):
        _Process_Password(update)
    elif(status == 3):
        _Process_Captcha(update)


    _bot_send_text(update.message.chat_id, "收到啦！")

def Command_Process(update): #用来处理指令
    command = update.message.text

    command_list = {
        '/start': _Process_Start,
        '/login': _Process_Login
    }
    if(command in command_list):
        command_list[command](update)
    elif(command[0] == '/'):
        _Process_Start(update)
    else:
        Text_Process(update)
        #不是命令，跳转到对文本的处理函数里去


if(__name__ == "__main__"):
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
    # 记录日志

    global bot
    global db
    #定义全局变量，使得所有函数用一个变量

    token = __Bot_token()
    bot = telegram.Bot(token = token)#bot
    print(bot.get_me())
    # 登录telegram

    db = firestore.Client()
    # 登录google filestore

    while(1):
        updates = bot.get_updates()
        if(updates != []):
            for update in updates:
                Command_Process(update)
                bot.get_updates(limit = 1, offset = update.update_id+1)
                print(update.message.text, " ", update.message.chat_id)
        else:
            sleep(0.01)



    #$env:GOOGLE_APPLICATION_CREDENTIALS="G:\github\telebot\key\My First Project-2035ff2d3024.json"