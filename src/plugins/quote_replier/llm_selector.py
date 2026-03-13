from nonebot.log import logger

from openai import OpenAI

from .config import Config
from .database import QuoteRecord


class LLMSelector:

    def __init__(self, api_key_file: str, model: str, llm_base_url: str, temperature: float, memes: dict[str, str]):
        self.api_key = self._get_api_key(api_key_file)
        self.model = model
        self.llm_base_url = llm_base_url
        self.temperature = temperature
        self.memes = memes

    def _get_api_key(self, file_path: str):
        try:
            with open(file_path, "r") as f:
                return f.readline().strip()
        except Exception as e:
            logger.error(f"Failed to read API key: {e}")
            raise

    def _build_prompt(self, query_text: str, candidate_records: list[QuoteRecord]):
        prompts = [
            "你是一个群聊消息回复器。",
            "任务：根据用户要回复的消息，在候选文本中选择最适合用于回复的一条。",
            "请只从候选 ID 中选择一个，或在都不合适时返回 null。",
            "输出必须是 ID（一个整数）或者null。",
            "以下是一些可能出现在候选文本或用户消息中的一些梗（meme），用来帮助你理解：",
            "\n".join(f"{k}: {v}" for k, v in self.memes.items()),
            f"用户消息: {query_text}",
            "候选文本列表:",
        ]
        for record in candidate_records:
            prompts.append(f"ID={record.id}, Text={record.text}")

        return [
            {"role": "system", "content": "你是一个群聊消息回复器。"},
            {"role": "user", "content": "\n".join(prompts)},
        ]

    async def select_best_match(self, query_text, candidate_records):
        if not query_text or not candidate_records:
            raise ValueError("Query text and candidate records must not be empty.")

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.llm_base_url,
        )
        messages = self._build_prompt(query_text, candidate_records)
        completion = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )

        if completion.choices[0].message.content == "null":
            return None
        for record in candidate_records:
            if str(record.id) == completion.choices[0].message.content.strip():
                return record
