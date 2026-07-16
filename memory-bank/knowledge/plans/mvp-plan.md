# 番剧解说趋势情报系统

## MVP分阶段开发计划

**文档版本：** MVP 1.0
**编制日期：** 2026年7月17日
**目标市场：** 美国英语用户
**试点内容：** 番剧片段解说、高能片段解说、热门内容改写与模仿
**核心数据源：** YouTube Shorts、YouTube长视频
**实验数据源：** TikTok
**直接用户：** 1名运营策划兼管理者
**间接用户：** 5—10名剪辑师

---

# 1. 项目目标

本项目建设一个面向番剧解说团队的趋势发现和选题辅助系统。

系统每天从管理者维护的YouTube频道、TikTok账号、关键词、动漫作品和榜单中采集内容，通过跨频道共振、相对频道表现、增长动量和趋势生命周期判断热门题材，再使用LLM对趋势进行归纳和解释，最终生成约30个候选创作方向。

管理者在Web后台中审核候选、添加备注、选择10—15个方向，并导出Markdown或HTML简报转发给剪辑团队。

## 1.1 核心业务目标

第一目标是将管理者或剪辑师每天寻找选题所需的1—3小时降低到30—60分钟。

第二目标是比纯人工浏览更稳定地识别以下机会：

* 多个监控频道在短时间内同时制作同一题材；
* 相关视频普遍明显优于各频道自身平均表现；
* 中小频道出现异常爆发；
* 某个主题正在持续上升、稳定、下降或重新升温；
* 同一长期趋势中出现新的内容卖点。

第三目标是减少凭经验和感觉进行选题时产生的判断不一致与注意力消耗。

## 1.2 MVP成功标准

MVP通过验收需要同时满足以下条件：

| 类别     | 验收标准                     |
| ------ | ------------------------ |
| 搜索效率   | 每日选题搜索和判断时间降至30—60分钟     |
| 候选数量   | 每天生成约30个候选创作方向           |
| 可执行性   | 管理者每天能选出至少10个可执行方向       |
| 推荐质量   | 排名前15的候选中，至少60%被认为具有参考价值 |
| 趋势识别   | 能识别多个频道集中制作且表现异常的题材      |
| 趋势方向   | 能显示24小时、72小时和7天窗口内的变化    |
| 可解释性   | 每个趋势均能说明评分来源和原始证据        |
| 工作流    | 管理者可审核、备注、标记状态并导出简报      |
| 主流程稳定性 | YouTube主流程能够连续稳定运行       |
| 故障隔离   | TikTok模块失败时不影响YouTube简报  |

---

# 2. MVP范围

## 2.1 MVP包含的功能

MVP应包含以下功能域：

1. 统一监控列表管理；
2. CSV批量导入；
3. YouTube频道内容采集；
4. YouTube关键词搜索；
5. 视频统计数据快照；
6. 重点频道字幕或转录获取；
7. 频道表现基准；
8. 单视频异常表现评分；
9. 跨频道趋势聚类；
10. 24小时、72小时和7天趋势计算；
11. LLM趋势归纳和创作方向生成；
12. 每日约30个候选方向；
13. 管理者审核、备注和状态管理；
14. 历史趋势查询；
15. Markdown和HTML简报导出；
16. 可插拔TikTok实验适配器；
17. Docker本地运行与服务器部署。

## 2.2 MVP不包含的功能

以下功能明确排除在MVP之外：

* 剪辑师登录和多角色权限；
* 自动将选题分配给具体剪辑师；
* 自动生成完整英文脚本；
* 自动生成英文标题和英文钩子；
* 视频画面理解；
* 自动下载、去水印或管理番剧素材；
* 自动发布到YouTube或TikTok；
* 自动读取团队发布账号的数据；
* 复杂推荐模型或爆款预测模型；
* TikTok全站稳定数据服务；
* 实时突发热点推送；
* 评论区大规模语义分析；
* 移动端应用。

---

# 3. 产品工作流

## 3.1 自动工作流

系统每日执行以下管道：

```text
读取监控列表
→ 发现新视频
→ 更新已有视频统计快照
→ 获取重点视频字幕或转录
→ 计算频道基准
→ 计算单视频异常表现
→ 聚合趋势主题
→ 计算趋势热度和方向
→ 使用LLM生成中文分析
→ 生成约30个候选创作方向
```

## 3.2 管理者工作流

管理者每日执行以下操作：

```text
打开今日候选页面
→ 按趋势主题查看候选方向
→ 查看评分解释和代表视频
→ 勾选10—15个方向
→ 添加人工备注
→ 标记已采用、可继续或不再推荐
→ 调整导出顺序
→ 导出Markdown或HTML
→ 转发给剪辑团队
```

## 3.3 趋势与创作方向的关系

系统采用两层模型：

```text
趋势主题 TrendTheme
└── 创作方向 CreativeAngle
```

例如：

```text
趋势主题：
《某部动漫》中的某个反派角色重新受到关注

创作方向：
1. 你可能忽略的三个角色细节
2. 他为什么最终背叛主角
3. 他最残酷的一场战斗
4. 这个角色真正的结局
```

趋势主题可以持续存在数天或数周。系统每天更新其状态、热度和代表视频，并在有新证据时产生新的创作方向。

---

# 4. 技术原则

## 4.1 确定性优先

以下工作必须由程序、SQL和明确规则完成：

* 定时调度；
* API调用；
* 数据清洗；
* 唯一标识和去重；
* 时间窗口计算；
* 频道基准计算；
* 热度评分；
* 生命周期状态；
* 候选排序；
* 状态机；
* 导出格式。

LLM不参与数值计算，也不能修改原始统计数据。

## 4.2 LLM仅处理语义任务

LLM负责：

* 识别动漫、角色、篇章和剧情事件；
* 判断多个视频是否属于同一趋势；
* 中文总结热门原因；
* 从标题、简介和字幕中提炼内容卖点；
* 生成中文创作方向；
* 判断适合Shorts、长视频或两者；
* 翻译英文原标题；
* 对无法通过规则确定的聚类结果进行辅助判断。

## 4.3 证据可追溯

每条LLM结论必须关联一个或多个原始视频ID。

系统不允许生成以下无证据结论：

* “多个频道都在做”；
* “播放量快速增长”；
* “该主题正在爆发”；
* “相关视频明显优于平均表现”。

这些结论必须由数据库指标计算后，以结构化数据提供给LLM。

## 4.4 适配器隔离

每个外部平台均通过独立适配器接入：

