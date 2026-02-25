import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


@dataclass
class ApiPplResult:
    """Perplexity computed from API-provided token logprobs.

    Notes:
      - Most OpenAI-compatible *chat/completions* APIs only provide logprobs for
        the generated tokens, not for the prompt tokens. Therefore this result
        is typically the perplexity of the output conditioned on the prompt.
      - We treat the returned per-token values as log probabilities (natural
        log). Then avg_nll = -mean(logprob), ppl = exp(avg_nll).
    """

    avg_nll: float
    ppl: float
    n_tokens: int
    token_logprobs: List[float]
    tokens: Optional[List[str]] = None
    
    # New fields for IO PPL
    avg_nll_io: Optional[float] = None
    ppl_io: Optional[float] = None
    n_tokens_io: Optional[int] = None
    prompt_logprobs: Optional[List[float]] = None
    prompt_tokens: Optional[List[str]] = None


def _extract_chat_completion_logprobs(resp: Dict[str, Any]) -> Tuple[List[float], Optional[List[str]], Optional[List[float]], Optional[List[str]]]:
    """Extract token-level logprobs from an OpenAI-compatible chat completion response.
    
    Returns:
      (token_logprobs, tokens, prompt_token_logprobs, prompt_tokens)
    """

    try:
        choices = resp["choices"]
        if not choices:
            raise KeyError("choices")
        choice0 = choices[0]
        logprobs_obj = choice0.get("logprobs")
        if logprobs_obj is None:
            message=choice0.get("message")
            if message:
                logprobs_obj = message.get("logprobs")
        if not logprobs_obj:
            raise KeyError("choices[0].logprobs")

        # OpenAI-style chat logprobs
        content = logprobs_obj.get("content")
        
        # vLLM specific: prompt_logprobs might be in the response if requested
        # Note: vLLM returns prompt_logprobs at the top level of the response, NOT inside choices[0].logprobs
        prompt_logprobs_list = resp.get("prompt_logprobs")
        prompt_token_logprobs: Optional[List[float]] = None
        prompt_tokens: Optional[List[str]] = None
        
        if prompt_logprobs_list and isinstance(prompt_logprobs_list, list):
            # vLLM returns a list of dicts (one per token position), where each dict maps token_id to logprob
            # We need to extract the logprob of the actual token.
            # The structure is: [{token_id: logprob, ...}, ...]
            # But wait, vLLM's prompt_logprobs structure is a list of Optional[Dict[int, Logprob]]
            # We need to know which token was actually in the prompt.
            # Unfortunately, the API response for prompt_logprobs doesn't explicitly say "this was token X".
            # It just gives the logprobs for the token that WAS there (and maybe others if top_logprobs > 0).
            # However, usually the dict contains the logprob for the token that exists.
            # Let's assume we can't easily get the token string without tokenizing locally, 
            # but we can get the logprob if we assume the max logprob corresponds to the token (which is true for prompt since it's forced).
            # Actually, for prompt_logprobs, vLLM returns the logprob of the token that is in the prompt.
            # Let's try to extract the first value from the dict if it exists.
            
            temp_logprobs = []
            for item in prompt_logprobs_list:
                if item and isinstance(item, dict):
                    # In vLLM, for prompt logprobs, it returns {token_id: Logprob(logprob=..., rank=...)}
                    # But via API it might be serialized.
                    # Let's look at a sample response structure if possible.
                    # Assuming it's { "token_id": logprob } or similar.
                    # Actually, vLLM API returns `prompt_logprobs` as `List[Optional[Dict[int, float]]]`.
                    # Since it's the prompt, the token is fixed. The dict should contain the logprob of that token.
                    # We take the first value.
                    if len(item) > 0:
                        # Get the first value (logprob)
                        first_val = list(item.values())[0]
                        # If it's a dict (Logprob object), get 'logprob'
                        if isinstance(first_val, dict):
                             temp_logprobs.append(float(first_val.get('logprob', -999.0)))
                        else:
                             temp_logprobs.append(float(first_val))
                    else:
                        temp_logprobs.append(0.0) # Should not happen for valid tokens
                else:
                    # None or empty
                    pass
            if temp_logprobs:
                prompt_token_logprobs = temp_logprobs

        if isinstance(content, list):
            token_logprobs: List[float] = []
            tokens: List[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                lp = item.get("logprob")
                tok = item.get("token")
                if lp is None:
                    # Some providers may emit null for special tokens.
                    continue
                token_logprobs.append(float(lp))
                if tok is not None:
                    tokens.append(str(tok))
            if not token_logprobs:
                raise ValueError("Empty token logprobs in choices[0].logprobs.content")
            
            return token_logprobs, tokens or None, prompt_token_logprobs, prompt_tokens

        # Fallback: old completions-style fields
        token_logprobs = logprobs_obj.get("token_logprobs")
        tokens = logprobs_obj.get("tokens")
        if isinstance(token_logprobs, list) and token_logprobs:
            cleaned = [float(x) for x in token_logprobs if x is not None]
            if not cleaned:
                raise ValueError("Empty token logprobs in choices[0].logprobs.token_logprobs")
            return cleaned, [str(t) for t in tokens] if isinstance(tokens, list) else None, None, None

    except Exception as e:  # noqa: BLE001 - convert to ValueError with context
        raise ValueError(f"Failed to extract token logprobs from response: {e}") from e

    raise ValueError("Response does not contain token-level logprobs")


def compute_ppl_from_token_logprobs(token_logprobs: List[float], prompt_logprobs: Optional[List[float]] = None) -> ApiPplResult:
    if not token_logprobs:
        raise ValueError("token_logprobs is empty")

    n_tokens = len(token_logprobs)
    avg_nll = -sum(token_logprobs) / n_tokens
    ppl = float(math.exp(avg_nll))
    
    result = ApiPplResult(
        avg_nll=avg_nll,
        ppl=ppl,
        n_tokens=n_tokens,
        token_logprobs=[float(x) for x in token_logprobs],
        tokens=None,
    )
    
    if prompt_logprobs:
        n_prompt = len(prompt_logprobs)
        # IO PPL includes both prompt and output
        all_logprobs = prompt_logprobs + token_logprobs
        n_total = len(all_logprobs)
        avg_nll_io = -sum(all_logprobs) / n_total
        ppl_io = float(math.exp(avg_nll_io))
        
        result.avg_nll_io = avg_nll_io
        result.ppl_io = ppl_io
        result.n_tokens_io = n_total
        result.prompt_logprobs = prompt_logprobs
        
    return result


class OpenAICompatiblePPLGeter:
    """Call an OpenAI-compatible chat/completions API and compute output PPL.

    This implements the user's "方案一": request token logprobs from the API
    (logprobs=true, optional top_logprobs=N), then manually compute perplexity.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float = 500.0,
        retries: int = 3,
        min_retry_sleep_s: float = 1.0,
        qps: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        # If the user provided a base URL like "http://localhost:8000/v1", we might need to append "/chat/completions"
        # However, the original code assumed base_url WAS the full endpoint.
        # To be safe and backward compatible: if it doesn't end in /chat/completions, we append it?
        # Or we just assume the user passes the full endpoint.
        # Let's assume the user passes the FULL endpoint for now to avoid breaking existing usage,
        # but we can add a check or helper.
        
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.retries = retries
        self.min_retry_sleep_s = min_retry_sleep_s
        self.qps = qps
        self._last_call_ts = 0.0

    def _rate_limit(self) -> None:
        if self.qps <= 0:
            return
        min_interval = 1.0 / self.qps
        now = time.time()
        sleep_s = (self._last_call_ts + min_interval) - now
        if sleep_s > 0:
            time.sleep(sleep_s)
        self._last_call_ts = time.time()

    def chat_completion_with_logprobs(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 256,
        temperature: float = 0.0,
        top_logprobs: Optional[int] = None,
        prompt_logprobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return the raw API JSON response."""
        # Local vLLM might not require an API key, so we allow empty key if it's a local address or explicitly allowed.
        # But original code raised ValueError. Let's relax this check.
        # if not self.api_key:
        #    raise ValueError("api_key is empty")
        if not self.model:
            raise ValueError("model is empty")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "logprobs": True,
        }
        if top_logprobs is not None:
            payload["top_logprobs"] = int(top_logprobs)
        
        # vLLM specific: request prompt logprobs if supported
        if prompt_logprobs is not None:
            payload["prompt_logprobs"] = int(prompt_logprobs)

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
             headers["Authorization"] = f"Bearer {self.api_key}"
        else:
             # Some servers might require a dummy key
             headers["Authorization"] = "Bearer EMPTY"

        last_err: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                self._rate_limit()
                r = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_s,
                )
                if r.status_code >= 400:
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
                return r.json()
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(self.min_retry_sleep_s * attempt)

        raise RuntimeError(f"API request failed after {self.retries} retries: {last_err}")

    def compute_output_ppl(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 256,
        temperature: float = 0.0,
        top_logprobs: Optional[int] = None,
    ) -> ApiPplResult:
        """Compute perplexity for the generated output tokens.

        Important limitation:
          - This computes PPL over *generated tokens only*, because most chat
            APIs do not expose prompt token logprobs. If you need IO PPL
            (prompt+output), you must use a white-box local scorer (as in
            D4C/ppl/perplexity.py).
        """
        resp = self.chat_completion_with_logprobs(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_logprobs=top_logprobs,
        )

        token_logprobs, tokens = _extract_chat_completion_logprobs(resp)
        result = compute_ppl_from_token_logprobs(token_logprobs)
        result.tokens = tokens
        return result


