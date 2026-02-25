# DPP / k-DPP (Greedy) Sampling

本目录提供基于 `D4C/embedding/clustering_results.json` 的多样性采样工具。

- 目标：从分层聚类结果里挑选“覆盖更广、冗余更少”的代表样本集合
- 算法：贪心 DPP（近似 MAP 选集），默认 cosine kernel（先 L2 normalize 再点积）
- 说明：工程上常称“k-DPP”，但这里实现的是贪心 DPP 近似（不是严格随机 k-DPP 分布采样器）

## 输入

- `D4C/embedding/clustering_results.json`
  - 来自 `D4C/embedding/hierarchical_clustering.py`
  - 需要包含 `hierarchy.level_N.*.center` 与 `hierarchy.level_N.*.vectors`（每个向量至少含 `id/folder/file/tokens`）

- （可选）`D4C/embedding/vector_index/`
  - `vectors.npy` + `id_mapping.pkl`
  - 用于簇内选择代表样本：按样本向量到簇中心的 L2 距离排序，优先取更“典型”的成员

## 输出

默认写到 `--out` 指定目录：

- `selected.json`
  - `config`：参数回显
  - `stats`：统计信息（selected 数、缺失向量数等）
  - `selected_ids`：选中的 id 列表
  - `selected`：每个样本的元数据摘要（`id/folder/file/tokens/cluster_key/level`）

- （可选）`selected.csv`

为了增强可读性，脚本还会生成：

- `selected.md`：同一份结果的 Markdown 表格版本（方便直接在 VS Code 里查看）

当使用 `--all-levels` / `--levels` 一次跑多层时，会在输出根目录额外生成：

- `summary.md`：按层汇总（每层链接到对应 `level_N/selected.*`）

## 用法

在仓库根目录执行：

```bash
python D4C/dpp/kdpp_sampling.py \
  --input D4C/embedding/clustering_results.json \
  --index-path D4C/embedding/vector_index \
  --level 1 \
  --k 0 \
  --seed 42 \
  --out D4C/dpp/result/level_1
```

说明：当前脚本会保证“**每个簇至少 1 个代表**”。因此：

- `--k 0` 表示自动：按 proposal 的每层默认规则计算每簇代表数并求和（推荐默认）。
- 如果显式设置 `--k N`，它表示“本层总输出上限”，且必须满足 `N >= 本层簇数`，否则无法做到每簇覆盖。

一次性对三层（或所有可用层）都跑：

```bash
python D4C/dpp/kdpp_sampling.py \
  --input D4C/embedding/clustering_results.json \
  --index-path D4C/embedding/vector_index \
  --all-levels \
  --k 0 \
  --seed 42 \
  --out D4C/dpp/result \
  --csv
```

如果你希望完全不依赖 `vector_index/`（只用聚类产物即可运行）：

```bash
python D4C/dpp/kdpp_sampling.py \
  --input D4C/embedding/clustering_results.json \
  --no-index \
  --level 1 \
  --k 32 \
  --seed 42 \
  --out D4C/dpp/result/level_1_no_index
```

生成 CSV：

```bash
python D4C/dpp/kdpp_sampling.py --csv --out D4C/dpp/out_csv
```

最小自检（不写文件；校验去重与同 seed 可复现）：

```bash
python D4C/dpp/kdpp_sampling.py --self-check
```

## 参数说明（摘要）

- `--input`：`clustering_results.json` 路径（默认指向 `D4C/embedding/clustering_results.json`）
- `--index-path`：`vector_index` 路径（默认 `D4C/embedding/vector_index`）
- `--no-index`：不加载 index（簇内代表选择退化为稳定排序截断）
- `--level`：采样层级 `level_N`（默认 deepest）
- `--k`：目标样本数（若不足则返回可用样本并在 stats 反映）
- `--seed`：随机种子（用于稳定 tie-break）
- `--per-cluster`：强制每个“被选簇”内取固定数量代表（覆盖默认启发式）