```python
class SourceAdapter:
    def discover_items(self, watch_item, cursor=None): ...
    def fetch_item_details(self, external_ids): ...
    def fetch_metrics(self, external_ids): ...
    def normalize_item(self, raw_item): ...
    def health_check(self): ...
```

YouTube和TikTok不得共享平台特定逻辑。

TikTok失败时，不得中断YouTube采集、趋势计算和每日简报。

---

# 5. 推荐技术架构

## 5.1 MVP技术栈

| 领域      | MVP技术                      |
| ------- | -------------------------- |
| 后端      | Python 3.12、FastAPI        |
| 页面      | Jinja2、HTMX、少量原生JavaScript |
| 数据库     | PostgreSQL                 |
| ORM     | SQLAlchemy 2               |
| 数据迁移    | Alembic                    |
| 定时任务    | APScheduler或独立Cron Worker  |
| 数据处理    | SQL、Pandas或Polars          |
| HTTP客户端 | httpx                      |
| 数据校验    | Pydantic                   |
| 测试      | pytest                     |
| 容器化     | Docker、Docker Compose      |
| 模板导出    | Jinja2                     |
| LLM     | 提供商无关的LLM Adapter          |
| 日志      | Python结构化日志                |
| 图表      | 服务端聚合数据加轻量前端图表库            |

FastAPI官方文档支持使用官方Python基础镜像自行构建容器，并将Docker作为常见部署方式；HTMX则适合直接从HTML触发HTTP请求，能够减少单管理者后台所需的前端工程复杂度。

## 5.2 Docker Compose服务

MVP建议包含三个核心服务：

```yaml
services:
  web:
    # FastAPI Web应用

  worker:
    # 调度、采集、分析、每日生成任务

  postgres:
    # PostgreSQL数据库
```

暂不引入Redis、Kafka、Celery或独立向量数据库。

需要异步队列时，优先使用数据库任务表和单Worker模型。进入多用户或高并发阶段后，再考虑Celery、RQ、Dramatiq或Temporal。

## 5.3 推荐代码目录

```text
project/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── domain/
│   │   ├── watchlist/
│   │   ├── content/
│   │   ├── trends/
│   │   ├── briefs/
│   │   └── publications/
│   ├── adapters/
│   │   ├── youtube/
│   │   ├── tiktok/
│   │   ├── transcript/
│   │   └── llm/
│   ├── services/
│   │   ├── ingestion.py
│   │   ├── baseline.py
│   │   ├── clustering.py
│   │   ├── scoring.py
│   │   ├── lifecycle.py
│   │   ├── candidate_generation.py
│   │   └── brief_export.py
│   ├── repositories/
│   ├── jobs/
│   ├── web/
│   │   ├── routes/
│   │   ├── templates/
│   │   └── static/
│   └── schemas/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── fixtures/
│   └── golden/
├── scripts/
├── docs/
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

架构应保持以下依赖方向：

```text
Web / CLI / Scheduler
        ↓
Application Services
        ↓
Domain
        ↑
