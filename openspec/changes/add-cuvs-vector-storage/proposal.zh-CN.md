# 变更提案：集成 cuVS 向量数据库实现层次聚类

## 为什么

当前的嵌入模块将向量存储为 JSON 文件，这对于下游的相似性搜索和聚类操作效率低下。为了对嵌入的提示词/代码片段进行层次聚类分析，我们需要一个支持高效最近邻搜索和批处理操作的 GPU 加速向量数据库。cuVS（CUDA Vector Search）提供了针对大规模向量数据集优化的 GPU 加速索引和搜索能力。

## 变更内容

- 添加 cuVS 作为依赖项，用于 GPU 加速的向量存储和检索
- 实现封装 cuVS 操作的 `VectorStore` 类（索引构建、搜索、批量检索）
- 修改 `TextEmbedder`，可选择将嵌入持久化到 cuVS 索引，而不是/或除了 JSON
- 为 cuVS 索引参数添加配置选项（索引类型、距离度量）
- 添加用于将现有 JSON 嵌入加载到 cuVS 索引的工具
- 为存储向量上的层次聚类操作创建基础
- 保持与现有基于 JSON 存储的向后兼容性

## 影响

- **受影响的规范：** `embedding`（新能力）
- **受影响的代码：**
  - `embedding/embedder.py` - 添加 cuVS 存储选项
  - `embedding/config.yaml` - 添加 cuVS 配置部分
  - `embedding/vector_store.py` - cuVS 封装的新文件
  - `embedding/clustering.py` - 聚类工具的新文件（未来）
  - `requirements.txt` - 添加 pylibraft 和 cuvs 依赖
- **破坏性变更：** 无（cuVS 存储通过配置选择性启用）
- **依赖项：** 需要支持 CUDA 的 GPU、pylibraft、cuvs 包
- **性能：** 对于大型数据集（>10K 向量）显著更快的相似性搜索
