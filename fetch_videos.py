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
THRESHOLD = 10000                              # この再生数以上を載せる
WINDOWS = {"d": 1, "w": 7, "m": 30}            # 今日=24時間 / 今週=7日 / 今月=30日
MAX_PER_WINDOW = 30                            # 1つの期間に載せる最大件数
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
    data = call("search", {
        "part": "id", "q": keyword, "type": "video", "order": "viewCount",
        "publishedAfter": iso(since), "maxResults": 50,
        "regionCode": "JP", "relevanceLanguage": "ja",
    })
    return [i["id"]["videoId"] for i in data.get("items", [])]


def fmt_duration(s):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    h, mi, se = (int(x or 0) for x in m.groups()) if m else (0, 0, 0)
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
            thumbs = it["snippet"].get("thumbnails", {})
            thumb = (thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
            out[it["id"]] = {
                "id": it["id"],
                "title": it["snippet"]["title"],
                "channel": it["snippet"]["channelTitle"],
                "views": int(stats["viewCount"]),
                "published": it["snippet"]["publishedAt"],
                "duration": fmt_duration(it["contentDetails"].get("duration")),
                "thumb": thumb,
            }
    return out


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
        result[k] = items[:MAX_PER_WINDOW]

    jst = timezone(timedelta(hours=9))
    out = {"updated": now.astimezone(jst).isoformat(timespec="minutes"),
           "threshold": THRESHOLD, "windows": result}
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print({k: len(v) for k, v in result.items()})


if __name__ == "__main__":
    main()
