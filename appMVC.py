# ===========================
# Example of MVC pattern on pure Python. Whiten for "Use Python in the Web"
# course. Institute Mathematics and Computer Science at Ural Federal University
# in 2014.
#
# By Pahaz Blinov.
# ===========================

__author__ = 'pahaz'

# ===========================
#
#        Utilities
#
# ===========================


from urlparse import parse_qs


def http_status(code):
    return "200 OK" if code == 200 else "404 Not Found"


def create_response_headers(sid=''):
    response_headers = [('Content-Type', 'text/html')]
    if sid:
        response_headers += [('Set-Cookie', 'sid=' + sid + '; path=/; expires=Thu, 1 Jan 2015 23:59:59 GMT')]
    return response_headers

# ===========================
#
#           Models
#
# ===========================

import shelve


class TextModel(object):
    DB_FILE = 'main.db'

    def __init__(self):
        self._db = shelve.open(self.DB_FILE)

    def get(self, name, default_value):
        return self._db.get(name, default_value)

    def all(self):
        return self._db.keys()

    def set(self, key, value):
        self._db[key] = value
        self._db.sync()

    def delete(self, key):
        del self._db[key]
        self._db.sync()


import time
import hashlib


class SessionModel(object):
    SESSION_DB = "sess.db"

    def __init__(self):
        self.db = shelve.open(self.SESSION_DB)

    def add(self):
        sid = hashlib.md5(str(time.time())).hexdigest()
        self.db[sid] = {
            "amount_of_viewed_pages": 0,
            "is_auth": 0
        }
        self.db.sync()
        return sid

    def get(self, sid, default_value=''):
        return self.db.get(sid, default_value)

    def set(self, sid, user_stat):
        self.db[sid] = user_stat
        self.db.sync()

    def delete(self, sid):
        del self.db[sid]
        self.db.sync()

# ===========================
#
#   Controller and Router
#
# ===========================


class Router(object):
    def __init__(self):
        self._paths = {}

    def route(self, environ, start_response):
        path = environ['PATH_INFO']
        query_dict = parse_qs(environ['QUERY_STRING'])

        if 'HTTP_COOKIE' in environ:
            cookie = parse_qs(environ['HTTP_COOKIE'])
            sid = cookie.get('sid')[0]
            if (not sess.get(sid)):
                sid = sess.add()
                response_headers = create_response_headers(sid)
            else:
                response_headers = create_response_headers()
        else:
            sid = sess.add()
            response_headers = create_response_headers(sid)

        if path in self._paths:
            if path == '/text' or path == '/text/login':
                res = self._paths[path](query_dict, sid)
            else:
                res = self._paths[path](query_dict)
        else:
            res = self.default_response(query_dict)
        return res + [response_headers]

    def register(self, path, callback):
        self._paths[path] = callback

    def default_response(self, *args):
        return [404, "Nooo 404!", create_response_headers()]


class TextController(object):

    @staticmethod
    def index(query_dict, sid):
        text = query_dict.get('id', [''])[0]
        text = model.get(text, '')
        titles = model.all()
        need_auth = 0
        user_stat = sess.get(sid)
        amount_of_viewed_pages = user_stat.get('amount_of_viewed_pages')

        if (amount_of_viewed_pages == 3) & (user_stat.get('is_auth') == 0):
            text = ''
            need_auth = 1
        elif (amount_of_viewed_pages < 3) & (text != ''):
            amount_of_viewed_pages += 1
            sess.set(sid, {
                'amount_of_viewed_pages': amount_of_viewed_pages,
                'is_auth': user_stat.get('is_auth')
            })
        context = {
            'titles': titles,
            'text': text,
            'auth': need_auth,
            'is_auth': user_stat.get('is_auth')
        }
        return [200, view_text.render(context)]

    @staticmethod
    def add(query_dict):
        key = query_dict.get('k', [''])[0]
        value = query_dict.get('v', [''])[0]
        model.set(key, value)
        context = {'url': "/text"}
        return [200, view_redirect.render(context)]

    @staticmethod
    def login(query_dict, sid):
        code = query_dict.get('code', [''])[0]
        user_stat = sess.get(sid)
        if code == "1234":
            user_stat['is_auth'] = 1
            sess.set(sid, user_stat)
        context = {'url': "/text"}
        return [200, view_redirect.render(context)]


# ===========================
#
#           View
#
# ===========================

class TextView(object):
    @staticmethod
    def render(context):
        t = ''
        if context['auth'] == 1:
            t = """
            <div style="color: red">Enter the code</div>
            <form method="GET" action="/text/login">
                <input type=password name=code />
                <input type=submit value=LogIn />
            </form>
            """
        else:
            if context['is_auth'] == 1:
                t = """
                Now you can read more articles!
                """
            t += """
            <form method="GET">
                <input type=text name=id />
                <input type=submit value=read />
            </form>
            """

        context['titles'] = [
            '<li>{0}</li>'.format(x) for x in context['titles']
        ]
        context['titles'] = '\n'.join(context['titles'])

        t += """
        <form method="GET" action="/text/add" >
            <input type=text name=k /> <input type=text name=v />
            <input type=submit value=write />
        </form>
        <div style="color: gray;">{text}</div>
        <ul>{titles}</ul>
        """
        return t.format(**context)


class RedirectView(object):
    @staticmethod
    def render(context):
        return '<meta http-equiv="refresh" content="0; url={url}" />' \
            .format(**context)


# ===========================
#
#          Main
#
# ===========================
sess = SessionModel()
rout = Router()
model = TextModel()
view_text = TextView()
view_redirect = RedirectView()
controller = TextController()

rout.register('/', lambda x: ([200, "Index HI!"]))
rout.register('/text', controller.index)
rout.register('/text/add', controller.add)
rout.register('/text/login', controller.login)

# ===========================
#
#          WSGI
#
# ===========================


def application(environ, start_response):
    http_status_code, response_body, response_headers = rout.route(environ, start_response)
    http_status_code_and_msg = http_status(http_status_code)
    start_response(http_status_code_and_msg, response_headers)
    return [response_body]
