from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import os
import json
import html
import hashlib
import uuid
import mimetypes

PORT = int(os.environ.get("PORT", "8000"))

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
UPLOADS = os.path.join(BASE, "uploads")

os.makedirs(DATA, exist_ok=True)
os.makedirs(UPLOADS, exist_ok=True)

FILES = {
    "users": os.path.join(DATA, "users.json"),
    "posts": os.path.join(DATA, "posts.json"),
    "comments": os.path.join(DATA, "comments.json"),
    "follows": os.path.join(DATA, "follows.json"),
    "messages": os.path.join(DATA, "messages.json"),
    "sessions": os.path.join(DATA, "sessions.json"),
    "warnings": os.path.join(DATA, "warnings.json"),
    "settings": os.path.join(DATA, "settings.json"),
}

DEFAULTS = {
    "users": {},
    "posts": [],
    "comments": [],
    "follows": [],
    "messages": [],
    "sessions": {},
    "warnings": [],
    "settings": {},
}


def load(name):
    path = FILES[name]

    if not os.path.exists(path):
        save(name, DEFAULTS[name])
        return DEFAULTS[name]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = DEFAULTS[name]

    return data


def save(name, data):
    with open(FILES[name], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def make_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def esc(text):
    return html.escape(str(text))


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_cookie(headers, name):
    cookie = headers.get("Cookie", "")

    for item in cookie.split(";"):
        item = item.strip()

        if item.startswith(name + "="):
            return item.split("=", 1)[1]

    return None


def make_session(username):
    sessions = load("sessions")

    token = uuid.uuid4().hex

    sessions[token] = {
        "username": username,
        "created": now(),
    }

    save("sessions", sessions)

    return token


class WebServer(BaseHTTPRequestHandler):

    def send_html(self, content, status=200, cookies=None):
        body = content.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))

        if cookies:
            for cookie in cookies:
                self.send_header("Set-Cookie", cookie)

        self.end_headers()
        self.wfile.write(body)

    def redirect(self, path, cookies=None):
        self.send_response(303)
        self.send_header("Location", path)

        if cookies:
            for cookie in cookies:
                self.send_header("Set-Cookie", cookie)

        self.end_headers()

    def read_post(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length).decode("utf-8")

        return parse_qs(data)

    def current_user(self):
        token = get_cookie(self.headers, "session")

        if not token:
            return None

        sessions = load("sessions")
        session = sessions.get(token)

        if not session:
            return None

        return session.get("username")

    def page(self, title, body):
        user = self.current_user()

        if user:
            nav = f"""
            <nav>
                <a href="/">🏠 ホーム</a>
                <a href="/channel">👤 マイチャンネル</a>
                <a href="/mail">💬 メール</a>
                <a href="/search">🔍 検索</a>
                <a href="/logout">ログアウト</a>
            </nav>
            """
        else:
            nav = """
            <nav>
                <a href="/">🏠 ホーム</a>
                <a href="/login">ログイン</a>
                <a href="/register">新規登録</a>
            </nav>
            """

        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>

<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue",
                 "Hiragino Kaku Gothic ProN", Meiryo, sans-serif;
    background: #f5f5f5;
    color: #222;
}}

header {{
    background: white;
    border-bottom: 1px solid #ddd;
    padding: 15px;
    position: sticky;
    top: 0;
    z-index: 10;
}}

header h1 {{
    margin: 0 0 10px 0;
    font-size: 22px;
}}

nav {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}}

nav a {{
    text-decoration: none;
    color: #222;
    background: #eee;
    padding: 9px 13px;
    border-radius: 10px;
}}

main {{
    max-width: 900px;
    margin: 20px auto;
    padding: 0 15px 100px;
}}

.card {{
    background: white;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
}}

input, textarea, button, select {{
    font: inherit;
}}

input, textarea, select {{
    width: 100%;
    padding: 11px;
    border: 1px solid #ccc;
    border-radius: 9px;
    margin: 6px 0 12px;
}}

textarea {{
    min-height: 120px;
    resize: vertical;
}}

button {{
    border: 0;
    border-radius: 9px;
    padding: 10px 15px;
    background: #222;
    color: white;
    cursor: pointer;
}}

button:hover {{
    opacity: .85;
}}

.post {{
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.7;
}}

.small {{
    color: #777;
    font-size: 13px;
}}

.error {{
    color: #c00;
}}

.success {{
    color: #087f23;
}}

.stat {{
    display: inline-block;
    background: #eee;
    padding: 8px 12px;
    border-radius: 10px;
    margin: 3px;
}}

.bottom {{
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    background: white;
    border-top: 1px solid #ddd;
    display: flex;
    justify-content: space-around;
    padding: 9px;
}}

.bottom a {{
    text-decoration: none;
    color: #222;
    font-size: 13px;
}}

