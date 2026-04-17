from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_API_URL = "https://hanime-python-api-eta.vercel.app"
SEARCH_API_URL = "https://search.htv-services.com"
BROWSE_CACHE_TTL_SECONDS = 300


@dataclass
class ApiResult:
    data: dict[str, Any] | None
    error: str | None = None


class HanimeApiClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.6,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET", "POST"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "User-Agent": "HanimeHomies/2.1 (+Flask)",
                "Accept": "application/json, text/plain, */*",
            }
        )

    def get_json(self, path: str, params: dict[str, Any] | None = None, timeout: int = 15) -> ApiResult:
        url = f"{BASE_API_URL}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=timeout)
            if not resp.ok:
                return ApiResult(data=None, error=f"API error {resp.status_code} from {path}")
            payload = resp.json()
            if not isinstance(payload, dict):
                return ApiResult(data=None, error=f"Unexpected response shape from {path}")
            return ApiResult(data=payload, error=None)
        except requests.exceptions.RequestException:
            return ApiResult(data=None, error="Unable to reach upstream API. Please retry.")
        except ValueError:
            return ApiResult(data=None, error="Invalid API response format.")

    def post_json(self, url: str, payload: dict[str, Any], timeout: int = 15) -> ApiResult:
        try:
            resp = self.session.post(url, json=payload, timeout=timeout)
            if not resp.ok:
                return ApiResult(data=None, error=f"Search API error {resp.status_code}")
            body = resp.json()
            if not isinstance(body, dict):
                return ApiResult(data=None, error="Unexpected search API response shape")
            return ApiResult(data=body, error=None)
        except requests.exceptions.RequestException:
            return ApiResult(data=None, error="Unable to reach search API. Please retry.")
        except ValueError:
            return ApiResult(data=None, error="Invalid search API response format.")


api_client = HanimeApiClient()
app = Flask(__name__)

browse_cache: dict[str, Any] = {"expires_at": 0.0, "data": None}


