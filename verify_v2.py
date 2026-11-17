# -*- coding: utf-8 -*-
"""语料自检。只读，不改任何文件。

用法
  python verify_v2.py        # 全部通过时退出码 0，否则 1

检查项（针对合并后的单文件 chinese_subtext_corpus.json）
  1. 合法 JSON 数组
  2. id 从 1 连续到 N，不跳号、不重复
  3. 每条 8 核心字段 id/scene/dialogue/target_phrase/literal/intent/emotion/alternative 齐全且非空
  4. dialogue 至少两轮，且至少有一句“我”的台词（不做严格“对方->我”顺序判定，允许不同来源的写法）
  5. 不存在“完全一样”的重复条目（scene+dialogue+target+literal+intent+emotion+alternative 全同）
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "chinese_subtext_corpus.json")

BASE_FIELDS = ["id", "scene", "dialogue", "target_phrase",
               "literal", "intent", "emotion", "alternative"]

errors, checks = [], []


def ok(msg):
    checks.append(msg)


def bad(msg):
    errors.append(msg)


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def content_key(r):
    return json.dumps({
        "scene": r.get("scene") or "",
        "dialogue": [[t.get("speaker"), t.get("text")] for t in r.get("dialogue", [])],
        "target_phrase": r.get("target_phrase") or "",
        "literal": r.get("literal") or "",
        "intent": r.get("intent") or "",
        "emotion": r.get("emotion") or "",
        "alternative": r.get("alternative") or "",
    }, ensure_ascii=False)


def main():
    rows = load(CORPUS)

    if not isinstance(rows, list):
        bad("chinese_subtext_corpus.json 不是数组")
        sys.exit(1)

    # id 连续
    ids = [r.get("id") for r in rows]
    if ids != list(range(1, len(rows) + 1)):
        bad("id 不连续或重复")
    else:
        ok("id 连续 1-%d" % len(rows))

    # 字段齐全非空
    n = 0
    for r in rows:
        tag = "第 %s 条" % r.get("id")
        for f in BASE_FIELDS:
            if f not in r or r[f] in (None, "", []):
                bad("%s 缺字段或为空：%s" % (tag, f))
                n += 1
    if not n:
        ok("每条 8 核心字段齐全且非空")

    # dialogue：至少两轮、含“我”、每句非空
    n = 0
    for r in rows:
        tag = "第 %s 条" % r.get("id")
        d = r.get("dialogue")
        if not isinstance(d, list) or len(d) < 2:
            bad("%s dialogue 不足两轮" % tag)
            n += 1
            continue
        if not any((t.get("speaker") == "我") for t in d):
            bad("%s dialogue 里没有“我”的台词" % tag)
            n += 1
        if any(not (t.get("text") or "").strip() for t in d):
            bad("%s 存在空的台词" % tag)
            n += 1
    if not n:
        ok("dialogue 至少两轮、含“我”的台词、无空白文本")

    # 无完全相同的重复条目
    seen = set()
    dup = 0
    for r in rows:
        k = content_key(r)
        if k in seen:
            bad("存在完全一样的重复条目（id %s）" % r.get("id"))
            dup += 1
        seen.add(k)
    if not dup:
        ok("无完全一样的重复条目（共 %d 条）" % len(rows))

    print("语料自检（chinese_subtext_corpus.json）")
    print("-" * 46)
    for c in checks:
        print("  ok  " + c)
    for e in errors:
        print("  !!  " + e)
    print("-" * 46)
    print("  %d 条／高危词 %d 个／场景 %d 个" % (
        len(rows), len({r.get("target_phrase") for r in rows}),
        len({r.get("scene") for r in rows})))
    print("-" * 46)
    if errors:
        print("结果：%d 项不通过。" % len(errors))
        sys.exit(1)
    print("结果：全部通过。")


if __name__ == "__main__":
    main()
