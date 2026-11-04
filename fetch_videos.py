"""YouTubeからイナズマイレブンの動画を集めて data.json を作るプログラム。"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API_KEY = os.environ.get("YOUTUBE_API_KEY")
KEYWORDS = ["イナズマイレブン", "イナイレ"]   # 検索するキーワード
THRESHOLD = 5000                               # この再生数以上を載せる
SHORT_MAX_SECONDS = 180                        # この秒数以下の動画は、ショートかどうかを調べる（3分）
SURE_SHORT_SECONDS = 60                        # この秒数以下は、調べずにショートとして除く
PAGES = 2                                      # 検索結果を何ページ分取るか（1ページ50件）
WINDOWS = {"d": 1, "w": 7, "m": 30}            # 今日=24時間 / 今週=7日 / 今月=30日
MAX_PER_WINDOW = 30                            # 期間ごとに載せる最大件数
BASE = "https://www.googleapis.com/youtube/v3"


def call(endpoint, params):
    query = urllib.parse.urlencode(dict(params, key=API_KEY))
    try:
        with urllib.request.urlopen(f"{BASE}/{endpoint}?{query}", timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        print(f"YouTube API error {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
        sys.exit(1)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def search_ids(keyword, since):
    ids, token = [], None
    for _ in range(PAGES):
        params = {
            "part": "id", "q": keyword, "type": "video", "order": "viewCount",
            "publishedAfter": iso(since), "maxResults": 50,
            "regionCode": "JP", "relevanceLanguage": "ja",
        }
        if token:
            params["pageToken"] = token
        data = call("search", params)
        ids += [i["id"]["videoId"] for i in data.get("items", [])]
        token = data.get("nextPageToken")
        if not token:
            break
    return ids


def parse_seconds(s):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", s or "")
    if not m:
        return 0
    h, mi, se = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + se


def fmt_duration(sec):
    h, rem = divmod(sec, 3600)
    mi, se = divmod(rem, 60)
    return f"{h}:{mi:02d}:{se:02d}" if h else f"{mi}:{se:02d}"


def get_details(ids):
    out = {}
    ids = list(ids)
    for i in range(0, len(ids), 50):
        data = call("videos", {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(ids[i:i + 50]), "maxResults": 50,
        })
        for it in data.get("items", []):
            stats = it.get("statistics", {})
            if "viewCount" not in stats:
                continue
            seconds = parse_seconds(it["contentDetails"].get("duration"))
            if seconds == 0:      # ライブ配信・プレミア公開などは除く
                continue
            thumbs = it["snippet"].get("thumbnails", {})
            thumb = (thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
            out[it["id"]] = {
                "id": it["id"],
                "title": it["snippet"]["title"],
                "channel": it["snippet"]["channelTitle"],
                "views": int(stats["viewCount"]),
                "published": it["snippet"]["publishedAt"],
                "seconds": seconds,
                "duration": fmt_duration(seconds),
                "thumb": thumb,
            }
    return out


_short_cache = {}


def is_short(v):
    """ショート動画ならTrue。3分以内の動画だけ、shortsのURLが通常の再生ページに転送されるかで判定する。
    調べられなかったときは、ショートとして扱う（除く）。"""
    if v["seconds"] > SHORT_MAX_SECONDS:
        return False
    if v["seconds"] <= SURE_SHORT_SECONDS:
        return True
    if v["id"] not in _short_cache:
        try:
            req = urllib.request.Request(
                f"https://www.youtube.com/shorts/{v['id']}",
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                         "Accept-Language": "ja"},
            )
            with urllib.request.urlopen(req, timeout=15) as res:
                final = res.geturl()
            _short_cache[v["id"]] = "/watch" not in final
        except Exception:
            _short_cache[v["id"]] = True
    return _short_cache[v["id"]]


def main():
    if not API_KEY:
        print("YOUTUBE_API_KEY が設定されていません")
        sys.exit(1)
    now = datetime.now(timezone.utc)
    since = {k: now - timedelta(days=d) for k, d in WINDOWS.items()}

    found = {k: set() for k in WINDOWS}
    for k in WINDOWS:
        for kw in KEYWORDS:
            found[k].update(search_ids(kw, since[k]))

    details = get_details(set().union(*found.values()))

    result = {}
    for k in WINDOWS:
        items = [
            details[i] for i in found[k]
            if i in details
            and details[i]["views"] >= THRESHOLD
            and details[i]["published"] >= iso(since[k])
        ]
        items.sort(key=lambda v: v["views"], reverse=True)
        result[k] = [v for v in items if not is_short(v)][:MAX_PER_WINDOW]

    jst = timezone(timedelta(hours=9))
    out = {"updated": now.astimezone(jst).isoformat(timespec="minutes"),
           "threshold": THRESHOLD, "windows": result}
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print({k: len(v) for k, v in result.items()})


if __name__ == "__main__":
    main()
