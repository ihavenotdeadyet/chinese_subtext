# -*- coding: utf-8 -*-
"""
把三套语料合并成 corpus_v3.json。

输入
  corpus_v2.json                       20 条（V1 十条 + 自撰十条）
  chinese_subtext_corpus.json          27 条（组员提交）
  pragmatic_cards.json                100 条（组员提交）
  v3/scene_map.json                    原 scene -> 统一大类
  v3/annot_v2.json                     20 条的说话人与关系
  v3/annot_c27.json                    27 条的说话人、关系、device、改写后的 alternative
  v3/annot_p100.json                  100 条的核心词、device、说话人修正

  （组员那两个源文件优先在仓库根目录找，找不到再去 TEMP/merge_src。
    本地开发副本把这些文件放在 corpus/ 下，结构等价。）

输出
  corpus_v3.json

原则：不改动任何原始语句（dialogue / literal / intent / emotion / target_phrase 一字不动），
只补字段、归一场景、统一 alternative 口径、去重。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TMP = os.path.join(os.environ.get("TEMP", "/tmp"), "merge_src")

DEVICES = {
    "false_agreement", "understatement", "deflection", "over_politeness",
    "self_deprecation", "silence_ending", "ironic_praise",
    "external_excuse", "hedging", "modest_humility", "sincere",
}

# speaker -> 人物关系（p100 用，100 条里角色已写好在 dialogue 中）
SPEAKER_RELATION = {
    "室友": "同宿舍室友",
    "同学": "同学",
    "组员": "同组组员",
    "朋友": "朋友",
    "老师": "师生",
    "班长": "班干部与同学",
    "负责人": "社团负责人与成员",
    "面试官": "面试官与面试者",
    "学长": "学长与学弟学妹",
}


# 人物关系归一：口语化 / 过细的描述合并到统一取值
RELATION_ALIAS = {
    "很久没见的老朋友": "朋友",
    "多年不见的老同学": "同学",
    "学长与学弟学妹": "同学",
    "关系较近的同事": "同组同事",
    "同事（前辈与后辈）": "同组同事",
    "母子或母女": "父母与子女",
    "亲戚（长辈）": "亲戚",
    "亲戚（叔侄）": "亲戚",
    "顾客与销售": "顾客与服务者",
    "顾客与店员": "顾客与服务者",
    "面试官与面试者": "求职者与面试官",
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def src_path(name):
    """组员提交的两个源文件：仓库里就放在根目录，本地开发时可能只在临时目录。

    依次尝试 仓库根 -> TEMP/merge_src，找到哪个用哪个，两处都没有就报错，
    免得静默读到空文件生成一份残缺的语料。
    """
    for d in (ROOT, TMP):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    raise SystemExit(
        "找不到源文件 %s，请把它放在仓库根目录 %s，或临时目录 %s" % (name, ROOT, TMP)
    )


def norm(s):
    """比对用：去掉空白与标点，避免全半角差异造成假不匹配。"""
    drop = " \t\r\n，。！？、；：""''（）()…—～~.,!?;:"
    return "".join(ch for ch in s if ch not in drop)


def build(item, scene_map, annot, source, default_speaker=None, use_annot_alt=False):
    """把一条源记录转成 v3 记录。"""
    aid = str(item["id"])
    a = annot.get(aid, {})

    other = default_speaker or a.get("speaker")
    if not other:
        # 对话可能由「我」先开口，要取第一个不是「我」的说话人
        for t in item["dialogue"]:
            if t["speaker"] != "我":
                other = t["speaker"]
                break
    if not other or other in ("对方", "我"):
        other = "对方"  # 兜底，最后会被校验拦下

    dialogue = []
    for t in item["dialogue"]:
        sp = t["speaker"]
        if sp == "我":
            dialogue.append({"speaker": "我", "role": "self", "text": t["text"]})
        else:
            dialogue.append({"speaker": other, "role": "other", "text": t["text"]})

    # 目标短语在谁嘴里：优先用标注，否则按文本找
    target = a.get("target_phrase") or item["target_phrase"]
    who = ""
    for t in dialogue:
        if norm(target) in norm(t["text"]):
            who = t["role"]
            if who == "self":
                break
    if not who:
        who = "unknown"

    core = a.get("core_word") or target
    alt = a.get("alternative") or item["alternative"]

    rel = a.get("relation") or SPEAKER_RELATION.get(other, "")
    rel = RELATION_ALIAS.get(rel, rel)

    rec = {
        "id": 0,
        "scene": scene_map[item["scene"]],
        "relation": rel,
        "dialogue": dialogue,
        "target_phrase": target,
        "target_speaker": who,
        "core_word": core,
        "literal": item["literal"],
        "intent": item["intent"],
        "emotion": item["emotion"],
        "alternative": alt,
        "device": a.get("device") or item.get("device") or "",
        "source": source,
    }
    return rec


def main():
    scene_map = load(os.path.join(HERE, "scene_map.json"))
    a_v2 = load(os.path.join(HERE, "annot_v2.json"))
    a_c27 = load(os.path.join(HERE, "annot_c27.json"))
    a_p100 = load(os.path.join(HERE, "annot_p100.json"))

    v2 = load(os.path.join(ROOT, "corpus_v2.json"))
    c27 = load(src_path("chinese_subtext_corpus.json"))
    p100 = load(src_path("pragmatic_cards.json"))

    rows = []
    for it in v2:
        rows.append(build(it, scene_map, a_v2, "v2#%d" % it["id"]))
    for it in c27:
        rows.append(build(it, scene_map, a_c27, "c27#%d" % it["id"]))
    for it in p100:
        rows.append(build(it, scene_map, a_p100, "p100#%d" % it["id"]))

    # ---- 去重：只有对话文本完全相同才合并（同词同策略不算重复，那是「同句异景」）----
    seen = {}
    kept, dropped = [], []
    for r in rows:
        key = norm("|".join(t["text"] for t in r["dialogue"]))
        if key in seen:
            dropped.append((r["source"], r["core_word"], r["device"], r["scene"], seen[key]))
            continue
        seen[key] = r["source"]
        kept.append(r)

    # ---- 近邻提示：同核心词 + 同策略 + 同场景，内容不同，只提示不删 ----
    combo = {}
    for r in kept:
        combo.setdefault((r["core_word"], r["device"], r["scene"]), []).append(r["source"])
    near = {k: v for k, v in combo.items() if len(v) > 1}

    for i, r in enumerate(kept, 1):
        r["id"] = i

    out = os.path.join(ROOT, "corpus_v3.json")
    # newline="\n" 固定 LF：Windows 上默认会写成 CRLF，和仓库其余文件不一致，
    # 会让以后每改一行都在 diff 里显示成整文件改动。
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("合并 %d 条 -> 去重后 %d 条（对话完全相同的 %d 条）" % (len(rows), len(kept), len(dropped)))
    for d in dropped:
        print("  合并: %-10s %-8s %-18s %-6s  与 %s 完全相同" % (d[0], d[1], d[2], d[3], d[4]))
    if near:
        print("同核心词 + 同策略 + 同场景（内容不同，保留）:")
        for k, v in sorted(near.items()):
            print("  %-10s %-18s %-5s  %s" % (k[0], k[1], k[2], "、".join(v)))

    # ---- 立即校验，有问题就报 ----
    bad = 0
    for r in kept:
        if r["target_speaker"] == "unknown":
            print("  !! target 不在对话中: #%d %s (%s)" % (r["id"], r["target_phrase"], r["source"]))
            bad += 1
        if r["device"] not in DEVICES:
            print("  !! device 非法: #%d %s (%s)" % (r["id"], r["device"], r["source"]))
            bad += 1
        if r["relation"] in ("", "对方"):
            print("  !! relation 缺失: #%d %s (%s)" % (r["id"], r["core_word"], r["source"]))
            bad += 1
        if len(r["core_word"]) > 8:
            print("  !! core_word 过长: #%d %s (%s)" % (r["id"], r["core_word"], r["source"]))
            bad += 1
        if any(t["speaker"] == "对方" for t in r["dialogue"]):
            print("  !! 说话人仍为「对方」: #%d (%s)" % (r["id"], r["source"]))
            bad += 1

    print("校验问题数:", bad)
    print("输出:", out)
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
