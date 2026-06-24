import os
from typing import List, Dict, Any, Optional
from huggingface_hub import InferenceClient

_client: Optional[InferenceClient] = None
_default_model_id = "Qwen/Qwen2.5-7B-Instruct"


def get_inference_client() -> InferenceClient:
    global _client
    if _client is None:
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HF_API_TOKEN")
        if not hf_token:
            raise RuntimeError("HF_TOKEN or HF_API_TOKEN environment variable is not set")
        _client = InferenceClient(token=hf_token)
    return _client


def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """Convert messages list to Zephyr-style chat prompt."""
    prompt = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            prompt += f"<|system|>\n{content}</s>\n"
        elif role == "user":
            prompt += f"<|user|>\n{content}</s>\n"
        elif role == "assistant":
            prompt += f"<|assistant|>\n{content}</s>\n"
    prompt += "<|assistant|>\n"
    return prompt


def chat_completion(
    messages: List[Dict[str, str]],
    model_id: Optional[str] = None,
    max_new_tokens: int = 512,
    temperature: float = 0.1,
    **kwargs: Any,
) -> str:
    client = get_inference_client()
    model = model_id or _default_model_id

    response = client.chat_completion(
        messages=messages,
        model=model,
        max_tokens=max_new_tokens,
        temperature=temperature,
    )

    if response and response.choices and len(response.choices) > 0:
        return response.choices[0].message.content.strip()
    return ""


if __name__ == "__main__":
    msgs = [
        {"role": "system", "content": "You are a helpful assistant that answers concisely."},
        {"role": "user", "content": "What is 2+2?"}
    ]
    print(chat_completion(msgs, max_new_tokens=200))