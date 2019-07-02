import telegram
import google
import requests
import logging
import base64
import re
import io
from telegram.ext import MessageHandler, Filters, Updater, CommandHandler
from google.cloud import firestore
from bs4 import BeautifulSoup
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES
from PIL import Image

def encrypt_AES(data, key, iv):#AES加密算法
    aes = AES.new(key, AES.MODE_CBC, iv)
    data = pad(data, AES.block_size, style='pkcs7')
    ret = base64.b64encode(aes.encrypt(data))
    return ret

def __get_mid_text(text, left_text, right_text, start=0):#获取中间文本
    left = text.find(left_text, start)
    if left == -1:
        return ('', -1)
    left += len(left_text)
    right = text.find(right_text, left)
    if right == -1:
        return ('', -1)
    return (text[left:right], right)

def get_my_ids(session):#获取ids号
    response = session.get(
        'http://eams.uestc.edu.cn/eams/courseTableForStd.action'
    )

    data = __get_mid_text(response.text, '(form,"ids",\"', '\")')
    if(data[1]== -1):
        print("ids获取失败")
        exit()
    return data[0]

def get_now_semesterid(session):#获取当前学期号
    response = session.get(
        'http://eams.uestc.edu.cn/eams/teach/grade/course/person.action'
    )

    data = __get_mid_text(response.text, 'semesterId=', '&')
    if(data[1]== -1):
        print("semesterid获取失败")
        exit()
    ret = int(data[0])
    return ret

def get_all_course(session, semester_id = 0):#获取学期的所有课程
    #如果未输入学期号，则默认为本学期
    semester_id = get_now_semesterid(session) + 20 * semester_id
    ids = get_my_ids(session)

    form = {
        "semester.id": semester_id,
        "startWeek": "1",
        "setting.kind": "std",
        "ignoreHead": "1",
        "isEng": "0",
        "ids": ids
    }

    url = "http://eams.uestc.edu.cn/eams/courseTableForStd!courseTable.action"
    response = session.get(url, params = form)

    course_content = response.text
    begin = course_content.find("var activity=null;")
    end = course_content.find("table0.marshalTable")
    course_content = course_content[begin+18:end]  #对js代码进行切片，以便读取课程表

    pattern = re.compile(r"(?<=\n).*?(?=\n)")#正则表达式获取每行的字符串
    str_table = pattern.findall(course_content)

    course_info = []
    course_temp = []
    course_time = []
    for content in str_table: #枚举里面的所有字符串
        if(content.find("activity = new TaskActivity") != -1):
            if(course_temp != []):#如果之前保存了课程信息，那么就和时间一起加入人列表
                course_info.append([course_temp, course_time])
                course_time = []

            pattern = re.compile(r"(?<=\").*?(?=\")")
            t = pattern.findall(content)

            temp = []
            for c in t[12]:
                temp.append(int(c))

            course_temp = [t[6], t[2], t[10], temp,]


        elif(content.find("index =") != -1):
            a = __get_mid_text(content, "=", "*")[0] #查找上课时间
            b = __get_mid_text(content, "+", ";")[0]
            course_time.append([int(a), int(b)])

    course_info.append([course_temp, course_time]) #收尾

    return course_info

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

def get_captcha(acc, passwd):#获取验证码图片
    url = 'https://idas.uestc.edu.cn/authserver/login'
    # 获取lt,execution
    new_session = requests.session()
    new_session.cookies.clear()
    response = new_session.get(url)
    lt_data, end = __get_mid_text(response.text, '"lt" value="', '"')

    execution, end = __get_mid_text(
        response.text, '"execution" value="', '"', end)
    key, end = __get_mid_text(response.text, 'pwdDefaultEncryptSalt = "', '";')
    passwd = encrypt_AES(b'a'*64 + passwd.encode('utf-8'), key.encode('utf-8'), b'a'*16).decode('utf-8')  #对密码进行加密

    captchaUrl = "https://idas.uestc.edu.cn/authserver/captcha.html?ts=1"
    img = new_session.get(captchaUrl)   #获取到验证码图片

    form = {  #构造post的form
        "username" : acc ,
        "password" : passwd, #需要加盐计算
        "lt": lt_data,
        "dllt": "userNamePasswordLogin",
        "execution": execution,
        "_eventId": "submit",
        "rmShown": "1"
    }

    return (form, img.content, new_session) #返回form和img还有登录时使用的session，以便进行登录

def login(form, captcha, cookies):#登录uestc
    form["captchaResponse"] = captcha
    url = 'https://idas.uestc.edu.cn/authserver/login'

    new_session = requests.session()

    response = new_session.post(url, data=form, cookies = cookies)

    if("密码有误" in response.text): #密码错误
        return (new_session, 1)
    elif("无效的验证码" in response.text):#验证码错误
        return (new_session, 2)
    elif("<small>忘记密码？</small>" in response.text):#账号错误
        return (new_session, 3)

    response = new_session.get(
        'http://eams.uestc.edu.cn/eams/courseTableForStd.action')
    if '踢出' in response.text:
        click_url = __get_mid_text(response.text, '请<a href="', '"')
        new_session.get(click_url[0])

    return (new_session, 0)

def func_start(bot, update):
    print("{} just started".format(update.message.chat_id))
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    doc_ref.set({
    'user_id': update.message.chat_id,
    'status': 0
    })
    #setstatus = 0
    bot.send_message(chat_id=update.message.chat_id,
        text="Welcome to YouESTC alarm clock!\n\nThis bot is used to query your timetable and alarm you before class.\n\nCommands:\n/login : to login into uestc")
    #bot.send_message(chat_id=update.message.chat_id, text="plz input your ID and passwd:")

def func_login(bot, update):
    print("{} just login".format(update.message.chat_id))
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    doc_ref.set({
    'status': 1
    }, merge=True)
    #setstatus = 1
    bot.send_message(chat_id=update.message.chat_id, text="plz input your ID:")

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
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    doc = doc_ref.get().to_dict()
    cookies = doc['cookies']
    form = doc['form']

    captcha = update.message.text
    new_session, res = login(form, captcha, cookies)

    if(res == 0):
        bot.send_message(chat_id=update.message.chat_id, text="Success! Pulling data...")

        mycourse = get_all_course(new_session)
        course_print(mycourse, bot, update)


    elif(res == 1):
        bot.send_message(chat_id=update.message.chat_id, text="Password wrong!")
    elif(res == 2):
        bot.send_message(chat_id=update.message.chat_id, text="Captcha wrong!")
    elif(res == 3):
        bot.send_message(chat_id=update.message.chat_id, text="Student id wrong!")

    doc_ref.set({
    'form': form,
    'cookies': new_session.cookies.get_dict(),
    'status': 0
    }, merge=True)

def func_message(bot, update):
    doc_ref = db.collection(u'uestc_calendar_bot').document(str(update.message.chat_id))
    try:
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
    #$env:GOOGLE_APPLICATION_CREDENTIALS="G:\github\telebot\key\My First Project-2035ff2d3024.json"
    db = firestore.Client()

    f = open("g:/github/telebot/key/token.txt","r")
    token = f.read()
    f.close()
    bot = telegram.Bot(token = token)
    print(bot.get_me())
    updater = Updater(token = token)
    dispatcher = updater.dispatcher
    handler = CommandHandler('start', func_start)
    dispatcher.add_handler(handler)
    handler = CommandHandler('login', func_login)
    dispatcher.add_handler(handler)
    handler = MessageHandler(Filters.text, func_message)
    dispatcher.add_handler(handler)


    updater.start_polling()