import requests
import json

# 配置
API_URL = "http://localhost:8000/v1/chat/completions"
MODEL_PATH = "/home/d1zzy/.cache/modelscope/hub/models/Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8"

def test_model():
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer EMPTY"  # 本地部署通常不需要真实 Key
    }
    
    data = {
        "model": MODEL_PATH,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Who are you?"}
        ],
        "max_tokens": 50,
        "temperature": 0.7
    }

    print(f"正在连接 {API_URL} ...")
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print("\n✅ 模型连接成功！")
            print("-" * 30)
            print(f"回复内容: {content}")
            print("-" * 30)
        else:
            print(f"\n❌ 请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接失败！请检查 vLLM 服务是否已启动 (端口 8000)。")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    test_model()
