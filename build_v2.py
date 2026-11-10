# -*- coding: utf-8 -*-
"""
把 V1 语料 + V2 新增条目 + device 标注，合并成 corpus_v2.json。

三个来源各管一件事，互不覆盖
  corpus_v1.json      V1 十条原文，只读。本脚本只给它追加 device 字段
  additions_v2.json   新增的 10 条（id 11-20），纯新增
  devices_v2.json     id -> device 的标注表

用法
  python corpus/build_v2.py

产物
  corpus/corpus_v2.json

设计原则
  1. V1 条目除了新增一个 device 字段，其余字段一个字节都不许变。
     脚本会在合并后逐字段回比，不一致直接抛异常退出，不会写出半成品。
  2. 新增条目与 V1 条目用同一套字段顺序，序列化后可以直接并排 diff。
  3. 幂等：反复跑，结果完全一致。
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V1 = os.path.join(HERE, "corpus_v1.json")
ADD = os.path.join(HERE, "additions_v2.json")
DEV = os.path.join(HERE, "devices_v2.json")
OUT = os.path.join(HERE, "corpus_v2.json")

# 字段顺序，与 V1 原文一致；device 追加在最后
BASE_FIELDS = ["id", "scene", "dialogue", "target_phrase", "literal", "intent", "emotion", "alternative"]


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def fail(msg):
    sys.stderr.write("  × " + msg + "\n")
    sys.exit(1)


def main():
    v1 = load(V1)
    additions = load(ADD)
    dev = load(DEV)

    enums = set(dev["enums"])
    mark = dev["items"]

    rows = []

    # ---- 1. V1 十条：原样复制，仅在末尾追加 device ----
    for row in v1:
        sid = str(row["id"])
        if sid not in mark:
            fail("V1 第 %s 条缺 device 标注" % sid)
        merged = {k: row[k] for k in BASE_FIELDS}
        merged["device"] = mark[sid]
        rows.append(merged)

    # ---- 2. 新增条目：必须是全新 id，且不能与 V1 词条重复覆盖 ----
    v1_ids = {r["id"] for r in v1}
    for row in additions:
        if row["id"] in v1_ids:
            fail("新增条目 id=%s 与 V1 冲突" % row["id"])
        sid = str(row["id"])
        if sid not in mark:
            fail("新增第 %s 条缺 device 标注" % sid)
        merged = {k: row[k] for k in BASE_FIELDS}
        merged["device"] = mark[sid]
        rows.append(merged)

    rows.sort(key=lambda r: r["id"])

    # ---- 3. 逐条校验 ----
    for r in rows:
        sid = r["id"]
        if r["device"] not in enums:
            fail("第 %s 条 device 取值非法：%s" % (sid, r["device"]))
        if len(r["dialogue"]) != 2:
            fail("第 %s 条 dialogue 不是两轮" % sid)
        if r["dialogue"][0]["speaker"] != "对方" or r["dialogue"][1]["speaker"] != "我":
            fail("第 %s 条说话人顺序不对（应为 对方 → 我）" % sid)
        if r["target_phrase"] not in r["dialogue"][1]["text"]:
            fail("第 %s 条目标短语「%s」不在我的台词里" % (sid, r["target_phrase"]))

    ids = [r["id"] for r in rows]
    if ids != list(range(1, len(rows) + 1)):
        fail("id 不连续或重复：%s" % ids)

    # ---- 4. 关键：回比 V1，确认原有字段一字未改 ----
    for original in v1:
        generated = next(r for r in rows if r["id"] == original["id"])
        for k in BASE_FIELDS:
            if generated[k] != original[k]:
                fail(
                    "第 %s 条的字段 %s 被改动了！\n      V1: %r\n      V2: %r"
                    % (original["id"], k, original[k], generated[k])
                )

    # ---- 5. 写出 ----
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # ---- 6. 统计 ----
    added = [r for r in rows if r["id"] > max(v1_ids)]
    print("V1 保留  : %d 条（原有字段零改动，仅追加 device）" % len(v1))
    print("V2 新增  : %d 条（id %d-%d）" % (len(added), added[0]["id"], added[-1]["id"]))
    print("合计     : %d 条 -> %s" % (len(rows), OUT))

    by_device = {}
    for r in rows:
        by_device[r["device"]] = by_device.get(r["device"], 0) + 1
    print("device 分布：" + "、".join("%s=%d" % (k, v) for k, v in sorted(by_device.items())))
    unused = enums - set(by_device)
    if unused:
        print("未使用的 device：" + "、".join(sorted(unused)) + "（枚举合法，本批未出现）")


if __name__ == "__main__":
    main()
