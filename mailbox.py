#!/usr/local/bin/python3
# coding:utf-8

from faker import Faker
import requests
import time


def get_suffix() -> str:
    return '@yzm.de'


class Mailbox(object):
    address: str = ''
    token: str = ''
    url: str = "https://mail.td"
    api_url = url + '/api/api/v1/mailbox/'
    faker = Faker()
    http = requests.Session()

    def __init__(self, get_new_mail: bool = False, default_handle: callable = None, username: str = ''):
        self.http.headers = {
            'authority': 'mail.td',
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
            'sec-ch-ua-mobile': '?0',
        }
        if default_handle:
            self.default_handle = default_handle
        if get_new_mail:
            self.get_new_mail_box(username)

    def faker_username(self) -> str:
        return self.faker.name().lower().replace(' ', '')

    def faker_mail_addr(self):
        return self.faker_username() + str(int(time.time())) + get_suffix()

    def delete_mail(self, mail_id: str) -> bool:
        return self.http.delete(f'{self.api_url}/{self.address}/{mail_id}').text == 'OK'

    def empty(self):
        for m in self.query_mails(None):
            print('删除邮件：', m['id'])
            self.delete_mail(m['id'])
        return self

    def get_new_mail_box(self, username: str = ''):
        self.address = username or self.faker_mail_addr()
        resp = self.http.get(self.url)
        if resp.status_code != 200:
            print('邮箱申请失败：', resp.text)
            return self
        print('邮箱申请成功：', self.address)
        self.token = resp.cookies.get('auth_token')
        self.http.headers['authorization'] = 'bearer ' + self.token
        return self

    def query_mails(self, seen=False) -> list:
        if not self.token:
            print('请先申请新邮箱！')
            return []
        resp = self.http.get(self.api_url + self.address)
        if resp.status_code != 200:
            print('查询新邮件失败：', resp.text)
            if 'expired' in resp.text:
                self.get_new_mail_box(self.address.split('@')[0])
            return []
        mails = resp.json()
        return seen is None and mails or [m for m in mails if m['seen'] == seen]

    def get_body(self, resp_item: dict):
        mid = resp_item.get('id', None)
        if not mid:
            return None
        resp = self.http.get(self.api_url + self.address + '/' + mid)
        if resp.status_code != 200:
            print('获取邮件内容失败：', resp.text)
            return None
        self.http.patch(self.api_url + self.address + '/' + mid, json={'seen': True})
        return resp.json()

    def default_handle(self, resp: dict) -> bool:
        if not resp: return False
        if not resp:
            return False
        print("%s - %s:\n\t%s\n\t%s\n\n" % (
            resp['from'], resp['date'], resp['subject'], resp['body']['html']))
        return True

    def forever(self, new_mail_handle: callable = None, interval: float = 2, clear=True):
        if not self.token:
            print('请先申请新邮箱！')
            return
        # 有新邮件时候的处理方式
        new_mail_handle = new_mail_handle or self.default_handle
        # 最小查询新邮件间隔
        if 0.5 > interval: interval = 0.5
        print('等待接收', self.address, '的新邮件中..')
        while True:
            new_mail_list = self.query_mails()
            new_mail_count = len(new_mail_list)
            if new_mail_count > 0:
                print('有 %d 封未读邮件' % new_mail_count)
                for resp_item in new_mail_list:
                    keep = new_mail_handle(self.get_body(resp_item))
                    if not keep:
                        if clear:
                            self.empty()
                        return
            time.sleep(interval)


def handle(r):
    print(r['body']['text'])
    return False


if __name__ == '__main__':
    Mailbox(True, username='tester'+get_suffix()).forever()
