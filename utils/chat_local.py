import platform
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer

class LocalChat:
    def __init__(self, dir, model, proxy):
        self.model_dir = dir
        self.model_name = model
        self.proxy = proxy

        if self.model_dir == 'default':
            self.model_path = self.model_name
        else:
            self.model_path = self.model_dir

        # Detect the operating system and choose the appropriate device
        self.device = self.detect_device()
        print(f"Using device: {self.device}")

        # Load the model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float32 if self.device.type == 'mps' else torch.float16,
            device_map='auto' if self.device.type == 'cuda' else None
        ).to(self.device)

        # Load the tokenizer and streamer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            padding_side="left",
            use_fast=False
        )
        self.streamer = TextStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )

    def detect_device(self):
        """Detect the best available device based on the system."""
        os_name = platform.system().lower()
        if os_name == 'darwin':  # macOS
            if torch.backends.mps.is_available():
                return torch.device("mps")
            else:
                print("Warning: MPS not available. Falling back to CPU.")
                return torch.device("cpu")
        else:  # Assume Windows/Linux
            if torch.cuda.is_available():
                return torch.device("cuda")
            else:
                print("Warning: CUDA not available. Falling back to CPU.")
                return torch.device("cpu")

    def encode(self, prompt):
        input_ids = self.tokenizer(prompt, 
                                    return_tensors="pt", 
                                    add_special_tokens=False).input_ids.to(self.device)
        return input_ids

    def generate(self, input_ids, streamer=None, temperature=0.0):
        output_ids = self.model.generate(
            input_ids,
            streamer=streamer,
            max_new_tokens=8192,
            do_sample=True,
            top_k=30,
            top_p=0.85,
            temperature=temperature,
            repetition_penalty=1.0,
            pad_token_id=self.tokenizer.eos_token_id
        )
        return output_ids

    def decode(self, output_ids):
        response = self.tokenizer.batch_decode(
            output_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0].split('[/INST]')[-1].strip()
        return response

    def chat(self, prompt, ID, temperature=0.0):
        with torch.no_grad():
            input_ids = self.encode('<s>')
            for msg in prompt:
                if msg['role'] == 'user':
                    input_ids = torch.cat([
                        input_ids,
                        self.encode("[INST]"),
                        self.encode(msg['content'].strip()),
                        self.encode("[/INST]")
                    ], dim=-1)
                else:
                    input_ids = torch.cat([
                        input_ids,
                        self.encode(msg['content'].strip()),
                        self.encode('</s>')
                    ], dim=-1)

            response = None
            if self.proxy == 'stream':
                output_ids = self.generate(input_ids, self.streamer, temperature)
            elif self.proxy == 'batch':
                output_ids = self.generate(input_ids, None, temperature)
            else:
                raise ValueError("Proxy must be 'stream' or 'batch'")
            response = self.decode(output_ids)
            print(f"ID: {ID}:\tSuccessfully made request")
        return response