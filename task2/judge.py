"""
任务 #2 快速判断卡 - 主入口。
读取 capture → 校验证据 → 评论去噪 → 输出卡片模板。
判断由模型完成，本脚本只负责证据整理。
"""
import json
import sys
from pathlib import Path

# 将 task2 目录加入 path
sys.path.insert(0, str(Path(__file__).parent))
from validate import validate
from comments import process as process_comments
from card import build_card

BRIDGE_CAPTURES = Path(__file__).parent.parent / "bridge" / "captures"


def get_latest_capture() -> Path:
    """获取最新一条 capture。"""
    files = sorted(BRIDGE_CAPTURES.glob("2026-*.json"))
    if not files:
        raise FileNotFoundError(f"未找到 capture 文件：{BRIDGE_CAPTURES}")
    return files[-1]


def judge(capture_path: Path = None) -> dict:
    """读取 capture，整理证据，返回卡片文本和结构化数据。"""
    if capture_path is None:
        capture_path = get_latest_capture()

    data = json.loads(Path(capture_path).read_text(encoding="utf-8"))
    validation = validate(data)
    comments = data.get("fields", {}).get("comments", [])
    comment_result = process_comments(comments)
    card_text = build_card(data, validation, comment_result)

    return {
        "capture_file": str(capture_path),
        "validation": validation,
        "comment_result": comment_result,
        "card_text": card_text,
        "raw_data": data,
    }


if __name__ == "__main__":
    cap_path = sys.argv[1] if len(sys.argv) > 1 else None
    result = judge(Path(cap_path) if cap_path else None)
    print(result["card_text"])
    print(f"\n[证据文件] {result['capture_file']}")
    print(f"[证据等级] {result['validation']['evidence_level']}")
    print(f"[可判断] {result['validation']['can_judge']}")