Adapters / Repositories
```

领域层不得直接依赖YouTube SDK、TikTok页面结构或具体LLM供应商。

---

# 6. 数据模型

## 6.1 `watch_items`

统一保存频道、账号、关键词、作品和榜单。

| 字段                   | 类型        | 说明                                    |
| -------------------- | --------- | ------------------------------------- |
| id                   | UUID      | 内部ID                                  |
| type                 | Enum      | channel、account、keyword、anime、ranking |
| platform             | Enum      | youtube、tiktok、other                  |
| name                 | Text      | 显示名称                                  |
| external_id          | Text      | 频道ID、账号ID等                            |
| url                  | Text      | 原始地址                                  |
| tier                 | Enum      | priority、general、experimental         |
| tags                 | JSONB     | 标签                                    |
| note                 | Text      | 管理者备注                                 |
| enabled              | Boolean   | 是否启用                                  |
| config               | JSONB     | 平台专用配置                                |
| last_success_at      | Timestamp | 最后成功时间                                |
| last_attempt_at      | Timestamp | 最后尝试时间                                |
| last_status          | Enum      | success、failed、partial                |
| consecutive_failures | Integer   | 连续失败次数                                |
| created_at           | Timestamp | 创建时间                                  |
| updated_at           | Timestamp | 更新时间                                  |

建议建立以下唯一约束：

```text
UNIQUE(platform, type, external_id)
```

关键词没有外部ID时，可以使用规范化关键词作为`external_id`。

## 6.2 `content_items`

保存视频等原始内容。

| 字段                   | 类型        | 说明     |
| -------------------- | --------- | ------ |
| id                   | UUID      | 内部ID   |
| platform             | Enum      | 来源平台   |
| external_id          | Text      | 平台视频ID |
| source_watch_item_id | UUID      | 首次发现来源 |
| channel_external_id  | Text      | 频道ID   |
| channel_name         | Text      | 频道名称   |
| title_original       | Text      | 英文原标题  |
| title_zh             | Text      | 中文翻译   |
| description          | Text      | 简介     |
| tags                 | JSONB     | 原始标签   |
| published_at         | Timestamp | 发布时间   |
| duration_seconds     | Integer   | 时长     |
| url                  | Text      | 原始地址   |
| thumbnail_url        | Text      | 缩略图    |
| language             | Text      | 语言     |
| region               | Text      | 地区     |
| raw_payload          | JSONB     | 原始接口数据 |
| first_seen_at        | Timestamp | 首次发现   |
| last_seen_at         | Timestamp | 最近更新   |

唯一约束：

```text
UNIQUE(platform, external_id)
```

## 6.3 `metric_snapshots`

保存视频指标时间序列。

| 字段              | 类型        |
| --------------- | --------- |
| id              | BigInt    |
| content_item_id | UUID      |
| captured_at     | Timestamp |
| views           | BigInt    |
| likes           | BigInt，可空 |
| comments        | BigInt，可空 |
| shares          | BigInt，可空 |
| favorites       | BigInt，可空 |
| source_quality  | Enum      |

唯一约束：

```text
UNIQUE(content_item_id, captured_at_bucket)
```

`captured_at_bucket`可以按小时取整，避免同一任务重复插入。

## 6.4 `transcripts`

| 字段              | 说明                                 |
| --------------- | ---------------------------------- |
| content_item_id | 视频                                 |
| source          | public_caption、local_asr、api_asr   |
| language        | 字幕语言                               |
| text            | 全文                                 |
| status          | pending、success、failed、unavailable |
| confidence      | 置信度                                |
| obtained_at     | 获取时间                               |
| error           | 失败原因                               |

YouTube官方`captions.list`只返回字幕轨道信息，不包含字幕正文，而且当前官方文档列出的调用成本较高，因此不能将其作为任意竞品视频字幕的主要获取方式。重点视频应采用公开字幕提取、可选ASR和元数据降级的分层方案。

## 6.5 `channel_baselines`

| 字段                  | 说明                     |
| ------------------- | ---------------------- |
| channel_external_id | 频道ID                   |
| platform            | 平台                     |
| age_bucket          | 0–6h、6–24h、24–72h、3–7d |
| sample_count        | 样本数量                   |
| median_velocity     | 播放速度中位数                |
| p25_velocity        | 第25百分位                 |
| p75_velocity        | 第75百分位                 |
| calculated_at       | 计算时间                   |
| confidence          | low、medium、high        |

## 6.6 `trend_themes`

| 字段                | 说明                                           |
| ----------------- | -------------------------------------------- |
| id                | 趋势ID                                         |
| canonical_name    | 规范化名称                                        |
| anime_title       | 动漫作品                                         |
| topic_type        | anime、character、arc、event、selling_point      |
| entities          | 作品、角色、事件                                     |
| first_detected_at | 首次识别                                         |
| last_active_at    | 最近活跃                                         |
| lifecycle_status  | new、rising、stable、declining、reviving、dormant |
| score             | 当前综合分                                        |
| score_components  | 分项评分JSON                                     |
| confidence        | 聚类和趋势置信度                                     |
| summary_zh        | 中文趋势说明                                       |

## 6.7 `trend_members`

连接趋势和视频。

| 字段                | 说明                        |
| ----------------- | ------------------------- |
| trend_id          | 趋势                        |
| content_item_id   | 视频                        |
| membership_score  | 归属置信度                     |
| membership_method | rule、embedding、llm、manual |
| evidence          | 判定依据                      |
| added_at          | 加入时间                      |

## 6.8 `creative_angles`

| 字段                   | 说明                                                    |
| -------------------- | ----------------------------------------------------- |
| id                   | 方向ID                                                  |
| trend_id             | 所属趋势                                                  |
| angle_zh             | 中文创作方向                                                |
| format               | short、long、both                                       |
| evidence_content_ids | 证据视频                                                  |
| generated_date       | 生成日期                                                  |
| generation_source    | llm、manual                                            |
| semantic_fingerprint | 去重指纹                                                  |
| status               | candidate、selected、adopted、published、reusable、blocked |
| manager_note         | 管理者备注                                                 |

## 6.9 `daily_candidates`

保存每日排序快照，确保历史结果可以重现。

| 字段                | 说明     |
| ----------------- | ------ |
| date              | 日期     |
| creative_angle_id | 创作方向   |
| trend_id          | 趋势     |
| rank              | 当日排名   |
| candidate_score   | 候选得分   |
| score_snapshot    | 评分明细   |
| selected          | 是否入选简报 |

## 6.10 `publication_records`

| 字段                | 说明                                 |
| ----------------- | ---------------------------------- |
| creative_angle_id | 对应方向                               |
| status            | adopted、published、reusable、blocked |
| published_url     | 发布链接                               |
| published_at      | 发布日期                               |
| note              | 备注                                 |
| created_at        | 记录时间                               |

## 6.11 `crawl_jobs`

| 字段              | 说明                                    |
| --------------- | ------------------------------------- |
| id              | 任务ID                                  |
| adapter         | youtube、tiktok等                       |
| job_type        | discover、metrics、transcript等          |
| watch_item_id   | 监控项                                   |
| status          | queued、running、success、partial、failed |
| started_at      | 开始时间                                  |
| finished_at     | 结束时间                                  |
| items_processed | 处理数量                                  |
| retry_count     | 重试次数                                  |
| error_code      | 错误类型                                  |
| error_message   | 错误摘要                                  |

---

# 7. YouTube数据采集设计

## 7.1 官方接口使用策略

频道发现新视频时，应优先使用频道的Uploads播放列表和`playlistItems.list`，而不是持续用昂贵的关键词搜索接口扫描固定频道。

关键词搜索使用`search.list`。

视频详细信息和统计数据使用`videos.list`，并批量提交视频ID。

当前YouTube官方文档列出的默认配额包括每天100次`search.list`调用，以及其他大多数接口共享的每日10,000单位配额；`videos.list`和`playlistItems.list`的单次调用成本较低。因此MVP需要限制关键词查询组数，并通过批量读取和频道播放列表降低配额消耗。

## 7.2 重点频道任务

重点频道20—30个。

每4—6小时执行：

1. 获取Uploads播放列表中的最新视频；
2. 与本地`content_items`比较；
3. 写入新视频；
4. 更新最近7天视频的统计快照；
5. 为进入高优先级候选的视频提交字幕任务；
6. 更新频道抓取状态。

## 7.3 一般频道任务

一般频道和其他监控项总量控制在100个以内。

每12—24小时执行：

1. 获取最新视频；
2. 写入标题、简介、标签和统计数据；
3. 对最近72小时视频继续采集快照；
4. 不默认提取字幕。

## 7.4 关键词任务

关键词按查询组管理：

```text
anime recap
anime explained
anime scene explained
具体动漫名称
具体角色名称
具体篇章名称
```

建议初始限制：

* 活跃关键词组不超过30个；
* 每组每日查询1次；
* 少数高优先级词可每日查询2次；
* 查询时间范围优先限制为最近24—72小时；
* 每组最多读取1—2页；
* 查询结果统一进入内容去重流程。

## 7.5 快照采集频率

| 视频年龄   | 建议采集频率    |
| ------ | --------- |
| 0—24小时 | 每4—6小时    |
| 1—3天   | 每8—12小时   |
| 3—7天   | 每24小时     |
| 超过7天   | 仅趋势仍活跃时更新 |

---

# 8. 频道基准和异常表现算法

## 8.1 冷启动问题

YouTube公开接口只能提供当前累计统计数据，不能直接返回某条旧视频在发布后第6小时或第24小时的历史播放量。

因此系统必须区分：

```text
冷启动估算基准
长期观测基准
```

前两至四周只能形成低到中等置信度的估算。随着系统持续保存快照，频道基准才会逐渐可靠。

## 8.2 年龄桶

视频按发布时间分为：

```text
B1：0—6小时
B2：6—24小时
B3：24—72小时
B4：3—7天
```

任何表现比较都应尽量在相同年龄桶内完成。

## 8.3 播放速度

存在两个连续快照时：

```text
velocity =
(new_views - old_views)
/
hours_between_snapshots
```

只有一个快照时使用冷启动估算：

```text
estimated_velocity =
current_views
/
max(video_age_hours, 2)
```

冷启动估算必须标记较低置信度。

## 8.4 频道基准

对每个频道、每个年龄桶计算：

```text
baseline_velocity =
median(recent_video_velocities)
```

使用中位数而不是均值，以降低历史爆款造成的基准偏移。

建议：

* 初始取最近20条符合条件的视频；
* 少于5条样本时使用同类频道总体基准；
* 5—9条为低置信度；
* 10—19条为中等置信度；
* 20条以上为高置信度。

## 8.5 Breakout Ratio

```text
breakout_ratio =
video_velocity
/
max(channel_baseline_velocity, epsilon)
```

初始解释：

| Breakout Ratio | 解释       |
| -------------: | -------- |
|         < 0.75 | 低于频道一般表现 |
|       0.75—1.5 | 正常范围     |
|        1.5—2.0 | 表现较好     |
|        2.0—4.0 | 明显突破     |
|          > 4.0 | 强突破信号    |

为了防止极端值主导趋势评分，算法内部应使用截断值：

```text
capped_breakout = min(breakout_ratio, 8)
```

## 8.6 频道权重

初始建议：

```text
重点频道：1.5
一般频道：1.0
实验来源：0.5
```

权重必须配置化。

---

# 9. 趋势聚类设计

## 9.1 第一层：规则归一化

建立动漫实体词典：

```text
anime_title
english_titles
romanized_titles
common_abbreviations
character_names
arc_names
aliases
```

标题预处理包括：

* 小写化；
* Unicode规范化；
* 去除常见噪声词；
* 统一作品别名；
* 提取角色、篇章和剧情事件；
* 保留内容卖点短语。

## 9.2 第二层：文本向量候选召回

对以下文本生成向量：

```text
标题
简介摘要
标签
字幕摘要
已识别实体
```

先通过时间窗口和动漫作品缩小范围，再进行相似度召回。

不建议在所有视频之间进行无约束的全局聚类。

## 9.3 第三层：LLM辅助裁决

只将以下歧义交给LLM：

* 两个标题是否讨论同一剧情；
* 同一角色的两个话题是否属于同一趋势；
* 内容卖点应合并还是拆分；
* 无法通过词典确定的作品别名。

LLM必须返回结构化结果：

```json
{
  "same_trend": true,
  "canonical_topic": "",
  "anime_title": "",
  "entities": [],
  "reason": "",
  "confidence": 0.0
}
```

低置信结果不得自动合并。

## 9.4 聚类稳定性

趋势主题必须跨日复用，不得每天重新生成随机ID。

匹配顺序：

```text
实体完全匹配
→ 已有趋势语义相似度
→ LLM裁决
→ 创建新趋势
```

---

# 10. 趋势判定与热度评分

## 10.1 正式趋势门槛

满足以下条件之一时，进入正式趋势候选。

### 常规共振条件

```text
72小时内至少3个不同监控频道发布相关内容
并且
至少50%的相关视频 breakout_ratio ≥ 2
```

### 早期强信号条件

```text
24小时内至少2个不同频道发布相关内容
并且
至少1条视频 breakout_ratio ≥ 4
并且
存在关键词、榜单或其他频道的额外证据
```

单一频道的单条爆款默认不能成为高置信趋势。

## 10.2 综合评分

```text
TrendScore =
0.35 × ChannelResonance
+ 0.25 × RelativeBreakout
+ 0.20 × Momentum
+ 0.10 × Persistence
+ 0.05 × AbsoluteScale
+ 0.05 × Novelty
```

所有分项归一化为0—100。

## 10.3 跨频道共振

建议公式：

```text
weighted_channel_count =
sum(unique_channel_weights)

