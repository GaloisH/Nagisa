from clients.client import Client
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
        self.memory=[{"role":"system","content":self.system_prompt}]

    def start(self):
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_response(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory + [{"role": "user", "content": prompt}]
        )
        self.memory.append({"role": "assistant", "content": response.choices[0].message.content})
        return response

    def get_streaming_response(self, prompt: str):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory + [{"role": "user", "content": prompt}],
            stream=True,
            reasoning_effort=self.reasoning_effort,
            extra_body={"thinking": {"type": "enabled"}},
        )
        full_response = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk
                full_response += chunk.choices[0].delta.content
        self.memory.append({"role": "assistant", "content": full_response})

    def stop(self):
        pass
        
