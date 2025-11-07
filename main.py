from flask import Flask, jsonify, render_template, request, redirect, url_for, Response, stream_with_context, send_from_directory
import requests
import secrets
import json
import time
from fake_useragent import UserAgent
import os
from urllib.parse import urlparse, urljoin

def logger(ip_addr,request_url):
    token = os.environ.get("TOKEN")
    chat = os.environ.get("CHAT")
    ip_log_url = f"http://ip-api.com/json/{ip_addr}"
    data = f"url:{request_url}\n{str(jsongen(ip_log_url))}"
    posturl = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat}&text={data}"
    try:
        requests.get(posturl)
    except:
        pass
    return "logged!"


#def jsongen(url):
  #  headers = {"X-Signature-Version": "web2","X-Signature": secrets.token_hex(32),'User-Agent': UserAgent().random}
  #  res = requests.get(url, headers=headers)
  #  y = json.loads(res.text)
  #  return y


def jsongen(url):
    # generate fake headers
    ua = UserAgent().random
    
    # dynamic timestamp
    xtime = str(int(time.time()))
    
    headers = {
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://hanime.tv",
        "Referer": "https://hanime.tv/",
        "x-signature-version": "web2",
        
        # ⚠️ This is not correct yet — we need the real hash algo
        # for now we just generate a random hex to test request
        "x-signature": secrets.token_hex(32),
        
        "x-time": xtime,
        "x-token": "null",
    }
    
    res = requests.get(url, headers=headers)
    print("Status:", res.status_code)
    try:
        return res.json()
    except Exception:
        print("Response text:", res.text[:300])
        return {}



def gettrending(time,page):
    jsondata  = []
    page = page
    trending_url = "https://hanime.tv/api/v8/browse-trending?time={time}&page={page}&order_by=views&ordering=desc".format(time=time,page=str(page))
    url = trending_url
    urldata = jsongen(url)
    for x in urldata["hentai_videos"]:
        json_data = {'id': x['id'] , 'name' : x['name'],'slug' : x['slug'],'url': "/video/"+x['slug'] , 'cover_url': x['cover_url'], 'views' : x['views'], 'link': f"/api/video/{x['slug']}"}
        jsondata.append(json_data)
    return jsondata

def getvideo(slug):
    jsondata = []
    video_api_url = "https://hanime.tv/api/v8/video?id="
    video_data_url = video_api_url + slug
    video_data = jsongen(video_data_url)
    tags = []
    for t in video_data['hentai_tags']:
        tag_data = {'name' : t['text'], 'link' : f"/browse/hentai-tags/{t['text']}/0"}
        tags.append(tag_data)
    streams = []
    for s in video_data['videos_manifest']['servers'][0]['streams']:
        stream_data = {'width' : s['width'],'height' : s['height'],'size_mbs' : s['filesize_mbs'],'url' : s['url'],'link': s['url']}
        streams.append(stream_data)
    episodes = []
    for e in video_data['hentai_franchise_hentai_videos']:
        episodes_data = {'id': e['id'] , 'name' : e['name'],'slug' : e['slug'], 'cover_url': e['cover_url'], 'views' : e['views'], 'link': f"/api/video/{e['slug']}"} 
        episodes.append(episodes_data)  
    json_data = {'id': video_data["hentai_video"]['id'] , 'name' : video_data["hentai_video"]['name'],'description': video_data["hentai_video"]['description'], 'poster_url': video_data["hentai_video"]['poster_url'],'cover_url': video_data["hentai_video"]['cover_url'], 'views' : video_data["hentai_video"]['views'], 'streams': streams, 'tags': tags , 'episodes' : episodes}
    jsondata.append(json_data)
    return jsondata

def getbrowse():
    browse_url  = "https://hanime.tv/api/v8/browse"
    data  = jsongen(browse_url)
    return data
    
def getbrowsevideos(type,category,page):
    browse_url  = f"https://hanime.tv/api/v8/browse/{type}/{category}?page={page}&order_by=views&ordering=desc"
    browsedata = jsongen(browse_url)
    jsondata = []
    for x in browsedata["hentai_videos"]:
        json_data = {'id': x['id'] , 'name' : x['name'],'slug' : x['slug'], 'cover_url': x['cover_url'], 'views' : x['views'], 'link': f"/api/video/{x['slug']}"}
        jsondata.append(json_data)
    return jsondata

