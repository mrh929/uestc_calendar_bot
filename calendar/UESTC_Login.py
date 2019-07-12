from requests_html import HTMLSession
from Crypto_AES import get_AES_cipher

def __get_mid_text(text, left_text, right_text, start=0):#获取中间文本
    left = text.find(left_text, start)
    if left == -1:
        return ('', -1)
    left += len(left_text)
    right = text.find(right_text, left)
    if right == -1:
        return ('', -1)
    return (text[left:right], right)

def get_captcha(acc, passwd):#获取验证码图片
    url = 'https://idas.uestc.edu.cn/authserver/login'
    # 获取lt,execution
    new_session = HTMLSession()
    response = new_session.get(url)
    response.html.render()
    lt_data, end = __get_mid_text(response.html.html, '"lt" value="', '"')

    execution, end = __get_mid_text(
        response.html.html, '"execution" value="', '"', end)
    key, end = __get_mid_text(response.html.html, 'pwdDefaultEncryptSalt = "', '";')
    passwd = get_AES_cipher(passwd, key)

    captchaUrl = "https://idas.uestc.edu.cn/authserver/captcha.html?ts=1"
    headers = {
        "Cookie":"route=b33ccb7ad9a0242cd671775d1be49fa3; FSSBBIl1UgzbN7N443S=mSqjkk00wVmGKjamNnk5tCnhuwF9Y3LqHzfPsc14lZSjCVQ5zJ12spaJMVskeUnM; FSSBBIl1UgzbN7N443T=4ZhMKolIRvblBne4355sWBvZbrwiCHeUdgohU35goPypVj3tBEIzX0pEjR7to4r1IAnWKhezXURHDfb1g9RadhRsU.XfLl4oVdqqFMTqtg_N3OTGKY0lWU1Yaq1GwHfKft5vyUBT4DH6QGQMSdX_4Cr00keeYOhCeM0rUxTu89VXGmudRsF6cOf9dTjtXMvclMYPk2seY0QsYwyIf.QZjKAaznaJunoIosZeUaE50wy3.T7Ns_HohwfUgEmlazB.QIk2GEtaDDJqr.56OY0lU_TdLA5cFi9caW56WXs8TogpC0fVPNQCYuTqt44quX1i.Vybv604DUVJFuLu23kRMKyIvlUnKSltyeyflouvdY5FLqG; JSESSIONID=a6jhqJ31hCMYmkphNarfg1AmjU-uNID8GRLN2wt5cSb817JOcqo7!-1519892835"
    }

    response = new_session.get(captchaUrl, headers=headers)
    #response.html.render()
    img = response.content   #获取到验证码图片
    #***图片如何处理

    form = {  #构造post的form
        "username" : acc ,
        "password" : passwd, #需要加盐计算
        "lt": lt_data,
        "dllt": "userNamePasswordLogin",
        "execution": execution,
        "_eventId": "submit",
        "rmShown": "1"
    }

    return (form, img, new_session) #返回form和img还有登录时使用的session，以便进行登录

def _login(form, captcha, cookies):#登录uestc
    form["captchaResponse"] = captcha
    url = 'https://idas.uestc.edu.cn/authserver/login'

    new_session = HTMLSession()
    response = new_session.post(url, data=form, cookies = cookies)
    response.html.render()

    if("密码有误" in response.html.html): #密码错误
        return (new_session, 1)
    elif("无效的验证码" in response.html.html):#验证码错误
        return (new_session, 2)
    elif("<small>忘记密码？</small>" in response.html.html):#账号错误
        return (new_session, 3)

    response = new_session.get(
        'http://eams.uestc.edu.cn/eams/courseTableForStd.action')
    response.html.render()
    if '踢出' in response.html.html:
        click_url = __get_mid_text(response.html.html, '请<a href="', '"')
        new_session.get(click_url[0])

    return (new_session, 0)