def logger(ip_addr: str | None, request_url: str) -> None:
    token = os.environ.get("TOKEN")
    chat = os.environ.get("CHAT")
    if not token or not chat or not ip_addr:
        return

    ip_log_url = f"http://ip-api.com/json/{ip_addr}"
    try:
        ip_data = api_client.session.get(ip_log_url, timeout=10).json()
        api_client.session.get(
            f"https://api.telegram.org/bot{token}/sendMessage",
            params={"chat_id": chat, "text": f"url:{request_url}\n{ip_data}"},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return


def normalize_video(item: dict[str, Any]) -> dict[str, Any]:
    slug = item.get("slug", "")
    return {
        "id": item.get("id"),
        "name": item.get("name", "Untitled"),
        "slug": slug,
        "url": f"/video/{slug}" if slug else "#",
        "cover_url": item.get("cover_url") or item.get("poster_url") or "",
        "poster_url": item.get("poster_url") or item.get("cover_url") or "",
        "views": item.get("views", 0),
        "likes": item.get("likes", 0),
        "duration_in_ms": item.get("duration_in_ms"),
        "released_at": item.get("released_at"),
        "brand": (item.get("brand") or {}).get("name") if isinstance(item.get("brand"), dict) else item.get("brand"),
    }


def _pick(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    for key in keys:
        if key in data and data.get(key) not in [None, ""]:
            return data.get(key)
    return default


def normalize_brand(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": _pick(item, ["title", "name", "text"], "Unknown Brand"),
        "slug": item.get("slug") or "",
        "count": item.get("count", 0),
        "logo_url": _pick(item, ["logo_url", "image_url", "cover_url"]),
        "website_url": item.get("website_url"),
        "email": item.get("email"),
        "raw": item,
    }


def normalize_tag(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "text": _pick(item, ["text", "title", "name"], "Unknown"),
        "slug": item.get("slug") or "",
        "count": item.get("count", 0),
        "description": item.get("description"),
        "image_url": _pick(item, ["tall_image_url", "cover_url", "image_url"]),
        "raw": item,
    }


def normalize_category(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": _pick(item, ["title", "name", "text", "slug"], "Unknown Category"),
        "slug": item.get("slug") or _pick(item, ["title", "name", "text"], "").lower().replace(" ", "-"),
        "count": item.get("count", 0),
        "image_url": _pick(item, ["cover_url", "image_url", "logo_url", "tall_image_url"]),
        "raw": item,
    }


def get_browse_data(force_refresh: bool = False) -> ApiResult:
    now = time.time()
    if not force_refresh and browse_cache.get("data") and now < float(browse_cache.get("expires_at", 0)):
        return ApiResult(data=browse_cache["data"])

    result = api_client.get_json("/browse")
    if result.error or not result.data:
        return ApiResult(data=None, error=result.error or "Browse data unavailable")

    data = result.data
    if not isinstance(data, dict):
        return ApiResult(data=None, error="Invalid browse payload")

    brands_raw = data.get("brands", []) if isinstance(data.get("brands"), list) else []
    tags_raw = data.get("hentai_tags", []) if isinstance(data.get("hentai_tags"), list) else []

    category_keys = [key for key, value in data.items() if key not in {"brands", "hentai_tags"} and isinstance(value, list)]
    categories = [
        {"key": key, "items": [normalize_category(item) for item in data.get(key, []) if isinstance(item, dict)]}
        for key in category_keys
    ]

    metadata_counts: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, list):
            metadata_counts[f"{key}_count"] = len(value)
        elif isinstance(value, (int, float, str, bool)):
            metadata_counts[key] = value

    browse_payload = {
        "raw": data,
        "brands": [normalize_brand(item) for item in brands_raw if isinstance(item, dict)],
        "tags": [normalize_tag(item) for item in tags_raw if isinstance(item, dict)],
        "categories": categories,
        "metadata": metadata_counts,
        "fetched_at": int(now),
        "cache_ttl_seconds": BROWSE_CACHE_TTL_SECONDS,
    }

    browse_cache["data"] = browse_payload
    browse_cache["expires_at"] = now + BROWSE_CACHE_TTL_SECONDS
    return ApiResult(data=browse_payload)


def get_homepage_payload() -> dict[str, Any]:
    recent_result = api_client.get_json("/getLanding/recent")
    browse_result = get_browse_data()

    error_messages = [msg for msg in [recent_result.error, browse_result.error] if msg]
    recent_data = recent_result.data or {}
    browse_data = browse_result.data or {}

    videos = [normalize_video(item) for item in recent_data.get("hentai_videos", [])]
    sections = []
    for key in ["latest_updates", "trending", "most_viewed"]:
        raw_list = recent_data.get(key, [])
        if isinstance(raw_list, list) and raw_list:
            sections.append({"title": key.replace("_", " ").title(), "items": [normalize_video(v) for v in raw_list]})

    return {
        "videos": videos,
        "sections": sections,
        "tags": browse_data.get("tags", []),
        "brands": browse_data.get("brands", []),
        "error": " | ".join(error_messages) if error_messages else None,
    }


def get_video_payload(slug: str) -> ApiResult:
    video_result = api_client.get_json(f"/getVideo/{slug}")
    if video_result.error or not video_result.data:
        return ApiResult(data=None, error=video_result.error or "Video not found.")

    data = video_result.data
    hentai_video = data.get("hentai_video", {})

    tags = [
        {
            "name": tag.get("text", "Unknown"),
            "link": f"/browse/hentai-tags/{tag.get('text', '')}/0",
        }
        for tag in data.get("hentai_tags", [])
        if tag.get("text")
    ]

    streams: list[dict[str, Any]] = []
    for server in (data.get("videos_manifest", {}) or {}).get("servers", []):
        for stream in server.get("streams", []):
            streams.append(
                {
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "size_mbs": stream.get("filesize_mbs"),
                    "url": stream.get("url"),
                }
            )

    episodes = [normalize_video(item) for item in data.get("hentai_franchise_hentai_videos", [])]
    payload = {
        "id": hentai_video.get("id"),
        "name": hentai_video.get("name", "Untitled"),
        "description": hentai_video.get("description") or "No description available.",
        "poster_url": hentai_video.get("poster_url") or hentai_video.get("cover_url") or "",
        "cover_url": hentai_video.get("cover_url") or hentai_video.get("poster_url") or "",
        "views": hentai_video.get("views", 0),
        "likes": hentai_video.get("likes", 0),
        "released_at": hentai_video.get("released_at"),
        "tags": tags,
        "streams": sorted(streams, key=lambda s: int(s.get("height") or 0), reverse=True),
        "episodes": episodes,
    }
    return ApiResult(data=payload)


def get_browse_payload(category_type: str, category: str, page: int) -> ApiResult:
    browse_data = api_client.get_json(
        f"/browse/{category_type}/{category}",
        params={"page": page, "order_by": "views", "ordering": "desc"},
    )
    if browse_data.error:
        return ApiResult(data=None, error=browse_data.error)

    tags_data = get_browse_data()
    videos = [normalize_video(item) for item in (browse_data.data or {}).get("hentai_videos", [])]
    return ApiResult(
        data={
            "videos": videos,
            "tags": (tags_data.data or {}).get("tags", []),
            "next_page": f"/browse/{category_type}/{category}/{page + 1}",
        }
    )


def get_search_payload(query: str, page: int) -> ApiResult:
    payload = {
        "search_text": query,
        "tags": [],
        "brands": [],
        "blacklist": [],
        "order_by": "views",
        "ordering": "desc",
        "page": page,
    }
    result = api_client.post_json(SEARCH_API_URL, payload)
    if result.error or not result.data:
        return ApiResult(data=None, error=result.error)

    try:
        raw_hits = result.data.get("hits", "[]")
        hits = raw_hits if isinstance(raw_hits, list) else json.loads(raw_hits)
    except Exception:
        hits = []

    videos = [normalize_video(item) for item in hits]
    total_pages = int(result.data.get("nbPages", 0))
    return ApiResult(data={"videos": videos, "total_pages": total_pages})


@app.route("/")
@app.route("/home")
def home() -> str:
    logger(request.remote_addr, request.url)
    payload = get_homepage_payload()
    return render_template("home.html", **payload)


@app.route("/logo3.png")
def public() -> Response:
    return send_from_directory(app.static_folder, "logo3.png")


@app.route("/terms")
def terms() -> str:
    return render_template("terms.html")


@app.route("/privacy")
def privacy() -> str:
    return render_template("privacy.html")


@app.route("/robots.txt")
def robots() -> Response:
    return send_from_directory(app.static_folder, "robots.txt")


@app.route("/sitemap_index.xml")
def sitemap() -> Response:
    return send_from_directory(app.static_folder, "sitemap_index.xml")


@app.route("/search", methods=["GET", "POST"])
def search() -> str:
    if request.method == "POST":
        search_query = request.form.get("search_query", "").strip()
        if not search_query:
            return redirect(url_for("search"))
        return redirect(url_for("search", query=search_query, page=0))

    query = (request.args.get("query") or "").strip()
    page = request.args.get("page", default=0, type=int)
    logger(request.remote_addr, request.url)

    if not query:
        return render_template("search.html", videos=[], next_page=None, query="", error=None)

    result = get_search_payload(query, page)
    videos = (result.data or {}).get("videos", [])
    next_page = f"/search?query={query}&page={page + 1}" if videos else None
    return render_template(
        "search.html",
        videos=videos,
        next_page=next_page,
        query=query,
        error=result.error,
    )


@app.route("/trending/<time>/<int:page>", methods=["GET"])
def trending_page(time: str, page: int) -> str:
    logger(request.remote_addr, request.url)
    result = api_client.get_json(f"/getLanding/{time}")
    if result.error:
        return render_template("trending.html", videos=[], next_page=None, time=time, error=result.error)

    videos = [normalize_video(item) for item in (result.data or {}).get("hentai_videos", [])]
    next_page = f"/trending/{time}/{page + 1}"
    return render_template("trending.html", videos=videos, next_page=next_page, time=time, error=None)


@app.route("/video/<slug>", methods=["GET"])
def video_page(slug: str) -> str:
    logger(request.remote_addr, request.url)
    result = get_video_payload(slug)
    if result.error:
        return render_template("video.html", video=None, error=result.error)
    return render_template("video.html", video=result.data, error=None)


@app.route("/browse", methods=["GET"])
def browse() -> str:
    logger(request.remote_addr, request.url)
    return render_template("browse.html")


@app.route("/browse/<category_type>/<category>/<int:page>", methods=["GET"])
def browse_category(category_type: str, category: str, page: int) -> str:
    logger(request.remote_addr, request.url)
    result = get_browse_payload(category_type, category, page)
    if result.error:
        return render_template(
            "cards.html",
            videos=[],
            next_page=None,
            category=category,
            tags=[],
            error=result.error,
        )

    return render_template(
        "cards.html",
        videos=result.data["videos"],
        next_page=result.data["next_page"],
        category=category,
        tags=result.data["tags"],
        error=None,
    )


@app.route("/api/video/<slug>", methods=["GET"])
def video_api(slug: str) -> tuple[Response, int]:
    result = get_video_payload(slug)
    if result.error:
        return jsonify({"error": result.error}), 502
    return jsonify({"result": result.data}), 200


@app.route("/api/trending/recent", methods=["GET"])
def trending_recent_api() -> tuple[Response, int]:
    payload = get_homepage_payload()
    return jsonify(payload), (502 if payload.get("error") else 200)


@app.route("/api/browse", methods=["GET"])
def browse_api() -> tuple[Response, int]:
    force_refresh = request.args.get("refresh") == "1"
    result = get_browse_data(force_refresh=force_refresh)
    if result.error:
        return jsonify({"error": result.error}), 502
    return jsonify(result.data), 200


@app.route("/api/browse/<category_type>", methods=["GET"])
def browse_type_api(category_type: str) -> tuple[Response, int]:
    data = get_browse_data()
    if data.error:
        return jsonify({"error": data.error}), 502

    values = (data.data or {}).get(category_type, [])
    return jsonify({"results": values}), 200


@app.route("/api/browse/<category_type>/<category>/<int:page>", methods=["GET"])
def browse_category_api(category_type: str, category: str, page: int) -> tuple[Response, int]:
    data = get_browse_payload(category_type, category, page)
    if data.error:
        return jsonify({"error": data.error}), 502
    return jsonify({"results": data.data["videos"], "next_page": data.data["next_page"]}), 200


@app.errorhandler(404)
def page_not_found(_e: Exception) -> tuple[str, int]:
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(_e: Exception) -> tuple[str, int]:
    return render_template("500.html"), 500


@app.route("/proxy")
def proxy() -> Response | tuple[str, int] | tuple[str, int, dict[str, str]]:
    target_url = request.args.get("url", "")
    if not target_url:
        return "Missing 'url' parameter", 400

    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"}:
        return "Invalid target URL", 400

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.hanime.tv/",
            "Origin": "https://www.hanime.tv",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        resp = api_client.session.get(target_url, headers=headers, stream=True, timeout=20)

        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Range",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
        }

        if resp.status_code >= 400:
            return f"Upstream request failed: {resp.status_code}", resp.status_code, cors_headers

        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        if "application/vnd.apple.mpegurl" in content_type or target_url.endswith(".m3u8"):
            base_url = target_url.rsplit("/", 1)[0] + "/"
            body = "\n".join(
                line
                if line.strip().startswith("#") or not line.strip()
                else "/proxy?url=" + urljoin(base_url, line.strip())
                for line in resp.text.splitlines()
            )
            response = Response(body, content_type=content_type)
        else:
            response = Response(resp.iter_content(chunk_size=8192), content_type=content_type)

        for k, v in cors_headers.items():
            response.headers[k] = v
        return response
    except requests.exceptions.RequestException as exc:
        return f"Proxy error: {exc}", 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
