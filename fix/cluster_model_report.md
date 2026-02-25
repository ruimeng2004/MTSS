# Cluster Modeling Report (GEN10 vs SR10)

生成时间：2025-12-16

## 数据来源
- 聚类结果：`D4C/dpp/result_cluster/level_{0,1,2}`
- GEN10 评测：`/home/data/result_from_135/sen/GEN10/eval_full_1shot_deepseek-chat_10try_temp=1.0.csv`
- SR10 评测：`/home/data/result_from_135/sen/SR10/eval_full_1shot_deepseek-chat_10try_temp=1.0.csv`
- 选择并套用模型后的输出：`D4C/fix/cluster_model_selector_out/level_{n}_points.csv`

## 口径
- “当前修复数量”：按 `level_{n}_points.csv` 里 `fixed==1` 计数（已按同一层级内 `point_id` 去重，保证一个 bug 只归属一个簇）。
- “理论最高修复数量”：对每层的 bug 集合，只要该 slug 在 GEN10 或 SR10 的 eval 中 **任意一次** `reward==True`，就计为可修复（即 $GEN \cup SR$ 的上界）。

## 结果汇总（每层）
| 层级 | bug 数量 | 当前修复数量 | 理论最高修复数量（GEN∪SR） |
|---:|---:|---:|---:|
| 0 | 696 | 309 | 368 |
| 1 | 696 | 317 | 368 |
| 2 | 696 | 330 | 368 |

## 备注
- level 2 出现过少量重复归属（同一个 `point_id` 落入多个簇），已在本轮改为“首次出现的簇优先”，并把被丢弃的归属记录到：`D4C/fix/cluster_model_selector_out/level_2_duplicates.csv`。
