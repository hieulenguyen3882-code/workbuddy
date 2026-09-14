"""批量运行10条真实素材的自动判断，输出对比表。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from judge import judge

CAP_DIR = Path(__file__).parent.parent / "bridge" / "captures"

# 人工判断结果（按文件顺序）
HUMAN_VERDICTS = {
    "2026-09-14T14-45-06-875Z.json": "继续深拆",
    "2026-09-14T14-46-33-963Z.json": "丢弃",
    "2026-09-14T16-24-53-897Z.json": "观察",
    "2026-09-14T16-24-59-231Z.json": "丢弃",
    "2026-09-14T16-25-04-335Z.json": "丢弃",
    "2026-09-14T16-25-10-588Z.json": "进入素材库",
    "2026-09-14T16-25-15-626Z.json": "进入市场反馈雷达",
    "2026-09-14T16-27-34-103Z.json": "证据不足",
    "2026-09-14T16-27-39-261Z.json": "证据不足",
    "2026-09-14T16-27-43-586Z.json": "丢弃",
}

files = sorted(CAP_DIR.glob("2026-*.json"))
print(f"{'#':<3} {'作者':<20} {'赞':<8} {'评':<6} {'藏':<6} {'自动判断':<14} {'人工判断':<14} {'一致'}")
print("-" * 90)

match_count = 0
diff_items = []

for i, f in enumerate(files, 1):
    result = judge(f)
    j = result["judgment"]
    eng = result["engagement"]
    author = result["raw_data"]["fields"].get("author", "?")[:18]
    auto = j["verdict"]
    human = HUMAN_VERDICTS.get(f.name, "?")
    match = "✓" if auto == human else "✗"
    if auto == human:
        match_count += 1
    else:
        diff_items.append((i, author, f.name, auto, human, j["reason"]))
    print(f"{i:<3} {author:<20} {eng['like']:<8} {eng['comment']:<6} {eng['collect']:<6} {auto:<14} {human:<14} {match}")

print("-" * 90)
print(f"一致: {match_count}/10")
print()
if diff_items:
    print("=== 不一致条目 ===")
    for i, author, fname, auto, human, reason in diff_items:
        print(f"#{i} {author} ({fname})")
        print(f"  自动: {auto} — {reason}")
        print(f"  人工: {human}")
        print()
