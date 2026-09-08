from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI


class ChatVLLM:
    def __init__(self, config):
        self.client = OpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
        )
        self.model = config["model_name"]
        self.temperature =  config["temperature"]

    def invoke(self, prompt, variables=None):
        content = prompt.format(**variables) if variables else prompt

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,  
            messages=[
                {"role": "user", "content": content},
            ],
            extra_body={
            "chat_template_kwargs": {"enable_thinking": False},
            },
        )
        return response.choices[0].message.content


def create_llm(config):
    model_type = config["type"]

    if model_type == "ollama":       
        return ChatOllama(
            base_url=config["base_url"],
            model=config["model_name"],
            temperature=config["temperature"],
            streaming=True,
        )

    elif model_type == "api":  
        return ChatOpenAI(
            model=config["model_name"],
            temperature=config["temperature"],
        )

    elif model_type == "vllm":              
        return ChatVLLM(config)