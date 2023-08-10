# coding:utf-8
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


def get_domain_prefix():
    today = datetime.datetime.now()
    return 'w%s%s%ss' % (today.month, today.day, today.hour)


key = b64_decode(read_file('keyjs.txt'))


def decode_response(r):
    return Cipher_AES(
        md5(r['s'] + key)[r['startIndex']:r['endIndex']], r['d']
    ).decrypt(r['d'], 'MODE_ECB', "PKCS5Padding", "base64")


def get_proxy_result(rsp):
    p = json.loads(decode_response(rsp))
    if p['strText'] == 'succ':
        p['jsonObject']['s'] = p['jsonObject']['_p']
        p['jsonObject']['d'] = p['jsonObject']['_s']
        return decode_response(p['jsonObject']).split('\'HTTPS ')[1].strip()[:-3]
    return None


plugin_version_info = {
    'strP': 'jajilbjjinjmgcibalaakngmkilboobh',
    'nonlinestate': '1',
    'version': '114'
}


def active_account(active_resp):
    active_url = re.findall(r'(http.+) ', active_resp['body']['text'])
    if active_url:
        requests.get(active_url[0])
        return False
    return True


class Astar(object):
    current_username: str = ''
    
    http = requests.Session()
    http.headers = {
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
    
    url_prefix = 'https://%s.iosedge.com/astarnew' % get_domain_prefix()
    
    mb = Mailbox(True, active_account)
    
    def __init__(self, proxy_addr: str = ''):
        self.http.proxies = proxy_addr and \
                            {"http": proxy_addr, "https": proxy_addr} or None
    
    def post(self, *arg, **kwarg):
        return self.http.post(*arg, **kwarg, timeout=10)
    
    def get(self, *arg, **kwarg):
        return self.http.get(*arg, **kwarg)
    
    def is_expire(self, username: str) -> bool:
        """
        账号vip体验期是否已过
        :param username:
        :return:
        """
        print('正在检测帐号%s是否在体验时间段内' % username)
        t = self.post(
            self.url_prefix + '/user/userInfo?1618148703377',
            {**plugin_version_info, 'strlognid': username}
        ).json()
        if t['nCode'] > 0:
            print(t['strText'])
            return True
        t = t['jsonObject']['nCurrValidTime']
        print('免费时长剩余：', t)
        return t == '0'
    
    def get_proxy(self, s, i):
        return self.post(
            self.url_prefix + '/NewVPN/getProxy',
            {'lid': i, 'strtoken': s, 'strlognid': self.current_username, **plugin_version_info}
        )
    
    def get_proxy_list(self):
        j = self.post(
            self.url_prefix + '/NewVPN/getProxyList',
            {**plugin_version_info, 'strlognid': self.current_username}
        ).json()
        
        return json.loads(decode_response(j)), j
    
    def get_proxy_nodes(self) -> list:
        print('正在获取可用代理列表', flush=True)
        l, j = self.get_proxy_list()
        l = [
            {'name': info['n'], 'i': info['i'], 'c': info['c']}
            for info in l['jsonObject']['d']
        ]
        print('共获取到%s个测试点' % len(l), flush=True)
        result = []
        for i in l:
            r = self.get_proxy(j['s'], i['i'])
            if r.status_code == 200:
                r = get_proxy_result(r.json())
                if r:
                    result.append(r)
        return result
    
    def save(self, filepath: str = 'proxy.list.txt'):
        nodes = self.get_proxy_nodes()
        write_file(filepath, '\r\n'.join(nodes))
        print('已将获取到的%s个代理写入 proxy.list 当中.' % len(nodes))
        print('开始筛选代理，你可以通过设置超时时间来作为筛选条件')
        TestProxy(nodes, timeout=1)
    
    def register(self, mail_addr: str = '', password: str = '123456bb'):
        mail_addr = mail_addr or self.mb.address
        print('正在注册：', mail_addr)
        data = {
            **plugin_version_info,
            'strlognid': mail_addr,
            'strpassword': password,
            'strvcode': '123456',
            'clientUUID': '8d3c97bd-57e3-432e-837d-44696eec34662091310224038437'
        }
        r = self.post(self.url_prefix + '/user/register?%s' % time.time(), data=data)
        if r.status_code != 200:
            print(r.text)
            return False
        r = r.json()
        if 'successful' in r['strText']:
            self.current_username = mail_addr
            write_file('login.id', self.current_username)
            print('注册成功，激活中')
            self.mb.forever(active_account)
            cks = {
                'JSESSIONID': '9AAD4A3329938A4C6545662F5368C463',
                'token': 'af0c24670c97dd78584b47a1a7d6f087',
                'strLoginId': mail_addr,
            }
            for k in cks:
                self.http.cookies.setdefault(k, cks[k])
            return True
        print(r['strText'])
        return r['strText']


if __name__ == '__main__':
    a = Astar('socks5://127.0.0.1:2021')
    if a.register():
        a.save()
