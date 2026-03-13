from pydantic import BaseModel, Field


class Config(BaseModel):
    database_path: str = Field(
        default="data/quote_replier.sqlite3",
        description="Path to the SQLite database file.",
    )
    image_path: str = Field(
        default="data/images",
        description="Directory to store quote images.",
    )
    max_concurrent_tasks: int = Field(
        default=5,
        description="Maximum number of concurrent tasks for image processing.",
    )
    list_page_size: int = Field(
        default=5,
        description="Number of items to display per page in the list command.",
    )
    api_key_file: str = Field(
        default="secrets/api_key.txt",
        description="File path storing API key, first line only.",
    )
    llm_model: str = Field(
        default="qwen-plus-2025-07-28",
        description="LLM model to use for selecting the best matching quote. Ensure this model is compatible with the Qwen API.",
    )
    llm_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="Base URL for the LLM API. Adjust if using a different provider or endpoint.",
    )
    llm_temperature: float = Field(
        default=0.2,
        description="Temperature for LLM selection requests.",
    )
    meme_for_llm: dict[str, str] = Field(
        default={
            "bt": "变态",
            "旮旯给木": "galgame，一种以恋爱为主题的游戏类型",
            "xyy": "性压抑，表面某人在某件事上对性表现出强烈的欲望",
            "诗人": "是人的谐音，质疑对方是不是人类",
        },
        description="A dictionary of meme phrases to help LLM understand user queries.",
    )