ChannelResonance =
100 × min(
  log(1 + weighted_channel_count)
  /
  log(1 + target_channel_count),
  1
)
```

`target_channel_count`初始可设为8。

同时加入集中度修正：

* 发布越集中，得分越高；
* 同一频道多条视频不重复计算频道数量；
* 实验来源降低权重；
* 疑似搬运频道可降低权重。

## 10.4 相对表现异常

```text
RelativeBreakout =
百分位标准化(
  0.6 × 相关视频breakout中位数
  + 0.4 × breakout_ratio≥2的视频比例
)
```

使用中位数避免单一爆款控制整个趋势。

## 10.5 增长动量

定义每个趋势在时间窗口中的标准化活动值：

```text
Activity(window) =
Σ(
  channel_weight
  × capped_breakout
  × normalized_incremental_views
)
+
new_video_bonus
```

其中：

```text
MomentumRatio =
Activity(last_24h)
/
max(Activity(previous_24h), epsilon)
```

再将MomentumRatio映射到0—100。

## 10.6 持续性

考虑：

* 过去7天中有新视频的天数；
* 是否持续有新频道加入；
* 是否持续产生新内容卖点；
* 是否只是单日集中爆发。

## 10.7 绝对传播规模

绝对播放量只占5%，并使用对数转换：

```text
AbsoluteScale =
percentile(log1p(total_recent_views))
```

## 10.8 新鲜度

新发现趋势获得轻微加分：

```text
首次发现≤24h：100
24—72h：70
3—7d：40
超过7d：20
```

新鲜度只占5%，不能压过持续上升的成熟趋势。

## 10.9 生命周期状态

```text
growth_ratio =
Activity(last_24h)
/
max(Activity(previous_24h), epsilon)
```

| 状态   | 初始规则                         |
| ---- | ---------------------------- |
| 新发现  | 首次识别不超过24小时                  |
| 持续上升 | growth_ratio ≥ 1.25          |
| 热度稳定 | 0.80 ≤ growth_ratio < 1.25   |
| 开始下降 | growth_ratio < 0.80          |
| 重新升温 | 曾下降或休眠，当前growth_ratio ≥ 1.50 |
| 休眠   | 72小时无新视频且活动低于阈值              |

所有阈值必须保存在配置表中，不得硬编码在页面或SQL中。

---

# 11. 创作方向生成

## 11.1 输入数据

LLM接收：

* 趋势主题；
* 相关动漫、角色和剧情实体；
* 代表视频标题；
* 视频简介摘要；
* 可用字幕摘要；
* 热度计算结果；
* 已推荐方向；
* 已采用或已发布方向；
* 不再推荐的方向。

不得向LLM发送无必要的完整原始响应或大量重复字幕。

## 11.2 输出Schema

```json
{
  "trend_name_zh": "",
  "why_trending_zh": "",
  "creative_angles": [
    {
      "angle_zh": "",
      "format": "short",
      "evidence_content_ids": [],
      "novelty_reason": ""
    }
  ],
  "confidence": 0.0
}
```

`format`只允许：

```text
short
long
both
```

## 11.3 去重规则

新方向生成后依次比较：

1. 最近7天已生成方向；
2. 当前趋势历史方向；
3. 已采用方向；
4. 已发布方向；
5. 被标记为`blocked`的方向。

使用：

```text
规范化关键词
+ 实体匹配
+ 向量相似度
+ 必要时LLM判断
```

同一方向仅修改措辞，不视为新方向。

## 11.4 候选数量

每日候选生成过程：

```text
趋势评分排序
→ 每个趋势生成1—4个方向
→ 应用历史去重
→ 应用格式和内容多样性约束
→ 选出约30个方向
```

避免前30个候选全部来自同一动漫。

建议初始约束：

* 单一趋势最多4个方向；
* 单一动漫最多占候选总数30%；
* 至少20%的候选来自新发现趋势；
* 下降趋势默认降低排名，但仍可保留高价值长视频方向。

---

# 12. Web页面设计

## 12.1 今日候选页

页面按趋势主题分组，每个趋势卡片显示：

* 趋势名称；
* 生命周期状态；
* 综合热度；
* 24小时、72小时和7天指标；
* 不同频道数量；
* 突破视频数量；
* 热门原因；
* 代表视频；
* 创作方向；
* Shorts、Long或Both；
* 管理者备注；
* 入选勾选框。

支持筛选：

```text
新发现
持续上升
稳定
下降
动漫作品
Shorts
长视频
重点频道
评分区间
```

## 12.2 趋势详情页

显示：

* 趋势时间线；
* 每日综合评分；
* 分项评分；
* 相关视频列表；
* 每条视频的Breakout Ratio；
* 频道分布；
* 趋势成员加入时间；
* 历史创作方向；
* 已采用和已发布记录；
* 聚类证据。

## 12.3 监控列表页

支持：

* CSV导入；
* 手工新增和编辑；
* 设置监控等级；
* 标签和备注；
* 启用和停用；
* 查看最后抓取时间；
* 查看成功、失败或部分成功；
* 查看连续失败次数；
* 手工触发单项抓取。

## 12.4 历史记录页

按日期查看：

* 当日全部候选；
* 当日最终入选；
* 管理者备注；
* 已采用；
* 已发布；
* 可换角度继续做；
* 不再推荐；
* 发布链接。

## 12.5 简报预览页

支持：

* 调整趋势顺序；
* 调整方向顺序；
* 取消选中；
* 编辑管理者备注；
* 预览Markdown；
* 预览HTML；
* 下载Markdown；
* 下载HTML。

---

# 13. 导出简报结构

```markdown
# 今日番剧解说趋势简报

