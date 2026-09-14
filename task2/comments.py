"""
评论去噪与粗分。
关键词只用于粗筛/去噪，最终判断必须结合语义。
"""
import re
from typing import List, Dict

# 低价值评论模式（去噪）
NOISE_PATTERNS = [
    r"^哈哈哈+$",
    r"^[66]+$",
    r"^支持$",
    r"^说得对$",
    r"^[?？]+$",
    r"^[!！]+$",
    r"^沙发$",
    r"^第一$",
    r"^前排$",
    r"^打卡$",
    r"^路过$",
    r"^学习了$",
    r"^受教了$",
    r"^mark$",
    r"^收藏了$",
]

# 需求/购买信号关键词（粗筛用，不下最终结论）
# 必须包含明确的请求/疑问意味，避免自我反思类评论误判
DEMAND_KEYWORDS = [
    # 明确求教程/方案/链接
    "怎么买", "多少钱", "哪里买", "求链接", "求教程", "求方案",
    "怎么做", "怎么弄", "能不能教", "求推荐", "求带", "求带飞",
    "教程发", "发教程", "咋做", "咋弄", "咋整", "怎么学",
    "学到什么", "能学到", "避险", "怎么办", "怎么破",
    # 明确表达想学/不会（需配合疑问语境）
    "我也想", "我也遇到", "不晓得怎么", "不知道怎么", "不会呀", "不懂怎么",
    # 问效果/质量
    "好用吗", "效果怎么样", "有用吗", "靠谱吗", "有链接吗", "怎么联系",
]

# 作者评论过滤模式（作者自评/回复不算作用户反馈）
AUTHOR_PATTERNS = [
    r"作者.*回复", r"作者\.\.\.", r"^作者",
]

# 质疑/反驳信号
QUESTION_KEYWORDS = [
    "不对", "假的", "骗人", "智商税", "割韭菜", "别信",
    "反驳", "不同意", "有问题", "bug", "没用",
]

# 补充案例/使用反馈
FEEDBACK_KEYWORDS = [
    "我用了", "我买了", "亲测", "实测", "用了半年",
    "确实", "真的", "我也是", "同感",
]


def is_noise(comment: str) -> bool:
    """判断是否为低价值噪音评论。"""
    c = comment.strip()
    if len(c) < 2:
        return True
    for p in NOISE_PATTERNS:
        if re.match(p, c):
            return True
    return False


def classify(comment: str) -> str:
    """粗分评论类型。只用于内部组织，不作为最终判断依据。"""
    c = comment
    for kw in DEMAND_KEYWORDS:
        if kw in c:
            return "demand"
    for kw in QUESTION_KEYWORDS:
        if kw in c:
            return "question"
    for kw in FEEDBACK_KEYWORDS:
        if kw in c:
            return "feedback"
    return "other"


def is_author_comment(comment: str) -> bool:
    """判断是否为作者自评/回复（不算作用户反馈）。"""
    for p in AUTHOR_PATTERNS:
        if re.search(p, comment):
            return True
    return False


def process(comments: List[str]) -> Dict:
    """处理评论列表：去噪、过滤作者评论、粗分、返回高价值评论。"""
    result = {
        "total": len(comments),
        "noise_count": 0,
        "author_count": 0,
        "high_value": [],
        "by_type": {"demand": [], "question": [], "feedback": [], "other": []},
    }
    for c in comments:
        if is_noise(c):
            result["noise_count"] += 1
            continue
        if is_author_comment(c):
            result["author_count"] += 1
            continue
        t = classify(c)
        result["by_type"][t].append(c)
        if t in ("demand", "question", "feedback"):
            result["high_value"].append({"type": t, "text": c})
    return result


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path
    cap_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not cap_path:
        print("用法: python comments.py <capture.json>")
        sys.exit(1)
    data = json.loads(Path(cap_path).read_text(encoding="utf-8"))
    comments = data.get("fields", {}).get("comments", [])
    print(json.dumps(process(comments), ensure_ascii=False, indent=2))