@media (max-width: 600px) {{
    main {{
        padding-bottom: 80px;
    }}
}}
</style>
</head>

<body>

<header>
<h1>ウェブサーバー</h1>
{nav}
</header>

<main>
{body}
</main>

<div class="bottom">
<a href="/">🏠<br>ホーム</a>
<a href="/channel">👤<br>マイチャンネル</a>
<a href="/mail">💬<br>メール</a>
<a href="/search">🔍<br>検索</a>
</div>

</body>
</html>
"""

    def do_GET(self):
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)

        if path == "/":
            self.home()
        elif path == "/register":
            self.register_page()
        elif path == "/login":
            self.login_page()
        elif path == "/logout":
            self.logout()
        elif path == "/channel":
            self.channel()
        elif path == "/mail":
            self.mail()
        elif path == "/search":
            self.search(query)
        elif path == "/chat":
            self.chat(query)
        elif path.startswith("/uploads/"):
            self.file()
        else:
            self.send_html(
                self.page("404", "<div class='card'><h2>ページがありません</h2></div>"),
                404
            )

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.read_post()

        if path == "/register":
            self.register(data)

        elif path == "/login":
            self.login(data)

        elif path == "/post":
            self.create_post(data)

        elif path == "/like":
            self.like(data)

        elif path == "/dislike":
            self.dislike(data)

        elif path == "/comment":
            self.comment(data)

        elif path == "/follow":
            self.follow(data)

        elif path == "/message":
            self.message(data)

        else:
            self.redirect("/")

    def home(self):
        posts = load("posts")
        users = load("users")

        posts = list(reversed(posts))

        body = ""

        user = self.current_user()

        if user:
            body += """
            <div class="card">
                <h2>投稿する</h2>
                <form method="post" action="/post">
                    <textarea name="text" placeholder="今なにしてる？"></textarea>
                    <button>投稿</button>
                </form>
            </div>
            """
        else:
            body += """
            <div class="card">
                <h2>ようこそ！</h2>
                <p>投稿を見るにはログインしてください。</p>
            </div>
            """

        if not posts:
            body += """
            <div class="card">
                <p>まだ投稿がありません。</p>
            </div>
            """

        for post in posts:
            author = post.get("author", "")
            author_data = users.get(author, {})

            likes = post.get("likes", [])
            dislikes = post.get("dislikes", [])

            body += f"""
            <div class="card">

                <h3>
                    {esc(author_data.get("icon", "👤"))}
                    {esc(author)}
                </h3>

                <div class="small">
                    {esc(post.get("time", ""))}
                </div>

                <div class="post">
                    {esc(post.get("text", ""))}
                </div>

                <p>
                    👍 {len(likes)}
                    &nbsp;&nbsp;
                    👎 {len(dislikes)}
                </p>
            """

            if user:
                body += f"""
                <form method="post" action="/like" style="display:inline">
                    <input type="hidden" name="id" value="{esc(post.get('id'))}">
                    <button>👍 いいね</button>
                </form>

                <form method="post" action="/dislike" style="display:inline">
                    <input type="hidden" name="id" value="{esc(post.get('id'))}">
                    <button>👎 よくない</button>
                </form>
                """

            body += "</div>"

        self.send_html(self.page("ホーム", body))

    def register_page(self, error=""):
        body = f"""
        <div class="card">
            <h2>新規登録</h2>

            <p class="error">{esc(error)}</p>

            <form method="post" action="/register">

                <label>ユーザー名</label>
                <input name="username" required>

                <label>パスワード</label>
                <input type="password" name="password" required>

                <label>アイコン</label>
                <input name="icon" value="👤">

                <button>登録する</button>
            </form>
        </div>
        """

        self.send_html(self.page("新規登録", body))

    def register(self, data):
        users = load("users")

        username = data.get("username", [""])[0].strip()
        password = data.get("password", [""])[0]
        icon = data.get("icon", ["👤"])[0].strip() or "👤"

        if not username or not password:
            self.send_html(
                self.page(
                    "登録エラー",
                    "<div class='card'><h2>ユーザー名とパスワードを入力してください。</h2></div>"
                ),
                400
            )
            return

        if username in users:
            self.send_html(
                self.page(
                    "登録エラー",
                    "<div class='card'><h2>そのユーザー名はすでに使われています。</h2></div>"
                ),
                400
            )
            return

        users[username] = {
            "username": username,
            "password": make_password(password),
            "icon": icon,
            "created": now(),
        }

        save("users", users)

        token = make_session(username)

        self.redirect(
            "/",
            [f"session={token}; Path=/; HttpOnly"]
        )

    def login_page(self, error=""):
        body = f"""
        <div class="card">
            <h2>ログイン</h2>

            <p class="error">{esc(error)}</p>

            <form method="post" action="/login">

                <label>ユーザー名</label>
                <input name="username" required>

                <label>パスワード</label>
                <input type="password" name="password" required>

                <button>ログイン</button>
            </form>

            <p>
                アカウントがない場合は
                <a href="/register">新規登録</a>
            </p>
        </div>
        """

        self.send_html(self.page("ログイン", body))

    def login(self, data):
        users = load("users")

        username = data.get("username", [""])[0].strip()
        password = data.get("password", [""])[0]

        user = users.get(username)

        if not user or user.get("password") != make_password(password):
            self.send_html(
                self.page(
                    "ログインエラー",
                    "<div class='card'><h2>ユーザー名またはパスワードが違います。</h2></div>"
                ),
                401
            )
            return

        token = make_session(username)

        self.redirect(
            "/",
            [f"session={token}; Path=/; HttpOnly"]
        )

    def logout(self):
        token = get_cookie(self.headers, "session")

        sessions = load("sessions")

        if token in sessions:
            del sessions[token]
            save("sessions", sessions)

        self.redirect(
            "/",
            ["session=; Path=/; Max-Age=0"]
        )

    def channel(self):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        users = load("users")
        posts = load("posts")
        follows = load("follows")

        me = users.get(user, {})

        my_posts = [
            p for p in posts
            if p.get("author") == user
        ]

        follower_count = sum(
            1 for f in follows
            if f.get("to") == user
        )

        following_count = sum(
            1 for f in follows
            if f.get("from") == user
        )

        body = f"""
        <div class="card">

            <h2>
                {esc(me.get("icon", "👤"))}
                {esc(user)}
            </h2>

            <div class="stat">
                投稿 {len(my_posts)}
            </div>

            <div class="stat">
                フォロワー {follower_count}
            </div>

            <div class="stat">
                フォロー {following_count}
            </div>

        </div>

        <div class="card">
            <h2>チャンネル</h2>

            <p>
                <a href="/channel/settings">
                    ⚙️ チャンネル設定
                </a>
            </p>

            <h3>自分の投稿</h3>
        """

        for post in reversed(my_posts):
            body += f"""
            <div class="card">
                <div class="small">
                    {esc(post.get("time", ""))}
                </div>

                <div class="post">
                    {esc(post.get("text", ""))}
                </div>

                <p>
                    👍 {len(post.get("likes", []))}
                    👎 {len(post.get("dislikes", []))}
                </p>

                <a href="/delete_post?id={esc(post.get('id'))}">
                    🗑️ この投稿を削除
                </a>
            </div>
            """

        body += "</div>"

        self.send_html(self.page("マイチャンネル", body))

    def create_post(self, data):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        text = data.get("text", [""])[0].strip()

        if not text:
            self.redirect("/")
            return

        posts = load("posts")

        posts.append({
            "id": uuid.uuid4().hex,
            "author": user,
            "text": text,
            "time": now(),
            "likes": [],
            "dislikes": [],
        })

        save("posts", posts)

        self.redirect("/")

    def like(self, data):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        post_id = data.get("id", [""])[0]

        posts = load("posts")

        for post in posts:
            if post.get("id") == post_id:

                if user in post.get("likes", []):
                    post["likes"].remove(user)
                else:
                    if user in post.get("dislikes", []):
                        post["dislikes"].remove(user)

                    post.setdefault("likes", []).append(user)

                break

        save("posts", posts)

        self.redirect("/")

    def dislike(self, data):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        post_id = data.get("id", [""])[0]

        posts = load("posts")

        for post in posts:
            if post.get("id") == post_id:

                if user in post.get("dislikes", []):
                    post["dislikes"].remove(user)
                else:
                    if user in post.get("likes", []):
                        post["likes"].remove(user)

                    post.setdefault("dislikes", []).append(user)

                break

        save("posts", posts)

        self.redirect("/")

    def delete_post(self):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        query = parse_qs(urlparse(self.path).query)
        post_id = query.get("id", [""])[0]

        posts = load("posts")

        posts = [
            p for p in posts
            if not (
                p.get("id") == post_id
                and p.get("author") == user
            )
        ]

        save("posts", posts)

        self.redirect("/channel")

    def comment(self, data):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        post_id = data.get("post_id", [""])[0]
        text = data.get("text", [""])[0].strip()

        if not text:
            self.redirect("/")
            return

        comments = load("comments")

        comments.append({
            "id": uuid.uuid4().hex,
            "post_id": post_id,
            "author": user,
            "text": text,
            "time": now(),
        })

        save("comments", comments)

        self.redirect("/")

    def follow(self, data):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        target = data.get("user", [""])[0]

        if not target or target == user:
            self.redirect("/")
            return

        follows = load("follows")

        found = None

        for f in follows:
            if f.get("from") == user and f.get("to") == target:
                found = f
                break

        if found:
            follows.remove(found)
        else:
            follows.append({
                "from": user,
                "to": target,
                "time": now(),
            })

        save("follows", follows)

        self.redirect("/")

    def mail(self):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        users = load("users")

        body = """
        <div class="card">
            <h2>💬 メール</h2>
            <p>ユーザーを選んでチャットできます。</p>
        </div>
        """

        for username, account in users.items():

            if username == user:
                continue

            body += f"""
            <div class="card">
                <h3>
                    {esc(account.get("icon", "👤"))}
                    {esc(username)}
                </h3>

                <a href="/chat?user={esc(username)}">
                    チャットを開く
                </a>
            </div>
            """

        self.send_html(self.page("メール", body))

    def chat(self, query):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        target = query.get("user", [""])[0]

        if not target:
            self.redirect("/mail")
            return

        users = load("users")
        messages = load("messages")

        if target not in users:
            self.redirect("/mail")
            return

        body = f"""
        <div class="card">
            <h2>💬 {esc(target)} とチャット</h2>

            <div>
        """

        for message in messages:

            a = message.get("from")
            b = message.get("to")

            if (
                (a == user and b == target)
                or
                (a == target and b == user)
            ):
                body += f"""
                <div class="card">

                    <b>{esc(a)}</b>

                    <div class="post">
                        {esc(message.get("text", ""))}
                    </div>

                    <div class="small">
                        {esc(message.get("time", ""))}
                    </div>

                </div>
                """

        body += f"""
            </div>

            <form method="post" action="/message">

                <input type="hidden" name="to" value="{esc(target)}">

                <textarea
                    name="text"
                    placeholder="メッセージ"
                    required
                ></textarea>

                <button>送信</button>

            </form>

        </div>
        """

        self.send_html(self.page("チャット", body))

    def message(self, data):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        target = data.get("to", [""])[0]
        text = data.get("text", [""])[0].strip()

        if not target or not text:
            self.redirect("/mail")
            return

        messages = load("messages")

        messages.append({
            "id": uuid.uuid4().hex,
            "from": user,
            "to": target,
            "text": text,
            "time": now(),
        })

        save("messages", messages)

        self.redirect("/chat?user=" + target)

    def search(self, query):
        q = query.get("q", [""])[0].strip()

        users = load("users")
        posts = load("posts")

        body = """
        <div class="card">

            <h2>🔍 検索</h2>

            <form method="get" action="/search">

                <input
                    name="q"
                    placeholder="ユーザー名や投稿を検索"
                    value="{0}"
                >

                <button>検索</button>

            </form>

        </div>
        """.format(esc(q))

        if q:

            body += "<div class='card'><h2>検索結果</h2>"

            for username, account in users.items():

                if q.lower() in username.lower():

                    body += f"""
                    <p>
                        {esc(account.get("icon", "👤"))}
                        <b>{esc(username)}</b>
                    </p>
                    """

            for post in posts:

                if q.lower() in post.get("text", "").lower():

                    body += f"""
                    <div class="card">

                        <b>{esc(post.get("author", ""))}</b>

                        <div class="post">
                            {esc(post.get("text", ""))}
                        </div>

                    </div>
                    """

            body += "</div>"

        self.send_html(self.page("検索", body))

    def file(self):
        filename = urlparse(self.path).path[len("/uploads/"):]

        filename = os.path.basename(filename)

        path = os.path.join(UPLOADS, filename)

        if not os.path.exists(path):
            self.send_response(404)
            self.end_headers()
            return

        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"

        with open(path, "rb") as f:
            data = f.read()

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def channel_settings_page(self):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        users = load("users")
        account = users.get(user, {})

        body = f"""
        <div class="card">

            <h2>⚙️ チャンネル設定</h2>

            <form method="post" action="/channel/settings">

                <label>表示名</label>

                <input
                    name="display"
                    value="{esc(account.get("display", user))}"
                >

                <label>アイコン</label>

                <input
                    name="icon"
                    value="{esc(account.get("icon", "👤"))}"
                >

                <button>保存</button>

            </form>

        </div>
        """

        self.send_html(self.page("チャンネル設定", body))

    def channel_settings(self, data):
        user = self.current_user()

        if not user:
            self.redirect("/login")
            return

        users = load("users")

        if user not in users:
            self.redirect("/login")
            return

        users[user]["display"] = data.get("display", [user])[0].strip() or user
        users[user]["icon"] = data.get("icon", ["👤"])[0].strip() or "👤"

        save("users", users)

        self.redirect("/channel")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), WebServer)

    print("================================")
    print("ウェブサーバー起動")
    print("http://localhost:" + str(PORT))
    print("================================")

    server.serve_forever()