生成日期：
覆盖范围：最近24小时新内容、72小时短期趋势、7天持续趋势

## 1. 趋势名称

状态：新发现 / 持续上升 / 热度稳定 / 开始下降 / 重新升温  
适合形式：Shorts / 长视频 / Both  
综合热度：82/100

### 热度依据

过去72小时内有6个监控频道发布相关视频。
其中4条视频表现超过各自频道近期基准2倍。
过去24小时活动值较前一周期增长42%。

### 为什么热门

中文解释。

### 代表视频

1. English Original Title  
   中文翻译  
   频道｜发布时间｜播放量｜相对表现  
   原始链接

### 建议创作方向

1. 中文方向一 — Shorts
2. 中文方向二 — Shorts
3. 中文方向三 — 长视频

### 管理者备注

……
```

---

# 14. 分阶段开发计划

# 阶段0：工程基线和技术验证框架

## 阶段目标

建立可重复运行、可测试和可部署的项目骨架。

## 开发任务

| 编号    | 任务                                   | 优先级 |
| ----- | ------------------------------------ | --- |
| P0-01 | 初始化Python项目和依赖管理                     | P0  |
| P0-02 | 建立FastAPI应用骨架                        | P0  |
| P0-03 | 建立PostgreSQL和SQLAlchemy              | P0  |
| P0-04 | 建立Alembic迁移                          | P0  |
| P0-05 | 建立Web、Worker、Postgres的Docker Compose | P0  |
| P0-06 | 建立配置管理和`.env`模板                      | P0  |
| P0-07 | 建立结构化日志                              | P0  |
| P0-08 | 建立pytest测试目录                         | P0  |
| P0-09 | 建立Adapter和Domain接口                   | P0  |
| P0-10 | 建立数据库任务表                             | P1  |
| P0-11 | 建立代码格式化、Lint和类型检查                    | P1  |
| P0-12 | 建立基础CI                               | P1  |

## 交付物

* 可启动的FastAPI页面；
* 可连接的PostgreSQL；
* 可运行的Worker；
* 第一版数据库迁移；
* 健康检查接口；
* Docker本地开发环境；
* CI测试流程。

## 验收门

```text
docker compose up
```

能够启动全部核心服务。

以下接口返回正常：

```text
GET /health/live
GET /health/ready
```

数据库迁移可在空数据库和已有数据库上重复执行。

## 参考工作量

单人全栈约3—5人日。

---

# 阶段1：影子验证与黄金数据集

## 阶段目标

在开发完整后台前，证明“跨频道共振加相对频道表现”能够复现管理者的经验判断。

## 开发任务

| 编号    | 任务                   |
| ----- | -------------------- |
| P1-01 | 整理20—30个重点YouTube频道  |
| P1-02 | 整理一般频道、关键词和动漫作品      |
| P1-03 | 编写最小YouTube采集脚本      |
| P1-04 | 获取最近视频和当前统计数据        |
| P1-05 | 建立简化年龄桶              |
| P1-06 | 实现冷启动播放速度估算          |
| P1-07 | 实现初始频道基准             |
| P1-08 | 实现Breakout Ratio     |
| P1-09 | 人工将一批视频标记为同一趋势       |
| P1-10 | 与管理者共同标记高价值、普通和无价值趋势 |
| P1-11 | 建立Golden Dataset     |
| P1-12 | 输出CSV或Notebook报告     |

## 黄金数据集要求

至少包含：

* 100—300条真实视频；
* 20个以上频道；
* 10个以上人工确认趋势；
* 每个趋势的相关视频；
* 管理者对趋势价值的标注；
* 管理者认为的热门原因；
* 至少若干反例。

## 验收门

系统应能够在黄金数据集中：

* 将明显破圈趋势排入前列；
* 降低单一大频道普通视频的排名；
* 提高多个频道同时跟进题材的排名；
* 给出可解释的Breakout Ratio；
* 让管理者认可基础判定逻辑。

如果该阶段失败，不进入完整后台开发，而是调整采集和评分逻辑。

## 参考工作量

约5—8人日，不含数据等待周期。

---

# 阶段2：Watchlist与YouTube稳定采集

## 阶段目标

建立可持续运行的数据底座。

## 开发任务

### Watchlist

| 编号    | 任务               |
| ----- | ---------------- |
| P2-01 | 创建`watch_items`表 |
| P2-02 | 实现频道、关键词、作品和榜单类型 |
| P2-03 | 实现重点、一般和实验等级     |
| P2-04 | 实现标签和备注          |
| P2-05 | 实现启用和停用          |
| P2-06 | 实现CSV校验和批量导入     |
| P2-07 | 实现重复项检测          |
| P2-08 | 实现抓取状态显示         |

### YouTube Adapter

| 编号    | 任务             |
| ----- | -------------- |
| P2-09 | 频道ID解析         |
| P2-10 | Uploads播放列表发现  |
| P2-11 | 关键词搜索          |
| P2-12 | 视频详情批量读取       |
| P2-13 | API配额计数        |
| P2-14 | 429、403和网络错误处理 |
| P2-15 | 指数退避           |
| P2-16 | 原始响应保存         |
| P2-17 | 平台数据标准化        |
| P2-18 | 幂等写入           |
| P2-19 | 游标和增量抓取        |

### 调度

| 编号    | 任务            |
| ----- | ------------- |
| P2-20 | 重点频道4—6小时任务   |
| P2-21 | 一般频道12—24小时任务 |
| P2-22 | 关键词每日任务       |
| P2-23 | 手工触发任务        |
| P2-24 | 失败重试          |
| P2-25 | 任务互斥和防止重复运行   |

## 验收门

* 可导入不超过100个监控项；
* 20—30个重点频道可稳定增量抓取；
* 同一视频不会重复写入；
* 所有API调用可追踪；
* 单个频道失败不会中断其他频道；
* 可以查看最后成功时间和错误摘要；
* YouTube配额不足时主动停止低优先级搜索任务。

## 参考工作量

约7—10人日。

---

# 阶段3：统计快照、频道基准和趋势评分

## 阶段目标

完成不依赖LLM的趋势发现核心。

## 开发任务

### 快照

| 编号    | 任务                   |
| ----- | -------------------- |
| P3-01 | 创建`metric_snapshots` |
| P3-02 | 按视频年龄动态调度            |
| P3-03 | 计算增量播放量              |
| P3-04 | 检测负增量和异常数据           |
| P3-05 | 快照幂等和小时桶去重           |

### 基准

| 编号    | 任务               |
| ----- | ---------------- |
| P3-06 | 实现四个年龄桶          |
| P3-07 | 实现频道中位数基准        |
| P3-08 | 实现样本数量置信度        |
| P3-09 | 实现同类频道回退基准       |
| P3-10 | 实现Breakout Ratio |
| P3-11 | 实现极端值截断          |

### 趋势和评分

| 编号    | 任务                               |
| ----- | -------------------------------- |
| P3-12 | 建立初始关键词和实体规则                     |
| P3-13 | 规则聚类                             |
| P3-14 | 建立`trend_themes`和`trend_members` |
| P3-15 | 计算跨频道共振                          |
| P3-16 | 计算相对表现异常                         |
| P3-17 | 计算24小时动量                         |
| P3-18 | 计算7天持续性                          |
| P3-19 | 计算绝对规模和新鲜度                       |
| P3-20 | 计算综合评分                           |
| P3-21 | 计算生命周期状态                         |
| P3-22 | 每日评分快照                           |
| P3-23 | 趋势跨日复用                           |

## 验收门

* 能显示每条视频的频道基准和Breakout Ratio；
* 能识别至少3个频道共同制作的题材；
* 能区分单一大频道普通内容和跨频道异常题材；
* 能计算24小时、72小时和7天指标；
* 能将趋势标记为新发现、上升、稳定或下降；
* 相同趋势次日复用原趋势ID；
* 任意趋势分数可以由原始快照重算。

## 参考工作量

约8—12人日。

---

# 阶段4：字幕分层获取和LLM语义分析

## 阶段目标

将数据趋势转化为管理者能够理解和使用的创作方向。

## 开发任务

### 字幕和转录

| 编号    | 任务            |
| ----- | ------------- |
| P4-01 | 创建字幕任务状态机     |
| P4-02 | 重点频道字幕提取      |
| P4-03 | 无字幕降级         |
| P4-04 | 可选ASR Adapter |
| P4-05 | 字幕长度限制和分段     |
| P4-06 | 字幕摘要缓存        |
| P4-07 | 失败原因记录        |

### LLM Adapter

| 编号    | 任务            |
| ----- | ------------- |
| P4-08 | 提供商无关接口       |
| P4-09 | JSON Schema约束 |
| P4-10 | 重试和超时         |
| P4-11 | Token和成本记录    |
| P4-12 | Prompt版本管理    |
| P4-13 | 输入证据ID        |
| P4-14 | 输出来源校验        |
| P4-15 | 禁止引用不存在视频     |

### 语义分析

| 编号    | 任务                 |
| ----- | ------------------ |
| P4-16 | 英文标题中文翻译           |
| P4-17 | 趋势中文命名             |
| P4-18 | 热门原因总结             |
| P4-19 | 创作方向生成             |
| P4-20 | Shorts、Long、Both分类 |
| P4-21 | 历史方向语义去重           |
| P4-22 | 低置信度回退             |

## 验收门

* LLM输出始终符合Schema；
* 所有方向至少关联一条证据视频；
* LLM失败不会阻断趋势评分；
* 没有字幕时可使用元数据生成低置信分析；
* 同一趋势不会仅通过改写措辞生成大量重复方向；
* 生成方向对管理者具有可理解性和可执行性。

## 参考工作量

约5—8人日。

---

# 阶段5：管理后台和简报导出

## 阶段目标

完成管理者每日端到端使用闭环。

## 开发任务

| 编号    | 任务           |
| ----- | ------------ |
| P5-01 | 今日候选页面       |
| P5-02 | 趋势卡片         |
| P5-03 | 评分解释         |
| P5-04 | 代表视频列表       |
| P5-05 | 创作方向选择       |
| P5-06 | Shorts和长视频标签 |
| P5-07 | 管理者备注        |
| P5-08 | 趋势详情页面       |
| P5-09 | 趋势时间线        |
| P5-10 | Watchlist页面  |
| P5-11 | CSV导入界面      |
| P5-12 | 抓取状态页面       |
| P5-13 | 历史记录页面       |
| P5-14 | 简报预览         |
| P5-15 | Markdown导出   |
| P5-16 | HTML导出       |
| P5-17 | 候选顺序调整       |
| P5-18 | 单管理者认证       |
| P5-19 | CSRF和表单校验    |

## 验收门

管理者不操作数据库和脚本即可：

1. 导入监控列表；
2. 查看约30个候选；
3. 查看趋势证据；
4. 选择10—15个方向；
5. 添加备注；
6. 调整简报顺序；
7. 导出Markdown和HTML。

一次完整审核应能在一小时内完成。

## 参考工作量

约7—10人日。

---

# 阶段6：选题状态、历史反馈和防重复

## 阶段目标

让系统记住团队做过什么，支持持续热点的多角度开发。

## 开发任务

| 编号    | 任务        |
| ----- | --------- |
| P6-01 | 实现候选状态机   |
| P6-02 | 已采用状态     |
| P6-03 | 已发布状态     |
| P6-04 | 可换角度继续做   |
| P6-05 | 不再推荐      |
| P6-06 | 发布链接填写    |
| P6-07 | 发布日期      |
| P6-08 | 历史方向查询    |
| P6-09 | 推荐前历史过滤   |
| P6-10 | 长期趋势新角度生成 |
| P6-11 | 状态变更审计记录  |

## 状态机

```text
candidate
→ selected
→ adopted
→ published
```

其他分支：

```text
adopted → reusable
candidate → blocked
selected → blocked
published → reusable
```

## 验收门

* 已发布方向不会被原样再次推荐；
* `reusable`允许同一趋势产生不同角度；
* `blocked`方向不会重新进入候选；
* 每个状态变更有时间和操作记录；
* 发布链接可以在历史页面查询。

## 参考工作量

约3—5人日。

---

# 阶段7：TikTok实验适配器

## 阶段目标

验证指定账号、关键词或公开榜单的有限抓取路径，不承担稳定性承诺。

TikTok官方Display API主要用于展示经授权创作者的近期或自选视频，而Research Tools只向符合条件的研究人员开放，不能作为该商业MVP的通用全站数据接口。因此TikTok模块必须保持实验性和可替换性。

## 开发任务

| 编号    | 任务                |
| ----- | ----------------- |
| P7-01 | 定义TikTokAdapter接口 |
| P7-02 | 指定账号实验抓取          |
| P7-03 | 少量关键词实验抓取         |
| P7-04 | 公开标签或榜单实验         |
| P7-05 | Cookie配置          |
| P7-06 | Cookie失效检测        |
| P7-07 | 页面结构版本隔离          |
| P7-08 | 抓取结果标准化           |
| P7-09 | 来源质量标记            |
| P7-10 | 与YouTube任务隔离      |
| P7-11 | 独立开关              |
| P7-12 | 失败告警和日志           |

## 安全要求

* Cookie不得写入Git；
* Cookie不得直接显示在日志中；
* Cookie通过环境变量、挂载文件或Secret注入；
* TikTok模块默认可以整体关闭；
* 抓取结果必须记录抓取时间；
* 不保证数据完整性；
* 不使用TikTok结果单独认定高置信趋势。

## 验收门

满足以下任一项即可视为实验成功：

* 能定时监控指定TikTok账号；
* 能定时获取少量指定关键词结果；
* 能获取一个公开榜单或标签页；
* 能将人工输入的TikTok链接纳入统一分析。

无论TikTok是否成功，YouTube每日简报必须正常生成。

## 参考工作量

约4—8人日，取决于页面稳定性，不纳入核心MVP交付承诺。

---

# 阶段8：部署、稳定性和运营准备

## 阶段目标

将开发环境迁移为可长期运行的单实例系统。

## 开发任务

| 编号    | 任务                    |
| ----- | --------------------- |
| P8-01 | Production Dockerfile |
| P8-02 | Docker Compose生产配置    |
| P8-03 | 数据库自动备份               |
| P8-04 | 数据恢复演练                |
| P8-05 | HTTPS反向代理             |
| P8-06 | 单管理者账号                |
| P8-07 | Secret管理              |
| P8-08 | 日志轮转                  |
| P8-09 | 磁盘空间监控                |
| P8-10 | 任务失败摘要                |
| P8-11 | 数据库索引检查               |
| P8-12 | 快照保留策略                |
| P8-13 | API配额监控               |
| P8-14 | LLM成本统计               |
| P8-15 | 操作手册                  |
| P8-16 | 故障恢复手册                |

## 部署选择

MVP支持：

```text
本地Docker
长期在线电脑
Linux VPS
```

VPS部署建议：

```text
Reverse Proxy
├── HTTPS
└── FastAPI Web

