#!/usr/local/bin/python3
# coding:utf-8
import grequests
import requests
import urllib3
import hashlib
from crypto import Cipher_AES
import base64
import time
import datetime
import json
import os
import re
from test_proxy import TestProxy
from mailbox import Mailbox
from http_utils import proxy_post, default_proxy

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings()
urllib3.disable_warnings()


def b64_decode(s):
    return base64.b64decode(s).decode()


def md5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def read_file(pf):
    return os.path.isfile(pf) and open(pf).read() or ''


def write_file(fn, c):
    open(fn, 'w').write(c)


headers = {
    'Connection': 'keep-alive',
    'sec-ch-ua': '"Google Chrome";v="91", "Chromium";v="91", ";Not A Brand";v="99"',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'DNT': '1',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': 'chrome-extension://jajilbjjinjmgcibalaakngmkilboobh',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
}


def get_domain_prefix():
    today = datetime.datetime.now()
    return 'w%s%s%ss' % (today.month, today.day, today.hour)


url_prefix = 'https://%s.clickext.com/astarnew' % get_domain_prefix()

key = b64_decode(read_file('keyjs.txt'))

current_acc = read_file('login.id')

plugin_version_info = {
    'strP': 'jajilbjjinjmgcibalaakngmkilboobh',
    'nonlinestate': '1',
    'version': '111'
}


def decode_response(r):
    return Cipher_AES(
        md5(r['s'] + key)[r['startIndex']:r['endIndex']], r['d']
    ).decrypt(r['d'], 'MODE_ECB', "PKCS5Padding", "base64")


def post(url, data):
    cookies = {
        'JSESSIONID': '9AAD4A3329938A4C6545662F5368C463',
        'token': 'af0c24670c97dd78584b47a1a7d6f087',
        'strLoginId': current_acc,
    }
    return requests.post(url, timeout=5, headers=headers, cookies=cookies, data=data, verify=False)


def gpost(url, data):
    cookies = {
        'JSESSIONID': '9AAD4A3329938A4C6545662F5368C463',
        'token': 'af0c24670c97dd78584b47a1a7d6f087',
        'strLoginId': current_acc,
    }
    return grequests.post(url, timeout=5, headers=headers, cookies=cookies, data=data, verify=False)


def get(url):
    cookies = {
        'JSESSIONID': '9AAD4A3329938A4C6545662F5368C463',
        'token': 'af0c24670c97dd78584b47a1a7d6f087',
        'strLoginId': current_acc,
    }
    return requests.get(url, headers=headers, cookies=cookies)


def is_expire(uid):
    print('正在检测帐号%s是否在体验时间段内' % uid)
    t = post(
        url_prefix + '/user/userInfo?1618148703377',
        {'strP': 'jajilbjjinjmgcibalaakngmkilboobh', 'strlognid': uid}
    ).json()
    if t['nCode'] > 0:
        print(t['strText'])
        return True
    t = t['jsonObject']['nCurrValidTime']
    print('免费时长剩余：', t)
    return t == '0'


def get_proxy_result(rsp):
    p = json.loads(decode_response(rsp))
    if p['strText'] == 'succ':
        p['jsonObject']['s'] = p['jsonObject']['_p']
        p['jsonObject']['d'] = p['jsonObject']['_s']
        return decode_response(p['jsonObject']).split('\'HTTPS ')[1].strip()[:-3]
    return None


def get_proxy(s, i) -> dict:
    return gpost(
        url_prefix + '/NewVPN/getProxy?%s' % time.time(),
        {'lid': i, 'strtoken': s, 'strlognid': current_acc, **plugin_version_info}
    )


def get_proxy_list():
    j = post(
        url_prefix + '/NewVPN/getProxyList',
        {**plugin_version_info, 'strlognid': current_acc}
    ).json()

    return json.loads(decode_response(j)), j


def map_proxy_list():
    print('正在获取可用代理列表', flush=True)
    l, j = get_proxy_list()
    l = [{'name': info['n'], 'i': info['i'], 'c': info['c']} for info in l['jsonObject']['d']]
    print('共获取到%s个测试点' % len(l), flush=True)
    return [
        get_proxy_result(r.json())
        for r in grequests.map(get_proxy(j['s'], i['i']) for i in l)
        if r and get_proxy_result(r.json())
    ]


def register(mail_addr):
    acc = mail_addr
    print('正在注册：', acc)
    data = {
        **plugin_version_info,
        'strlognid': acc,
        'strpassword': acc,
        'strvcode': '123456',
        'clientUUID': '8d3c97bd-57e3-432e-837d-44696eec34662021310224038437'
    }
    request_method = default_proxy and proxy_post or post
    r = request_method(url_prefix + '/user/register?%s'%time.time(), data=data).json()
    if 'successful' in r['strText']:
        global current_acc
        current_acc = acc
        write_file('login.id', acc)
        print('注册成功')
        return True
    print(r['strText'])
    return r['strText']


def active_account(active_resp):
    active_url = re.findall(r'(http.+) ', active_resp['body']['text'])
    if active_url:
        requests.get(active_url[0])
        return False
    return True


if __name__ == '__main__':
    mail = Mailbox(True, active_account)
    register(mail.address)
    mail.forever(active_account)
    pl = map_proxy_list()
    plt = '\r\n'.join(pl)
    write_file('proxy.list', plt)
    print('已将获取到的%s个代理写入 proxy.list 当中.' % len(pl))
    print('开始筛选代理，你可以通过设置超时时间来作为筛选条件')
    TestProxy(pl, timeout=1)
