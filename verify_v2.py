# -*- coding: utf-8 -*-
"""
语料 V2 的自检脚本。只读，不改任何文件。

用法
  python corpus/verify_v2.py

检查项
  1. corpus_v1.json 与 GitHub 原文的内容哈希一致（确认从未被改动）
  2. V2 里 V1 那十条的原有字段，逐字段与 V1 完全相同
  3. V2 每条只比 V1 多一个 device 字段，没有别的增删
  4. id 连续、device 取值合法、对话两轮、目标短语在我的台词里
  5. additions_v2.json 是纯新增，且与 V2 合并结果一致
  6. translations.json 覆盖全部条目，en / ja 字段齐全，
     第一条替代表达与语料的 alternative 逐字相同

任何一项不过，脚本以非零码退出，可以直接挂在提交前跑。
"""

import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V1 = os.path.join(HERE, "corpus_v1.json")
V2 = os.path.join(HERE, "corpus_v2.json")
ADD = os.path.join(HERE, "additions_v2.json")
DEV = os.path.join(HERE, "devices_v2.json")
TRANS = os.path.join(HERE, "translations.json")

# corpus_v1.json 从仓库拉下来时的内容哈希，用作"未被改动"的基线。
# 这是 git 的 blob 哈希算法，改一个字节就会变。
V1_BASELINE = "cc8abcc3b37e3b26347ac5f2b95f8bd448c53cdc"

BASE_FIELDS = ["id", "scene", "dialogue", "target_phrase", "literal", "intent", "emotion", "alternative"]

errors = []
checks = []


def ok(msg):
    checks.append(msg)


def bad(msg):
    errors.append(msg)


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def blob_hash(path):
    """复算 git 的 blob 哈希：sha1('blob <len>\\0' + content)。

    先把 CRLF 归一成 LF 再算：Windows 上 git 检出时可能把行尾转成 CRLF，
    字节就会变、哈希对不上，但这并不代表内容被改过。仓库里存的始终是 LF。
    """
    with open(path, "rb") as f:
        data = f.read()
    if b"\r\n" in data:
        data = data.replace(b"\r\n", b"\n")
    head = ("blob %d\0" % len(data)).encode("utf-8")
    return hashlib.sha1(head + data).hexdigest()