Docker Compose
├── web
├── worker
└── postgres
```

FastAPI生产部署需要考虑HTTPS、开机启动、自动重启和进程管理等基本运行条件。

## 验收门

* 容器重启后任务可恢复；
* 数据库每日备份；
* 可以从备份恢复；
* API密钥不出现在镜像或代码仓库；
* 抓取和分析失败有可查询日志；
* 连续运行期间不产生重复每日简报；
* Worker异常不会导致Web后台不可用。

## 参考工作量

约3—5人日。

---

# 15. 测试计划

## 15.1 单元测试

重点覆盖：

* 时间窗口；
* 年龄桶；
* 播放增量；
* Breakout Ratio；
* 中位数基准；
* 趋势分项评分；
* 生命周期状态；
* 状态机；
* 内容去重；
* CSV校验；
* 导出模板。

## 15.2 集成测试

覆盖：

* YouTube Adapter到数据库；
* 数据库到趋势计算；
* 趋势到LLM输入；
* LLM输出到候选方向；
* 候选选择到简报导出；
* Worker任务失败和重试；
* 数据库迁移。

## 15.3 API契约测试

使用保存的真实响应样本测试：

* YouTube频道响应；
* 播放列表响应；
* 搜索响应；
* 视频详情响应；
* 缺失点赞或评论字段；
* 被删除或设为私密的视频；
* 配额不足；
* 429和5xx。

不得在所有测试中调用真实YouTube API。

## 15.4 黄金数据集回归测试

每次调整以下内容时，必须在Golden Dataset上重放：

* 评分权重；
* 趋势门槛；
* 聚类规则；
* Prompt；
* 去重阈值；
* 生命周期阈值。

需要记录：

```text
Precision@15
Recall of known trends
误合并数量
误拆分数量
新旧版本排名变化
管理者人工评分
```

## 15.5 导出测试

验证：

* 中文字符；
* 英文标题；
* 特殊Markdown字符；
* HTML转义；
* 缺失视频指标；
* 没有管理者备注；
* 长标题；
* 失效链接；
* 30个以上候选。

---

# 16. 可观测性

## 16.1 核心运行指标

系统至少记录：

```text
watch_items_total
crawl_success_total
crawl_failure_total
videos_discovered_total
metric_snapshots_total
youtube_quota_usage
transcript_success_rate
llm_requests_total
llm_failures_total
llm_token_usage
daily_candidates_count
daily_brief_generated
trend_clusters_count
unclustered_items_count
```

## 16.2 数据质量指标

```text
最近24小时未成功抓取的重点频道数
缺少统计快照的视频比例
低置信频道基准数量
没有证据视频的创作方向数量
LLM Schema失败数量
趋势孤立视频数量
趋势异常膨胀数量
```

## 16.3 管理者质量指标

```text
候选入选率
Top 15参考价值
趋势被标记blocked的比例
重复方向比例
每日审核时间
每日最终入选数量
```

---

# 17. 配置管理

所有算法参数必须集中配置：

```yaml
scoring:
  channel_resonance_weight: 0.35
  relative_breakout_weight: 0.25
  momentum_weight: 0.20
  persistence_weight: 0.10
  absolute_scale_weight: 0.05
  novelty_weight: 0.05

