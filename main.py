#!/usr/bin/python3
# coding:utf-8
import grequests
import requests
import hashlib
from crypto import Cipher_AES
import base64
import time
import datetime
import json
import os
from urllib3.exceptions import InsecureRequestWarning
from test_proxy import TestProxy

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


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
    return 'w%s%s%ss'%(today.month,today.day,today.hour)

url_prefix = 'https://%s.astarvpn.center/astarnew'%get_domain_prefix()

key = b64_decode(read_file('keyjs.txt'))

current_acc = read_file('login.id')


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
        url_prefix+'/user/userInfo?1618148703377',
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
        url_prefix+'/NewVPN/getProxy?%s' % time.time(),
        {'strP': 'jajilbjjinjmgcibalaakngmkilboobh', 'lid': i, 'strtoken': s, 'nonlinestate': '1', 'version': '109',
         'strlognid': current_acc}
    )


def get_proxy_list():
    j = post(
        url_prefix+'/NewVPN/getProxyList',
        {'strP': 'jajilbjjinjmgcibalaakngmkilboobh', 'nonlinestate': '1', 'version': '109',
         'strlognid': current_acc}
    ).json()
    return json.loads(decode_response(j)), j


def map_proxy_list():
    if is_expire(current_acc):
        print('免费时间过去了，正在注册新帐号...')
        reg = register()
        if reg is True:
            print('注册成功，使用新注册帐号[%s]重新获取代理' % read_file('login.id'))
            return map_proxy_list()
        print(reg)
        print('想个办法换个 ip 试试？')
        exit(2)
    print('正在获取可用代理列表', flush=True)
    l, j = get_proxy_list()
    l = [{'name': info['n'], 'i': info['i'], 'c': info['c']} for info in l['jsonObject']['d']]
    print('共获取到%s个测试点' % len(l), flush=True)
    # 非异步请求
    # for i in l:
    #     print('正在获取', i['name'], '代理', flush=True)
    #     r = get_proxy(j['s'], i['i'])
    #     if r:
    #         pl.append({'http_proxy': r, 'name': i['name']})

    return [
        get_proxy_result(r.json())
        for r in grequests.map(get_proxy(j['s'], i['i']) for i in l)
        if r and get_proxy_result(r.json())
    ]


def register():
    acc = '%s@qq.com' % time.time()
    print('正在注册：', acc)
    data = {
        'strP': 'jajilbjjinjmgcibalaakngmkilboobh',
        'strlognid': acc,
        'strpassword': acc,
        'strvcode': 'zz43',
        'clientUUID': '8d3c97bd-57e3-432e-837d-44696eec34662021310224038437'
    }

    r = post(url_prefix+'/user/register', data=data).json()
    if 'successful' in r['strText']:
        global current_acc
        current_acc = acc
        write_file('login.id', acc)
        return True
    return r['strText']


if __name__ == '__main__':
    print(decode_response(
    {"startIndex":11,"s":"e71a2be934d04b419ec401d3ae9161af",
    "d":"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","endIndex":27}))
    '''

    pl = map_proxy_list()
    plt = '\r\n'.join(pl)
    write_file('proxy.list', plt)
    print('已将获取到的%s个代理写入 proxy.list 当中.' % len(pl))
    print('开始筛选代理，你可以通过设置超时时间来作为筛选条件')
    TestProxy(pl,timeout=0.5)
    '''
