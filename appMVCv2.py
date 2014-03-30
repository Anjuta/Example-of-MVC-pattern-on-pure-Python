# ===========================
# Example of MVC pattern on pure Python. Whiten for "Use Python in the Web"
# course. Institute Mathematics and Computer Science at Ural Federal University
# in 2014.
#
# By Pahaz Blinov.
# ===========================

__author__ = "pahaz"

DB_FILE = "main.db"
SESSION_DB = "sess.db"
DEBUG = False

# ===========================
#
#        Utilities
#
# ===========================

from urlparse import parse_qs
import shelve


def http_status(code):
    return "200 OK" if code == 200 else "404 Not Found"


def parse_http_post_data(environ):
    try:
        request_body_size = int(environ.get("CONTENT_LENGTH", 0))
    except ValueError:
        request_body_size = 0

    request_body = environ["wsgi.input"].read(request_body_size)
    body_query_dict = parse_qs(request_body)

    return body_query_dict


def parse_http_get_data(environ):
    return parse_qs(environ["QUERY_STRING"])


def get_client_session(environ):
    sid = ''
    if 'HTTP_COOKIE' in environ:
        cookie = parse_qs(environ['HTTP_COOKIE'])
        sid = cookie.get('sid')[0]
    return Session(sid)


def create_response_headers(session):
    response_headers = [('Content-Type', 'text/html')]
    if session.is_new():
        response_headers += [('Set-Cookie', 'sid=' + session.get_sid() + '; path=/; expires=Thu, 1 Jan 2015 23:59:59 GMT')]
        session.change_is_new()
    return response_headers


def take_one_or_None(dict_, key):
    val = dict_.get(key)
    if type(val) in (list, tuple) and len(val) > 0:
        val = val[0]
    return val


# ===========================
#
#         1. Model
#
# ===========================


class TextModel(object):
    def __init__(self, title, content):
        self.title = title
        self.content = content


class TextManager(object):
    def __init__(self):
        self._db = shelve.open(DB_FILE)

    def get_by_title(self, title):
        content = self._db.get(title)
        return TextModel(title, content) if content else None

    def get_all(self):
        return [
            TextModel(title, content) for title, content in self._db.items()
        ]

    def create(self, title, content):
        if title in self._db:
            return False

        self._db[title] = content
        self._db.sync()
        return True

    def delete(self, title):
        if title not in self._db:
            return False

        del self._db[title]
        self._db.sync()
        return True

import time
import hashlib


class Session(object):
    def __init__(self, sid):
        if (sid != '') & (session_storage.get(sid) != None):
            self.sid = sid
            self.user_stat = session_storage.get(sid)
        else:
            self.sid = hashlib.md5(str(time.time())).hexdigest()
            self.user_stat = {
                'amount_of_viewed_pages': 0,
                'is_new': True,
                'is_auth': False
            }

    def get_sid(self):
        return self.sid

    def get_amount_of_viewed_pages(self):
        return self.user_stat['amount_of_viewed_pages']

    def inc_amount_of_viewed_pages(self):
        self.user_stat['amount_of_viewed_pages'] += 1
        session_storage.set(self.sid, self.user_stat)

    def is_auth(self):
        return self.user_stat['is_auth']

    def is_new(self):
        return self.user_stat['is_new']

    def change_is_new(self):
        self.user_stat['is_new'] = not self.user_stat['is_new']
        session_storage.set(self.sid, self.user_stat)

    def change_is_auth(self):
        self.user_stat['is_auth'] = not self.user_stat['is_auth']
        session_storage.set(self.sid, self.user_stat)


class SessionStorage(object):

    def __init__(self):
        self.db = shelve.open(SESSION_DB)

    def get(self, sid):
        return self.db.get(sid)

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

    def route(self, request_path, request_get_data, session):

        if request_path in self._paths:
            res = self._paths[request_path](request_get_data, session)
        else:
            res = self.default_response(request_get_data)

        return res

    def register(self, path, callback):
        self._paths[path] = callback

    def default_response(self, *args):
        return 404, "Nooo 404!"


