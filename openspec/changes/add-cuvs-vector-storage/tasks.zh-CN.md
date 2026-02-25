## 1. 依赖项

- [x] 1.1 将 `pylibraft` 和 `cuvs` 添加到 requirements.txt
- [ ] 1.2 在 embedding/README.md 中记录 CUDA 要求
- [x] 1.3 添加 GPU 检测和回退警告逻辑

## 2. 向量存储实现

- [x] 2.1 创建 `embedding/vector_store.py` 及 `VectorStore` 类
- [x] 2.2 实现索引构建方法（IVF-Flat、IVF-PQ、CAGRA）
- [x] 2.3 实现向量插入（单个和批量）
- [x] 2.4 实现相似性搜索（k-最近邻）
- [x] 2.5 实现索引从磁盘保存/加载
- [x] 2.6 添加向量 ID 和源信息的元数据存储

## 3. 嵌入器集成

- [x] 3.1 在 config.yaml 中添加 `use_vector_store` 选项
- [x] 3.2 添加 cuVS 配置部分（index_type、metric、nlist、nprobe）
- [x] 3.3 修改 `TextEmbedder.process_file()` 以可选地存储在 cuVS 中
- [x] 3.4 修改 `TextEmbedder.process_folders()` 以构建/更新 cuVS 索引
- [x] 3.5 保持 JSON 导出以实现向后兼容性

## 4. 数据迁移工具

- [x] 4.1 创建 `embedding/migrate_to_cuvs.py` 脚本
- [x] 4.2 实现 JSON 到 cuVS 索引加载器
- [x] 4.3 为大型迁移添加进度跟踪
- [x] 4.4 添加验证步骤以比较 JSON 与 cuVS 结果

## 5. 聚类基础

- [ ] 5.1 创建 `embedding/clustering.py` 模块
- [ ] 5.2 实现从 cuVS 批量检索向量
- [ ] 5.3 添加计算成对距离的工具
- [ ] 5.4 为层次聚类集成添加占位符（scipy/cuML）

## 6. 测试与文档

- [x] 6.1 为 `VectorStore` 类添加单元测试
- [ ] 6.2 添加启用 cuVS 的嵌入器集成测试
- [ ] 6.3 使用 cuVS 使用示例更新 embedding/README.md
- [ ] 6.4 在 embedding/config.yaml 注释中添加配置示例
- [ ] 6.5 记录性能基准（JSON vs cuVS 搜索）

## 7. 错误处理与边界情况

- [x] 7.1 优雅地处理缺失的 CUDA，提供信息性错误
- [x] 7.2 处理 cuVS 初始化失败
- [x] 7.3 为向量维度一致性添加验证
- [x] 7.4 处理索引损坏并提供重建能力
