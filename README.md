# chinese_subtext —— Echo 中文潜台词解码器 · 语料库

本仓库是 Echo 项目的种子语料库，用于训练和评测「中文潜台词解码」能力：
把一句日常应答（如「行吧」「算了」「随便」）还原成字面义、真实意图、情绪与得体替代回复。

## 文件

| 文件 | 说明 |
|---|---|
| `chinese_subtext_corpus.json` | 完整语料，147 条，**唯一数据源** |
| `rag_kb.py` | 检索增强生成脚本，读取上面这份语料 |
| `SCHEMA.md` | 标注规范：字段定义、写作口径 |
| `verify_v2.py` | 只读自检，非零退出码 |

## `chinese_subtext_corpus.json` 结构

严格 JSON 数组，每个元素 8 个字段：

```json
{
  "id": 1,
  "scene": "宿舍",
  "dialogue": [
    {"speaker": "对方", "text": "原话"},
    {"speaker": "我", "text": "回应"}
  ],
  "target_phrase": "行吧",
  "literal": "字面英文直译",
  "intent": "真实意图",
  "emotion": "情绪",
  "alternative": "得体回复"
}
```

> 本语料由多个来源合并去重而来。多数条目为「对方 → 我」两轮、`target_phrase` 在「我」的台词里；
> 少量历史条目为多轮或 `target_phrase` 在对方台词里，自检脚本不强求该顺序（见 `SCHEMA.md`）。

## 用法

```bash
python verify_v2.py    # 自检：结构合法、id 连续、无完全重复
```

改 `chinese_subtext_corpus.json` 前先看 `SCHEMA.md`；改完跑自检，全绿再提交。

## 许可

自有内容，随项目许可发布。
