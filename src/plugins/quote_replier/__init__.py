from pathlib import Path

from nonebot import get_plugin_config, on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me
from nonebot.exception import MatcherException

import math
import asyncio
import tempfile
import httpx

from rapidocr_onnxruntime import RapidOCR


from .config import Config
from .database import QuoteDatabase
from .llm_selector import LLMSelector

__plugin_meta__ = PluginMetadata(
    name="Quote Replier",
    description="A plugin to reply by an image to quoted messages in group chats.",
    usage="@机器人并发送 /help 或 /帮助查看帮助；"
    "引用图片并@机器人发送 /upload 或 /上传 入库；"
    "@机器人发送 /list 或 /列表 [页码] 查看图库；"
    "回复机器人发出的图片并@机器人发送 /delete 或 /删除 删除；"
    "引用消息并@机器人发送 /评论 或 /comment 进行回复文字图。",
    config=Config,
)

config = get_plugin_config(Config)
try:
    quote_db = QuoteDatabase(config.database_path, config.image_path)
    quote_db.init_database()
except Exception as e:
    logger.error(f"Failed to initialize QuoteDatabase: {e}")
    exit(1)
max_concurrent_tasks = max(1, config.max_concurrent_tasks)
ocr_engine = RapidOCR()
llm_selector = LLMSelector(
    config.api_key_file, config.llm_model, config.llm_base_url, config.llm_temperature, config.meme_for_llm
)


help_cmd = on_command("help", aliases={"帮助"}, rule=to_me())
upload_cmd = on_command("upload", aliases={"上传"}, rule=to_me())
list_cmd = on_command("list", aliases={"列表"}, rule=to_me())
delete_cmd = on_command("delete", aliases={"删除"}, rule=to_me())
comment_cmd = on_command("comment", aliases={"评论"}, rule=to_me())


@help_cmd.handle()
async def handle_help():
    await help_cmd.finish(str(__plugin_meta__.usage))


def _get_image_urls(message: Message):
    image_urls = []
    for segment in message:
        if segment.type == "image":
            url = segment.data.get("url")
            if url:
                image_urls.append(url)
    return image_urls


async def _download_image(url: str, save_path: str):
    try:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            await asyncio.to_thread(Path(save_path).write_bytes, response.content)
        return True
    except Exception as e:
        logger.exception(f"Exception occurred while downloading image from {url}: {e}")
        return False


async def _extract_image_text(image_file_path: str):
    try:
        ocr_result = await asyncio.to_thread(ocr_engine, image_file_path)
        if not ocr_result or len(ocr_result) < 2 or not ocr_result[0]:
            return ""
        image_text = ocr_result[0][-1][1]
        return image_text.strip() if isinstance(image_text, str) else ""
    except Exception as e:
        logger.exception(f"Exception occurred while OCR image {image_file_path}: {e}")
        return ""


async def _process_upload_image(url: str, image_file_path: str, group_id: int, user_id: int, message_id: int):
    downloaded = await _download_image(url, image_file_path)
    if not downloaded:
        return False

    image_text = await _extract_image_text(image_file_path)
    if not image_text:
        return False

    await asyncio.to_thread(quote_db.add_quote, group_id, user_id, message_id, image_file_path, image_text)
    return True

@upload_cmd.handle()
async def handle_upload(event: GroupMessageEvent):
    if event is None or event.reply is None:
        await upload_cmd.finish("请先引用一条图片消息，再@我发送 /upload 或 /上传。")

    image_urls = _get_image_urls(event.reply.message)
    if not image_urls:
        await upload_cmd.finish("引用消息里没有图片，请换一条消息再试。")

    tasks = []
    max_concurrency = min(max_concurrent_tasks, len(image_urls))
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _run_bounded(url: str, image_file_path: str) -> bool:
        async with semaphore:
            return await _process_upload_image(url, image_file_path, event.group_id, event.user_id, event.message_id)

    for idx, url in enumerate(image_urls):
        image_file_path = f"{config.image_path}/{event.group_id}/{event.message_id}_{idx}.jpg"
        tasks.append(_run_bounded(url, image_file_path))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    image_count = 0
    for result in results:
        if result:
            image_count += 1
    if image_count > 0:
        await upload_cmd.finish(f"已收录 {image_count} 张文字图。")
    else:
        await upload_cmd.finish("这张图我没识别到足够清晰的文字，换一张试试。")


