# 语料 V2 变更清单

从 V1（10 条）扩到 V2（20 条）。本文件逐项说明**哪些是新增、哪些是修改、哪些没动**，
便于核对，也便于随时回滚。

一句话结论：**V1 的十条原文一个字节没改**，只在末尾追加了一个 `device` 字段；
另外新增了十条自撰语料。改动提交到分支 `corpus-v2-add-10`，`main` 未动。

---

## 一、与开源项目的关系

先划清边界，因为这是最容易说不清的一项。

| 项目 | 许可状态 | 我们用了什么 | 有没有搬数据 |
|---|---|---|---|
| **SwordsmanImp**（上海交大 `sjtu-compling/llm-pragmatics`，200 段《武林外传》） | 仓库**无 LICENSE**，剧本另有版权 | 只借它的**标注方法论**：把「一句台词 → 字面义 → 语用解读」的拆法，升级成 `device` 七分类，并对应到 Gricean 四准则 | **没有**。一条原文都没复制 |
| **LCCC**（清华 `thu-coai/CDial-GPT`） | 声明仅限研究用途，来源为微博爬取 | 看过它的 toy 样本格式 | **没有**。样本被预处理成单字空格串、说话人标记丢失，无法定位「谁说了哪句」，本来也用不了 |
| 豆瓣多轮 / 小黄鸡 | — | — | 早前试过，命中率过低，已放弃（见 `README.md`） |
| **CLiMP** | — | — | 是句法最小对立对基准，与语用无关，排除 |

**为什么不直接搬 SwordsmanImp 的条目**：没有许可协议就意味着默认保留所有权利，
把 200 条内容抄进一个要公开、要答辩的项目，等于无授权再分发。答辩被问到「语料哪来的、有授权吗」，
这个问题答不上来。所以只借方法、不碰数据。

V2 新增的十条都是本项目自己写的，场景取自中文日常语用的常见模式（催婚、甩活、长辈塞钱、
亲戚问工资、导师改稿、让玩具……）。

---

## 二、文件级变更

| 文件 | 状态 | 说明 |
|---|---|---|
| `corpus_v1.json` | **未改动** | 仓库原文的本地副本，只读。blob 哈希仍是 `cc8abcc3…` |
| `corpus_v2.json` | **新增（生成物）** | 由 `build_v2.py` 合并产出，20 条。**不要手改**，改源文件后重跑脚本 |
| `additions_v2.json` | **新增** | 只装新增的 10 条（id 11–20），是这十条的唯一手写来源 |
| `devices_v2.json` | **新增** | 只装 `id → device` 的标注表 + 合法取值枚举 |
| `build_v2.py` | **新增** | 合并脚本，内置「V1 原字段零改动」断言，不通过就直接退出 |
| `verify_v2.py` | **新增** | 只读自检，9 项检查，非零退出码可直接挂提交前 |
| `SCHEMA.md` | **新增** | 标注规范：字段定义、`device` 七分类、写作口径 |
| `MIGRATION-v2.md` | **新增** | 本文件 |
| `translations.json` | **修改** | `scenes` 补 8 个新场景；`items` 从 10 条扩到 20 条。**1–10 条原有内容未改** |
| `sync_corpus.py` | **修改** | 源文件从 v1 改指向 v2（v2 不存在时回落 v1）；拼音表补 7 个词 |

### 为什么要拆成三个 JSON

直接把新条目塞进 `corpus_v1.json` 最省事，但那样「修改」和「新增」就混在同一个文件里，
没法证明原文没被动过。拆开之后：

- `corpus_v1.json` 的哈希只要不变，V1 原文就一定是原样；
- `additions_v2.json` 里出现的每一条，都必然是新增；
- `corpus_v2.json` 是两者的合并结果，随时可以删掉重建。

---

## 三、修改项：V1 十条（只加了 `device`）

唯一的结构变化是**新增一个 `device` 字段**，追加在每条末尾。
`id` / `scene` / `dialogue` / `target_phrase` / `literal` / `intent` / `emotion` / `alternative`
八个字段全部保持原样，`verify_v2.py` 会逐字段比对（8 × 10 = 80 次）。

| id | 场景 | 目标短语 | device | 机制 |
|---|---|---|---|---|
| 1 | 宿舍 | 行吧 | `false_agreement` | 口头应承，心里记账 |
| 2 | 办公室 | 行吧 | `false_agreement` | 接受需求，把风险推回排期 |
| 3 | 情侣约会 | 算了 | `silence_ending` | 用两个字关掉话题，等对方补救 |
| 4 | 办公室会议室 | 算了 | `silence_ending` | 放弃争辩，不是放弃方案 |
| 5 | 情侣日常 | 随便 | `understatement` | 有偏好但不说，等对方猜 |
| 6 | 朋友群聊 | 改天 | `deflection` | 把邀约推到不确定的以后 |
| 7 | 微信社交 | 改天 | `understatement` | 礼貌拒绝，不留具体时间 |
| 8 | 办公室工位 | 再看看 | `understatement` | 拖延，不表态 |
| 9 | 求职面试后 | 再看看 | `understatement` | 双方用模糊话术互留体面 |
| 10 | 商场门店 | 再看看 | `deflection` | 终止推销，不落人脸面 |

> `device` 这一列是**新增的元数据**，不改变任何一句原文。
> 前端目前不读取它，加它是为了以后能做「按话语策略筛选/出题」。

---

## 四、新增项：id 11–20

