# server.py
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from email.parser import BytesParser
from email.policy import default
from datetime import datetime
import json
import os
import html
import uuid
import mimetypes

PORT = int(os.environ.get("PORT", "8000"))

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

FILES = {
    "posts": "posts.json",
    "users": "users.json",
    "channels": "channels.json",
    "follows": "follows.json",
    "messages": "messages.json"
}


def load(name, default_value):
    filename = FILES[name]

    if not os.path.exists(filename):
        return default_value

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default_value


def save(name, data):
    with open(FILES[name], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def esc(value):
    return html.escape(str(value))


def now():
    return datetime.now().strftime("%Y年%m月%d日 %H:%M")


def safe_filename(name):
    name = os.path.basename(name)
    result = ""

    for c in name:
        if c.isalnum() or c in "._-":
            result += c

    return result[:100] or "file"


def get_user(handler):
    cookie = handler.headers.get("Cookie", "")

    for item in cookie.split(";"):
        item = item.strip()

        if item.startswith("username="):
            return item[len("username="):]

    return ""


class Server(BaseHTTPRequestHandler):

    def html(self, body, title="ウェブサーバー"):
        user = get_user(self)

        if user:
            user_html = f"👤 {esc(user)}"
        else:
            user_html = ""

        page = f"""
<!DOCTYPE html>
<html lang="ja">
<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>{esc(title)}</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    padding-bottom: 75px;
    background: #f2f2f2;
    font-family: Arial, sans-serif;
}}

header {{
    background: white;
    padding: 15px;
    border-bottom: 1px solid #ddd;
    position: sticky;
    top: 0;
    z-index: 10;
}}

header h1 {{
    margin: 0;
}}

main {{
    max-width: 700px;
    margin: auto;
    padding: 12px;
}}

.card {{
    background: white;
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px #ddd;
}}

button,
input,
textarea,
select {{
    font-size: 16px;
}}

button {{
    padding: 9px 13px;
    border: 0;
    border-radius: 8px;
    background: #eee;
}}

.primary {{
    background: #222;
    color: white;
}}

.danger {{
    background: #d33;
    color: white;
}}

input,
textarea,
select {{
    width: 100%;
    padding: 10px;
    margin: 5px 0 10px;
    border: 1px solid #ccc;
    border-radius: 8px;
}}

textarea {{
    min-height: 90px;
}}

.post-head {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}}

.dots {{
    font-size: 24px;
    padding: 2px 9px;
}}

.menu-box {{
    display: none;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 8px;
    margin-top: 5px;
}}

.menu-box:target {{
    display: block;
}}

.menu-box form {{
    margin: 0;
}}

.file img {{
    width: 100%;
    max-height: 500px;
    object-fit: contain;
    border-radius: 8px;
}}

.file video {{
    width: 100%;
    max-height: 500px;
    border-radius: 8px;
}}

.comment {{
    background: #f5f5f5;
    padding: 7px;
    border-radius: 7px;
    margin: 5px 0;
}}

.small {{
    color: #777;
    font-size: 13px;
}}

.channel {{
    display: block;
    background: white;
    padding: 15px;
    margin-bottom: 10px;
    border-radius: 10px;
    color: black;
    text-decoration: none;
}}

nav {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 65px;
    background: white;
    border-top: 1px solid #ccc;
    display: flex;
    justify-content: space-around;
    z-index: 20;
}}

nav a {{
    color: black;
    text-decoration: none;
    text-align: center;
    padding-top: 8px;
}}

nav span {{
    display: block;
    font-size: 11px;
}}

</style>

</head>

<body>

<header>

<h1>🌐 ウェブサーバー</h1>

<div class="small">
{user_html}
</div>

</header>

<main>

{body}

</main>

<nav>

<a href="/mychannels">
👤
<span>マイチャンネル</span>
</a>

<a href="/">
🏠
<span>ホーム</span>
</a>

<a href="/mail">
💬
<span>メール</span>
</a>

<a href="/search">
🔍
<span>検索</span>
</a>

</nav>

</body>
</html>
"""

        data = page.encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(data))
        )
        self.end_headers()

        self.wfile.write(data)


    def redirect(self, url="/"):
        self.send_response(303)
        self.send_header("Location", url)
        self.end_headers()


    def registration(self):

        body = """
<div class="card">

<h2>はじめまして！</h2>

<p>使う名前を入力してください。</p>

<form method="POST"
      action="/setname">

<input
name="username"
placeholder="名前"
maxlength="30"
required>

<button class="primary">
登録する
</button>

</form>

</div>
"""

        self.html(body, "名前登録")


    def post_form(self, channel=""):

        username = get_user(self)

        channels = load("channels", {})
        mine = channels.get(username, [])

        options = ""

        for ch in mine:

            selected = ""

            if ch == channel:
                selected = "selected"

            options += f"""
<option {selected}>
{esc(ch)}
</option>
"""

        if not options:
            options = """
<option>メインチャンネル</option>
"""

        return f"""
<div class="card">

<h2>投稿する</h2>

<form method="POST"
      action="/post"
      enctype="multipart/form-data">

<label>チャンネル</label>

<select name="channel">
{options}
</select>

<textarea
name="text"
placeholder="何を投稿しますか？"></textarea>

<input
type="file"
name="file">

<button class="primary">
投稿する
</button>

</form>

</div>
"""


    def file_html(self, filename):

        if not filename:
            return ""

        url = "/uploads/" + filename

        ext = os.path.splitext(filename)[1].lower()

        if ext in [
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp"
        ]:

            return f"""
<div class="file">
<img src="{url}">
</div>
"""

        if ext in [
            ".mp4",
            ".webm",
            ".ogg",
            ".mov"
        ]:

            return f"""
<div class="file">

<video controls playsinline>

<source src="{url}">

</video>

</div>
"""

        return f"""
<p>
📎
<a href="{url}" download>
{esc(filename)}
</a>
</p>
"""


    def post_html(self, post):

        username = get_user(self)

        author = post.get("username", "")

        post_id = post.get("id", "")

        channel = post.get("channel", "")

        comments = post.get("comments", [])

        menu = ""

        # 投稿者本人だけ⋮を表示
        if author == username:

            menu = f"""

<div>

<a
href="#menu-{post_id}"
class="dots">
⋮
</a>

<div
id="menu-{post_id}"
class="menu-box">

<form method="POST"
action="/delete_post"
onsubmit="return confirm('この投稿を削除しますか？');">

<input
type="hidden"
name="id"
value="{esc(post_id)}">

<button class="danger">
投稿を削除
</button>

</form>

</div>

</div>
"""

        comments_html = ""

        for c in comments:

            comments_html += f"""
<div class="comment">

<b>{esc(c.get("username", ""))}</b>

<br>

{esc(c.get("text", ""))}

</div>
"""

        channel_html = ""

        if channel:

            channel_html = f"""
<div class="small">

📺
<a href="/channel/{esc(author)}/{esc(channel)}">

{esc(channel)}

</a>

</div>
"""

        return f"""

<div class="card">

<div class="post-head">

<div>

<b>{esc(author)}</b>

<div class="small">
{esc(post.get("time", ""))}
</div>

{channel_html}

</div>

{menu}

</div>

<p>
{esc(post.get("text", "")).replace(chr(10), "<br>")}
</p>

{self.file_html(post.get("filename", ""))}

<form method="POST"
action="/like"
style="display:inline">

<input
type="hidden"
name="id"
value="{esc(post_id)}">

<button>
👍 {post.get("likes", 0)}
</button>

</form>

<form method="POST"
action="/dislike"
style="display:inline">

<input
type="hidden"
name="id"
value="{esc(post_id)}">

<button>
👎 {post.get("dislikes", 0)}
</button>

</form>

<hr>

<b>コメント</b>

{comments_html}

<form method="POST"
action="/comment">

<input
type="hidden"
name="id"
value="{esc(post_id)}">

<input
name="text"
placeholder="コメントを書く"
required>

<button>
送信
</button>

</form>

</div>
"""


    def home(self):

        posts = load("posts", [])

        content = self.post_form()

        content += """
<div class="card">
<h2>🏠 ホーム</h2>
</div>
"""

        for post in reversed(posts):
            content += self.post_html(post)

        self.html(content)


    def my_channels(self):

        username = get_user(self)

        channels = load("channels", {})

        mine = channels.get(username, [])

        content = f"""
<div class="card">

<h2>👤 マイチャンネル</h2>

<p>
{esc(username)}
</p>

<h3>チャンネルを作る</h3>

<form method="POST"
action="/create_channel">

<input
name="channel"
placeholder="チャンネル名"
required
maxlength="50">

<button class="primary">
作成
</button>

</form>

</div>
"""

        for ch in mine:

            content += f"""
<a class="channel"
href="/channel/{esc(username)}/{esc(ch)}">

📺 {esc(ch)}

</a>
"""

        self.html(content, "マイチャンネル")


    def channel_page(self, owner, channel):

        channels = load("channels", {})

        if channel not in channels.get(owner, []):

            self.html(
                "<div class='card'>チャンネルがありません。</div>"
            )

            return

        username = get_user(self)

        follows = load("follows", {})

        following = owner in follows.get(username, [])

        if owner == username:

            follow = ""

            delete = f"""
<form method="POST"
action="/delete_channel"
onsubmit="return confirm('このチャンネルを削除しますか？');">

<input
type="hidden"
name="channel"
value="{esc(channel)}">

<button class="danger">
⋮ チャンネルを削除
</button>

</form>
"""

        else:

            if following:

                follow = f"""
<form method="POST"
action="/unfollow">

<input
type="hidden"
name="target"
value="{esc(owner)}">

<button>
フォロー中
</button>

</form>
"""

            else:

                follow = f"""
<form method="POST"
action="/follow">

<input
type="hidden"
name="target"
value="{esc(owner)}">

<button class="primary">
フォローする
</button>

</form>
"""

            delete = ""

        content = f"""
<div class="card">

<h2>📺 {esc(channel)}</h2>

<p>
投稿者：{esc(owner)}
</p>

{follow}

<br>

{delete}

</div>

{self.post_form(channel)}
"""

        posts = load("posts", [])

        for post in reversed(posts):

            if (
                post.get("username") == owner
                and post.get("channel") == channel
            ):

                content += self.post_html(post)

        self.html(content, channel)


    def mail(self):

        username = get_user(self)

        follows = load("follows", {})

        content = """
<div class="card">

<h2>💬 メール</h2>

<p>
相互フォローした人とメッセージできます。
</p>

</div>
"""

        for target in follows.get(username, []):

            if username in follows.get(target, []):

                content += f"""
<a class="channel"
href="/conversation/{esc(target)}">

💬 {esc(target)}

</a>
"""

        self.html(content, "メール")


    def conversation(self, target):

        username = get_user(self)

        follows = load("follows", {})

        if not (
            target in follows.get(username, [])
            and username in follows.get(target, [])
        ):

            self.html(
                "<div class='card'>相互フォローではありません。</div>",
                "メール"
            )

            return

        messages = load("messages", [])

        content = f"""
<div class="card">

<h2>💬 {esc(target)}</h2>

</div>
"""

        for m in messages:

            if (
                (
                    m.get("from") == username
                    and m.get("to") == target
                )
                or
                (
                    m.get("from") == target
                    and m.get("to") == username
                )
            ):

                content += f"""
<div class="card">

<b>{esc(m.get("from", ""))}</b>

<p>
{esc(m.get("text", ""))}
</p>

<div class="small">
{esc(m.get("time", ""))}
</div>

</div>
"""

        content += f"""
<div class="card">

<form method="POST"
action="/send_message">

<input
type="hidden"
name="target"
value="{esc(target)}">

<textarea
name="text"
placeholder="メッセージ"></textarea>

<button class="primary">
送信
</button>

</form>

</div>
"""

        self.html(content, "メール")


    def search(self, q):

        content = f"""
<div class="card">

<h2>🔍 検索</h2>

<form method="GET"
action="/search">

<input
name="q"
value="{esc(q)}"
placeholder="人・チャンネル・投稿・ファイル">

<button class="primary">
検索
</button>

</form>

</div>
"""

        if q:

            posts = load("posts", [])
            users = load("users", [])
            channels = load("channels", {})

            for user in users:

                if q.lower() in user.lower():

                    content += f"""
<div class="card">

👤
<a href="/channel/{esc(user)}/メインチャンネル">

{esc(user)}

</a>

</div>
"""

            for owner, chs in channels.items():

                for ch in chs:

                    if (
                        q.lower() in ch.lower()
                        or q.lower() in owner.lower()
                    ):

                        content += f"""
<div class="card">

📺
<a href="/channel/{esc(owner)}/{esc(ch)}">

{esc(ch)}

</a>

<div class="small">
{esc(owner)}
</div>

</div>
"""

            for post in posts:

                text = post.get("text", "")
                author = post.get("username", "")
                filename = post.get("filename", "")

                if (
                    q.lower() in text.lower()
                    or q.lower() in author.lower()
                    or q.lower() in filename.lower()
                ):

                    content += self.post_html(post)

        self.html(content, "検索")


    def parse_form(self):

        length = int(
            self.headers.get(
                "Content-Length",
                "0"
            )
        )

        body = self.rfile.read(length)

        content_type = self.headers.get(
            "Content-Type",
            ""
        )

        if content_type.startswith(
            "multipart/form-data"
        ):

            header = (
                b"Content-Type: "
                + content_type.encode()
                + b"\r\n\r\n"
            )

            msg = BytesParser(
                policy=default
            ).parsebytes(
                header + body
            )

            fields = {}
            files = {}

            for part in msg.iter_parts():

                name = part.get_param(
                    "name",
                    header="content-disposition"
                )

                filename = part.get_filename()

                data = part.get_payload(
                    decode=True
                ) or b""

                if filename:

                    files[name] = (
                        safe_filename(filename),
                        data
                    )

                else:

                    fields[name] = data.decode(
                        "utf-8",
                        "replace"
                    )

            return fields, files

        data = parse_qs(
            body.decode(
                "utf-8",
                "replace"
            )
        )

        return {
            k: v[0]
            for k, v in data.items()
        }, {}


    def do_GET(self):

        path = urlparse(self.path).path

        query = parse_qs(
            urlparse(self.path).query
        )

        username = get_user(self)

        if not username:

            return self.registration()

        if path == "/":
            return self.home()

        if path == "/mychannels":
            return self.my_channels()

        if path == "/mail":
            return self.mail()

        if path == "/search":

            q = query.get(
                "q",
                [""]
            )[0]

            return self.search(q)

        if path.startswith("/conversation/"):

            target = path[
                len("/conversation/"):
            ]

            return self.conversation(target)

        if path.startswith("/channel/"):

            parts = path.split("/")

            if len(parts) >= 4:

                owner = parts[2]
                channel = "/".join(parts[3:])

                return self.channel_page(
                    owner,
                    channel
                )

        if path.startswith("/uploads/"):

            filename = os.path.basename(
                path[len("/uploads/"):]
            )

            filepath = os.path.join(
                UPLOAD_DIR,
                filename
            )

            if not os.path.exists(filepath):

                self.send_error(404)
                return

            mime = mimetypes.guess_type(
                filepath
            )[0]

            if not mime:
                mime = "application/octet-stream"

            size = os.path.getsize(filepath)

            self.send_response(200)

            self.send_header(
                "Content-Type",
                mime
            )

            self.send_header(
                "Content-Length",
                str(size)
            )

            self.end_headers()

            with open(filepath, "rb") as f:

                while True:

                    data = f.read(65536)

                    if not data:
                        break

                    self.wfile.write(data)

            return

        self.send_error(404)


    def do_POST(self):

        path = urlparse(self.path).path

        username = get_user(self)

        fields, files = self.parse_form()

        if path == "/setname":

            new_name = fields.get(
                "username",
                ""
            ).strip()

            if not new_name:
                return self.registration()

            users = load("users", [])

            if new_name not in users:
                users.append(new_name)

            save("users", users)

            channels = load("channels", {})

            if new_name not in channels:

                channels[new_name] = [
                    "メインチャンネル"
                ]

            save("channels", channels)

            self.send_response(303)

            self.send_header(
                "Location",
                "/"
            )

            self.send_header(
                "Set-Cookie",
                "username="
                + new_name
                + "; Path=/"
            )

            self.end_headers()

            return


        if not username:
            return self.redirect("/setname")


        if path == "/post":

            text = fields.get(
                "text",
                ""
            ).strip()

            channel = fields.get(
                "channel",
                "メインチャンネル"
            ).strip()

            filename = ""

            if "file" in files:

                original, data = files["file"]

                if data:

                    filename = (
                        uuid.uuid4().hex
                        + "_"
                        + original
                    )

                    with open(
                        os.path.join(
                            UPLOAD_DIR,
                            filename
                        ),
                        "wb"
                    ) as f:

                        f.write(data)

            posts = load("posts", [])

            posts.append({

                "id": uuid.uuid4().hex,

                "username": username,

                "channel": channel,

                "text": text,

                "filename": filename,

                "time": now(),

                "likes": 0,

                "dislikes": 0,

                "liked_users": [],

                "disliked_users": [],

                "comments": []

            })

            save("posts", posts)

            return self.redirect("/")


        if path == "/like":

            post_id = fields.get(
                "id",
                ""
            )

            posts = load("posts", [])

            for post in posts:

                if post.get("id") == post_id:

                    liked = post.setdefault(
                        "liked_users",
                        []
                    )

                    disliked = post.setdefault(
                        "disliked_users",
                        []
                    )

                    if username not in liked:

                        liked.append(username)

                        if username in disliked:

                            disliked.remove(username)

                        post["likes"] = len(liked)
                        post["dislikes"] = len(disliked)

                    break

            save("posts", posts)

            return self.redirect("/")


        if path == "/dislike":

            post_id = fields.get(
                "id",
                ""
            )

            posts = load("posts", [])

            for post in posts:

                if post.get("id") == post_id:

                    disliked = post.setdefault(
                        "disliked_users",
                        []
                    )

                    liked = post.setdefault(
                        "liked_users",
                        []
                    )

                    if username not in disliked:

                        disliked.append(username)

                        if username in liked:
                            liked.remove(username)

                    post["likes"] = len(liked)
                    post["dislikes"] = len(disliked)

                    break

            save("posts", posts)

            return self.redirect("/")


        if path == "/comment":

            post_id = fields.get(
                "id",
                ""
            )

            text = fields.get(
                "text",
                ""
            ).strip()

            if text:

                posts = load("posts", [])

                for post in posts:

                    if post.get("id") == post_id:

                        post.setdefault(
                            "comments",
                            []
                        ).append({

                            "username": username,

                            "text": text,

                            "time": now()

                        })

                        break

                save("posts", posts)

            return self.redirect("/")


        if path == "/delete_post":

            post_id = fields.get(
                "id",
                ""
            )

            posts = load("posts", [])

            new_posts = []

            for post in posts:

                if post.get("id") == post_id:

                    # 投稿者本人だけ削除できる
                    if post.get("username") == username:

                        filename = post.get(
                            "filename",
                            ""
                        )

                        if filename:

                            filepath = os.path.join(
                                UPLOAD_DIR,
                                os.path.basename(filename)
                            )

                            if os.path.exists(filepath):
                                os.remove(filepath)

                        continue

                new_posts.append(post)

            save("posts", new_posts)

            return self.redirect("/")


        if path == "/create_channel":

            channel = fields.get(
                "channel",
                ""
            ).strip()

            if channel:

                channels = load("channels", {})

                channels.setdefault(
                    username,
                    []
                )

                if channel not in channels[username]:

                    channels[username].append(
                        channel
                    )

                save("channels", channels)

            return self.redirect(
                "/mychannels"
            )


        if path == "/delete_channel":

            channel = fields.get(
                "channel",
                ""
            )

            channels = load("channels", {})

            if channel in channels.get(
                username,
                []
            ):

                channels[username].remove(
                    channel
                )

                save("channels", channels)

                posts = load("posts", [])

                new_posts = []

                for post in posts:

                    if (
                        post.get("username") == username
                        and post.get("channel") == channel
                    ):

                        filename = post.get(
                            "filename",
                            ""
                        )

                        if filename:

                            filepath = os.path.join(
                                UPLOAD_DIR,
                                os.path.basename(filename)
                            )

                            if os.path.exists(filepath):
                                os.remove(filepath)

                    else:

                        new_posts.append(post)

                save("posts", new_posts)

            return self.redirect(
                "/mychannels"
            )


        if path == "/follow":

            target = fields.get(
                "target",
                ""
            )

            follows = load("follows", {})

            follows.setdefault(
                username,
                []
            )

            if (
                target
                and target != username
                and target not in follows[username]
            ):

                follows[username].append(
                    target
                )

            save("follows", follows)

            return self.redirect("/")


        if path == "/unfollow":

            target = fields.get(
                "target",
                ""
            )

            follows = load("follows", {})

            if target in follows.get(
                username,
                []
            ):

                follows[username].remove(
                    target
                )

            save("follows", follows)

            return self.redirect("/")


        if path == "/send_message":

            target = fields.get(
                "target",
                ""
            )

            text = fields.get(
                "text",
                ""
            ).strip()

            follows = load("follows", {})

            mutual = (
                target in follows.get(username, [])
                and
                username in follows.get(target, [])
            )

            if mutual and text:

                messages = load(
                    "messages",
                    []
                )

                messages.append({

                    "from": username,

                    "to": target,

                    "text": text,

                    "time": now()

                })

                save(
                    "messages",
                    messages
                )

            return self.redirect(
                "/conversation/"
                + target
            )

        self.send_error(404)


if __name__ == "__main__":

    server = HTTPServer(
        ("0.0.0.0", PORT),
        Server
    )

    print(
        "サーバー起動中 PORT="
        + str(PORT)
    )

    server.serve_forever()
