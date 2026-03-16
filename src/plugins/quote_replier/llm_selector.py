from nonebot.log import logger

from openai import OpenAI

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
            "你是一个群聊消息评论器。",
            "任务：根据用户的消息，在候选文本中选择一条，用来评价用户消息。",
            "你的评价风格应该是偏吐槽的，请选择你认为**最适合**的**一条**候选文本。",
            "输出格式：仅输出被选中文本的ID（一个整数）。",
            "注意：候选文本的开头可能会有一些群头衔，或者人名，这是OCR识别的结果，不是文本的一部分。",
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
        prompts = self._build_prompt(query_text, candidate_records)
        completion = client.chat.completions.create(
            model=self.model,
            messages=prompts,
            temperature=self.temperature,
        )
        try:
            selected_id = int(completion.choices[0].message.content.strip())
        except ValueError:
            logger.error("Failed to parse LLM response as an integer.")
            raise
        for record in candidate_records:
            if record.id == selected_id:
                return record
