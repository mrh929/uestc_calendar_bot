#这个程序模拟了教务系统对密码的加密过程
import execjs

def aes_from_js(data):
    jsstr = get_js()
    ctx = execjs.compile(jsstr) #加载JS文件
    return (ctx.call('encryptAES', data, '1gaE7SDnOefweukF'))  #调用js方法  第一个参数是JS的方法名，后面的data和key是js方法的参数


def get_js():
    f = open("encrypt.wisedu.js", 'r', encoding='utf-8') # 打开JS文件
    line = f.readline()
    htmlstr = ''
    while line:
        htmlstr = htmlstr+line
        line = f.readline()
    return htmlstr


if __name__ == '__main__':
    print(aes_from_js("929281"))