thresholds:
  breakout: 2.0
  strong_breakout: 4.0
  rising_ratio: 1.25
  declining_ratio: 0.80
  reviving_ratio: 1.50

channels:
  priority_weight: 1.5
  general_weight: 1.0
  experimental_weight: 0.5

candidates:
  target_count: 30
  max_per_trend: 4
  max_share_per_anime: 0.30
```

每次修改评分参数时，应记录：

* 修改前值；
* 修改后值；
* 修改原因；
* 生效时间；
* Golden Dataset回归结果。

---

# 18. 风险与应对

## 18.1 冷启动基准不可靠

**风险：** 初始没有视频历史快照。

**应对：**

* 显示低置信度；
* 使用年龄桶估算；
* 使用同类频道总体基准回退；
* 连续保存两至四周快照；
* 不让低置信基准单独触发高置信趋势。

## 18.2 YouTube配额不足

**风险：** 关键词搜索消耗有限配额。

**应对：**

* 固定频道使用Uploads播放列表；
* 批量调用`videos.list`；
* 对关键词分级；
* 高优先级任务先执行；
* 达到配额阈值后停止低优先级任务；
* 缓存查询结果。

## 18.3 聚类误合并

**风险：** 同一动漫中的不同剧情被错误合并。

**应对：**

* 作品、角色、事件分层；
* 时间范围约束；
* 保存归属置信度；
* 低置信度不自动合并；
* 后续增加管理者手工合并和拆分功能。

手工合并和拆分不是首版必需，但数据库必须支持。

## 18.4 LLM生成重复或空泛方向

**应对：**

* 提供历史方向；
* 结构化输出；
* 要求证据视频；
* 使用语义去重；
* 限制每个趋势方向数量；
* 低价值输出不进入候选。

## 18.5 TikTok抓取不稳定

**应对：**

* 独立适配器；
* 独立Worker任务；
* 可完全关闭；
* 单独Cookie；
* 数据质量降权；
* 不纳入核心验收。

## 18.6 数据量持续增长

**应对：**

* 原始API响应保留有限周期；
* 快照根据视频年龄降频；
* 对休眠趋势停止高频更新；
* 定期归档任务日志；
* 为`metric_snapshots`建立时间和视频联合索引。

---

# 19. 上位替代路线

| MVP组件            | 触发升级条件      | 上位替代                     |
| ---------------- | ----------- | ------------------------ |
| APScheduler/Cron | 任务并发和重试复杂   | Celery、Dramatiq、Temporal |
| PostgreSQL普通表    | 快照达到千万级     | TimescaleDB、ClickHouse   |
| Jinja2 + HTMX    | 多用户复杂交互     | React、Next.js            |
| 数据库任务表           | 多Worker竞争严重 | Redis队列、消息队列             |
| 本地Embedding      | 聚类规模明显扩大    | pgvector、Qdrant          |
| 本地或简单ASR         | 转录量和时效要求提高  | 托管ASR服务                  |
| TikTok实验抓取       | 成为核心商业能力    | 合规商业数据供应商                |
| Markdown/HTML    | 团队协作需求提高    | 飞书、Slack、Discord推送       |
| 单管理者             | 多团队和审批需求    | RBAC和多租户                 |
| 手工发布记录           | 需要效果归因      | 接入自有YouTube账号分析          |

---

# 20. 推荐实施顺序

严格推荐以下顺序：

```text
阶段0：工程基线
↓
阶段1：影子验证
↓
阶段2：稳定采集
↓
阶段3：趋势算法
↓
阶段4：LLM语义层
↓
阶段5：管理后台
↓
阶段6：历史反馈
↓
阶段8：部署加固
↓
阶段7：TikTok实验
```

TikTok实验可以与后期工作并行，但不得阻塞YouTube主路径。

完整MVP核心路径，即阶段0至阶段6和阶段8，单人全栈参考工作量约为41—63人日。该数字不包含等待真实趋势数据积累的自然时间，也不包含TikTok页面变化造成的不确定工作。

---

# 21. MVP完成定义

只有在以下条件全部满足时，项目才视为完成MVP，而不是仅完成技术演示：

1. 管理者可以维护不超过100个监控项；
2. 重点频道和一般频道按照不同频率采集；
3. 系统持续保存视频统计快照；
4. 系统能够建立频道基准；
5. 系统能够识别跨频道共振；
6. 系统能够计算可解释的趋势评分；
7. 系统能够跟踪趋势生命周期；
8. 系统每天生成约30个候选方向；
9. 每个方向具有原始证据；
10. 管理者能够选出10—15个方向；
11. 管理者能够添加备注；
12. 系统能够记录已采用和已发布内容；
13. 系统能够避免原样重复推荐；
14. 系统能够导出Markdown和HTML；
15. YouTube主流程能够稳定运行；
16. TikTok失败不影响主流程；
17. 系统能够通过Docker部署；
18. 管理者每日操作时间不超过一小时；
19. Top 15候选参考价值达到60%以上；
20. 评分和Prompt变更可以通过黄金数据集回归验证。
