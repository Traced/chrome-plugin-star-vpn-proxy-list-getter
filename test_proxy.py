#!/usr/local/bin/python3
# coding:utf-8

import requests
import telnetlib
import socket


class TestProxy(object):
    default_test_url = 'https://youtube.com'
    test_url = 'https://youtube.com'
    test_timeout = 3
    default_test_method = 'telnet'
    test_method = 'telnet'

    def __init__(self, proxys=[], method: str = 'telnet', start_test=True, timeout: float = 3, test_url: str = ''):
        self.set_test_url(test_url)
        self.set_test_timeout(timeout)
        self.set_test_method(method)
        if start_test:
            self.test(*proxys)

    def test(self, *proxys):
        ok_list = []
        print('test proxy method:', self.test_method)
        print('test proxy timeout:', self.test_timeout, 'seconds')
        if self.test_method == 'url':
            print('test proxy url:', self.test_url)
        print('test starting.')
        print('=' * 30)
        for proxy in proxys:
            proxy = proxy.strip()
            is_ok = getattr(self, self.test_method)(*proxy.split(':'))
            if is_ok:
                print(proxy)
                ok_list.append(proxy)
        print('=' * 30)
        print('test done.')
        return ok_list

    def set_test_method(self, method='url'):
        if not hasattr(self, self.test_method):
            print('Unsupported test method ', self.test_method, ', using default method:', self.default_test_method)
            method = self.default_test_method
        self.test_method = method
        return self

    def set_test_url(self, url=''):
        self.test_url = url or self.default_test_url
        return self

    def set_test_timeout(self, timeout=3):
        self.test_timeout = timeout or 3
        return self

    def telnet(self, url, port) -> bool:
        try:
            telnetlib.Telnet(url, port=port, timeout=self.test_timeout)
        except:
            return False
        return True

    def telnet_test(self, *urls):
        return [
            url
            for url in map(lambda u: u.split(':'))
            if self.telnet(url[0], url[1])
        ]

    def url(self, url, port) -> bool:
        _url = "%s:%s" % (url, port)
        config = {"http": 'https://%s' % _url, 'https': 'https://%s' % _url}
        try:
            requests.get(self.test_url, timeout=self.test_timeout, proxies=config)
        except Exception as e:
            return False
        return True

    def url_test(self, *urls):
        return [url for url in urls if self.url(url)]


if __name__ == '__main__':
    pl = open('proxy.list').readlines()
    tp = TestProxy(pl, timeout=0.5)
