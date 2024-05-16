#!/usr/bin python3
# @File    : rsa_util.py
# @Time    : 2021-08-17 19:21:54
# @Author  : Kelvin.Ye
import base64

from Crypto.Cipher import PKCS1_v1_5  # RSA/ECB/PKCS1Padding
from Crypto.PublicKey import RSA


def encrypt_by_public_key(plaintext: str, public_key: str | bytes) -> str:
    """
    通过RSA公钥加密

    :param plaintext:   加密内容
    :param public_key:  RSA公钥

    :return:            密文
    """
    rsakey = RSA.importKey(public_key)
    cipher = PKCS1_v1_5.new(rsakey)
    return base64.b64encode(cipher.encrypt(plaintext.encode())).decode()


def decrypt_by_private_key(ciphertext, private_key):
    """
    通过RSA私钥解密

    :param ciphertext:  密文
    :param private_key: RSA私钥

    :return:            明文
    """
    rsakey = RSA.importKey(private_key)
    cipher = PKCS1_v1_5.new(rsakey)
    plaintext = cipher.decrypt(base64.b64decode(ciphertext), None)
    return plaintext.decode()
