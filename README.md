# nonebot_plugin_quote_replier

一个基于 NoneBot2 + OneBot V11 的群聊文字图回复插件。

插件核心思路：
- 通过 OCR 识别引用图片中的文字并入库。
- 在群内分页查看图库。
- 通过 OCR 文本匹配删除已收录图片。
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
- OCR：`rapidocr-onnxruntime`
- LLM SDK：`openai`

> 注意：当前代码中 `llm_selector.py` 使用 OpenAI SDK 调用“兼容 OpenAI 接口”的模型服务，因此需要安装 `openai`。

## 安装

### 1. 安装依赖

在项目根目录执行：

```bash
pip install -e .
pip install openai
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

如果你通过 `nb` 命令管理插件，可执行：

```bash
nb plugin install --local quote_replier
```

或手动在配置中将 `quote_replier` 加入本地插件列表。

### 4. 启动

```bash
nb run --reload
```

## 配置项

插件配置定义在 `src/plugins/quote_replier/config.py`，可通过 NoneBot 的配置机制覆盖。

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `database_path` | `data/quote_replier.sqlite3` | SQLite 数据库路径 |
| `image_path` | `data/images` | 图片落盘目录 |
| `max_concurrent_tasks` | `5` | 下载/OCR 并发上限 |
| `list_page_size` | `5` | `/list` 每页展示数量 |
| `zhipu_api_key_file` | `secrets/api_key.txt` | API Key 文件路径（读取第一行） |
| `llm_model` | `glm-4.7-flash` | LLM 模型名（当前代码中仅作为配置项保留） |
| `llm_temperature` | `0.2` | LLM 采样温度 |
| `meme_for_llm` | 内置词典 | 传给 LLM 的梗词解释映射 |

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
- 密钥文件：`secrets/api_key.txt`

## 工作机制说明

### 上传（/upload）

1. 读取被引用消息中的图片 URL。
2. 下载图片到本地。
3. OCR 提取文字。
4. 仅当识别到非空文本时写入数据库。

### 删除（/delete）

1. 下载并 OCR 被引用图片。
2. 以 OCR 文本执行 `LIKE` 匹配查库。
3. 删除匹配记录并删除对应图片文件。

### 评论选图（/comment）

1. 读取被引用文本作为查询语句。
2. 取当前群所有候选记录。
3. 让 LLM 在候选 ID 中返回最合适的一条（或 `null`）。
4. 发送命中的图片。

## 常见问题

### 1. `/upload` 提示“没识别到足够清晰的文字”

- 该图 OCR 结果为空或不稳定。
- 建议换更清晰、文字更明显的图。

### 2. `/comment` 无法返回图片

- 请检查 `secrets/api_key.txt` 是否存在且第一行有效。
- 确认模型服务可访问。
- 确认当前群至少已收录 1 张图片。

### 3. 插件不生效

- 确认本地插件 `quote_replier` 已被 NoneBot 加载。
- 确认适配器为 OneBot V11，且机器人已正常连通。

## 开发与调试

```bash
nb run --reload
```

可选安装类型检查：

```bash
pip install pyright
pyright
```

## 致谢

- [NoneBot2](https://nonebot.dev/)
- [nonebot-adapter-onebot](https://github.com/nonebot/adapter-onebot)
- [RapidOCR](https://github.com/RapidAI/RapidOCR)
