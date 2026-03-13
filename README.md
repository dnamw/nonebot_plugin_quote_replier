# nonebot_plugin_quote_replier

一个基于 NoneBot2 + OneBot V11 的群聊文字图回复插件。

插件核心功能：

- 通过 OCR 识别引用图片中的文字并入库。
- 在“引用一条消息 + @机器人 + /comment”场景下，使用 LLM 从候选图库中选出最合适的一张图进行回复。

## 功能清单

- `/help` 或 `/帮助`：查看插件帮助。
- `/upload` 或 `/上传`：引用图片消息并入库（支持多图并发处理）。
- `/list [页码]` 或 `/列表 [页码]`：分页查看当前群图片库。
- `/delete` 或 `/删除`：引用图片消息，按 OCR 文本匹配并删除记录。
- `/comment` 或 `/评论`：引用文本消息，自动挑选并发送最合适的已收录图片。

## 运行环境

- Python 3.10+
- NoneBot2
- OneBot V11 适配器
- LLM SDK：`openai`

> 注意：当前代码中 `llm_selector.py` 使用 OpenAI SDK 调用“兼容 OpenAI 接口”的模型服务，因此需要安装 `openai`。

## 安装

### 1. 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

### 2. 准备 API Key

默认从文件读取 API Key：

- 路径：`secrets/api_key.txt`
- 内容：第一行写入你的 Key

示例：

```text
sk-xxxxxxxxxxxxxxxx
```

### 3. 启用插件

本项目插件位于 `src/plugins/quote_replier`。请确保在 NoneBot 配置中加载该本地插件。

### 4. 启动

```bash
nb run --reload
```

## 配置项

插件配置定义在 `src/plugins/quote_replier/config.py`，可通过 NoneBot 的配置机制覆盖。

| 配置项 | 说明 |
| --- | --- |
| `database_path` | SQLite 数据库路径 |
| `image_path` | 图片落盘目录 |
| `max_concurrent_tasks` | 下载/OCR 并发上限 |
| `list_page_size` | `/list` 每页展示数量 |
| `api_key_file` | API Key 文件路径（读取第一行） |
| `llm_model` | LLM 模型名 |
| `llm_base_url` | LLM API Base URL |
| `llm_temperature` | LLM 采样温度 |
| `meme_for_llm` | 传给 LLM 的梗词解释映射 |

## 使用示例

以下示例都需要“@机器人”：

1. 入库图片
	- 在群聊里先“引用一条包含图片的消息”
	- 发送：`/upload`

2. 查看图库
	- 发送：`/list`
	- 或查看第 2 页：`/list 2`

3. 删除图片
	- 先引用机器人发出的某张图（或 OCR 文本可匹配的图）
	- 发送：`/delete`

4. 自动选图回复
	- 先引用一条文本消息
	- 发送：`/comment`

## 数据与目录

- 数据库：`data/quote_replier.sqlite3`
- 图片目录：`data/images/<group_id>/`

## 致谢

- [NoneBot2](https://nonebot.dev/)
- [NapCatQQ](https://napneko.github.io/)
- [RapidOCR](https://github.com/RapidAI/RapidOCR)