class TextController(object):
    def __init__(self, index_view, add_view, manager):
        self.index_view = index_view
        self.add_view = add_view
        self.model_manager = manager

    def index(self, request_get_data, session):
        need_auth = False
        current_text = ''
        if (not session.is_auth()) & (session.get_amount_of_viewed_pages() == 3):
            need_auth = True
        else:
            title = take_one_or_None(request_get_data, "title")
            current_text = self.model_manager.get_by_title(title)
            if (current_text != None):
                session.inc_amount_of_viewed_pages()
        all_texts = self.model_manager.get_all()

        context = {
            "all": all_texts,
            "current": current_text,
            'need_auth': need_auth
        }

        return 200, self.index_view.render(context)

    def add(self, request_get_data, session):
        title = take_one_or_None(request_get_data, 'title')
        content = take_one_or_None(request_get_data, 'content')

        if not title or not content:
            error = "Need fill the form fields."
        else:
            error = None
            is_created = self.model_manager.create(title, content)
            if not is_created:
                error = "Title already exist."

        context = {
            'title': title,
            'content': content,
            'error': error,
        }
        return 200, self.add_view.render(context)

    @staticmethod
    def login(query_dict, session):
        code = query_dict.get('code', [''])[0]
        if code == "1234":
            session.change_is_auth()
        context = {'url': "/text"}
        return 200, redirect_view.render(context)

    def start(self, query_dict, session):
        return 200, 'Index HI!'


# ===========================
#
#           View
#
# ===========================

class TextIndexView(object):
    @staticmethod
    def render(context):
        context["titles"] = "\n".join([
            "<li>{text.title}</li>".format(text=text) for text in context["all"]
        ])

        if context["current"]:
            context["content"] = """
            <h1>{current.title}</h1>
            {current.content}
            """.format(current=context["current"])
        else:
            context["content"] = 'What do you want read?'
        if context['need_auth']:
            t = """
            <div style="color: red">Enter the code</div>
            <form method="GET" action="/text/login">
                <input type=password name=code />
                <input type=submit value=LogIn />
            </form>
            """
        else:
            t = """
            <form method="GET">
                <input type=text name=title placeholder="Text title" />
                <input type=submit value=read />
            </form>
            """
        t += """
        <form method="GET" action="/text/add">
            <input type=text name=title placeholder="Text title" /> <br>
            <textarea name=content placeholder="Text content!" ></textarea> <br>
            <input type=submit value=write/rewrite />
        </form>
        <div>{content}</div>
        <ul>{titles}</ul>
        """
        return t.format(**context)


class RedirectView(object):
    @staticmethod
    def render(context):
        return '<meta http-equiv="refresh" content="0; url=/text" />'


# ===========================
#
#          Main
#
# ===========================

text_manager = TextManager()
redirect_view = RedirectView()
controller = TextController(TextIndexView, RedirectView, text_manager)
session_storage = SessionStorage()
router = Router()
router.register("/", controller.start)
router.register("/text", controller.index)
router.register("/text/add", controller.add)
router.register('/text/login', controller.login)


# ===========================
#
#          WSGI
#
# ===========================

def application(environ, start_response):
    request_path = environ["PATH_INFO"]
    request_get_data = parse_http_get_data(environ)
    session = get_client_session(environ)

    # TODO: You can add this interesting line
    # print(parse_http_post_data(environ))

    http_status_code, response_body = router.route(request_path, request_get_data, session)

    if DEBUG:
        response_body += "<br><br> The request ENV: {0}".format(repr(environ))

    response_status = http_status(http_status_code)
    response_headers = create_response_headers(session)

    start_response(response_status, response_headers)
    return [response_body]  # it could be any iterable.


# if run as script do tests.
if __name__ == "__main__":
    import doctest
    doctest.testmod()