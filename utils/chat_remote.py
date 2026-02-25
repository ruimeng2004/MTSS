import requests
import time
from urllib.parse import urljoin

try:
    from retry import retry  # type: ignore
except Exception:  # pragma: no cover
    def retry(*, tries: int = 3, delay: int = 2, backoff: int = 2):
        def deco(fn):
            def wrapper(*args, **kwargs):
                last_exc: Exception | None = None
                d = float(delay)
                for _ in range(int(tries)):
                    try:
                        return fn(*args, **kwargs)
                    except Exception as e:
                        last_exc = e
                        time.sleep(d)
                        d *= float(backoff)
                if last_exc is not None:
                    raise last_exc
                return fn(*args, **kwargs)

            return wrapper

        return deco

class RemoteChat:
    def __init__(self, api_key, model, proxy, *, base_url: str | None = None):
        self.api_key = api_key
        self.model = model
        self.proxy = proxy
        self.base_url = base_url

    @retry(tries=3, delay=2, backoff=2)
    def safe_request(self, url, data, headers):
        response = requests.post(url, json=data, headers=headers)
        # print(response.json())
        # exit()
        return response.json()
        
    def chat(self, prompt, ID, temperature=0.0):
        data = {
            'model': self.model,
            'messages': prompt,
            'temperature': temperature
        }
        if self.proxy == 'AI':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            url = 'https://api.ai-gaochao.cn/v1/chat/completions'
        elif self.proxy == 'OMG':
            headers = {
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            url = 'https://aigptx.top/v1/chat/completions'
        elif self.proxy == 'OpenAI':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer sk-KAShPcbh6zidpAv768680a0488E24f0bBf766814F5900b3d'
            }
            url = 'https://api.shubiaobiao.cn/v1/chat/completions'
        elif self.proxy == 'OpenAIf2':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer sk-f2sNzJXqWaFtBg9hRXYnanHWHAG0zaTOi1ZYt9y04zPwsNqS'
            }
            url = 'https://api.f2gpt.com/v1/chat/completions'
        elif self.proxy == 'DeepSeek':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer sk-4aba884b61424f59b1fab0f60d188103'
            }
            url = 'https://api.deepseek.com/chat/completions'
        elif self.proxy == 'bailian':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer sk-4d88933783f844ed99cc603b0ac4a70d'
            }
            url = 'https://api.deepseek.com/chat/completions'    
        else:
            raise ValueError("proxy must be 'AI', 'OMG', or 'OpenAI'")
        ti = 0
        backend_model = 'Unknown'
        total_tokens = 'N/A'
        while ti <= 10:
            response_api = self.safe_request(url, data, headers)
            try:
                response = response_api['choices'][0]['message']['content']
                if 'usage' in response_api:
                    total_tokens = response_api['usage'].get('total_tokens', 'N/A')
                if 'model' in response_api:
                    backend_model = response_api['model']  # 提取后端运行的具体模型型号
                    if backend_model != self.model:
                        print(f"Warning: Requested model {self.model} but got response from {backend_model}")
                break
            except Exception as e:
                print(f"ID: {ID}:\t{response_api}")
                response = None
                ti += 1
                time.sleep(3)
        return response,total_tokens
    
    def get_embedding(self, text, ID):
        """Get text embedding using the configured model.
        
        Args:
            text (str): Text to embed.
            ID (str): Identifier for logging.
            
        Returns:
            tuple: (embedding_vector, token_count) or (None, None) on failure.
        """
        data = {
            'model': self.model,
            'input': text
        }

        def _normalize_embedding_url(base: str) -> str:
            b = str(base).strip()
            if not b:
                return b
            # If caller already provided a concrete embeddings endpoint, keep it.
            if "/embeddings" in b:
                return b
            # Otherwise treat base_url as host root and append a common embeddings path.
            # Prefer /embeddings to match the server docs screenshot; fall back to /v1/embeddings
            # only if the server requires OpenAI-style prefix.
            if not b.endswith("/"):
                b = b + "/"
            return urljoin(b, "embeddings")

        def _extract_embedding(resp: dict):
            # Common OpenAI-compatible shape: {"data":[{"embedding":[...]}], "usage":{...}}
            if isinstance(resp, dict) and "data" in resp and isinstance(resp.get("data"), list) and resp["data"]:
                d0 = resp["data"][0]
                if isinstance(d0, dict) and "embedding" in d0:
                    return d0.get("embedding"), resp.get("usage", {}).get("total_tokens", "N/A")

            # Alternative shapes some proxies use
            for key in ("embedding", "embeddings", "vector", "vectors"):
                if isinstance(resp, dict) and key in resp:
                    return resp.get(key), resp.get("usage", {}).get("total_tokens", "N/A")

            # Unknown
            raise KeyError("embedding")
        
        if self.base_url:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            url = _normalize_embedding_url(self.base_url)
        elif self.proxy == 'bailian':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings'
        elif self.proxy == 'OpenAI':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            url = 'https://api.openai.com/v1/embeddings'
        else:
            # Fallback to chat completion for proxies without embedding endpoints
            return self._embedding_via_chat(text, ID)
        
        ti = 0
        while ti <= 10:
            try:
                response_api = self.safe_request(url, data, headers)
                embedding, total_tokens = _extract_embedding(response_api)
                return embedding, total_tokens
            except Exception as e:
                preview = None
                try:
                    if isinstance(response_api, dict):
                        preview = {k: response_api.get(k) for k in list(response_api.keys())[:8]}
                except Exception:
                    preview = None
                if preview is not None:
                    print(f"ID: {ID}:\tEmbedding request failed: {e}; url={url}; resp_keys={list(preview.keys())}; resp_preview={preview}")
                else:
                    print(f"ID: {ID}:\tEmbedding request failed: {e}; url={url}")
                ti += 1
                if ti <= 10:
                    time.sleep(3)
        
        return None, None
    
    def _embedding_via_chat(self, text, ID):
        """Fallback method to get embedding via chat completion.
        
        Args:
            text (str): Text to embed.
            ID (str): Identifier for logging.
            
        Returns:
            tuple: (text_representation, token_count) or (None, None) on failure.
        """
        prompt = [
            {
                "role": "system",
                "content": "Generate a semantic representation of the following text."
            },
            {
                "role": "user",
                "content": text
            }
        ]
        return self.chat(prompt, ID, temperature=0.0)
