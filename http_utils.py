import time
import httpx
import asyncio
from functools import reduce

default_proxy = ''


def get(url, **args) -> httpx.Response:
    return request(lambda http: http.get(url), **args)


def async_get(urls: list, response_handle: callable = None, need_handle=True, **args) -> list:
    urls = isinstance(urls, str) and [urls] or urls
    return async_request(lambda http: [http.get(url) for url in urls], response_handle, need_handle, **args)


def request(request_handle: callable, **client_config) -> httpx.Response:
    request_handle = request_handle or (lambda r: r)
    with httpx.Client(**client_config) as http:
        return request_handle(http)


def get_async_result(async_handle: callable):
    loop = asyncio.get_event_loop()
    t = loop.create_task(async_handle())
    loop.run_until_complete(t)
    return t.result()


def async_request(request_handle: callable, response_handle: callable = None, need_handle=True, **client_config):
    '''
    异步发送请求
    :param request_handle:(http) 可以返回多个 http请求
    :param response_handle:(response) 处理请求结果
    :param need_handle: True 会调用 response_handle
                        False 将只发送请求，不对结果进行任何处理
    :return: need_handle == False 返回 None
             response_handle == callable 返回处理结果
             response_handle == None : 返回请求结果
    '''
    if not callable(request_handle): return None
    is_single_request: list = []
    create_task = getattr(asyncio, 'create_task', asyncio.ensure_future)
    
    async def __request():
        # http = globals()['async_http_client']
        async with httpx.AsyncClient(**client_config) as http:
            # 传递 http 客户端给调用者，调用方返回一个或者多个异步请求对象
            req_list = request_handle(http)
            if not isinstance(req_list, (list, tuple, iter)):
                is_single_request.append(0)
                req_list = (req_list,)
            return iter(await asyncio.gather(*[create_task(req) for req in req_list]))
    
    # 不需要处理时候等待请求执行完毕后不做任何操作
    if not need_handle: return asyncio.run(__request())
    responses = get_async_result(__request)
    # response_handle 可调用时返回处理结果，否则返回请求结果
    responses = callable(response_handle) and (response_handle(rsp) for rsp in responses) or responses
    # 根据请求数量优化返回类型，多个请求时将返回结果，生成器类型。单个直接返回结果
    return is_single_request and next(responses) or responses


class Method(object):
    this = None
    
    def __init__(self, name=None, *arg, **args):
        self.attrs = dict(name=name, args=arg, kwargs=args)
    
    def info(self):
        return self.attrs
    
    def bind(self, this: object = None):
        self.this = this
        if hasattr(this, self.attrs['name']):
            func = getattr(self.this, self.attrs['name'])
            asyncio.iscoroutine(func)
            #  执行协程
            return asyncio.iscoroutinefunction(func) and func(*self.attrs['args'], **self.attrs['kwargs']) or func
        return self


class ClassMethodParser(object):
    __parse_list__ = []
    __caller__ = None
    
    def __init__(self, caller=None):
        self.__caller__ = caller
    
    def __getattr__(self, name):
        protected = {'__caller__': self.__caller__, '__parse_list__': self.__parse_list__}
        
        def injector(*arg, **args):
            m = Method(name, *arg, **args)
            self.__parse_list__.append(m)
            return self.this and m.bind(self.this) or m.bind
        
        return name in protected and protected[name] or injector
    
    def __len__(self):
        return len(self.__parse_list__)
    
    def __delitem__(self, key):
        return self.__parse_list__.pop(key)
    
    def __getitem__(self, index):
        return self.__parse_list__[index]


class Proxy(object):
    proxy_server: str = ''
    debug: bool = False
    
    def __init__(self, proxy_server: str = default_proxy, debug=False):
        self.proxy_server = proxy_server
        self.debug = debug
    
    def log(self, *arg, **args):
        if self.debug:
            print(*arg, **args)
        return self
    
    def set_proxy_server(self, proxy_server: str = ''):
        self.proxy_server = proxy_server
        return self
    
    def request(self, route: str = ''):
        return get(self.proxy_server + route, verify=False, timeout=3)
    
    def delete(self, proxy_ip: str = ''):
        self.request(f'/delete/?proxy={proxy_ip}')
        return self
    
    def pop(self, proxy_type='http'):
        return self.request(f'/pop/?type={proxy_type}').json()
    
    def get(self, proxy_type='http'):
        return self.request(f'/get/?type={proxy_type}').json().get('proxy', '')
    
    def get_and_test(self, url: str = 'https://baidu.com', num: int = 3, timeout=1):
        proxy_list, proxy_type = [], f'http{["", "s"][url[5] == "s"]}'
        while num > 0:
            proxy_ip = self.get(proxy_type)
            if not proxy_ip:
                print('代理池准备中', proxy_ip)
                time.sleep(3)
            try:
                self.log('获取到代理 ip：', proxy_ip, proxy_type)
                self.log(f'使用{url}来测试代理')
                get(url, proxies=f'{proxy_type}://{proxy_ip}', timeout=timeout, verify=False)
                num -= 1
                proxy_list.append(f'{proxy_type}://{proxy_ip}')
            except Exception as e:
                self.log(f'代理 {proxy_ip} 出错：{e}')
                self.delete(proxy_ip)
        self.log('获取代理完成：', proxy_list)
        return proxy_list


proxy = Proxy(debug=True)


def proxy_get(url, **args) -> httpx.Response:
    pl = proxy.get_and_test(url, num=1)
    return request(lambda http: http.get(url), proxies=pl.pop(), **args)


def proxy_post(url, **args) -> httpx.Response:
    pl = proxy.get_and_test(url, num=1)
    return request(lambda http: http.post(url, **args), proxies=pl.pop())


def proxy_async_get(urls: list, response_handle: callable = None,
                    need_handle=True,
                    request_chunk_number: int = 30,
                    proxy_pool_server: str = default_proxy,
                    **client_config) -> list:
    urls = isinstance(urls, str) and [urls] or urls
    return proxy_async_request(
        lambda http: [http.get(url) for url in urls],
        response_handle, need_handle, request_chunk_number, proxy_pool_server, **client_config
    )


def chunks(l, n):
    return (l[i:i + n] for i in range(0, len(l), n))


def proxy_async_request(request_handle: callable,
                        response_handle: callable = None,
                        need_handle=True,
                        request_chunk_number: int = 30,
                        proxy_pool_server: str = default_proxy,
                        **client_config):
    # 指定代理池地址
    if proxy_pool_server:
        proxy.set_proxy_server(proxy_pool_server)
    cmp = ClassMethodParser()
    request_chunk = chunks(request_handle(cmp), request_chunk_number)
    print(f'本次请求总数：{len(cmp)},分块个数{request_chunk_number}')
    
    def re_wrap(reqs):
        return lambda http: isinstance(reqs, Method) and reqs.bind(http) or [req.bind(http) for req in reqs]
    
    test_url = cmp[0].attrs.get('args')[0]
    pl = proxy.get_and_test(test_url, num=len(cmp))
    print('本次访问使用代理：', pl)
    return reduce(lambda a, b: [*a, *b], (
        async_request(re_wrap(chunk), response_handle, need_handle=need_handle, proxies=pl.pop(), **client_config)
        for chunk in request_chunk
    ), [])


if __name__ == '__main__':
    r = proxy_async_request(
        lambda http: (http.get('http://baidu.com', timeout=3), http.get('http://qq.com', timeout=4),),
        request_chunk_number=1)
    for e in r:
        print(e.status_code)
