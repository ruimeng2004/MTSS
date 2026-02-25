# PPL (Perplexity) 评估

这个目录用于：
- 用“推理模型”（可通过 API，如 deepseek-chat）生成修复输出；
- 用“白盒 CLM 模型”（本地 HuggingFace 模型，如 Mixtral）计算两种困惑度口径：
  - **O**：只对模型输出部分计入 loss/ppl
  - **IO**：对 prompt+output 的整段序列计入 loss/ppl

## 脚本

- [D4C/ppl/d4j_ppl_eval.py](d4j_ppl_eval.py)
- [D4C/ppl/d4j_api_ppl_gen.py](d4j_api_ppl_gen.py)
- [D4C/ppl/d4j_api_ppl_edit.py](d4j_api_ppl_edit.py)

## Quickstart（uv）

启动模型（vLLM，单独开一个终端）：

```bash
cd /home/d1zzy/work/model_inference
bash ./start_vllm_server.sh

# 可选：降低峰值显存
# MAX_NUM_BATCHED_TOKENS=1024 bash ./start_vllm_server.sh
```

```bash
cd /home/d1zzy/work/MTSS-main/ppl
uv sync
```

配置：修改 `config.json`（重点：`base_url` / `model` / `api_key` / `n_samples`）

运行（gen / edit）：

```bash
cd /home/d1zzy/work/MTSS-main/ppl

uv run python d4j_api_ppl_gen.py
uv run python d4j_api_ppl_edit.py

# 只跑一个 case
uv run python d4j_api_ppl_gen.py  --slug Math_106
uv run python d4j_api_ppl_edit.py --slug Math_106

# 限制数量
uv run python d4j_api_ppl_gen.py  --limit 5
uv run python d4j_api_ppl_edit.py --limit 5

# 指定 config
uv run python d4j_api_ppl_gen.py  --config ./config.json
uv run python d4j_api_ppl_edit.py --config ./config.json
```

## API logprobs 方式（方案一）

如果你的“远端 API”支持在 `chat/completions` 响应里返回 token 级 `logprobs`，可以用
[D4C/ppl/ppl_geter.py](ppl_geter.py) 直接从 API 的 log 概率手动计算困惑度。

限制说明：大多数 OpenAI 兼容的 Chat API **只返回生成 tokens 的 logprobs**，不返回 prompt tokens 的 logprobs；因此该方式通常只能计算“输出部分在给定 prompt 条件下”的 PPL，无法得到严格意义的 IO（prompt+output）PPL。若你需要 IO 口径，请继续使用本目录的白盒 scorer（[D4C/ppl/perplexity.py](perplexity.py)）。

### 用法示例

1) 单个 bug（slug）跑一条输出并计算 O/IO

```bash
python D4C/ppl/d4j_ppl_eval.py \
  --data_path D4C/data/defects4j_code.csv \
  --msg_path  D4C/data/defects4j_artifact.csv \
  --slug Closure_126 \
  --history_name HISTORY_AGENT_D4J_MUTI \
  --mode agent \
  --chat_mode remote \
  --remote_model deepseek-chat \
  --remote_proxy DeepSeek \
  --temperature 1.0 \
  --max_try 1 \
  --scorer_model mistralai/Mixtral-8x7B-Instruct-v0.1 \
  --out_csv D4C/result/ppl/closure_126_ppl.csv
```

2) 对比两种任务建模（只换 history）

```bash
python D4C/ppl/d4j_ppl_eval.py ... --history_name HISTORY_AGENT_D4J_MUTI      --out_csv D4C/result/ppl/formatA.csv
python D4C/ppl/d4j_ppl_eval.py ... --history_name HISTORY_AGENT_D4J_MUTI_NO_TEST --out_csv D4C/result/ppl/formatB.csv
```

## 说明

- 你们现有的 `RemoteChat` 不返回 `logprobs`，因此困惑度计算是“生成后在本地白盒模型上 teacher-forcing 计算 CLM loss”。
- `O` 的边界通过 `tokenizer.apply_chat_template(..., add_generation_prompt=True)` 的 prompt token 数来对齐，然后只对后续输出 token 计入 loss。
