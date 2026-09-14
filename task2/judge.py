"""
任务 #2 快速判断卡 - 主入口（自动判断版）。
读取 capture → 校验证据 → 评论去噪 → 多维度证据评分 → 自动生成完整判断卡。
判断基于多维度证据综合评分，不是固定关键词分类器。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from validate import validate
from comments import process as process_comments
from card import build_card

BRIDGE_CAPTURES = Path(__file__).parent.parent / "bridge" / "captures"


def parse_count(s) -> int:
    """解析抖音显示格式的数字，如 '1.6万' -> 16000, '抢首评' -> 0。"""
    if not s or not isinstance(s, str):
        return 0
    s = s.strip()
    if "万" in s:
        try:
            return int(float(s.replace("万", "")) * 10000)
        except ValueError:
            return 0
    try:
        return int(s)
    except ValueError:
        return 0


def get_latest_capture() -> Path:
    files = sorted(BRIDGE_CAPTURES.glob("2026-*.json"))
    if not files:
        raise FileNotFoundError(f"未找到 capture 文件：{BRIDGE_CAPTURES}")
    return files[-1]


def score_content(caption: str, author: str = "") -> dict:
    """正文维度评分：信息密度、具体性、真实案例信号。"""
    length = len(caption) if caption else 0
    has_concrete = bool(re.search(r"\d+", caption)) if caption else False
    has_case = any(kw in caption for kw in ["案例", "实际", "真实", "我是", "我在", "开店", "做了", "亲测"]) if caption else False
    # 作者名含实体商家信号（酒/店/教育/智能等）作为辅助
    author_entity = any(kw in author for kw in ["酒", "店", "教育", "智能", "科技", "商贸", "实业", "厂", "铺"]) if author else False
    density = "strong" if length > 200 else ("medium" if length > 50 else "weak")
    # 真实案例需要正文有一定密度，不能只是标题式正文
    has_real_case = has_case and density != "weak"
    return {
        "length": length,
        "density": density,
        "has_concrete": has_concrete,
        "has_case": has_real_case,
        "author_entity": author_entity,
    }


def score_engagement(stats: dict) -> dict:
    """互动维度评分：收藏/点赞比、分享/点赞比、评论/点赞比。"""
    like = parse_count(stats.get("likeCount"))
    comment = parse_count(stats.get("commentCount"))
    collect = parse_count(stats.get("collectCount"))
    share = parse_count(stats.get("shareCount"))
    cl_ratio = round(collect / like, 2) if like > 0 else 0
    sl_ratio = round(share / like, 2) if like > 0 else 0
    cmt_ratio = round(comment / like, 2) if like > 0 else 0
    # 评论率高需要最小基数，避免极低基数虚高
    high_comment_rate = cmt_ratio > 0.2 and comment >= 10
    return {
        "like": like, "comment": comment, "collect": collect, "share": share,
        "collect_like_ratio": cl_ratio,
        "share_like_ratio": sl_ratio,
        "comment_like_ratio": cmt_ratio,
        "high_collect": cl_ratio > 1,
        "high_share": sl_ratio > 0.1,
        "high_comment_rate": high_comment_rate,
    }


def score_comments(comment_result: dict) -> dict:
    """评论维度评分：有效评论率、需求/质疑/反馈分布。"""
    total = comment_result.get("total", 0)
    high_value = comment_result.get("high_value", [])
    by_type = comment_result.get("by_type", {})
    demand = by_type.get("demand", [])
    question = by_type.get("question", [])
    feedback = by_type.get("feedback", [])
    valid_rate = round(len(high_value) / total, 2) if total > 0 else 0
    return {
        "total": total,
        "high_value_count": len(high_value),
        "valid_rate": valid_rate,
        "demand_count": len(demand),
        "question_count": len(question),
        "feedback_count": len(feedback),
        "demand_comments": demand[:3],
        "question_comments": question[:2],
        "feedback_comments": feedback[:2],
        "has_demand": len(demand) > 0,
        "has_question": len(question) > 0,
        "has_feedback": len(feedback) > 0,
    }


def infer_what(caption: str, author: str) -> str:
    """基于正文生成一句话概括。"""
    if not caption or len(caption) < 5:
        return "正文信息不足，无法概括"
    # 取第一句或前60字
    first_sentence = re.split(r"[。！？\n]", caption)[0]
    if len(first_sentence) > 60:
        first_sentence = first_sentence[:57] + "..."
    return first_sentence


def infer_why(content_score: dict, engagement: dict, comment_score: dict, caption: str) -> tuple:
    """推断核心注意力来源，返回 (触发点, 证据)。"""
    reasons = []
    # 收藏信号
    if engagement["high_collect"]:
        reasons.append(("利益/实用价值", f"收藏/点赞比 > 1（收藏{engagement['collect']} > 点赞{engagement['like']}），用户感知到保存价值"))
    # 评论率信号
    if engagement["high_comment_rate"]:
        reasons.append(("身份代入/共鸣", f"评论/点赞比 {engagement['comment_like_ratio']}，高互动率说明观众有表达欲"))
    # 需求评论
    if comment_score["has_demand"]:
        reasons.append(("明确问题/需求", f"评论中有{comment_score['demand_count']}条需求表达（求教程/问方法/说困境）"))
    # 真实案例
    if content_score["has_case"]:
        reasons.append(("真实案例", "正文含第一人称真实经历/具体案例"))
    # 具体数据
    if content_score["has_concrete"] and content_score["density"] == "strong":
        reasons.append(("信息密度", f"正文{content_score['length']}字，含具体数据/时间线"))
    # 分享信号
    if engagement["high_share"]:
        reasons.append(("传播价值", f"分享/点赞比 {engagement['share_like_ratio']}，用户愿意转发"))

    if not reasons:
        return ("无法判断", "当前证据不足以推断注意力来源")
    # 取评分最高的（按顺序：收藏>需求>评论率>案例>信息密度>分享）
    return reasons[0]


def infer_comments_summary(comment_score: dict) -> str:
    """生成评论区总结。"""
    if comment_score["total"] == 0:
        return "当前抓取评论无有效正文，无法用评论证明价值。"
    lines = []
    idx = 1
    for c in comment_score["demand_comments"]:
        lines.append(f"{idx}. [需求] {c[:80]}")
        idx += 1
    for c in comment_score["question_comments"]:
        lines.append(f"{idx}. [质疑] {c[:80]}")
        idx += 1
    for c in comment_score["feedback_comments"]:
        lines.append(f"{idx}. [反馈] {c[:80]}")
        idx += 1
    if not lines:
        if comment_score["high_value_count"] == 0:
            return "当前抓取评论无有效正文，无法用评论证明价值。"
        return f"共{comment_score['total']}条评论，有效评论{comment_score['high_value_count']}条，但无明确需求/质疑/反馈信号。"
    return "\n".join(lines)


def infer_value(verdict: str, content_score: dict, engagement: dict, comment_score: dict) -> tuple:
    """推断主价值和次价值。"""
    if verdict == "证据不足":
        return ("暂无明显价值", "无")
    if verdict == "丢弃":
        return ("暂无明显价值", "无")

    main = "暂无明显价值"
    sub = "无"

    # 主价值判断
    if comment_score["has_demand"]:
        main = "用户需求"
    elif engagement["high_collect"]:
        main = "爆款素材"
    elif engagement["high_comment_rate"] and comment_score["valid_rate"] > 0:
        main = "用户需求"
    elif content_score["has_case"]:
        main = "商业案例"
    elif content_score["density"] == "strong":
        main = "市场反馈"
    else:
        main = "选题信号"

    # 次价值
    if main == "用户需求" and engagement["high_collect"]:
        sub = "爆款素材"
    elif main == "用户需求" and content_score["has_case"]:
        sub = "商业案例"
    elif main == "爆款素材" and comment_score["has_demand"]:
        sub = "用户需求"
    elif main == "商业案例" and comment_score["has_demand"]:
        sub = "用户需求"
    elif engagement["high_share"]:
        sub = "内容方法"
    elif content_score["density"] == "strong":
        sub = "内容方法"
    else:
        sub = "无"

    return (main, sub)


def infer_transferable(verdict: str, content_score: dict, engagement: dict, caption: str) -> str:
    """推断可迁移点。"""
    if verdict in ("丢弃", "证据不足"):
        return "无"
    points = []
    if engagement["high_collect"]:
        points.append("清单式/收藏型内容结构")
    if content_score["has_case"]:
        points.append("第一人称真实案例背书")
    if engagement["high_comment_rate"]:
        points.append("身份共鸣型选题框架")
    if content_score["density"] == "strong" and content_score["has_concrete"]:
        points.append("高密度信息+具体数据的正文结构")
    return "；".join(points) if points else "无明显可迁移点"


def infer_risk(content_score: dict, engagement: dict, comment_score: dict, caption: str) -> str:
    """推断最重要的一条风险/反证。"""
    risks = []
    if comment_score["total"] >= 5 and comment_score["high_value_count"] == 0:
        risks.append("评论数不少但全部无有效正文，无法用评论证明真实价值")
    elif 0 < comment_score["total"] < 5 and comment_score["high_value_count"] == 0:
        risks.append("仅少量评论且无有效正文，无法用评论证明价值")
    if comment_score["has_question"]:
        risks.append(f"评论中有质疑信号：{comment_score['question_comments'][0][:50]}")
    if engagement["like"] < 50 and engagement["collect"] < 20:
        risks.append("互动数据极低，市场响应不足")
    if content_score["density"] == "weak":
        risks.append("正文信息密度弱（仅标题式正文），具体内容可能在视频中未被抓取")
    if not risks:
        risks.append("暂无明显反证")
    return risks[0]


def auto_verdict(validation: dict, content_score: dict, engagement: dict, comment_score: dict) -> tuple:
    """
    多维度证据综合判断，返回 (判断, 一句话理由)。
    不是固定关键词分类器，而是基于证据强度综合。
    判断优先级：证据不足 > 丢弃 > 继续深拆 > 市场反馈雷达 > 素材库 > 选题池 > 观察
    """
    # 1. 证据不足：字段缺失 or 零评论+极低互动
    if not validation.get("can_judge", False):
        return ("证据不足", "证据不足，无法判断")
    if comment_score["total"] == 0 and engagement["like"] < 50:
        return ("证据不足", "零评论+低互动，无市场反馈证据")

    # 2. 丢弃：低数据 + 无有效评论 + (正文弱且无案例/实体)
    low_data = engagement["like"] < 50 and engagement["collect"] < 20 and engagement["share"] < 10
    no_valid_comments = comment_score["high_value_count"] == 0
    weak_no_case = content_score["density"] == "weak" and not content_score["has_case"] and not content_score["author_entity"]
    if low_data and no_valid_comments and weak_no_case:
        return ("丢弃", "低数据+无有效评论+正文弱无案例，三重弱信号")

    # 3. 继续深拆：高数据 + 强正文 + 真实需求/高价值评论
    high_data = engagement["like"] > 1000 or (engagement["collect"] > 500 and engagement["like"] > 100)
    strong_content = content_score["density"] in ("strong", "medium") and (content_score["has_concrete"] or content_score["has_case"])
    has_real_demand = (
        comment_score["has_demand"]
        or comment_score["has_feedback"]
        or (comment_score["valid_rate"] > 0.2 and comment_score["total"] >= 5)
    )
    if high_data and strong_content and has_real_demand:
        return ("继续深拆", "高数据+强正文+真实需求评论，值得深拆")

    # 4. 素材库：高收藏比（收藏>点赞）优先于市场反馈雷达
    # 高收藏比本身就是强信号，正文可能在视频里，不要求 density!=weak
    if engagement["high_collect"]:
        return ("进入素材库", "收藏/点赞比>1，内容有保存价值，可入素材库")

    # 5. 市场反馈雷达：有需求评论 + (真实案例/实体身份/高分享)
    real_entity = content_score["has_case"] or content_score["author_entity"]
    if comment_score["has_demand"] and (real_entity or engagement["share"] > 30):
        return ("进入市场反馈雷达", "有真实需求评论+实体/案例/传播信号，值得跟踪")

    # 6. 选题池：高评论率(有基数) + 有效评论
    if engagement["high_comment_rate"] and comment_score["valid_rate"] > 0:
        return ("进入选题池", "高评论率+有效评论，身份共鸣选题可入池")

    # 7. 观察：有信号但不足（需有一定数据或有效评论，弱信号不单独触发）
    has_strong_signal = (
        engagement["high_comment_rate"]
        or engagement["high_collect"]
        or comment_score["has_demand"]
        or (content_score["has_case"] and engagement["like"] >= 30)
        or (content_score["author_entity"] and engagement["like"] >= 30)
    )
    if has_strong_signal:
        return ("观察", "有信号但强度不足，需更多样本确认")

    # 8. 兜底丢弃
    return ("丢弃", "无明显价值信号，丢弃")


def judge(capture_path: Path = None) -> dict:
    """读取 capture，自动生成完整判断卡。"""
    if capture_path is None:
        capture_path = get_latest_capture()

    data = json.loads(Path(capture_path).read_text(encoding="utf-8"))
    validation = validate(data)
    fields = data.get("fields", {})
    stats = fields.get("stats", {})
    caption = fields.get("caption", "")
    author = fields.get("author", "")
    comments = fields.get("comments", [])

    comment_result = process_comments(comments)
    content_score = score_content(caption, author)
    engagement = score_engagement(stats)
    comment_score = score_comments(comment_result)

    # 自动判断
    verdict, reason = auto_verdict(validation, content_score, engagement, comment_score)
    what = infer_what(caption, author)
    why_trigger, why_evidence = infer_why(content_score, engagement, comment_score, caption)
    comments_summary = infer_comments_summary(comment_score)
    main_value, sub_value = infer_value(verdict, content_score, engagement, comment_score)
    transferable = infer_transferable(verdict, content_score, engagement, caption)
    risk = infer_risk(content_score, engagement, comment_score, caption)

    judgment = {
        "what": what,
        "why_trigger": why_trigger,
        "why_evidence": why_evidence,
        "comments_summary": comments_summary,
        "main_value": main_value,
        "sub_value": sub_value,
        "transferable": transferable,
        "risk": risk,
        "verdict": verdict,
        "reason": reason,
    }

    card_text = build_card(data, validation, comment_result, judgment, engagement)

    return {
        "capture_file": str(capture_path),
        "validation": validation,
        "comment_result": comment_result,
        "content_score": content_score,
        "engagement": engagement,
        "comment_score": comment_score,
        "judgment": judgment,
        "card_text": card_text,
        "raw_data": data,
    }


if __name__ == "__main__":
    cap_path = sys.argv[1] if len(sys.argv) > 1 else None
    result = judge(Path(cap_path) if cap_path else None)
    print(result["card_text"])
    print(f"\n[证据文件] {result['capture_file']}")
    print(f"[证据等级] {result['validation']['evidence_level']}")
    print(f"[自动判断] {result['judgment']['verdict']}")
