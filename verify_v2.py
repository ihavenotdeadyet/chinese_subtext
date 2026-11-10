# -*- coding: utf-8 -*-
"""语料自检。只读，不改任何文件。

用法
  python verify_v2.py        # 全部通过时退出码 0，否则 1

检查项
  1. corpus_v1.json 与仓库原文的内容哈希一致（确认从未被改动）
  2. V2 里 V1 那十条的原有字段，逐字段与 V1 完全相同
  3. V1 条目只比 V1 多一个 device 字段，没有别的增删
  4. id 连续、device 合法、对话两轮、目标短语在我的台词里
  5. translations.json 覆盖全部条目，en / ja 齐全，首条替补与 alternative 一致
"""

import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V1 = os.path.join(HERE, "corpus_v1.json")
V2 = os.path.join(HERE, "corpus_v2.json")
TRANS = os.path.join(HERE, "translations.json")

# corpus_v1.json 从仓库拉下来时的 git blob 哈希，作为"未被改动"的基线。
V1_BASELINE = "cc8abcc3b37e3b26347ac5f2b95f8bd448c53cdc"

BASE_FIELDS = ["id", "scene", "dialogue", "target_phrase",
               "literal", "intent", "emotion", "alternative"]

DEVICES = {"false_agreement", "understatement", "deflection", "over_politeness",
           "self_deprecation", "silence_ending", "ironic_praise"}

errors, checks = [], []


def ok(msg):
    checks.append(msg)


def bad(msg):
    errors.append(msg)


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def blob_hash(path):
    """复算 git blob 哈希：sha1('blob <len>\\0' + content)。

    先把 CRLF 归一成 LF：Windows 检出可能转换行尾，字节变了但内容没变。
    """
    with open(path, "rb") as f:
        data = f.read()
    if b"\r\n" in data:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(("blob %d\0" % len(data)).encode("utf-8") + data).hexdigest()


def check_v1_untouched(v1, by_id):
    actual = blob_hash(V1)
    if actual == V1_BASELINE:
        ok("corpus_v1.json 与原文一致（%s…）" % actual[:12])
    else:
        bad("corpus_v1.json 内容变了：基线 %s / 当前 %s" % (V1_BASELINE, actual))

    diff = 0
    for row in v1:
        gen = by_id.get(row["id"])
        if not gen:
            bad("V2 缺 V1 第 %s 条" % row["id"])
            continue
        for k in BASE_FIELDS:
            if gen.get(k) != row.get(k):
                bad("第 %s 条字段 %s 被改动" % (row["id"], k))
                diff += 1
        extra = set(gen) - set(BASE_FIELDS)
        lost = set(BASE_FIELDS) - set(gen)
        if extra != {"device"}:
            bad("第 %s 条多余字段：%s" % (row["id"], sorted(extra)))
            diff += 1
        if lost:
            bad("第 %s 条丢字段：%s" % (row["id"], sorted(lost)))
            diff += 1
    if not diff:
        ok("V1 十条原有字段零改动，仅追加 device")


def check_structure(v2):
    ids = [r["id"] for r in v2]
    if ids != list(range(1, len(v2) + 1)):
        bad("id 不连续或重复：%s" % ids)
    else:
        ok("id 连续 1-%d" % len(v2))

    n = 0
    for r in v2:
        tag = "第 %s 条" % r["id"]
        if r.get("device") not in DEVICES:
            bad("%s device 非法：%r" % (tag, r.get("device")))
            n += 1
        if len(r.get("dialogue", [])) != 2:
            bad("%s dialogue 不是两轮" % tag)
            n += 1
            continue
        if [t["speaker"] for t in r["dialogue"]] != ["对方", "我"]:
            bad("%s 说话人顺序不是 对方 -> 我" % tag)
            n += 1
        if r["target_phrase"] not in r["dialogue"][1]["text"]:
            bad("%s 目标短语「%s」不在我的台词里" % (tag, r["target_phrase"]))
            n += 1
    if not n:
        ok("每条都满足：device 合法 / 两轮 / 对方先说 / 目标短语在我的台词里")


def check_translations(v2, trans):
    items = trans.get("items", {})
    missing = [str(r["id"]) for r in v2 if str(r["id"]) not in items]
    if missing:
        bad("translations 缺条目：%s" % "、".join(missing))
        return

    n = 0
    for r in v2:
        sid = str(r["id"])
        blk = items[sid]
        for lang in ("en", "ja"):
            piece = blk.get(lang) or {}
            for f in ("literal", "intent", "relation", "emotion"):
                if not piece.get(f):
                    bad("%s 的 %s.%s 为空" % (sid, lang, f))
                    n += 1
            if len(piece.get("replies") or []) < 2:
                bad("%s 的 %s 替代表达少于 2 条" % (sid, lang))
                n += 1
        if ((blk.get("en") or {}).get("replies") or [{}])[0].get("zh") != r["alternative"]:
            bad("%s 首条替代表达与 alternative 不一致" % sid)
            n += 1
    if not n:
        ok("translations 覆盖 %d 条，en / ja 齐全，首条替补与 alternative 一致" % len(v2))


def main():
    v1, v2, trans = load(V1), load(V2), load(TRANS)
    by_id = {r["id"]: r for r in v2}

    check_v1_untouched(v1, by_id)
    check_structure(v2)
    check_translations(v2, trans)

    print("语料自检")
    print("-" * 46)
    for c in checks:
        print("  ok  " + c)
    for e in errors:
        print("  !!  " + e)

    by_dev = {}
    for r in v2:
        by_dev[r["device"]] = by_dev.get(r["device"], 0) + 1
    print("-" * 46)
    print("  %d 条（V1 %d + 新增 %d）／高危词 %d 个／场景 %d 个"
          % (len(v2), len(v1), len(v2) - len(v1),
             len({r["target_phrase"] for r in v2}), len({r["scene"] for r in v2})))
    print("  device：" + "、".join("%s=%d" % kv for kv in sorted(by_dev.items())))
    print("-" * 46)

    if errors:
        print("结果：%d 项不通过。" % len(errors))
        sys.exit(1)
    print("结果：全部通过。")


if __name__ == "__main__":
    main()
