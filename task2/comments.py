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
DEMAND_KEYWORDS = [
    "怎么买", "多少钱", "哪里买", "求链接", "求教程", "求方案",
    "怎么做", "怎么弄", "能不能教", "我也想", "我也有", "我也遇到",
    "求推荐", "好用吗", "效果怎么样", "有用吗", "靠谱吗",
    "在哪买", "有链接吗", "怎么联系", "求带", "求带飞",
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


def process(comments: List[str]) -> Dict:
    """处理评论列表：去噪、粗分、返回高价值评论。"""
    result = {
        "total": len(comments),
        "noise_count": 0,
        "high_value": [],
        "by_type": {"demand": [], "question": [], "feedback": [], "other": []},
    }
    for c in comments:
        if is_noise(c):
            result["noise_count"] += 1
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
