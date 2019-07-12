import requests
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

