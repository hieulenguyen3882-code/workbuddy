"""
快速判断卡格式输出。
只输出模板和证据，判断由模型完成。
"""

CARD_TEMPLATE = """━━━━━━━━━━━━━━━━━━
快速判断卡
━━━━━━━━━━━━━━━━━━
【素材】
作者：{author}
发布时间：{publish_time}
链接：{url}
当前数据：点赞 {like} / 评论 {comment} / 收藏 {collect} / 分享 {share}

【它在讲什么】
一句话：{caption_summary}

【为什么有人看】
核心触发点：[待判断]
证据：{trigger_evidence}

【评论区真实反馈】
{comments_section}

【我能拿走什么】
主价值：[待判断]
次价值：[待判断]
可迁移点：[待判断]

【风险 / 反证】
{risk}

【判断】
[待判断：继续深拆 / 市场反馈雷达 / 素材库 / 选题池 / 观察 / 丢弃 / 证据不足]

【一句话理由】
[待判断，不超过40字]
━━━━━━━━━━━━━━━━━━"""


def build_card(data: dict, validation: dict, comment_result: dict) -> str:
    """构建快速判断卡模板（证据已填充，判断待模型完成）。"""
    fields = data.get("fields", {})
    stats = fields.get("stats", {})
    caption = fields.get("caption", "")
    caption_summary = caption[:80] + "..." if len(caption) > 80 else caption

    # 评论区部分
    high_value = comment_result.get("high_value", [])
    if high_value:
        lines = []
        for i, c in enumerate(high_value[:5], 1):
            t = c["type"]
            type_label = {"demand": "需求", "question": "质疑", "feedback": "反馈"}.get(t, t)
            text = c["text"][:100]
            lines.append(f"{i}. [{type_label}] {text}")
        comments_section = "\n".join(lines)
    elif comment_result.get("total", 0) > 0:
        comments_section = "【未发现足够高价值评论】"
    else:
        comments_section = "【当前仅基于已加载评论判断】"

    # 风险/反证
    questions = comment_result.get("by_type", {}).get("question", [])
    risk = questions[0][:100] if questions else "暂无明显反证"

    # 证据不足提示
    if not validation.get("can_judge", False):
        risk = f"证据不足：缺失 {validation.get('missing_fields', [])}，评论数 {validation.get('comment_count', 0)}"

    return CARD_TEMPLATE.format(
        author=fields.get("author", "未知"),
        publish_time=stats.get("publishTime", "未知"),
        url=data.get("url", ""),
        like=stats.get("likeCount", "未知"),
        comment=stats.get("commentCount", "未知"),
        collect=stats.get("collectCount", "未知"),
        share=stats.get("shareCount", "未知"),
        caption_summary=caption_summary,
        trigger_evidence=f"正文 {len(caption)} 字 / 评论 {comment_result.get('total', 0)} 条 / 高价值 {len(high_value)} 条",
        comments_section=comments_section,
        risk=risk,
    )
