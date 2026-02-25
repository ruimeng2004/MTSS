# Legacy Scripts

这些脚本已被新的 `btms` 模块替代，保留仅供参考。

## 替代关系

| 旧脚本 | 新模块 |
|--------|--------|
| `cluster_hac.py` | `btms.clustering.HACClusterer`, `btms.clustering.ClustererFactory` |
| `cluster_representatives.py` | `btms.sampling.FarthestFirstSampler`, `btms.sampling.KDPPSampler` |
| `task_model_selector.py` | `btms.selection.TaskModelSelector` |
| `cluster_metrics.py` | `btms.experiment.ExperimentRunner` |
| `overall_metrics.py` | `btms.experiment.ExperimentRunner` |

## 新用法

使用新的统一 CLI：

```bash
# 从配置文件运行
python scripts/run_experiment.py --config configs/experiment.yaml

# 从命令行参数运行
python scripts/run_experiment.py \
    --embeddings data/embeddings.jsonl \
    --ppl edit:data/edit.jsonl gen:data/gen.jsonl \
    --view buggy_code \
    --algorithm kmeans hac_average \
    --k 50 100 150 \
    --sampling farthest_first kdpp \
    --reps 1 3 5 \
    --output results/
```

或者直接使用 Python API：

```python
from btms import (
    ClustererFactory, ClusteringConfig,
    SamplerFactory, SamplingConfig,
    TaskModelSelector,
    ExperimentRunner, ExperimentConfig,
)

# 单次实验
config = ClusteringConfig(n_clusters=100, seed=42)
clusterer = ClustererFactory.create('kmeans', config)
result = clusterer.fit(vectors)

# 批量实验
exp_config = ExperimentConfig(...)
runner = ExperimentRunner(exp_config)
results = runner.run()
```
