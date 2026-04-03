import json
import os
import re
import threading
import time
from datetime import datetime
from html import unescape
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "rankings.json")

NATE_RANK_URL = "https://news.nate.com/rank/interest?sc={category}&p=day&date={date}"
CATEGORIES = {
    "ent": "연예",
    "eco": "경제",
}
MAX_RANK = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

EXCLUDED_SOURCE_HOST_KEYWORDS = (
    "news.nate.com",
    "nate.com/etc/",
    "nateimg.co.kr",
    "doubleclick.net",
    "ad.",
)


def ensure_dirs() -> None:
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)


def normalize_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"https://news.nate.com{url}"
    return url


def fetch_html(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as res:
        raw = res.read()

    for encoding in ("cp949", "euc-kr", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def strip_tags(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", no_tags).strip()
    return unescape(clean)


def extract_rank_items(html: str, limit: int = MAX_RANK) -> list[dict]:
    rank_markers = list(re.finditer(r'<dl class="mduRank rank(\d+)">', html))
    if not rank_markers:
        return []

    items = []
    for idx, marker in enumerate(rank_markers):
        rank = int(marker.group(1))
        if rank > limit:
            continue

        start = marker.start()
        end = rank_markers[idx + 1].start() if idx + 1 < len(rank_markers) else len(html)
        segment = html[start:end]

        href_m = re.search(r'<a href="([^"]+)"', segment)
        title_m = re.search(r"<h2[^>]*>(.*?)</h2>", segment, flags=re.S)
        media_m = re.search(r'<span class="medium">([^<]+)', segment)
        img_m = re.search(r'<img src="([^"]+)"', segment)

        if not href_m or not title_m:
            continue

        link = normalize_url(href_m.group(1))
        title = strip_tags(title_m.group(1))
        media = strip_tags(media_m.group(1)) if media_m else ""
        thumb = normalize_url(img_m.group(1)) if img_m else ""

        items.append(
            {
                "rank": rank,
                "title": title,
                "media": media,
                "url": link,
                "nateUrl": link,
                "thumbnail": thumb,
                # og:image가 차단되어 깨질 때를 대비한 안전 폴백 이미지
                "fallbackThumbnail": thumb,
            }
        )

    items.sort(key=lambda x: x["rank"])
    return items[:limit]


def fetch_og_image(article_url: str) -> str:
    # 원문 기사 HTML에서 og:image를 뽑아 고화질 썸네일로 사용한다.
    try:
        html = fetch_html(article_url, timeout=15)
    except URLError:
        return ""

    og = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        flags=re.I,
    )
    if og:
        return normalize_url(og.group(1))

    tw = re.search(
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        flags=re.I,
    )
    return normalize_url(tw.group(1)) if tw else ""


def is_excluded_source_url(url: str) -> bool:
    # 광고/내부 링크는 원문 링크 후보에서 제외한다.
    lower = url.lower()
    return any(token in lower for token in EXCLUDED_SOURCE_HOST_KEYWORDS)


def resolve_original_article_url(nate_url: str) -> str:
    # 네이트 뷰 페이지에서 실제 언론사 원문 링크를 찾는다.
    # 1) 원문보기/기사원문 버튼 우선
    # 2) 없으면 외부 링크 중 첫 번째를 사용
    try:
        html = fetch_html(nate_url, timeout=15)
    except URLError:
        return nate_url

    direct_patterns = [
        r'<a[^>]+href="([^"]+)"[^>]*>원문보기',
        r'<a[^>]+href="([^"]+)"[^>]*>기사원문',
    ]
    for pat in direct_patterns:
        m = re.search(pat, html, flags=re.I)
        if m:
            candidate = normalize_url(m.group(1))
            if candidate and not is_excluded_source_url(candidate):
                return candidate

    for m in re.finditer(r'href="([^"]+)"', html):
        candidate = normalize_url(m.group(1))
        if not candidate:
            continue
        if not (candidate.startswith("http://") or candidate.startswith("https://")):
            continue
        if is_excluded_source_url(candidate):
            continue

        host = urlparse(candidate).netloc.lower()
        if not host:
            continue
        if "nate.com" in host:
            continue
        return candidate

    return nate_url


def enrich_missing_thumbnails(items: list[dict]) -> None:
    # 썸네일 화질 개선:
    # 기존에는 "썸네일이 없을 때만" og:image를 넣었는데,
    # 이제는 항상 og:image를 먼저 시도하고 실패하면 기존 썸네일을 유지한다.
    for item in items:
        og_image = fetch_og_image(item["url"])
        if og_image:
            item["thumbnail"] = og_image
        else:
            item["thumbnail"] = item.get("fallbackThumbnail", item.get("thumbnail", ""))
        time.sleep(0.08)


def refresh_rankings() -> dict:
    date_key = datetime.now().strftime("%Y%m%d")
    payload = {
        "updatedAt": datetime.now().isoformat(timespec="seconds"),
        "date": date_key,
        "categories": {},
    }

    for key, label in CATEGORIES.items():
        url = NATE_RANK_URL.format(category=key, date=date_key)
        html = fetch_html(url)
        items = extract_rank_items(html, limit=MAX_RANK)

        for item in items:
            nate_url = item.get("nateUrl") or item.get("url") or ""
            if not nate_url:
                continue
            item["url"] = resolve_original_article_url(nate_url)
            time.sleep(0.05)

        enrich_missing_thumbnails(items)
        payload["categories"][key] = {
            "label": label,
            "sourceUrl": url,
            "items": items,
        }

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return payload


def read_cached_rankings() -> dict:
    if not os.path.exists(CACHE_FILE):
        return refresh_rankings()
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def scheduler_loop() -> None:
    # 5분마다 데이터 파일(data/rankings.json)을 갱신한다.
    # 주의: 이 방식은 "상시 실행 서버"에서만 유효하다.
    # Vercel 같은 서버리스 환경에서는 Vercel Cron을 쓰는 것이 맞다.
    while True:
        try:
            refresh_rankings()
            print(f"[scheduler] refreshed at {datetime.now().isoformat(timespec='seconds')}")
        except Exception as exc:
            print(f"[scheduler] refresh failed: {exc}")
        time.sleep(300)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/rankings":
            try:
                self._send_json(read_cached_rankings())
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        if self.path == "/api/refresh":
            try:
                self._send_json(refresh_rankings())
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        return super().do_GET()


def main() -> None:
    ensure_dirs()
    try:
        # 서버 시작 직후 1회 즉시 갱신
        refresh_rankings()
        print("[startup] initial data fetch complete")
    except Exception as exc:
        print(f"[startup] initial fetch failed: {exc}")

    # 백그라운드 스케줄러 시작 (상시 실행 환경용)
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", 8000), Handler)
    print("Server running on http://localhost:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
