from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import json
import os
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
    "users": "users.json",
    "posts": "posts.json",
    "messages": "messages.json",
    "follows": "follows.json",
    "comments": "comments.json",
    "sessions": "sessions.json",
    "warnings": "warnings.json",
    "settings": "settings.json"
}


def load(name, default=None):
    path = os.path.join(DATA, FILES[name])

    if not os.path.exists(path):
        return default if default is not None else []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else []


def save(name, data):
    path = os.path.join(DATA, FILES[name])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now():
    return datetime.now().strftime("%Y/%m/%d %H:%M")


def password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


def esc(text):
    return html.escape(str(text))


def find_user(username):
    for u in load("users", []):
        if u.get("username") == username:
            return u
    return None


def session_user(handler):
    cookie = handler.headers.get("Cookie", "")

    if not cookie:
        return None

    token = None

    for item in cookie.split(";"):
        item = item.strip()

        if item.startswith("session="):
            token = item.split("=", 1)[1]

    if not token:
        return None

    sessions = load("sessions", {})

    if token in sessions:
        return sessions[token]

    return None


def new_session(username):
    sessions = load("sessions", {})

    token = str(uuid.uuid4())

    sessions[token] = username

    save("sessions", sessions)

    return token


def add_warning(username, action, text):
    warnings = load("warnings", [])

    warnings.append({
        "id": str(uuid.uuid4()),
        "username": username,
        "action": action,
        "text": text,
        "date": now()
    })

    save("warnings", warnings)


def layout(title, body, username=None):
    user = find_user(username) if username else None

    icon = ""

    if user:
        icon = user.get("icon", "")

    top = f"""
    <div class="top">
        <b>{esc(title)}</b>
        <a href="/menu">⋮</a>
    </div>
    """

    bottom = ""

    if username:
        bottom = """
        <div class="bottom">
            <a href="/channel">👤<span>マイチャンネル</span></a>
            <a href="/">🏠<span>ホーム</span></a>
            <a href="/mail">💬<span>メール</span></a>
            <a href="/search">🔍<span>検索</span></a>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>

<style>

:root {{
    --bg:#f3f3f3;
    --card:#ffffff;
    --text:#222;
    --border:#ddd;
    --blue:#1976d2;
}}

* {{
    box-sizing:border-box;
}}

body {{
    margin:0;
    background:var(--bg);
    color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;
    padding-bottom:80px;
}}

.top {{
    position:sticky;
    top:0;
    z-index:5;
    background:var(--card);
    border-bottom:1px solid var(--border);
    padding:15px;
    display:flex;
    justify-content:space-between;
    align-items:center;
}}

.top a {{
    color:var(--text);
    text-decoration:none;
    font-size:28px;
}}

.container {{
    max-width:800px;
    margin:auto;
    padding:15px;
}}

.card {{
    background:var(--card);
    border:1px solid var(--border);
    border-radius:14px;
    padding:15px;
    margin-bottom:15px;
}}

input, textarea, select {{
    width:100%;
    padding:12px;
    margin:5px 0 10px;
    border:1px solid var(--border);
    border-radius:10px;
    font-size:16px;
}}

button {{
    border:0;
    border-radius:10px;
    padding:10px 15px;
    background:var(--blue);
    color:white;
    font-size:15px;
    cursor:pointer;
}}

button.gray {{
    background:#777;
}}

a {{
    color:var(--blue);
}}

.bottom {{
    position:fixed;
    bottom:0;
    left:0;
    right:0;
    height:70px;
    background:var(--card);
    border-top:1px solid var(--border);
    display:flex;
    justify-content:space-around;
    z-index:10;
}}

.bottom a {{
    text-decoration:none;
    color:var(--text);
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    font-size:23px;
}}

.bottom span {{
    font-size:11px;
    margin-top:3px;
}}

.user {{
    display:flex;
    align-items:center;
    gap:10px;
}}

.user-icon {{
    width:48px;
    height:48px;
    border-radius:50%;
    object-fit:cover;
    background:#ddd;
}}

.post-actions {{
    display:flex;
    gap:8px;
    margin-top:10px;
}}

.post-actions form {{
    display:inline;
}}

.message {{
    max-width:75%;
    padding:10px 13px;
    border-radius:15px;
    margin:7px 0;
}}

.me {{
    margin-left:auto;
    background:#9fe7a8;
}}

.other {{
    margin-right:auto;
    background:var(--card);
    border:1px solid var(--border);
}}

.chat {{
    min-height:60vh;
}}

.chat-user {{
    display:flex;
    align-items:center;
    gap:10px;
}}

.chat-user img {{
    width:42px;
    height:42px;
    border-radius:50%;
    object-fit:cover;
}}

.chat-input {{
    position:sticky;
    bottom:70px;
    background:var(--bg);
    padding:10px 0;
}}

.users {{
    display:flex;
    gap:12px;
    overflow-x:auto;
    padding:10px 0;
}}

.user-box {{
    min-width:90px;
    text-align:center;
    text-decoration:none;
    color:var(--text);
}}

.user-box img {{
    width:60px;
    height:60px;
    border-radius:50%;
    object-fit:cover;
    display:block;
    margin:auto;
}}

.preview {{
    max-width:100%;
    max-height:350px;
    border-radius:10px;
}}

.warning {{
    padding:10px;
    border-left:4px solid #e53935;
    background:#fff0f0;
    margin:5px 0;
}}

body.dark {{
    --bg:#111;
    --card:#202020;
    --text:#eee;
    --border:#444;
}}

</style>

<script>
function darkMode() {{
    document.body.classList.add("dark");
    localStorage.setItem("mode","dark");
}}

function lightMode() {{
    document.body.classList.remove("dark");
    localStorage.setItem("mode","light");
}}

window.addEventListener("load",function() {{
    if(localStorage.getItem("mode") === "dark") {{
        document.body.classList.add("dark");
    }}
}});
</script>

</head>
<body>

{top}

<div class="container">
{body}
</div>

{bottom}

</body>
</html>
"""


