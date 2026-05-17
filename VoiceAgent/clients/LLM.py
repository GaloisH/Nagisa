from .client import Client
from openai import OpenAI

@Client.register("LLM")
class LLM(Client):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        system_prompt: str,
        model: str,
        reasoning_effort: str = "low",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.system_prompt = system_prompt
        self.model = model
        self.reasoning_effort = reasoning_effort

    def start(self):
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_response(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]

        )
        return response

    def get_streaming_response(self, prompt: str):
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            reasoning_effort=self.reasoning_effort,
            extra_body={"thinking": {"type": "enabled"}},
        )
        return response