def main():
    v1 = load(V1)
    v2 = load(V2)
    add = load(ADD)
    dev = load(DEV)
    trans = load(TRANS)
    enums = set(dev["enums"])
    marks = dev["items"]

    # ---- 1. V1 原文未被改动 ----
    actual = blob_hash(V1)
    if actual == V1_BASELINE:
        ok("corpus_v1.json 与仓库原文一致（%s…）" % actual[:12])
    else:
        bad("corpus_v1.json 内容变了！\n      基线: %s\n      当前: %s" % (V1_BASELINE, actual))

    # ---- 2. V1 十条原字段逐字段相同 ----
    by_id_v2 = {r["id"]: r for r in v2}
    diff = 0
    for row in v1:
        gen = by_id_v2.get(row["id"])
        if not gen:
            bad("V2 缺 V1 第 %s 条" % row["id"])
            continue
        for k in BASE_FIELDS:
            if gen.get(k) != row.get(k):
                bad("第 %s 条字段 %s 被改动" % (row["id"], k))
                diff += 1
    if not diff:
        ok("V1 十条原有字段零改动（%d 字段 × %d 条）" % (len(BASE_FIELDS), len(v1)))

    # ---- 3. 字段集合：V1 条只多 device ----
    extra_problem = 0
    for row in v1:
        gen = by_id_v2.get(row["id"], {})
        if set(gen) - set(BASE_FIELDS) != {"device"}:
            bad("第 %s 条新增字段不是且仅是 device：%s" % (row["id"], sorted(set(gen) - set(BASE_FIELDS))))
            extra_problem += 1
        if set(BASE_FIELDS) - set(gen):
            bad("第 %s 条丢字段：%s" % (row["id"], sorted(set(BASE_FIELDS) - set(gen))))
            extra_problem += 1
    if not extra_problem:
        ok("V1 条目结构变化仅为追加 device")

    # ---- 4. 结构校验 ----
    ids = [r["id"] for r in v2]
    if ids != list(range(1, len(v2) + 1)):
        bad("id 不连续或重复：%s" % ids)
    else:
        ok("id 连续 1-%d" % len(v2))

    for r in v2:
        tag = "第 %s 条" % r["id"]
        if r.get("device") not in enums:
            bad("%s device 非法：%r" % (tag, r.get("device")))
        if len(r.get("dialogue", [])) != 2:
            bad("%s dialogue 不是两轮" % tag)
            continue
        if r["dialogue"][0]["speaker"] != "对方" or r["dialogue"][1]["speaker"] != "我":
            bad("%s 说话人顺序不是 对方 -> 我" % tag)
        if r["target_phrase"] not in r["dialogue"][1]["text"]:
            bad("%s 目标短语「%s」不在我的台词里" % (tag, r["target_phrase"]))
    ok("每条都满足：device 合法 / 两轮 / 对方先说 / 目标短语在我的台词里")

    # ---- 5. additions 是纯新增且与合并结果一致 ----
    v1_ids = {r["id"] for r in v1}
    clash = [r["id"] for r in add if r["id"] in v1_ids]
    if clash:
        bad("additions 与 V1 id 冲突：%s" % clash)
    else:
        ok("additions_v2.json 的 %d 条均为全新 id" % len(add))

    mismatch = 0
    for row in add:
        gen = by_id_v2.get(row["id"])
        if not gen:
            bad("V2 缺新增第 %s 条" % row["id"])
            continue
        for k in BASE_FIELDS:
            if gen.get(k) != row.get(k):
                bad("新增第 %s 条字段 %s 与 additions 不一致（V2 被手改过？）" % (row["id"], k))
                mismatch += 1
    if not mismatch:
        ok("新增条目与 additions_v2.json 逐字段一致")

    # ---- 6. 翻译覆盖 ----
    items = trans.get("items", {})
    missing = [str(r["id"]) for r in v2 if str(r["id"]) not in items]
    if missing:
        bad("translations 缺条目：%s" % "、".join(missing))
    else:
        ok("translations 覆盖全部 %d 条" % len(v2))

    tbad = 0
    for r in v2:
        sid = str(r["id"])
        blk = items.get(sid)
        if not blk:
            continue
        for lang in ("en", "ja"):
            piece = blk.get(lang) or {}
            for f in ("literal", "intent", "relation", "emotion"):
                if not piece.get(f):
                    bad("%s 的 %s.%s 为空" % (sid, lang, f))
                    tbad += 1
            reps = piece.get("replies") or []
            if len(reps) < 2:
                bad("%s 的 %s 替代表达少于 2 条" % (sid, lang))
                tbad += 1
        first = (blk.get("en") or {}).get("replies") or [{}]
        if first[0].get("zh") != r["alternative"]:
            bad("%s 的第一条替代表达与 alternative 不一致" % sid)
            tbad += 1
    if not tbad:
        ok("en / ja 讲解齐全，首条替代表达与 alternative 逐字一致")

    # ---- 输出 ----
    print("语料自检")
    print("-" * 46)
    for c in checks:
        print("  ok  " + c)
    for e in errors:
        print("  !!  " + e)

    total = len(v2)
    print("-" * 46)
    by_dev = {}
    for r in v2:
        by_dev[r["device"]] = by_dev.get(r["device"], 0) + 1
    print("  条数 %d（V1 %d + 新增 %d）" % (total, len(v1), len(add)))
    print("  device：" + "、".join("%s=%d" % (k, v) for k, v in sorted(by_dev.items())))
    uniq = len({r["target_phrase"] for r in v2})
    print("  高危词 %d 个，场景 %d 个" % (uniq, len({r["scene"] for r in v2})))
    print("-" * 46)

    if errors:
        print("结果：%d 项不通过，请修复后重跑。" % len(errors))
        sys.exit(1)
    print("结果：全部通过。")


if __name__ == "__main__":
    main()