class Server(BaseHTTPRequestHandler):

    def send_html(self, content, status=200, cookie=None):

        data = content.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))

        if cookie:
            self.send_header("Set-Cookie", cookie)

        self.end_headers()
        self.wfile.write(data)

    def redirect(self, path, cookie=None):

        self.send_response(303)
        self.send_header("Location", path)

        if cookie:
            self.send_header("Set-Cookie", cookie)

        self.end_headers()

    def parse_post(self):

        length = int(self.headers.get("Content-Length", "0"))

        body = self.rfile.read(length)

        content_type = self.headers.get("Content-Type", "")

        if content_type.startswith("application/x-www-form-urlencoded"):

            from urllib.parse import parse_qs

            parsed = parse_qs(body.decode("utf-8"))

            return {
                k: v[0]
                for k, v in parsed.items()
            }, None

        return {}, body

    def do_GET(self):

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        user = session_user(self)

        # アップロード画像
        if path.startswith("/uploads/"):

            filename = os.path.basename(path[len("/uploads/"):])

            filepath = os.path.join(UPLOADS, filename)

            if not os.path.exists(filepath):
                self.send_error(404)
                return

            mime = mimetypes.guess_type(filepath)[0] or "application/octet-stream"

            with open(filepath, "rb") as f:
                data = f.read()

            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

            return

        # ログイン
        if not user:

            if path == "/register":

                body = """
                <div class="card">
                    <h2>新規登録</h2>

                    <form method="post" action="/register">

                        <input name="username"
                               placeholder="アカウント名"
                               required>

                        <input type="password"
                               name="password"
                               placeholder="パスワード"
                               required>

                        <input name="icon"
                               placeholder="アイコン画像URL（任意）">

                        <button>登録する</button>

                    </form>
                </div>

                <div class="card">
                    <a href="/login">ログインはこちら</a>
                </div>
                """

                self.send_html(layout("新規登録", body))
                return

            body = """
            <div class="card">

                <h2>ログイン</h2>

                <form method="post" action="/login">

                    <input name="username"
                           placeholder="アカウント名"
                           required>

                    <input type="password"
                           name="password"
                           placeholder="パスワード"
                           required>

                    <button>ログイン</button>

                </form>

            </div>

            <div class="card">
                <a href="/register">新規登録</a>
            </div>
            """

            self.send_html(layout("ログイン", body))
            return

        # ホーム
        if path == "/":

            posts = load("posts", [])

            body = ""

            body += """
            <div class="card">
                <h2>ホーム</h2>

                <form method="post" action="/post">

                    <textarea name="text"
                              placeholder="何を投稿しますか？"></textarea>

                    <button>投稿する</button>

                </form>
            </div>
            """

            warnings = load("warnings", [])

            if warnings:

                body += """
                <div class="card">
                    <h3>⚠️ 最近の活動</h3>
                """

                for w in warnings[-5:][::-1]:

                    body += f"""
                    <div class="warning">
                        {esc(w.get("username"))}さんが
                        {esc(w.get("action"))}しました
                    </div>
                    """

                body += "</div>"

            for p in reversed(posts):

                liked = user in p.get("liked_by", [])
                disliked = user in p.get("disliked_by", [])

                body += f"""
                <div class="card">

                    <div class="user">
                        <div>
                            <b>{esc(p.get("username",""))}</b><br>
                            <small>{esc(p.get("date",""))}</small>
                        </div>
                    </div>

                    <p>{esc(p.get("text",""))}</p>

                    <div class="post-actions">

                        <form method="post" action="/like">
                            <input type="hidden"
                                   name="id"
                                   value="{esc(p.get("id"))}">
                            <button>{"👍" if not liked else "👍 解除"}</button>
                        </form>

                        <form method="post" action="/dislike">
                            <input type="hidden"
                                   name="id"
                                   value="{esc(p.get("id"))}">
                            <button class="gray">
                                {"👎" if not disliked else "👎 解除"}
                            </button>
                        </form>

                    </div>

                </div>
                """

            self.send_html(layout("ホーム", body, user))
            return

        # メール一覧
        if path == "/mail":

            users = load("users", [])

            search = query.get("q", [""])[0].lower()

            body = """
            <div class="card">

                <form method="get" action="/mail">

                    <input name="q"
                           value="{0}"
                           placeholder="🔍 メールを検索">

                </form>

            </div>

            <div class="users">
            """.format(esc(search))

            for u in users:

                name = u.get("username", "")

                if name == user:
                    continue

                if search and search not in name.lower():
                    continue

                icon = u.get("icon", "")

                if icon:
                    image = f'<img src="{esc(icon)}">'
                else:
                    image = '<img src="/uploads/default-user.png">'

                body += f"""
                <a class="user-box"
                   href="/chat?user={esc(name)}">

                    {image}

                    <div>{esc(name)}</div>

                </a>
                """

            body += "</div>"

            body += """
            <div class="card">
                <h3>💬 メール</h3>
                <p>話したい相手を選んでください。</p>
            </div>
            """

            self.send_html(layout("メール", body, user))
            return

        # チャット
        if path == "/chat":

            target = query.get("user", [""])[0]

            target_user = find_user(target)

            if not target_user:

                self.send_html(
                    layout(
                        "チャット",
                        '<div class="card">ユーザーが見つかりません。</div>',
                        user
                    )
                )

                return

            messages = load("messages", [])

            body = f"""
            <div class="card">

                <div class="chat-user">

                    <img src="{esc(target_user.get("icon",""))}"
                         onerror="this.style.display='none'">

                    <b>{esc(target)}</b>

                </div>

            </div>

            <div class="chat">
            """

            chat_messages = []

            for m in messages:

                a = m.get("from")
                b = m.get("to")

                if (a == user and b == target) or \
                   (a == target and b == user):

                    chat_messages.append(m)

            for m in chat_messages:

                mine = m.get("from") == user

                cls = "me" if mine else "other"

                mtype = m.get("type", "text")

                if mtype == "image":

                    content = f"""
                    <img class="preview"
                         src="/uploads/{esc(m.get("filename",""))}">
                    """

                elif mtype == "gif":

                    content = f"""
                    <img class="preview"
                         src="/uploads/{esc(m.get("filename",""))}">
                    """

                else:

                    content = esc(m.get("text", ""))

                body += f"""
                <div class="message {cls}">

                    {content}

                    <br>
                    <small>{esc(m.get("date",""))}</small>

                </div>
                """

            body += """
            </div>

            <div class="chat-input card">

                <form method="post"
                      action="/send_message"
                      enctype="application/x-www-form-urlencoded">

                    <input type="hidden"
                           name="to"
                           value="{TARGET}">

                    <input name="text"
                           placeholder="メッセージを入力">

                    <button>送信</button>

                </form>

                <br>

                <form method="post"
                      action="/send_image"
                      enctype="multipart/form-data">

                    <input type="hidden"
                           name="to"
                           value="{TARGET}">

                    <input type="file"
                           name="file"
                           accept="image/*,.gif"
                           required>

                    <button>🖼️ 画像・GIFを送る</button>

                </form>

            </div>
            """.replace("{TARGET}", html.escape(target))

            self.send_html(layout(target, body, user))
            return

        # チャンネル
        if path == "/channel":

            u = find_user(user)

            body = f"""
            <div class="card">

                <div class="user">

                    <img class="user-icon"
                         src="{esc(u.get("icon",""))}"
                         onerror="this.style.display='none'">

                    <div>
                        <h2>{esc(user)}</h2>
                        <a href="/studio">YouTube Studio風 管理画面</a>
                    </div>

                </div>

            </div>
            """

            self.send_html(layout("マイチャンネル", body, user))
            return

        # Studio
        if path == "/studio":

            posts = load("posts", [])

            count = sum(
                1 for p in posts
                if p.get("username") == user
            )

            body = f"""
            <div class="card">

                <h2>📊 チャンネル管理</h2>

                <p>投稿数：{count}</p>

                <a href="/">ホームを見る</a>

            </div>
            """

            self.send_html(layout("チャンネル管理", body, user))
            return

        # 検索
        if path == "/search":

            q = query.get("q", [""])[0].lower()

            users = load("users", [])

            body = """
            <div class="card">

                <form method="get" action="/search">

                    <input name="q"
                           placeholder="🔍 検索"
                           value="{0}">

                    <button>検索</button>

                </form>

            </div>
            """.format(esc(q))

            if q:

                for u in users:

                    if q in u.get("username", "").lower():

                        body += f"""
                        <div class="card">
                            <a href="/chat?user={esc(u.get("username"))}">
                                👤 {esc(u.get("username"))}
                            </a>
                        </div>
                        """

            self.send_html(layout("検索", body, user))
            return

        # メニュー
        if path == "/menu":

            body = """
            <div class="card">

                <h2>メニュー</h2>

                <p><a href="/settings">⚙️ 設定</a></p>

                <p><a href="/warnings">⚠️ 警告</a></p>

                <p><a href="/logout">ログアウト</a></p>

            </div>
            """

            self.send_html(layout("メニュー", body, user))
            return

        # 設定
        if path == "/settings":

            body = """
            <div class="card">

                <h2>⚙️ 設定</h2>

                <h3>画面</h3>

                <button onclick="lightMode()">
                    ☀️ ライト
                </button>

                <button onclick="darkMode()">
                    🌙 ダーク
                </button>

                <h3>明るさ</h3>

                <input type="range"
                       min="50"
                       max="150"
                       value="100"
                       onchange="
                       document.body.style.filter=
                       'brightness('+this.value+'%)'
                       ">

            </div>
            """

            self.send_html(layout("設定", body, user))
            return

        # 警告
        if path == "/warnings":

            warnings = load("warnings", [])

            body = """
            <div class="card">
                <h2>⚠️ 警告・活動履歴</h2>
            """

            for w in reversed(warnings):

                body += f"""
                <div class="warning">

                    <b>{esc(w.get("username"))}</b>

                    {esc(w.get("action"))}

                    <br>

                    {esc(w.get("text",""))}

                    <br>

                    <small>{esc(w.get("date",""))}</small>

                </div>
                """

            body += "</div>"

            self.send_html(layout("警告", body, user))
            return

        # ログアウト
        if path == "/logout":

            token = None

            cookie = self.headers.get("Cookie", "")

            for item in cookie.split(";"):

                item = item.strip()

                if item.startswith("session="):
                    token = item.split("=",1)[1]

            if token:

                sessions = load("sessions", {})

                sessions.pop(token, None)

                save("sessions", sessions)

            self.redirect("/login", "session=; Max-Age=0")

            return

        self.send_error(404)

    def do_POST(self):

        path = urlparse(self.path).path

        user = session_user(self)

        data, raw = self.parse_post()

        # 登録
        if path == "/register":

            username = data.get("username", "").strip()
            password = data.get("password", "").strip()
            icon = data.get("icon", "").strip()

            if not username or not password:

                self.send_html(
                    layout(
                        "エラー",
                        '<div class="card">入力してください。</div>'
                    )
                )

                return

            if find_user(username):

                self.send_html(
                    layout(
                        "エラー",
                        '<div class="card">その名前はすでに使われています。</div>'
                    )
                )

                return

            users = load("users", [])

            users.append({
                "username": username,
                "password": password_hash(password),
                "icon": icon
            })

            save("users", users)

            token = new_session(username)

            self.redirect(
                "/",
                f"session={token}; Path=/; HttpOnly"
            )

            return

        # ログイン
        if path == "/login":

            username = data.get("username", "")
            password = data.get("password", "")

            u = find_user(username)

            if not u or u.get("password") != password_hash(password):

                self.send_html(
                    layout(
                        "ログインエラー",
                        '<div class="card">名前またはパスワードが違います。</div>'
                    )
                )

                return

            token = new_session(username)

            self.redirect(
                "/",
                f"session={token}; Path=/; HttpOnly"
            )

            return

        if not user:

            self.redirect("/login")
            return

        # 投稿
        if path == "/post":

            text = data.get("text", "").strip()

            if text:

                posts = load("posts", [])

                posts.append({
                    "id": str(uuid.uuid4()),
                    "username": user,
                    "text": text,
                    "date": now(),
                    "liked_by": [],
                    "disliked_by": []
                })

                save("posts", posts)

                add_warning(user, "投稿", text)

            self.redirect("/")
            return

        # いいね・低評価
        if path in ["/like", "/dislike"]:

            pid = data.get("id", "")

            posts = load("posts", [])

            for p in posts:

                if p.get("id") != pid:
                    continue

                p.setdefault("liked_by", [])
                p.setdefault("disliked_by", [])

                if path == "/like":

                    if user in p["liked_by"]:
                        p["liked_by"].remove(user)

                    else:
                        p["liked_by"].append(user)

                        if user in p["disliked_by"]:
                            p["disliked_by"].remove(user)

                else:

                    if user in p["disliked_by"]:
                        p["disliked_by"].remove(user)

                    else:
                        p["disliked_by"].append(user)

                        if user in p["liked_by"]:
                            p["liked_by"].remove(user)

                break

            save("posts", posts)

            self.redirect("/")
            return

        # テキストメール
        if path == "/send_message":

            target = data.get("to", "")
            text = data.get("text", "").strip()

            if target and text:

                messages = load("messages", [])

                messages.append({
                    "id": str(uuid.uuid4()),
                    "from": user,
                    "to": target,
                    "type": "text",
                    "text": text,
                    "date": now()
                })

                save("messages", messages)

                add_warning(
                    user,
                    "メール送信",
                    f"{target}さんへメッセージ"
                )

            self.redirect(
                "/chat?user=" + target
            )

            return

        # 画像/GIF送信
        if path == "/send_image":

            content_type = self.headers.get("Content-Type", "")

            if not content_type.startswith("multipart/form-data"):

                self.redirect("/mail")
                return

            boundary = ""

            for part in content_type.split(";"):

                part = part.strip()

                if part.startswith("boundary="):
                    boundary = part.split("=",1)[1]

            boundary = boundary.encode()

            raw_body = raw

            sections = raw_body.split(b"--" + boundary)

            target = ""

            filename = ""
            filedata = b""

            for section in sections:

                if b'name="to"' in section:

                    try:
                        target = section.split(b"\r\n\r\n",1)[1].strip().decode()
                    except:
                        pass

                if b'name="file"' in section:

                    header_end = section.find(b"\r\n\r\n")

                    if header_end == -1:
                        continue

                    headers = section[:header_end].decode(
                        "utf-8",
                        errors="ignore"
                    )

                    content = section[
                        header_end + 4:
                    ]

                    content = content.rstrip(b"\r\n-")

                    marker = 'filename="'

                    if marker in headers:

                        filename = headers.split(
                            marker,1
                        )[1].split('"',1)[0]

                    filedata = content

            if filename and target and filedata:

                ext = os.path.splitext(filename)[1].lower()

                allowed = [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                    ".gif"
                ]

                if ext in allowed:

                    newname = (
                        str(uuid.uuid4())
                        + ext
                    )

                    filepath = os.path.join(
                        UPLOADS,
                        newname
                    )

                    with open(filepath, "wb") as f:
                        f.write(filedata)

                    mtype = "gif" if ext == ".gif" else "image"

                    messages = load("messages", [])

                    messages.append({
                        "id": str(uuid.uuid4()),
                        "from": user,
                        "to": target,
                        "type": mtype,
                        "filename": newname,
                        "date": now()
                    })

                    save("messages", messages)

            self.redirect(
                "/chat?user=" + target
            )

            return

        self.redirect("/")


if __name__ == "__main__":

    print("サーバー起動")
    print("http://localhost:8000")

    server = HTTPServer(
        ("0.0.0.0", PORT),
        Server
    )

    server.serve_forever()
