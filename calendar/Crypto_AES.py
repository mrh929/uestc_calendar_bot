from Crypto.Util.Padding import pad
from Crypto.Cipher import AES
import base64

def __encrypt_AES(data, key, iv):#AES加密算法
    aes = AES.new(key, AES.MODE_CBC, iv)
    data = pad(data, AES.block_size, style='pkcs7')
    ret = base64.b64encode(aes.encrypt(data))
    return ret

def get_AES_cipher(passwd, key):
    ret = __encrypt_AES(b'a'*64 + passwd.encode('utf-8'), key.encode('utf-8'), b'a'*16).decode('utf-8')  #对密码进行加密
    return ret