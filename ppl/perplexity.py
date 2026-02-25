#白盒ppl评分器
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class PplResult:
    avg_nll_o: float
    ppl_o: float
    n_tokens_o: int

    avg_nll_io: float
    ppl_io: float
    n_tokens_io: int


def _get_device(device: str) -> torch.device:
    if device == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")
    return torch.device(device)


def load_scorer(model_name_or_path: str, device: str = "auto", torch_dtype: str = "auto"):
    device_obj = _get_device(device)

    dtype: Optional[torch.dtype]
    if torch_dtype == "auto":
        dtype = torch.float16 if device_obj.type == "cuda" else torch.float32
    else:
        dtype = getattr(torch, torch_dtype)

    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=False)
    model = AutoModelForCausalLM.from_pretrained(
        model_name_or_path,
        torch_dtype=dtype,
        device_map="auto" if device_obj.type == "cuda" else None,
    )
    if device_obj.type != "cuda":
        model = model.to(device_obj)

    model.eval()
    return model, tokenizer, device_obj


def build_prompt_ids(
    tokenizer,
    messages: List[Dict[str, str]],
    add_generation_prompt: bool,
) -> torch.Tensor:
    """Build token ids for a chat prompt.

    Prefer tokenizer.apply_chat_template when available; fallback to a simple Mistral/Llama [INST] style.
    """
    if hasattr(tokenizer, "apply_chat_template") and getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=add_generation_prompt,
            return_tensors="pt",
        )

    # Fallback: mimic LocalChat's prompt format.
    parts: List[str] = ["<s>"]
    for msg in messages:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if role == "user":
            parts.append("[INST]")
            parts.append(content)
            parts.append("[/INST]")
        else:
            parts.append(content)
            parts.append("</s>")

    if add_generation_prompt:
        # Start a new assistant turn.
        parts.append("")

    text = "".join(parts)
    return tokenizer(text, return_tensors="pt", add_special_tokens=False).input_ids


def build_io_input_ids(
    tokenizer,
    prompt_messages: List[Dict[str, str]],
    assistant_output: str,
) -> Tuple[torch.Tensor, int]:
    """Return concatenated input_ids for (prompt + assistant_output) and the response start index.

    response_start_idx is the token index in the concatenated sequence where assistant_output tokens begin.
    """
    prompt_ids = build_prompt_ids(tokenizer, prompt_messages, add_generation_prompt=True)
    resp_ids = tokenizer(assistant_output, return_tensors="pt", add_special_tokens=False).input_ids
    input_ids = torch.cat([prompt_ids, resp_ids], dim=1)
    response_start_idx = int(prompt_ids.shape[1])
    return input_ids, response_start_idx


def _masked_nll_sum_and_count(
    model,
    input_ids: torch.Tensor,
    label_mask: torch.Tensor,
    device: torch.device,
    max_length: Optional[int] = None,
    stride: int = 512,
) -> Tuple[float, int]:
    """Compute total NLL sum and token count with a per-position mask.

    label_mask is shape [L] over positions in input_ids (same indexing). A value of 1 means
    the token at that position contributes to loss (as a label). Note: position 0 is always ignored
    for causal LM loss.

    Uses a sliding window when sequence is longer than max_length.
    """
    if input_ids.dim() != 2 or input_ids.shape[0] != 1:
        raise ValueError("input_ids must have shape [1, L]")

    seq_len = int(input_ids.shape[1])
    if max_length is None:
        max_length = int(getattr(model.config, "max_position_embeddings", 4096))

    input_ids = input_ids.to(device)
    label_mask = label_mask.to(device)

    total_nll = 0.0
    total_tokens = 0

    # Ensure first position is ignored (labels[0] is dropped by shift anyway, but keep consistent).
    label_mask = label_mask.clone()
    if seq_len > 0:
        label_mask[0] = 0

    # Sliding window scoring.
    # We score each token exactly once using HF-style overlapping windows: only the last trg_len
    # tokens in each window are labeled.
    for end_loc in range(1, seq_len + 1, stride):
        end_loc = min(end_loc, seq_len)
        begin_loc = max(0, end_loc - max_length)
        input_window = input_ids[:, begin_loc:end_loc]

        # New tokens for this window start at: max(begin_loc, end_loc - stride)
        new_tokens_begin = max(begin_loc, end_loc - stride)
        trg_len = end_loc - new_tokens_begin

        target_ids = input_window.clone()
        # Ignore all but the last trg_len tokens in this window.
        if trg_len < target_ids.shape[1]:
            target_ids[:, :-trg_len] = -100

        # Apply external mask (global positions).
        global_positions = torch.arange(begin_loc, end_loc, device=device)
        allowed = label_mask[global_positions].bool()
        # Convert to label positions: disallow by setting -100.
        target_ids[0, ~allowed] = -100

        # Also make sure any positions we already ignored remain ignored.
        num_labels = int((target_ids != -100).sum().item())
        if num_labels == 0:
            if end_loc == seq_len:
                break
            continue

        with torch.inference_mode():
            outputs = model(input_window, labels=target_ids)
            loss = float(outputs.loss.item())

        total_nll += loss * num_labels
        total_tokens += num_labels

        if end_loc == seq_len:
            break

    return total_nll, total_tokens


def compute_ppl_o_io(
    model,
    tokenizer,
    prompt_messages: List[Dict[str, str]],
    assistant_output: str,
    device: torch.device,
    max_length: Optional[int] = None,
    stride: int = 512,
) -> PplResult:
    input_ids, response_start_idx = build_io_input_ids(tokenizer, prompt_messages, assistant_output)
    seq_len = int(input_ids.shape[1])

    # IO: score every token in the concatenated sequence (except position 0).
    mask_io = torch.ones(seq_len, dtype=torch.int64)

    # O: score only assistant output tokens.
    mask_o = torch.zeros(seq_len, dtype=torch.int64)
    if response_start_idx < seq_len:
        mask_o[response_start_idx:] = 1

    nll_io_sum, n_tokens_io = _masked_nll_sum_and_count(
        model,
        input_ids=input_ids,
        label_mask=mask_io,
        device=device,
        max_length=max_length,
        stride=stride,
    )

    nll_o_sum, n_tokens_o = _masked_nll_sum_and_count(
        model,
        input_ids=input_ids,
        label_mask=mask_o,
        device=device,
        max_length=max_length,
        stride=stride,
    )

    if n_tokens_io == 0:
        raise ValueError("No valid tokens counted for IO perplexity")
    if n_tokens_o == 0:
        raise ValueError("No valid tokens counted for O perplexity (empty output?)")

    avg_nll_io = nll_io_sum / n_tokens_io
    avg_nll_o = nll_o_sum / n_tokens_o

    return PplResult(
        avg_nll_o=avg_nll_o,
        ppl_o=float(math.exp(avg_nll_o)),
        n_tokens_o=n_tokens_o,
        avg_nll_io=avg_nll_io,
        ppl_io=float(math.exp(avg_nll_io)),
        n_tokens_io=n_tokens_io,
    )