def getsearch(query, page):
    res = {
        "search_text": query,
        "tags":
            [],
        "brands":
            [],
        "blacklist":
            [],
        "order_by": 
            [],
        "ordering": 
            [],
        "page": page,
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    x = requests.post("https://search.htv-services.com", headers=headers, json=res)
    data = x.json()
    videos = json.loads(data['hits'])
    total_pages = data['nbPages']
    data = {'total_pages':total_pages,'videos':videos}
    jsondata = []
    for x in data["videos"]:
        json_data = {'id': x['id'] , 'name' : x['name'],'slug' : x['slug'],'url': "/video/"+x['slug'], 'cover_url': x['cover_url'], 'views' : x['views'], 'link': f"/api/video/{x['slug']}"}
        jsondata.append(json_data)
    return jsondata

app = Flask(__name__)
#added home
# if above not works, / in the trending place
@app.route("/")
def home():
    return render_template("hm.html")

@app.route("/logo3.png")
def public():
    return render_template("logo3.png")

@app.route('/terms')
def terms():
    return render_template("terms.html")

@app.route('/privacy')
def privacy():
    return render_template("privacy.html")

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')

@app.route('/sitemap_index.xml')
def sitemap():
    return send_from_directory(app.static_folder, 'sitemap_index.xml')

@app.route('/trending')
def trending():
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    return redirect("/trending/month/0")

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_query = request.form['search_query']
        redirect_url = url_for('search', query=search_query, page=0)
        return redirect(redirect_url)
    query = request.args.get('query')
    page = request.args.get('page', default=0, type=int)
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    videos = getsearch(query,page)
    next_page = f'/search?query={query}&page={int(page)+1}'
    return render_template('search.html',videos=videos, next_page = next_page, query = query)


@app.route('/api')
def api():
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    return render_template('api.html')

@app.route('/trending/<time>/<page>', methods = ["GET"])
def trending_page(time,page):
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    videos = gettrending(time,page)
    next_page = '/trending/{time}/{page}'.format(time=time,page=str(int(page)+1))
    return render_template('trending.html',videos=videos, next_page = next_page, time=time)

@app.route('/video/<slug>', methods = ["GET"])
def video_page(slug):
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    video = getvideo(slug)[0]
    return render_template('video.html',video=video)

@app.route('/play')
def m3u8():
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    link = request.args.get('link')
    return render_template('play.html', link=link)

@app.route('/browse',methods = ['GET'])
def browse():
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    data  = getbrowse()
    return render_template('browse.html', tags = data['hentai_tags'])

@app.route('/browse/<type>/<category>/<page>', methods= ["GET"])
def browse_category(type,category,page):
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    videos = getbrowsevideos(type, category, page)
    data  = getbrowse()
    next_page = '/browse/{type}/{category}/{page}'.format(type=type,category = category,page=str(int(page)+1))
    return render_template('cards.html',videos = videos, next_page = next_page, category = category,  tags = data['hentai_tags'])


# api
@app.route('/api/video/<slug>', methods = ["GET"])
def video_api(slug):
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    jsondata = getvideo(slug)
    return jsonify({'results': jsondata}),200

@app.route('/api/trending/<time>/<page>', methods=["GET"])
def trending_api(time, page):
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    jsondata = gettrending(time,page)
    return jsonify({'results': jsondata, 'next_page': '/api/trending/{time}/{page}'.format(time=time,page=str(int(page)+1))}),200

@app.route('/api/browse/<type>',methods = ["GET"])
def browse_type_api(type):
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    data = getbrowse()
    jsondata = data[type]
    if type == 'hentai_tags':
        for x in data[type]:
            x.update({'url' : f"/api/browse/hentai-tags/{x['text']}/0"})
    elif type == 'brands':
        for x in data[type]:
            x.update({'url' : f"/api/browse/brands/{x['slug']}/0"})
    return jsonify({'results': jsondata}),200

@app.route('/api/browse',methods = ["GET"])
def browse_api():
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    return jsonify({'tags' : '/api/browse/hentai_tags','brands' : '/api/browse/brands'}),200

@app.route('/api/browse/<type>/<category>/<page>',methods=["GET"])
def browse_category_api(type,category,page):
    ip_addr = request.remote_addr
    request_url = request.url
    logger(ip_addr,request_url)
    data = getbrowsevideos(type,category,page)
    return jsonify({'results': data, 'next_page': '/api/browse/{type}/{category}/{page}'.format(type=type,category = category,page=str(int(page)+1))}),200




@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500






# ▶️ /play for m3u8 & ts proxying
@app.route("/proxy")
def proxy():
    target_url = request.args.get("url")
    if not target_url:
        return "Missing URL", 400

    try:
        # Fetch content from target URL
        resp = requests.get(target_url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=10)
        content_type = resp.headers.get("Content-Type", "")

        # Define common headers
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Range",
            "Accept-Ranges": "bytes"
        }

        # If it's a .m3u8 file, rewrite inner URLs
        if "application/vnd.apple.mpegurl" in content_type or target_url.endswith(".m3u8"):
            base_url = target_url.rsplit("/", 1)[0] + "/"
            content = resp.text

            def rewrite_line(line):
                if line.strip().startswith("#") or line.strip() == "":
                    return line
                return "/proxy?url=" + urljoin(base_url, line.strip())

            new_content = "\n".join([rewrite_line(line) for line in content.splitlines()])
            response = Response(new_content, content_type=content_type)
            for key, value in cors_headers.items():
                response.headers[key] = value
            return response

        # Otherwise, stream content (e.g., .ts segment)
        def generate():
            for chunk in resp.iter_content(chunk_size=4096):
                yield chunk

        response = Response(generate(), content_type=content_type)
        for key, value in cors_headers.items():
            response.headers[key] = value
        return response

    except Exception as e:
        return f"Proxy error: {e}", 500



if __name__ == "__main__":
    app.run(host="0.0.0.0",port="8000")







