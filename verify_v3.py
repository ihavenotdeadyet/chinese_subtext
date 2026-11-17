# -*- coding: utf-8 -*-
"""
corpus_v3.json 只读自检。不通过则非零退出，可挂在提交前。

检查项
  1  id 从 1 连续递增，无重复
  2  字段齐全、类型正确
  3  scene 在 12 个统一大类内
  4  dialogue ≥2 轮，speaker 不为「对方」，role 只有 self / other
  5  target_phrase 必须出现在 dialogue 中
  6  target_speaker 与 target_phrase 实际出现的那一方一致
  7  core_word 非空且不超过 8 字
  8  device 在允许取值内
  9  relation 非空且在统一取值内
  10 intent / emotion / alternative / literal 非空
  11 与上一批已入库的 20 条对得上（v2 内容未被改写）

用法：python verify_v3.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.join(HERE, "corpus_v3.json")
V2 = os.path.join(HERE, "corpus_v2.json")

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


def norm(s):
    drop = " \t\r\n，。！？、；：""''（）()…—～~.,!?;:"
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

    for x in data:
        tag = "#%d(%s)" % (x["id"], x.get("source", "?"))
        # 2
        chk(list(x.keys()) == FIELDS, "%s 字段或顺序不对" % tag)
        # 3
        chk(x["scene"] in SCENES, "%s scene 非法: %s" % (tag, x["scene"]))
        # 4
        chk(len(x["dialogue"]) >= 2, "%s 对话不足 2 轮" % tag)
        for t in x["dialogue"]:
            chk(t["role"] in ("self", "other"), "%s role 非法" % tag)
            chk(t["speaker"] != "对方", "%s 说话人仍是「对方」" % tag)
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

    # 11 与 v2 的 20 条逐字段比对：合并不得改写原文
    if os.path.exists(V2):
        with open(V2, encoding="utf-8") as f:
            v2 = json.load(f)
        by_src = {x["source"]: x for x in data}
        miss = []
        for it in v2:
            src = "v2#%d" % it["id"]
            cur = by_src.get(src)
            if not cur:
                miss.append(src)
                continue
            chk(cur["target_phrase"] == it["target_phrase"], "%s target 被改" % src)
            chk(cur["intent"] == it["intent"], "%s intent 被改" % src)
            chk(cur["emotion"] == it["emotion"], "%s emotion 被改" % src)
            chk(cur["literal"] == it["literal"], "%s literal 被改" % src)
            chk(cur["alternative"] == it["alternative"], "%s alternative 被改" % src)
            chk([t["text"] for t in cur["dialogue"]] == [t["text"] for t in it["dialogue"]],
                "%s 对话原文被改" % src)
        chk(not miss, "v2 有 %d 条没进 v3: %s" % (len(miss), "、".join(miss[:6])))

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


if __name__ == "__main__":
    main()