@list_cmd.handle()
async def handle_list(event: GroupMessageEvent, args: Message = CommandArg()):
    raw_page = args.extract_plain_text().strip()
    page = 1
    if raw_page:
        if not raw_page.isdigit():
            await list_cmd.finish("页码必须是正整数，例如：/list 2")
        page = int(raw_page)
        if page <= 0:
            await list_cmd.finish("页码必须大于 0，例如：/list 1")

    total = await asyncio.to_thread(quote_db.count_by_group, event.group_id)
    if total <= 0:
        await list_cmd.finish("本群还没有收录任何图片，快上传第一张吧！")

    page_size = max(1, config.list_page_size)
    total_pages = math.ceil(total / page_size)
    if page > total_pages:
        await list_cmd.finish(f"页码超出范围，当前最大页码为 {total_pages}。")

    records = await asyncio.to_thread(quote_db.list_page_by_group, event.group_id, page, page_size)
    await list_cmd.send(f"当前群已收录 {total} 张图片，正在显示第 {page}/{total_pages} 页。")

    start_index = ((page - 1) * page_size) + 1
    for offset, record in enumerate(records):
        if not record.image_path:
            continue
        with open(record.image_path, "rb") as f:
            image_bytes: bytes = f.read()
        if not image_bytes:
            raise Exception(f"Failed to read image file: {record.image_path}")
        message = Message(
            [MessageSegment.text(f"[{start_index + offset}] ID={record.id}\n"), MessageSegment.image(image_bytes)]
        )
        await list_cmd.send(message)

    if page < total_pages:
        await list_cmd.send(f"查看更多请使用 /list {page + 1}")


async def _process_delete_image(url: str, temp_file_path: str, group_id: int) -> list[int]:
    downloaded = await _download_image(url, temp_file_path)
    if not downloaded:
        return []

    image_text = await _extract_image_text(temp_file_path)
    if not image_text:
        return []

    records = await asyncio.to_thread(quote_db.select_by_text, group_id, image_text)
    return [record.id for record in records] if records else []


@delete_cmd.handle()
async def handle_delete(event: GroupMessageEvent):
    if event is None or event.reply is None:
        await delete_cmd.finish("请引用图片消息，再@我发送 /delete 或 /删除。")

    image_urls = _get_image_urls(event.reply.message)
    if not image_urls:
        await upload_cmd.finish("引用消息里没有图片，请换一条消息再试。")

    tasks = []
    max_concurrency = min(max_concurrent_tasks, len(image_urls))
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _run_bounded(url: str, temp_file_path: str) -> list[int]:
        async with semaphore:
            return await _process_delete_image(url, temp_file_path, event.group_id)

    for idx, url in enumerate(image_urls):
        temp_file_path = tempfile.gettempdir() + f"/nonebot_quote_replier_temp_delete_{event.message_id}_{idx}.jpg"
        tasks.append(_run_bounded(url, temp_file_path))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    delete_ids: set[int] = set()
    for result in results:
        if isinstance(result, list):
            delete_ids.update(result)

    if not delete_ids:
        await delete_cmd.finish("未找到 OCR 文本相同的图片，未执行删除。")

    await asyncio.gather(*(asyncio.to_thread(quote_db.delete_quote, quote_id) for quote_id in delete_ids))
    await delete_cmd.finish(f"已删除 {len(delete_ids)} 条图片记录。")


@comment_cmd.handle()
async def handle_comment(event: GroupMessageEvent):
    if event is None or event.reply is None:
        await comment_cmd.finish("请先引用一条消息，再@我发送 /comment 或 /评论。")

    query_text = event.reply.message.extract_plain_text().strip()
    if not query_text:
        await comment_cmd.finish("引用消息里没有可用于匹配的文字，请换一条消息再试。")

    candidate_records = await asyncio.to_thread(quote_db.select_by_group, event.group_id)
    if not candidate_records:
        await comment_cmd.finish("本群还没有收录任何图片，快上传第一张吧！")

    try:
        best_record = await llm_selector.select_best_match(query_text, candidate_records)
        if best_record is None:
            await comment_cmd.finish("未找到合适的图片进行回复。")
        with open(best_record.image_path, "rb") as f:
            image_bytes: bytes = f.read()
        if not image_bytes:
            raise Exception(f"Failed to read image file: {best_record.image_path}")
        message = Message([MessageSegment.image(image_bytes)])
        await comment_cmd.finish(message)
    except MatcherException:
        raise
    except Exception as e:
        logger.exception(f"Exception occurred while selecting best match: {e}")
        await comment_cmd.finish("选择最佳匹配时发生错误，请稍后再试。")
