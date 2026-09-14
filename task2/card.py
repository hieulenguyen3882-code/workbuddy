"""
快速判断卡格式输出（自动判断版）。
接收 judgment 字典，输出完整卡片，无 [待判断] 占位。
"""

CARD_TEMPLATE = """━━━━━━━━━━━━━━━━━━
快速判断卡（自动生成）
━━━━━━━━━━━━━━━━━━
【素材】
作者：{author}
发布时间：{publish_time}
链接：{url}
当前数据：点赞 {like} / 评论 {comment} / 收藏 {collect} / 分享 {share}
收藏/点赞比：{cl_ratio}

【它在讲什么】
一句话：{what}

【为什么有人看】
核心触发点：{why_trigger}
证据：{why_evidence}

【评论区真实反馈】
{comments_summary}

【我能拿走什么】
主价值：{main_value}
次价值：{sub_value}
可迁移点：{transferable}

【风险 / 反证】
{risk}

【判断】
{verdict}

【一句话理由】
{reason}
━━━━━━━━━━━━━━━━━━"""


def build_card(data: dict, validation: dict, comment_result: dict,
               judgment: dict, engagement: dict) -> str:
    """构建完整快速判断卡。"""
    fields = data.get("fields", {})
    stats = fields.get("stats", {})

    # 证据不足时的特殊处理
    if judgment["verdict"] == "证据不足":
        judgment["what"] = judgment.get("what", "正文信息不足")
        judgment["why_trigger"] = "证据不足，无法判断"
        judgment["why_evidence"] = f"缺失字段: {validation.get('missing_fields', [])}，评论数: {validation.get('comment_count', 0)}"
        judgment["comments_summary"] = "当前抓取评论无有效正文，无法用评论证明价值。"
        judgment["main_value"] = "暂无明显价值"
        judgment["sub_value"] = "无"
        judgment["transferable"] = "无"
        judgment["risk"] = "证据不足"
        judgment["reason"] = "证据不足，无法判断"

    cl_ratio = engagement.get("collect_like_ratio", 0)
    cl_ratio_str = f"{cl_ratio}（{'收藏 > 点赞' if cl_ratio > 1 else '收藏 < 点赞'}）" if cl_ratio > 0 else "0"

    return CARD_TEMPLATE.format(
        author=fields.get("author", "未知"),
        publish_time=stats.get("publishTime", "未知"),
        url=data.get("url", ""),
        like=stats.get("likeCount", "未知"),
        comment=stats.get("commentCount", "未知"),
        collect=stats.get("collectCount", "未知"),
        share=stats.get("shareCount", "未知"),
        cl_ratio=cl_ratio_str,
        what=judgment["what"],
        why_trigger=judgment["why_trigger"],
        why_evidence=judgment["why_evidence"],
        comments_summary=judgment["comments_summary"],
        main_value=judgment["main_value"],
        sub_value=judgment["sub_value"],
        transferable=judgment["transferable"],
        risk=judgment["risk"],
        verdict=judgment["verdict"],
        reason=judgment["reason"],
    )