十条全部自撰，格式与 V1 完全对齐：两轮对话、对方先说、目标短语在我的回应里、
`intent` 解释「为什么这么说」而不是复述字面。

| id | 场景 | 目标短语 | device | 关系与场合 | 补的是什么缺口 |
|---|---|---|---|---|---|
| 11 | 家庭电话 | 你开心就好 | `ironic_praise` | 长辈–晚辈 | README 承认缺家庭长辈场景 |
| 12 | 办公室 | 我尽量 | `understatement` | 上下级 | 职场「不承诺的承诺」 |
| 13 | 情侣吵架后 | 没事 | `false_agreement` | 亲密关系 | 冲突后的试探 |
| 14 | 家里客厅 | 不用不用 | `over_politeness` | 长辈–晚辈 | 亲情中的客气仪式 |
| 15 | 办公室工位 | 好的呢 | `over_politeness` | 平级同事 | 用语气词包住不情愿 |
| 16 | 导师办公室 | 挺好的 | `ironic_praise` | 师生 | 权力不对等下的放弃解释 |
| 17 | 亲戚饭桌 | 还行吧 | `understatement` | 亲戚 | 拒绝被比较 |
| 18 | 家庭餐桌 | 行吧 | `false_agreement` | 亲子 | 同一句「行吧」的第三种读法 |
| 19 | 部门会议 | 算了 | `silence_ending` | 上下级 | 同一句「算了」的第三种读法 |
| 20 | 微信家庭群 | 再看看 | `understatement` | 亲子 | 把冲突推到以后 |

三个已有高危词被复用，特意安排成**同句异景**：`行吧` 现在有宿舍 / 办公室 / 家庭餐桌三个场景，
`算了` 有情侣约会 / 会议室 / 部门会议三个场景。前端会先弹出场景提问卡让用户选，
这本身就是「语境决定意思」的现场演示。

---

## 五、未改动声明

- `corpus_v1.json`：blob 哈希 `cc8abcc3b37e3b26347ac5f2b95f8bd448c53cdc`，与仓库 `main` 分支原文一致。
  本次只读，**没有任何写入**，也没有进入本次提交。
- 提交发生在分支 `corpus-v2-add-10` 上，**`main` 未动**。
  是否合并由组长在该分支的 Pull Request 里决定。
- `translations.json` 的 1–10 条：只动了文件末尾（追加 11–20 的块）和 `scenes` 字典（追加 8 个键），
  原有条目的排版与文字未变。

---

## 六、怎么回滚

按影响面从小到大：

| 想撤销的范围 | 操作 |
|---|---|
| 只撤销前端展示的新语料 | `sync_corpus.py` 的 `SRC` 改回 `corpus_v1.json`，重跑，前端立刻回到 10 条 |
| 撤销 V2 全部语料改动 | 删除 `corpus_v2.json` / `additions_v2.json` / `devices_v2.json` 即可。`corpus_v1.json` 从未被改，不需要恢复 |
| 撤销翻译里新增的部分 | 删掉 `translations.json` 的 `items` 中 `"11"`–`"20"` 六行以外的键块（即 11 到 20 这十块），保留 1–10 |
| 彻底回到 V1 | 上面三条都做完，`corpus.js` 重跑一次 |

**不需要**任何 git 操作，因为原始数据从来没进过 git 的修改区。

---

## 七、怎么核对

```bash
python corpus/build_v2.py    # 合并（内置 V1 零改动断言）
python corpus/verify_v2.py   # 只读自检，9 项
python corpus/sync_corpus.py # 生成前端数据
```

`verify_v2.py` 当前输出：

```
ok  corpus_v1.json 与仓库原文一致（cc8abcc3b37e…）
ok  V1 十条原有字段零改动（8 字段 × 10 条）
ok  V1 条目结构变化仅为追加 device
ok  id 连续 1-20
ok  每条都满足：device 合法 / 两轮 / 对方先说 / 目标短语在我的台词里
ok  additions_v2.json 的 10 条均为全新 id
ok  新增条目与 additions_v2.json 逐字段一致
ok  translations 覆盖全部 20 条
ok  en / ja 讲解齐全，首条替代表达与 alternative 逐字一致

条数 20（V1 10 + 新增 10）
device：deflection=2、false_agreement=4、ironic_praise=2、over_politeness=2、silence_ending=3、understatement=7
高危词 12 个，场景 18 个
结果：全部通过。
```

`self_deprecation`（自贬）这批没用到。它在枚举里是合法值，没有为了凑数硬塞一条不自然的对话。

---

## 八、入库记录

本次改动进的是**分支，不是 `main`**：

| 项 | 值 |
|---|---|
| 分支 | `corpus-v2-add-10` |
| 基线 | `main` 的 `f08f27f`（2026-11-05 初始化 V1，提交前已确认远程未被更新） |
| 新增文件 | `corpus_v2.json`、`additions_v2.json`、`devices_v2.json`、`SCHEMA.md`、`MIGRATION-v2.md`、`build_v2.py`、`verify_v2.py`、`translations.json` |
| 修改文件 | 仅 `README.md`（追加 V2 说明段） |
| 未包含 | `corpus_v1.json`（零改动，不进提交） |

合并与否由组长在该分支的 Pull Request 里决定。若 PR 被关闭，`main` 不受任何影响；
即使误合，按第六节回滚即可，`corpus_v1.json` 始终可以回到原点。

`sync_corpus.py` 没有进仓库：它生成的 `echo-web/corpus.js` 属于前端工程，不在本仓库范围内。
需要重建前端语料时，在完整工作区里跑一次即可。
