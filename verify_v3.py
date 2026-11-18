# -*- coding: utf-8 -*-
"""
corpus_v3.json 只读自检。不通过则非零退出，可挂在提交前。

检查项
  1  id 从 1 连续递增，无重复
  2  字段齐全、顺序与 SCHEMA 一致
  3  scene 在 12 个统一大类内
  4  dialogue ≥2 轮；speaker 只有「我 / 对方」，且与 role（self / other）对得上
  5  target_phrase 必须出现在 dialogue 中
  6  target_speaker 与 target_phrase 实际出现的那一方一致
  7  core_word 非空且不超过 8 字
  8  device 在 11 个允许取值内
  9  relation 在 16 个统一关系内
  10 literal 以 . ! ? 结尾；emotion 顿号并列 2–4 个词；intent 8–70 字；
     alternative 非空
  11 source 形如 v2#3 / c27#12 / p100#45，且不重复
  12 与 v3/src/corpus_v2.json 的 20 条逐字段比对：合并不得改写 V2 原文

用法：python verify_v3.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.join(HERE, "corpus_v3.json")
V2 = os.path.join(HERE, "v3", "src", "corpus_v2.json")

SCENES = {"宿舍", "课堂", "自习", "小组", "社团", "校园",
          "职场", "家庭", "恋爱", "朋友", "线上", "消费"}
DEVICES = {"false_agreement", "understatement", "deflection", "over_politeness",
           "self_deprecation", "silence_ending", "ironic_praise",
           "external_excuse", "hedging", "modest_humility", "sincere"}
RELATIONS = {"同宿舍室友", "同学", "同组组员", "同组同事", "上下级", "情侣",
             "夫妻", "父母与子女", "家人", "师生", "朋友", "亲戚",
             "班干部与同学", "社团负责人与成员", "顾客与服务者", "求职者与面试官"}
FIELDS = ["id", "scene", "relation", "dialogue", "target_phrase", "target_speaker",
          "core_word", "literal", "intent", "emotion", "alternative", "device", "source"]
SOURCE_RE = re.compile(r"^(v2|c27|p100)#\d+$")


def norm(s):
    drop = " \t\r\n，。！？、；：“”‘’（）()…—～~.,!?;:"
    return "".join(ch for ch in s if ch not in drop)


def main():
    fails = []

    def chk(cond, msg):
        if not cond:
            fails.append(msg)

    with open(V3, encoding="utf-8") as f:
        data = json.load(f)

    print("条数: %d" % len(data))

    # 1
    ids = [x["id"] for x in data]
    chk(ids == list(range(1, len(data) + 1)), "id 不是 1..N 连续")

    seen_src = set()

    for x in data:
        tag = "#%d(%s)" % (x["id"], x.get("source", "?"))
        # 2
        chk(list(x.keys()) == FIELDS, "%s 字段或顺序不对" % tag)
        # 3
        chk(x["scene"] in SCENES, "%s scene 非法: %s" % (tag, x["scene"]))
        # 4
        chk(len(x["dialogue"]) >= 2, "%s 对话不足 2 轮" % tag)
        for t in x["dialogue"]:
            chk((t["speaker"], t["role"]) in (("我", "self"), ("对方", "other")),
                "%s 说话人与角色不匹配: %s/%s" % (tag, t["speaker"], t["role"]))
            chk(t["text"].strip() != "", "%s 存在空台词" % tag)
        # 5
        hit = [t["role"] for t in x["dialogue"] if norm(x["target_phrase"]) in norm(t["text"])]
        chk(bool(hit), "%s target 不在对话中: %s" % (tag, x["target_phrase"]))
        # 6
        if hit:
            chk(x["target_speaker"] in hit,
                "%s target_speaker=%s 但实际出现在 %s" % (tag, x["target_speaker"], hit))
        # 7
        chk(x["core_word"] and len(x["core_word"]) <= 8, "%s core_word 为空或过长" % tag)
        # 8
        chk(x["device"] in DEVICES, "%s device 非法: %s" % (tag, x["device"]))
        # 9
        chk(x["relation"] in RELATIONS, "%s relation 非法: %s" % (tag, x["relation"]))
        # 10
        for k in ("literal", "intent", "emotion", "alternative"):
            chk(bool(str(x[k]).strip()), "%s %s 为空" % (tag, k))
        chk(x["literal"].strip().endswith((".", "!", "?")),
            "%s literal 句末缺句号: %s" % (tag, x["literal"]))
        parts = [p for p in x["emotion"].split("、") if p.strip()]
        chk(2 <= len(parts) <= 4, "%s emotion 不是 2–4 个词: %s" % (tag, x["emotion"]))
        chk(not any("。" in p for p in parts), "%s emotion 写成了句子" % tag)
        chk(8 <= len(x["intent"]) <= 70,
            "%s intent 长度 %d 字，超出 8–70" % (tag, len(x["intent"])))
        # 11
        chk(bool(SOURCE_RE.match(x["source"])), "%s source 格式不对: %s" % (tag, x["source"]))
        chk(x["source"] not in seen_src, "%s source 重复: %s" % (tag, x["source"]))
        seen_src.add(x["source"])

    # 12 与 v2 的 20 条逐字段比对：合并不得改写原文
    #    （标注表里显式登记过的修正不算改写，比如 v2#15 的 literal 标点）
    if os.path.exists(V2):
        with open(V2, encoding="utf-8") as f:
            v2 = json.load(f)
        annot = {}
        annot_path = os.path.join(HERE, "v3", "annot_v2.json")
        if os.path.exists(annot_path):
            with open(annot_path, encoding="utf-8") as f:
                annot = json.load(f)
        by_src = {x["source"]: x for x in data}
        miss = []
        for it in v2:
            src = "v2#%d" % it["id"]
            cur = by_src.get(src)
            if not cur:
                miss.append(src)
                continue
            a = annot.get(str(it["id"]), {})
            for k in ("target_phrase", "intent", "emotion", "literal", "alternative"):
                expect = a.get(k, it[k])
                chk(cur[k] == expect, "%s %s 被改" % (src, k))
            chk([t["text"] for t in cur["dialogue"]] == [t["text"] for t in it["dialogue"]],
                "%s 对话原文被改" % src)
        chk(not miss, "v2 有 %d 条没进 v3: %s" % (len(miss), "、".join(miss[:6])))
    else:
        print("  注意: 没找到 %s，跳过第 12 项（V2 基线比对）" % V2)

    if fails:
        print("\n未通过 %d 项:" % len(fails))
        for m in fails:
            print("  -", m)
        sys.exit(1)

    print("全部通过")
    print("  场景大类 %d 个 / 人物关系 %d 种 / 核心词 %d 个"
          % (len({x["scene"] for x in data}), len({x["relation"] for x in data}),
             len({x["core_word"] for x in data})))
    print("  device 分布:", {k: sum(1 for x in data if x["device"] == k) for k in sorted(DEVICES)})
    short = [x["id"] for x in data if len(x["intent"]) < 20]
    if short:
        print("  提示: %d 条 intent 短于 20 字（p100 导入的卡片偏简，待补全）: %s%s"
              % (len(short), "、".join("#%d" % i for i in short[:8]),
                 " …" if len(short) > 8 else ""))


if __name__ == "__main__":
    main()
