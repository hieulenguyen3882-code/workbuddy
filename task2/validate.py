"""
校验 capture 证据完整性。
只做事实校验，不做判断。
"""
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = ["caption", "author", "stats", "comments"]
REQUIRED_STATS = ["likeCount", "commentCount", "collectCount", "shareCount"]


def validate(data: dict) -> dict:
    """返回校验结果：缺失字段、证据强度、是否可判断。"""
    result = {
        "ok": data.get("ok") is True,
        "url": data.get("url", ""),
        "missing_fields": [],
        "missing_stats": [],
        "comment_count": 0,
        "evidence_level": "none",  # strong / partial / weak / none
        "can_judge": False,
    }

    if not result["ok"]:
        result["reason"] = data.get("reason", "未读取内容")
        return result

    fields = data.get("fields", {})
    for f in REQUIRED_FIELDS:
        v = fields.get(f)
        if v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and len(v) == 0):
            result["missing_fields"].append(f)

    stats = fields.get("stats", {})
    for s in REQUIRED_STATS:
        if not stats.get(s):
            result["missing_stats"].append(s)

    comments = fields.get("comments", [])
    result["comment_count"] = len(comments)

    # 证据强度评估（纯事实，不含判断）
    has_caption = bool(fields.get("caption", "").strip())
    has_author = bool(fields.get("author", "").strip())
    has_stats = len(result["missing_stats"]) == 0
    has_comments = len(comments) > 0

    score = sum([has_caption, has_author, has_stats, has_comments])
    if score >= 3 and has_comments:
        result["evidence_level"] = "strong"
        result["can_judge"] = True
    elif score >= 2:
        result["evidence_level"] = "partial"
        result["can_judge"] = True
    elif score >= 1:
        result["evidence_level"] = "weak"
        result["can_judge"] = False
    else:
        result["evidence_level"] = "none"
        result["can_judge"] = False

    return result


if __name__ == "__main__":
    cap_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not cap_path:
        print("用法: python validate.py <capture.json>")
        sys.exit(1)
    data = json.loads(Path(cap_path).read_text(encoding="utf-8"))
    print(json.dumps(validate(data), ensure_ascii=False, indent=2))
