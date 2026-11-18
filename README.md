# chinese_subtext —— Echo 中文潜台词解码器 · 语料库

本仓库是 Echo 项目的种子语料库，用于训练和评测「中文潜台词解码」能力：
把一句日常应答（如「行吧」「算了」「随便」）还原成字面义、真实意图、情绪与得体替代回复。

## 文件

| 文件 | 说明 |
|---|---|
| `corpus_v3.json` | **当前唯一数据源**，147 条，13 字段 |
| `SCHEMA.md` | 标注规范：字段定义、`device` 11 类、场景与关系取值 |
| `verify_v3.py` | 只读自检，12 项，非零退出码 |
| `rag_kb.py` | 检索增强生成脚本，读 `corpus_v3.json` |
| `v3/merge_v3.py` | 合并脚本：读三套源 + 标注表，生成 `corpus_v3.json` |
| `v3/scene_map.json` | 86 个原始场景名 → 12 个大类的映射 |
| `v3/annot_v2.json` | V2 二十条的说话人与关系 |
| `v3/annot_c27.json` | 27 条的说话人、关系、`device`、改写后的 `alternative` |
| `v3/annot_p100.json` | 100 条的核心词、`device`、说话人修正 |
| `v3/src/` | 三套源文件原样留档，供复现合并 |

## `corpus_v3.json` 结构

严格 JSON 数组，每个元素 13 个字段：

```json
{
  "id": 1,
  "scene": "宿舍",
  "relation": "同宿舍室友",
  "dialogue": [
    {"speaker": "对方", "role": "other", "text": "你下楼买饭吗？顺便帮我带一份呗，我打游戏走不开。"},
    {"speaker": "我",   "role": "self",  "text": "行吧。"}
  ],
  "target_phrase": "行吧",
  "target_speaker": "self",
  "core_word": "行吧",
  "literal": "Alright then.",
  "intent": "不想去，但不想为这点小事跟室友闹不愉快，先答应下来，心里已经记了一笔。",
  "emotion": "无奈、敷衍、轻微不情愿",
  "alternative": "行，不过下次换你带了。我这周作业堆得有点多。",
  "device": "false_agreement",
  "source": "v2#1"
}
```

## 口径要点

1. **`speaker` 只有两个值：`我` / `对方`**。谁是谁不写在这里，看 `relation`
   （同宿舍室友 / 上下级 / 顾客与服务者…）。`role` 是 `self` / `other`，与 `speaker` 一一对应。
2. **不限定谁先说**。真实对话里「我」先开口很常见，`dialogue[0]` 不必是对方。
   `target_speaker` 记录目标短语落在谁嘴里：`self` 是「我」说的（120 条），
   `other` 是对方说的（27 条），前端据此决定展示方式。
3. **`target_phrase` 可以是一整句**（如「不了不了，我喝不下了」），另设 `core_word`
   （如「不了不了」）供词卡与「同句异景」归类使用。
4. **`device` 11 类**：7 类沿用 V2，新增 `external_excuse` / `hedging` /
   `modest_humility` / `sincere`，详见 `SCHEMA.md`。
5. 147 条里 `行吧`（4 个场景）、`再看看`（4 个）、`算了`（3 个）、`随便`（3 个）用来看「同句异景」。

## 用法

```bash
python v3/merge_v3.py    # 改完标注表重跑，重新生成 corpus_v3.json
python verify_v3.py      # 自检 12 项，全绿再提交
```

`merge_v3.py` 输出固定 LF 换行 + 2 空格缩进，重跑结果与仓库里的 `corpus_v3.json`
逐字节一致（JSON 层面完全相等），所以「改语料」只应该改 `v3/src/` 或 `v3/annot_*.json`，
不要手改 `corpus_v3.json`。

## 数据来源与可复现

`corpus_v3.json` = `v3/src/corpus_v2.json`(20) + `v3/src/corpus_c27.json`(27) +
`v3/src/pragmatic_cards.json`(100)，去重 0 条，编号 1–147。

> 旧文件 `chinese_subtext_corpus.json`（147 条 8 字段版）已被 `corpus_v3.json` 取代：
> 两者是同一批 147 条，V3 只是补了 `relation` / `target_speaker` / `core_word` /
> `device` / `source`，并把 `scene` 归并成 12 类、说话人统一成「我 / 对方」。
> 需要旧版可看 commit `5ba271b`。

- **对话原文、`intent`、`target_phrase` 一字未改**；`literal` / `emotion` / `alternative`
  只有标注表里显式登记的修正（27 条 `alternative` 只留台词、`v2#15` 的 `literal` 标点、
  `c27#2` 的 `emotion` 写法），其余原样。
- 人物关系有 5 条是推断的：`c27#4 / #12 / #13 / #16 / #21` 的对话里看不出确切关系
  （恋人还是室友、家人还是配偶），现按上下文取了最常见的一种，**需要组里确认**。
- `c27#25`（卖保养套餐那条）的标注把对方写成了「销售」，实际对话里「我」是销售、
  对方是顾客（`alternative` 也是销售该说的话），已把 `speaker` 改成「顾客」。

## 已知待办

- **`sincere`（25 条）**：真诚道歉、道谢、答应，字面即本意，本来不需要解码。
  为不把它们硬归成「过度客气」单列了一类，属于**待替换项**，后续应换成真有潜台词的场景。
- **127 条缺英日讲解**：V2 时期的 `translations.json` 只覆盖 20 条，V3 合并时连同已失效的
  `corpus_v1.json` / `corpus_v2.json` 一起删除（原文在 git 历史里）。补齐前不建议对外展示英文版。
- **89 条 `intent` 偏短**：`p100` 导入的卡片多为 8–28 字（V2/V3 自撰条目 30–56 字），
  解释得住但不够展开，补写时按 30 字以上、说清「为什么这么说」。
- **场景分布偏「校园」**：原 86 个具体场景归并成 12 类后，校园占 36 条，消费只有 3 条。

## 与 V2 的口径差异

1. **取消「必须对方先说」**，改用 `target_speaker` 记录目标短语的说话人。
2. **`alternative` 只保留台词**：原 27 条混着「听出TA其实不情愿：『…』」这类策略说明，
   教学时没法直接照着说，已逐条改写；原本的意思留在 `intent` 里。
3. **`device` 从 7 类扩到 11 类**：合并进来的 127 条里，「借客观理由婉拒」「拖延不表态」
   「受夸谦辞」占了大头，7 类覆盖不了，硬塞会误导标注。
4. **说话人统一为「我 / 对方」**（与 main 的口径一致），具体关系由 `relation` 承担。

## 回滚

`corpus_v3.json` 由 `v3/` 下的源文件和标注表生成，回滚上一版直接 `git revert` 即可：
V2 的 20 条原文在 `v3/src/corpus_v2.json`（前 10 条即 V1 原文），27 条与 100 条源文件也在
`v3/src/`，没有不可再生的内容。

## 许可

自有内容，随项目许可发布。
