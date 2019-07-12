from bs4 import BeautifulSoup
import requests
import telegram
import re
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES
import base64

def encrypt_AES(data, key, iv):
    aes = AES.new(key, AES.MODE_CBC, iv)
    data = pad(data, AES.block_size, style='pkcs7')
    ret = base64.b64encode(aes.encrypt(data))
    return ret

def __get_mid_text(text, left_text, right_text, start=0):
    """获取中间文本"""
    left = text.find(left_text, start)
    if left == -1:
        return ('', -1)
    left += len(left_text)
    right = text.find(right_text, left)
    if right == -1:
        return ('', -1)
    return (text[left:right], right)

def get_now_semesterid(session):
    response = session.get(
        'http://eams.uestc.edu.cn/eams/teach/grade/course/person.action'
    )

    data = __get_mid_text(response.text, 'semesterId=', '&')
    if(data[1]== -1):
        print("semesterid获取失败")
        exit()
    ret = int(data[0])
    return ret

def get_all_course(session, semester_id = 0):
    #如果未输入学期号，则默认为本学期
    semester_id = get_now_semesterid(session) + 20 * semester_id

    form = {
        "semester.id": semester_id,
        "startWeek": "1",
        "setting.kind": "std",
        "ignoreHead": "1",
        "isEng": "0",
        "ids": "157348" #这个是std对应的ids
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

def course_print(mycourse):
    for course in mycourse:
        info = course[0]
        time = course[1]
        print(info[0],'\n' ,info[1], info[2],'\n', info[3])
        for t in time:
            print(t, end = "")
        print()

def get_captcha(acc, passwd):
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

def login(form, captcha, new_session):
    form["captchaResponse"] = captcha
    url = 'https://idas.uestc.edu.cn/authserver/login'
    response = new_session.post(url, data=form)
#    print(response.content.decode('utf-8'))

    if("密码有误" in response.text): #密码错误
        return (new_session, 1)
    elif("无效的验证码" in response.text):#验证码错误
        return (new_session, 2)

    response = new_session.get(
        'http://eams.uestc.edu.cn/eams/courseTableForStd.action')
    if '踢出' in response.text:
        click_url = __get_mid_text(response.text, '请<a href="', '"')
        new_session.get(click_url[0])

    return (new_session, 0)

if __name__ == '__main__':
    acc = "2018091605016"
    passwd = "929281"
    print("input captcha:")
    ret = get_captcha(acc, passwd)

    f = open("CaptchaUrl.png","wb")
    f.write(ret[1])
    f.close()

    captcha = input("")
    mysession, status = login(ret[0], captcha, ret[2])
    if(status == 1):
        print("密码错误")
        exit()
    elif(status == 2):
        print("验证码错误")
        exit()
    mycourse = get_all_course(mysession)

    course_print(mycourse)
    #print(mycourse[0])