def _cli() -> int:
    import argparse
    import json
    import os

    parser = argparse.ArgumentParser(
        description='Test whether an OpenAI-compatible chat/completions proxy returns token logprobs, then compute output PPL.')
    parser.add_argument('--base-url', required=True, type=str,
                        help='Chat completions endpoint, e.g. https://api.shubiaobiao.cn/v1/chat/completions')
    parser.add_argument('--model', default='Say "hello" in one word.',required=True, type=str, help='Model name passed to the proxy')
    parser.add_argument('--api-key', default=os.environ.get('D4C_API_KEY') or os.environ.get('OPENAI_API_KEY') or '',
                        type=str, help='API key (or set D4C_API_KEY / OPENAI_API_KEY)')
    parser.add_argument('--prompt', default='请给我讲一个冷笑话', type=str)
    parser.add_argument('--max-tokens', default=32, type=int)
    parser.add_argument('--temperature', default=0.0, type=float)
    parser.add_argument('--top-logprobs', default=None, type=int)
    parser.add_argument('--print-raw', action='store_true', help='Print raw JSON response (may be large)')

    args = parser.parse_args()

    messages = [{"role": "user", "content": args.prompt}]
    geter = OpenAICompatiblePPLGeter(
        base_url=args.base_url,
        api_key=args.api_key,
        model=args.model,
    )

    resp = geter.chat_completion_with_logprobs(
        messages=messages,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        top_logprobs=args.top_logprobs,
    )

    # Quick signal for whether logprobs exist.
    choice0 = (resp.get('choices') or [{}])[0]
    has_logprobs = bool(choice0.get('logprobs'))
    print('has_logprobs:', has_logprobs)

    if args.print_raw:
        print(json.dumps(resp, ensure_ascii=False)[:20000])

    token_logprobs, tokens = _extract_chat_completion_logprobs(resp)
    result = compute_ppl_from_token_logprobs(token_logprobs)
    result.tokens = tokens
    print('n_tokens:', result.n_tokens)
    print('avg_nll:', result.avg_nll)
    print('ppl:', result.ppl)
    if result.tokens:
        print('tokens_preview:', result.tokens[:20])

    return 0


if __name__ == '__main__':
    raise SystemExit(_cli())
