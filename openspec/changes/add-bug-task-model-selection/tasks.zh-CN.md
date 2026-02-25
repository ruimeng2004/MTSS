## 1. 多视角 Bug 工件构造

- [x] 0.1 为本流水线创建一个全新、可自包含的模块目录（尽量不修改既有模块），并按 `src/`（代码）与 `data/`（输出）分层组织
- [x] 1.1 定义 view schema，并建立 `prompt_list/<slug>/` 文件到视角的映射（report/test/code/obfuscated/mixed）
- [x] 1.2 实现可选的 buggy code 混淆/匿名化流水线，用于 "obfuscated" 视角
- [x] 1.3 扩展 embedding 生成逻辑：对每个 (slug, view) 生成 embedding，并写入稳定 ID 与丰富元数据

## 2. 凝聚式层次聚类（Agglomerative）

- [x] 2.0 准备聚类输入导出：从 embeddings.jsonl 导出 vectors.npy / id_mapping.pkl / metadata.pkl
- [x] 2.1 实现凝聚式层次聚类 runner（默认 cosine + average；支持配置）
- [x] 2.2 为可解释性导出 merge tree / dendrogram 所需数据
- [x] 2.3 导出多个切分粒度（例如 k=10/20/50）的聚类结果（支持嵌套/多层 cut）

## 3. 代表点选择（多样性采样）

- [x] 3.1 实现或适配代表点选择：保证每簇覆盖、可复现
- [x] 3.2 生成 per-cluster 导出：代表点 ID + 点的元信息（便于下游 selector 复用）

## 4. PPL 读取与簇级任务建模选择

- [x] 4.1 实现 `ppl/result/` 读取器（同时支持扁平目录与按 sample 分目录两种布局）
- [x] 4.2 定义 per-bug 的 PPL 聚合口径（例如跨 samples 的 IO PPL 中位数）
- [x] 4.3 实现簇级任务建模选择器：基于代表点 PPL 信号做选择（含 tie-break 与缺失回退）

## 5. 评估与报告

- [x] 5.1 计算并导出簇级指标（PPL 分布、不同任务建模的差异等）
- [x] 5.2 计算并导出整体指标与基线对比（always-A / always-B / oracle）
- [x] 5.3 生成面向人工检查的 Markdown 报告（强调可解释性）

## 6. 质量、校验与文档

- [ ] 6.1 增加 schema/一致性校验（缺失 view、缺失 PPL、重复归属等）
- [ ] 6.2 增加最小测试（PPL 解析、聚类导出 schema）
- [ ] 6.3 文档化端到端运行方式与输出解释方法
