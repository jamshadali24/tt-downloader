from urllib.parse import urlparse
from flask import Flask, request, jsonify, Response, render_template_string
import requests
import yt_dlp

app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TikTok Downloader</title>
<style>
body{font-family:sans-serif;background:#111;color:#fff;margin:0;padding:20px;text-align:center}
input{width:100%;padding:14px;border-radius:8px;border:0;font-size:16px;box-sizing:border-box}
button,a.btn{display:block;width:100%;padding:14px;margin-top:12px;border:0;border-radius:8px;
background:#fe2c55;color:#fff;font-size:17px;text-decoration:none;box-sizing:border-box}
img{max-width:60%;border-radius:8px;margin-top:16px}
#msg{margin-top:14px;color:#ffb3c0}
</style>
</head>
<body>
<h2>TikTok Video Downloader (No Watermark)</h2>
<input id="u" placeholder="Paste TikTok link here">
<button onclick="go()">Download</button>
<div id="msg"></div>
<div id="out"></div>
<script>
async function go(){
  const u=document.getElementById('u').value.trim();
  const msg=document.getElementById('msg'), out=document.getElementById('out');
  out.innerHTML=''; msg.textContent='Please wait...';
  try{
    const r=await fetch('/api/info?url='+encodeURIComponent(u));
    const d=await r.json();
    if(!r.ok){msg.textContent=d.error||'Error';return;}
    msg.textContent='';
    const q=encodeURIComponent(u);
    out.innerHTML=(d.thumbnail?'<img src="'+d.thumbnail+'">':'')+
      '<p>'+d.title+'</p>'+
      '<a class="btn" href="/download?kind=video&url='+q+'">Download Video</a>'+
      '<a class="btn" href="/download?kind=audio&url='+q+'">Download Audio</a>';
  }catch(e){msg.textContent='Something went wrong, please try again';}
}
</script>
</body>
</html>"""


def valid(url):
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host == "tiktok.com" or host.endswith(".tiktok.com")


def resolve(url, kind):
    fmt = "bestaudio/best" if kind == "audio" else "best"
    opts = {"quiet": True, "no_warnings": True, "format": fmt}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info


@app.route("/")
def home():
    return render_template_string(PAGE)


@app.route("/api/info")
def api_info():
    url = request.args.get("url", "")
    if not valid(url):
        return jsonify(error="Please enter a valid TikTok link"), 400
    try:
        info = resolve(url, "video")
    except Exception:
        return jsonify(error="Video not found. Check the link or try again later"), 502
    return jsonify(title=(info.get("title") or "TikTok")[:120],
                   thumbnail=info.get("thumbnail"))


@app.route("/download")
def download():
    url = request.args.get("url", "")
    kind = request.args.get("kind", "video")
    if not valid(url):
        return "invalid link", 400
    try:
        info = resolve(url, kind)
        direct = info["url"]
        headers = info.get("http_headers", {})
        upstream = requests.get(direct, headers=headers, stream=True, timeout=30)
    except Exception:
        return "download failed", 502
    ext = "mp3" if kind == "audio" and info.get("vcodec") == "none" else "mp4"
    name = "tiktok_%s.%s" % (info.get("id", "video"), ext)
    resp = Response(upstream.iter_content(chunk_size=65536),
                    content_type=upstream.headers.get("Content-Type", "video/mp4"))
    resp.headers["Content-Disposition"] = 'attachment; filename="%s"' % name
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
