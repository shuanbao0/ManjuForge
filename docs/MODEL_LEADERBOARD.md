# 各能力维度最强模型排行榜

> 截至 **2026-05** ManjuForge Studio 支持(或可接入)的全部 AI 模型,按能力维度排出的"单点冠军"清单。
>
> 数据来源:lmarena Elo、VBench、DPG-Bench、官方榜单、业界共识。
>
> 配合使用:
> - [`COST_PER_MODEL.md`](COST_PER_MODEL.md) — 每个模型的成本对照
> - [`COST_COMPARISON.md`](COST_COMPARISON.md) — 全平台横向决策树

## 🏷️ 图例

| 标记 | 含义 |
|------|------|
| 🟢 **【开源】** | 权重公开,可本地部署 / 微调,商用安全(Apache 2.0 / MIT) |
| 🟡 **【开源·限商用】** | 权重公开但有许可限制(非商用 / 学术许可 / 营收阈值) |
| 🔴 **【闭源】** | 仅通过厂商 API 调用,不可本地部署 |

---

## 📝 LLM(剧本 / 分镜文案 / 提示词润色)

ManjuForge 用途:剧本分析、实体抽取、分镜文案、提示词润色,单部约 2M tokens。

### 综合排行

| 排名 | 模型 | 提供方 | 开源? | 关键指标 | 单部成本 |
|------|------|--------|-------|---------|---------|
| 🥇 综合旗舰 | **Claude Opus 4.7** | Anthropic | 🔴**【闭源】** | 1M context,业界推理基准 | ¥579 |
| 🥈 国内综合 | **qwen3-max** | 阿里 | 🔴**【闭源】**(API)+ 🟢**【开源】**(qwen3 系列开源) | 32K context,中文最优 | ¥11.36 |
| 🥉 海外性价比 | **Gemini 2.5 Pro** | Google | 🔴**【闭源】** | 1M context,多模态 | ¥48 |
| 4 | **GPT-5** | OpenAI | 🔴**【闭源】** | 推理基准 | ¥98 |
| 5 | **DeepSeek V3.2** | DeepSeek | 🟢**【开源】** | 性价比 + 推理,671B MoE 全开源 | ~¥4 |
| 6 | **Doubao-Seed-2.0-Pro** | 字节 | 🔴**【闭源】** | 火山生态 + 全模态 | ~¥15 |

### 细分维度冠军

| 维度 | 冠军 | 开源? | 备注 |
|------|------|-------|------|
| 🏆 推理深度 | **Claude Opus 4.7** / **DeepSeek-R1** | 🔴**【闭源】** / 🟢**【开源】** | 最佳推理质量 |
| 🏆 长上下文 | **Gemini 2.5 Pro**(1M)🔴**【闭源】** / **qwen3.6-plus**(256K)🔴**【闭源】** | 🔴**【闭源】** / 🔴**【闭源】** | 整本小说 ingest |
| 🏆 中文剧本 | **qwen3-max** | 🔴**【闭源】**(API) | 中文写作最自然 |
| 🏆 性价比 | **Gemini 2.5 Flash**(¥0.54/¥2.16) | 🔴**【闭源】** | 单部 ¥2.46 |
| 🏆 开源旗舰 | **DeepSeek V3.2**(671B MoE)/ **Qwen3-235B-A22B** | 🟢**【开源】** / 🟢**【开源】** | 完全开源,可商用 |
| 🏆 开源消费级 | **Qwen3-7B** / **Qwen3-32B** | 🟢**【开源】** / 🟢**【开源】** | 4090 / A100 单卡可跑 |
| 🏆 开源 Llama 系 | **Llama 4 / Llama 3.3 70B** | 🟡**【开源·限商用】** | Meta 商业许可有条件 |

---

## 🎨 T2I(角色 / 场景 / 道具 / 分镜图)

ManjuForge 用途:静态资产 + 分镜图生成,单部约 1,510 张。

### 综合排行(lmarena Elo)

| 排名 | 模型 | 提供方 | 开源? | Elo | 关键指标 | 单价 |
|------|------|--------|-------|-----|---------|------|
| 🥇 | **GPT Image 2** | OpenAI | 🔴**【闭源】** | **1338** | 榜首 | ¥1.08/张 |
| 🥈 | **Nano Banana 2** | Google | 🔴**【闭源】** | **1261** | 14 张参考 | ¥0.48-1.09/张 |
| 🥉 | **Nano Banana Pro** | Google | 🔴**【闭源】** | **1220** | 4K 原生,工具完整 | ¥0.96-1.73/张 |
| 4 | **FLUX.2 Max** | BFL | 🔴**【闭源】** | **1201** | 业内写实顶级 | ~¥0.40/张 |
| 5 | **GPT Image 1.5** | OpenAI | 🔴**【闭源】** | 1272 | 性价比 | ¥0.72/张 |
| 6 | **FLUX.2 Pro** | BFL | 🔴**【闭源】** | — | 10 张参考 | ¥0.22/张 |
| 7 | **FLUX.2 dev** | BFL | 🟡**【开源·限商用】** | — | 开源版,非商用 | 自部署 |
| 8 | **Qwen-Image-2.0** | 阿里 | 🟢**【开源】** | — | DPG-Bench 88.32 | 自部署 |

### 细分维度冠军

| 维度 | 冠军 | 开源? | 关键能力 |
|------|------|-------|---------|
| 🏆 **综合榜首** | **GPT Image 2** | 🔴**【闭源】** | Elo 1338 |
| 🏆 **中文文字渲染** | **Seedream 5.0**(字节) | 🔴**【闭源】** | 集成实时联网搜索,**中英文海报业界第一** |
| 🏆 **角色一致性** | **Nano Banana Pro**(14 张参考)/ **FLUX.2 Pro**(10 张参考) | 🔴**【闭源】** / 🔴**【闭源】** | 多参考图业内最强 |
| 🏆 **写实摄影(开源)** | **FLUX.2 dev** | 🟡**【开源·限商用】** | 开源写实之最,非商用许可 |
| 🏆 **写实摄影(闭源)** | **FLUX.2 Max / Pro** | 🔴**【闭源】** | 200 词长 prompt 高保真 |
| 🏆 **4K 原生输出** | **Nano Banana Pro** / **Veo 3.1 Standard** | 🔴**【闭源】** / 🔴**【闭源】** | 原生 4K |
| 🏆 **国内综合** | **wan2.7-image-pro** | 🔴**【闭源】**(API,wan2.2 系开源) | 4K + 多图参考 |
| 🏆 **国内中文专精** | **Qwen-Image-Plus** | 🟢**【开源】**(同 family) | 2K 原生 |
| 🏆 **开源综合** | **Qwen-Image-2.0**(7B) | 🟢**【开源】** | DPG-Bench **88.32**(超 FLUX.1 83.84) |
| 🏆 **开源 SD 系** | **sd3.5-large** / **SDXL** | 🟢**【开源】** | 8B,Stable Diffusion 经典 |
| 🏆 **开源国产** | **HunyuanDiT** / **CogView4** | 🟢**【开源】** / 🟢**【开源】** | 腾讯 / 智谱开源图像 |
| 🏆 **性价比批量** | **Gemini 3.1 Flash Image batch**(7.5 折) | 🔴**【闭源】** | $0.034-0.076/张 |

---

## 🖼️ I2I(多参考图编辑 / 角色一致性)

ManjuForge 用途:角色 / 服饰 / 道具的多参考图编辑,保持一致性。

### 综合排行

| 排名 | 模型 | 提供方 | 开源? | 关键指标 | 单价 |
|------|------|--------|-------|---------|------|
| 🥇 性价比 | **Gemini 3.1 Flash Image** | Google | 🔴**【闭源】** | **14 张参考**,$0.084/张 | ¥0.48-1.09/张 |
| 🥈 高保真 | **FLUX.2 Pro** | BFL | 🔴**【闭源】** | **10 张参考**,角色保持最佳 | ¥0.22/张 |
| 🥉 国内 | **wan2.7-image-pro** | 阿里 | 🔴**【闭源】**(API,wan2.2 系开源) | 多图参考 + 边界框编辑 | ¥0.50/张 |
| 4 | **Qwen-Image-Edit-2511** | 阿里 | 🟢**【开源】** | 指令式修改,完全开源 | ¥0.20/张(API)/ 自部署 |
| 5 | **GPT Image 2 Edit** | OpenAI | 🔴**【闭源】** | 通用编辑 | ¥1.08/张 |
| 6 | **FLUX.2 Kontext dev** | BFL | 🟡**【开源·限商用】** | 编辑专用开源,非商用 | 自部署 |

### 细分维度冠军

| 维度 | 冠军 | 开源? |
|------|------|-------|
| 🏆 **最多参考图** | **Gemini 3.1 Flash Image / Nano Banana Pro**(14 张) | 🔴**【闭源】** |
| 🏆 **角色一致性性价比** | **Gemini 3.1 Flash Image** | 🔴**【闭源】** |
| 🏆 **写实高保真** | **FLUX.2 Pro**(10 张参考) | 🔴**【闭源】** |
| 🏆 **指令式编辑** | **Qwen-Image-Edit-2511** | 🟢**【开源】** |
| 🏆 **开源 + 本地部署** | **Qwen-Image-Edit-2511** / **FLUX.2 Kontext dev** | 🟢**【开源】** / 🟡**【开源·限商用】** |

---

## 🎬 I2V(图生视频 — ManjuForge 最关键能力)

ManjuForge 用途:分镜图 → 5 秒视频片段,单部 1,440 帧 / 7,200 秒。

### 综合排行

| 排名 | 模型 | 提供方 | 开源? | 关键指标 | 单价 / 秒 |
|------|------|--------|-------|---------|----------|
| 🥇 综合 | **Google Veo 3.1 Standard** | Google | 🔴**【闭源】** | **2026 综合榜首** | ¥2.88(直连) |
| 🥈 多镜头 | **Doubao Seedance 2.0 Pro** | 字节 | 🔴**【闭源】** | **业界首发音视频联合,8+ 语言唇音同步** | ¥1.00 |
| 🥉 人像运镜 | **Kling 3.0** | 快手 | 🔴**【闭源】** | **业内人像 / 运镜基准** | ¥0.54-¥1.21 |
| 4 | **Kling 2.1 Master** | 快手 | 🔴**【闭源】** | 电影级多人同框 | ~¥1.00 |
| 5 | **wan2.7-i2v** | 阿里 | 🔴**【闭源】**(API,wan2.2 系开源) | 国内主流,音画同步 | ¥0.60-1.00 |
| 6 | **Sora 2** | OpenAI | 🔴**【闭源】** | 海外强势 | ~$0.087/秒 |
| 7 | **wan2.6-i2v** | 阿里 | 🔴**【闭源】**(API,wan2.2 系开源) | 上一代,质量稳定 | ¥0.60-1.00 |
| 8 | **MiniMax Hailuo 02 Pro** | MiniMax | 🔴**【闭源】** | 日常向 | ~¥0.50 |
| 9 | **Wan2.2-I2V-A14B** | 阿里(开源) | 🟢**【开源】** | 开源旗舰,VBench 高分 | 自部署 |
| 10 | **HunyuanVideo** | 腾讯 | 🟢**【开源】** | 开源时间一致性最强 | 自部署 |

### 细分维度冠军

| 维度 | 冠军 | 开源? | 关键能力 |
|------|------|-------|---------|
| 🏆 **综合榜首** | **Google Veo 3.1 Standard** | 🔴**【闭源】** | 原生 4K + cinematic 音频 |
| 🏆 **多镜头叙事** | **Doubao Seedance 2.0 Pro** | 🔴**【闭源】** | 同一帧切换机位,业界首发 |
| 🏆 **音视频联合 / 唇音同步** | **Doubao Seedance 2.0** / **Veo 3.1** | 🔴**【闭源】** / 🔴**【闭源】** | 原生音频,自动对口型 |
| 🏆 **人像 / 运镜** | **Kling 3.0** | 🔴**【闭源】** | 业内基准 |
| 🏆 **电影级多人同框** | **Kling 2.1 Master** | 🔴**【闭源】** | 大片质感 |
| 🏆 **国内综合(DashScope)** | **wan2.7-i2v** | 🔴**【闭源】**(API) | 享阿里节省计划 |
| 🏆 **业界最便宜 1080P** | **Seedance 2.0 Fast**(via fal) | 🔴**【闭源】** | ¥0.16/秒 |
| 🏆 **极致省钱(画质够用)** | **Hailuo 02 标准 512P** | 🔴**【闭源】** | ¥0.12/秒 |
| 🏆 **开源 - VBench 第一** | **Wan2.1 14B** | 🟢**【开源】** | VBench 86.2 |
| 🏆 **开源旗舰** | **Wan2.2-I2V-A14B**(14B MoE) | 🟢**【开源】** | 同 wan family,本地可部署 |
| 🏆 **开源 - 时间一致性** | **HunyuanVideo**(腾讯 13B) | 🟢**【开源】** | 最强时间一致性 |
| 🏆 **开源 - prompt 理解** | **CogVideoX-5b**(智谱) | 🟢**【开源】** | 复杂场景描述执行准 |
| 🏆 **开源 - 消费级单卡** | **Wan2.2-ti2v-5B** | 🟢**【开源】** | 4090 24GB 可跑 |
| 🏆 **开源 - 首尾帧** | **Wan2.1-flf2v-14B-720p** | 🟢**【开源】** | First-Last-Frame 控制 |
| 🏆 **开源 - 极轻量** | **CogVideoX-2b** | 🟢**【开源】** | 8GB 显存可跑 |
| 🏆 **开源 - Genmo 系** | **Mochi 1**(Genmo) | 🟢**【开源】** | Apache 2.0 许可,4090 8min/clip |
| 🏆 **开源 - 快速** | **LTX-Video** | 🟢**【开源】** | 速度最快开源视频 |

---

## 📹 T2V(文生视频)

> 与 I2V 主流模型基本重叠,排名相同。

| 排名 | 模型 | 开源? | 备注 |
|------|------|-------|------|
| 🥇 | **Google Veo 3.1 Standard** | 🔴**【闭源】** | 综合榜首 |
| 🥈 | **Doubao Seedance 2.0 Pro** | 🔴**【闭源】** | 国内多镜头领先 |
| 🥉 | **Kling 3.0** | 🔴**【闭源】** | 人像运镜 |
| 4 | **Sora 2**(OpenAI) | 🔴**【闭源】** | 海外强势 |
| 5 | **wan2.7-i2v / wan2.6-i2v**(T2V 模式) | 🔴**【闭源】**(API) | 国内主流 |
| 6 | **Wan2.2-T2V-A14B**(开源) | 🟢**【开源】** | 14B MoE,本地可部署 |
| 7 | **HunyuanVideo**(腾讯开源) | 🟢**【开源】** | 13B,VBench 高分 |
| 8 | **CogVideoX-5b**(智谱开源) | 🟢**【开源】** | 5B,prompt 理解最准 |

---

## 🎞️ R2V(参考视频生成)

> 把参考视频的运镜 / 风格 / 节奏迁移到新内容。

| 排名 | 模型 | 提供方 | 开源? | 备注 |
|------|------|--------|-------|------|
| 🥇 国内 | **wan2.7-r2v / wan2.6-r2v** | 阿里 | 🔴**【闭源】**(API) | 唯一支持的国内大厂 API |
| 🥈 海外 | **Kling 3.0 V2V** | 快手 | 🔴**【闭源】** | 部分支持 |
| 🥉 开源 | **Wan2.1-flf2v-14B-720p** | 阿里 | 🟢**【开源】** | 首尾帧控制 |
| 4 | **Wan2.2-r2v**(等价于 wan2.2-i2v 的 r2v 变种) | 阿里 | 🟢**【开源】** | 开源,本地部署 |

---

## 🎙️ TTS(配音 / 旁白)

ManjuForge 用途:角色对白 + 旁白,单部约 48,000 计费字符。

### 综合排行

| 排名 | 模型 | 提供方 | 开源? | 关键指标 | 单价 |
|------|------|--------|-------|---------|------|
| 🥇 戏剧化 | **ElevenLabs v3** | ElevenLabs | 🔴**【闭源】** | 业界戏剧化基准 | $0.30/千字符 |
| 🥈 多语言 | **ElevenLabs Multilingual v2** | ElevenLabs | 🔴**【闭源】** | 32 语言,音色克隆质量第一 | 同上 |
| 🥉 性价比 | **Fish Audio S2** | Fish Audio | 🟢**【开源】**(Fish Speech 系列开源) | **Elo #1**,80+ 语言,**1/10 ElevenLabs 价格** | $15/百万字符 |
| 4 | **Cartesia Sonic 3** | Cartesia | 🔴**【闭源】** | **首字节 40-90ms**,实时 Agent 最佳 | $0.03/分钟 |
| 5 | **cosyvoice-v3-plus** | 阿里 | 🟢**【开源】**(CosyVoice 系列开源) | 中文情感最稳 | ¥1.5/万字符 |
| 6 | **MiniMax Speech 2.6 HD** | MiniMax | 🔴**【闭源】** | 40+ 语言,中文情感强 | ~¥10/万字符 |
| 7 | **CosyVoice 3 自部署** | FunAudioLLM | 🟢**【开源】** | 同阿里 API 同款 | 自部署(<6GB VRAM)|
| 8 | **Fish Speech 1.5 自部署** | Fish Audio | 🟢**【开源】** | Fish Audio 开源版 | 自部署 |

### 细分维度冠军

| 维度 | 冠军 | 开源? |
|------|------|-------|
| 🏆 **戏剧化 / 角色配音** | **ElevenLabs v3** | 🔴**【闭源】** |
| 🏆 **音色克隆质量** | **ElevenLabs Multilingual v2** | 🔴**【闭源】** |
| 🏆 **多语言性价比** | **Fish Audio S2**(Elo #1,80+ 语言) | 🟢**【开源】**(同款开源) |
| 🏆 **实时 / 低延迟** | **Cartesia Sonic 3**(40-90ms 首字节) | 🔴**【闭源】** |
| 🏆 **中文情感** | **cosyvoice-v3-plus** / **MiniMax Speech 2.6 HD** | 🟢**【开源】** / 🔴**【闭源】** |
| 🏆 **3 秒声音克隆** | **CosyVoice 3** | 🟢**【开源】** |
| 🏆 **开源同款 API** | **CosyVoice 3**(< 6GB 显存)/ **Fish Speech 1.5** | 🟢**【开源】** / 🟢**【开源】** |
| 🏆 **极致便宜 + 国内合规** | **cosyvoice-v3-flash**(¥3.84/部) | 🟢**【开源】**(同源) |
| 🏆 **完全 CPU 部署** | **CosyVoice-300M Lite** | 🟢**【开源】** |
| 🏆 **开源多语言** | **F5-TTS** / **MeloTTS** | 🟢**【开源】** / 🟢**【开源】** |
| 🏆 **开源对话式** | **ChatTTS** | 🟢**【开源】** |
| 🏆 **开源 Qwen 系** | **Qwen3-TTS**(0.6B / 1.7B) | 🟢**【开源】** |

---

## 🏆 各能力单点冠军汇总(国内 / 海外 / 开源)

> 🟢 **【开源】** 可本地部署 / 商用安全;🟡 **【开源·限商用】** 权重公开但许可受限;🔴 **【闭源】** 仅 API。

| 能力 | 海外单点冠军 | 国内单点冠军 | 开源单点冠军 |
|------|------------|------------|------------|
| LLM | **Claude Opus 4.7** 🔴**【闭源】** | **qwen3-max** 🔴**【闭源】**(API) | **DeepSeek V3.2** 🟢**【开源】** / **Qwen3-235B** 🟢**【开源】** |
| T2I 综合 | **GPT Image 2** 🔴**【闭源】**(Elo 1338) | **wan2.7-image-pro** 🔴**【闭源】**(API) | **Qwen-Image-2.0** 🟢**【开源】** |
| T2I 中文 | — | **Seedream 5.0** 🔴**【闭源】** | **Qwen-Image-2.0** 🟢**【开源】** |
| T2I 写实 | **FLUX.2 Max** 🔴**【闭源】** | — | **FLUX.1 Dev** 🟡**【开源·限商用】** / **FLUX.2 dev** 🟡**【开源·限商用】** |
| I2I 多参考 | **Gemini 3.1 Flash Image** 🔴**【闭源】**(14 张) | **wan2.7-image-pro** 🔴**【闭源】**(API) | **Qwen-Image-Edit-2511** 🟢**【开源】** |
| **I2V 综合** | **Google Veo 3.1 Standard** 🔴**【闭源】** | **wan2.7-i2v** 🔴**【闭源】**(API) | **Wan2.2-I2V-A14B** 🟢**【开源】** |
| I2V 多镜头 | — | **Seedance 2.0 Pro** 🔴**【闭源】** | — |
| I2V 人像运镜 | **Kling 3.0** 🔴**【闭源】** | **Kling 3.0** 🔴**【闭源】** | — |
| I2V 时间一致性 | — | — | **HunyuanVideo** 🟢**【开源】** |
| I2V 消费级 | — | **wan2.2-i2v-flash** 🔴**【闭源】**(API) | **Wan2.2-ti2v-5B** 🟢**【开源】** / **CogVideoX-2b** 🟢**【开源】** |
| TTS 情感 | **ElevenLabs v3** 🔴**【闭源】** | **cosyvoice-v3-plus** 🟢**【开源】**(同款 API) | **CosyVoice 3** 🟢**【开源】** |
| TTS 性价比 | **Fish Audio S2** 🟢**【开源】**(同款) | **cosyvoice-v3-flash** 🟢**【开源】**(同款 API) | **Fish Speech 1.5** 🟢**【开源】** |
| TTS 实时 | **Cartesia Sonic 3** 🔴**【闭源】** | **cosyvoice-v3-flash** 🟢**【开源】**(同款) | **CosyVoice 3** 🟢**【开源】** |

### 关键观察

1. **绝大多数顶级 LLM / 视频模型仍是闭源**(Claude / GPT / Gemini / Veo / Kling / Seedance)
2. **图像生成开源生态最成熟** — Qwen-Image-2.0、FLUX 系、SDXL 都能本地跑
3. **TTS 几乎是"开源同源 API"** — CosyVoice / Fish Audio 都把 API 同款模型开源,自部署零质量损失
4. **国内大厂集体开源 I2V** — 阿里(Wan2.2)+ 腾讯(HunyuanVideo)+ 智谱(CogVideoX),开源 I2V 几乎全是中国出品
5. **API 端通常领先开源 1 代** — 阿里 wan2.7 是 API,wan2.2 是开源;字节 Seedance 2.0 是 API,无对应开源

---

## 🎯 三种"最强组合"

### 💎 全能力旗舰(画质优先,钱不是问题)

| 阶段 | 选用 | 单部 |
|------|------|------|
| LLM | **Claude Opus 4.7** | ¥579 |
| T2I 静态 | **Nano Banana Pro 4K** | ¥121 |
| T2I 分镜图 | **GPT Image 2** | ¥1,555 |
| I2I 多参考 | **Gemini 3.1 Flash Image**(含分镜图内) | — |
| **I2V 主体** | **Google Veo 3.1 Standard 含音频** | **¥20,736** |
| TTS | **ElevenLabs v3** | ¥10.40 |
| **合计** | | **¥23,001 / 部** |

### 🏯 国内合规最强(中文 + 监管 + 量产)

| 阶段 | 选用 | 单部 |
|------|------|------|
| LLM | **qwen3-max** | ¥11.36 |
| T2I 海报 / 中文文字 | **Seedream 5.0** | ¥28(70 张) |
| T2I 分镜图 | **wan2.7-image-pro** | ¥720 |
| **I2V 主体** | **wan2.7-i2v 1080P 含音画** | ¥7,200 |
| (关键剧情 +) | **Seedance 2.0 Pro** / **Kling 3.0** 试镜 | 加成本 |
| TTS | **cosyvoice-v3-plus** | ¥7.20 |
| **合计** | | **¥7,967 / 部** |
| **+ AI 通用型节省计划 7.6 折** | | **¥6,055 / 部** |

### 🚀 开源全栈最强(自部署,极致省钱)

| 阶段 | 选用 | Xinference 模型名 | 单部 GPU 摊销 |
|------|------|------------------|--------------|
| LLM | **Qwen3-32B**(若 A100)/ Qwen3-7B(若 4090) | `qwen3-instruct` | ¥2 |
| T2I | **Qwen-Image-2.0**(7B,Q4 量化或 FP16) | `Qwen-Image-2512` | ¥4.50 |
| I2I | **Qwen-Image-Edit-2511** | `Qwen-Image-Edit-2511` | (含 T2I 内) |
| **I2V** | **Wan2.2-i2v-A14B**(若 A100)/ Wan2.2-ti2v-5B(若 4090) | `Wan2.2-i2v-A14B` / `Wan2.2-ti2v-5B` | ¥36-288 |
| TTS | **CosyVoice 3** | `CosyVoice2-0.5B` | ¥1 |
| **合计(4090 单卡)** | | | **¥43 / 部** |
| **合计(A100 80GB 第三方)** | | | **¥312 / 部** |

---

## 📈 推荐路径(按场景)

| 场景 | 推荐 | 单部成本 |
|------|------|---------|
| 💎 单部精品 / 提案级 | 全能力旗舰 | ¥23,001 |
| 🏯 国内合规量产 | 国内最强 + 节省计划 | **¥6,055** |
| 🌏 海外多语言发行 | Veo 3.1 Fast + Nano Banana Pro + ElevenLabs | ¥8,400 |
| ⚡ 性价比中小规模 | fal.ai Kling 3.0 + 阿里外接 | ¥1,848 |
| 💰 业界最便宜 1080P | fal.ai Seedance 2.0 Fast + 外接 | ¥1,488 |
| 🚀 极致省钱 / 工厂级 | 全开源自部署 | ¥43-414 |
| 🎬 人像 / 运镜重剧 | Kling 3.0 + 阿里外接 | ¥1,848-5,626 |
| 🏯 中文海报 + 多镜头 | Seedream 5.0 + Seedance 2.0 | ¥7,815 |
| 🏃 草样 / 内审 | wan2.2-i2v-flash 480P | ¥1,063 |

---

## 💡 选型核心原则

1. **I2V 决定 90% 成本** — 这一栏是选型的"主战场"
2. **LLM / TTS 占比 < 1%** — 选最强的没影响,不必为省钱降档
3. **角色一致性 > 单帧质量** — 漫剧最痛是"前后人脸不一样",Gemini 3.1 Flash Image / Nano Banana Pro 的 14 张参考无敌
4. **国内合规要走国内模型** — Veo / GPT Image / Claude 等海外模型用于发行,国内备案优先国内
5. **混搭 > 单一栈** — 没有任何一个供应商在所有能力都是冠军;最优解永远是 "I2V 走 A 家 + T2I 走 B 家 + TTS 走 C 家"
6. **聚合平台(fal.ai)是性价比之王** — Kling 3.0 直连 ¥0.96 → fal.ai ¥0.21,**节约 78%**
7. **开源已经够用** — Wan2.2-14B / Qwen-Image-2.0 / CosyVoice 3 全部是阿里同款,只是 API 端领先一代

---

## 🟢**【开源】** 开源模型完整清单(按 ManjuForge 可用性排序)

> 仅列出**权重公开 + 可本地部署**的模型;闭源 API-only 不在此表。

### LLM 开源(单卡可跑首选)

| 模型 | 参数 | 许可 | 单卡硬件 | Xinference 名 |
|------|------|------|---------|--------------|
| **Qwen3-7B** | 7B | Apache 2.0 ✅ | RTX 4090 24GB | `qwen3-instruct --size-in-billions 7` |
| **Qwen3-32B** | 32B | Apache 2.0 ✅ | A100 80GB / 4090 量化 | `qwen3-instruct --size-in-billions 32` |
| **Qwen3-72B** | 72B | Apache 2.0 ✅ | 2× A100 / 单 A100 量化 | `qwen3-instruct --size-in-billions 72` |
| **Qwen3-235B-A22B** | 235B MoE | Apache 2.0 ✅ | 多卡 H100 | `qwen3-moe-instruct` |
| **DeepSeek V3.2** | 671B MoE | MIT ✅ | 8× H100 | `deepseek-v3` |
| **DeepSeek R1** | 671B MoE | MIT ✅ | 8× H100 | `deepseek-r1` |
| **Llama 4** / **Llama 3.3 70B** | 70B | Meta 商业许可 ⚠️ | 2× A100 | `llama-3-instruct` |
| **GLM-4.5 / GLM-5** | 多档 | 智谱许可 ⚠️ | A100 | `glm4-chat` |

### T2I 开源

| 模型 | 参数 | 许可 | 单卡 | Xinference 名 |
|------|------|------|------|--------------|
| **Qwen-Image-2.0**(2512) | 7B | Apache 2.0 ✅ | RTX 4090(Q4 13GB) | `Qwen-Image-2512` |
| **Qwen-Image** | 7B | Apache 2.0 ✅ | 同上 | `Qwen-Image` |
| **Qwen-Image-Layered** | 7B | Apache 2.0 ✅ | 同上 | `Qwen-Image-Layered` |
| **FLUX.1 Dev** | 12B | 非商用 ⚠️ | RTX 4090 | `FLUX.1-dev` |
| **FLUX.1 Schnell** | 12B | Apache 2.0 ✅(快速档) | RTX 4090 | `FLUX.1-schnell` |
| **FLUX.2 Dev** | 32B | 非商用 ⚠️ | A100 / 量化后 4090 | `FLUX.2-dev` |
| **FLUX.2 Klein** | 4B / 9B | Apache 2.0 ✅ | RTX 4090 | `FLUX.2-klein-4B/9B` |
| **sd3.5-large** | 8B | SAI 社区许可 ⚠️ | A100 | `sd3.5-large` |
| **sd3.5-medium** | — | 同上 | RTX 4090 | `sd3.5-medium` |
| **SDXL** | 6.6B | SAI 开源 ✅ | RTX 3090+ | `sdxl-base` |
| **HunyuanDiT**(腾讯) | — | 商用许可 ✅ | RTX 4090 | `HunyuanDiT` |
| **CogView4**(智谱) | — | Apache 2.0 ✅ | RTX 4090 | `cogview4` |
| **Kolors** | — | 快手开源 ✅ | RTX 4090 | `kolors` |
| **Z-Image** | — | 开源 ✅ | RTX 4090 | `Z-Image` |

### I2I 开源

| 模型 | 参数 | 许可 | Xinference 名 |
|------|------|------|--------------|
| **Qwen-Image-Edit-2511** | 7B | Apache 2.0 ✅ | `Qwen-Image-Edit-2511` |
| **Qwen-Image-Edit-2509** | 7B | Apache 2.0 ✅ | `Qwen-Image-Edit-2509` |
| **FLUX.1 Kontext Dev** | 12B | 非商用 ⚠️ | `FLUX.1-Kontext-dev` |

### I2V / T2V / R2V 开源(本场景最关键)

#### 概览表

| 模型 | 参数 | 许可 | 推荐硬件 | Xinference 名 |
|------|------|------|---------|--------------|
| **Wan2.2-ti2v-5B** ⭐ | **5B** | Apache 2.0 ✅ | RTX 3060+ | `Wan2.2-ti2v-5B` |
| **Wan2.2-i2v-A14B** ⭐ | **27B MoE / 14B 激活** | Apache 2.0 ✅ | RTX 4090(量化)/ A100 80GB | `Wan2.2-i2v-A14B` |
| **Wan2.2-A14B** | 27B MoE / 14B 激活 | Apache 2.0 ✅ | RTX 4090(量化)/ A100 80GB | `Wan2.2-A14B` |
| **Wan2.1-1.3B** | 1.3B | Apache 2.0 ✅ | RTX 3060 | `Wan2.1-1.3B` |
| **Wan2.1-14B** | 14B 稠密 | Apache 2.0 ✅ | A100 40GB / 4090 量化 | `Wan2.1-14B` |
| **Wan2.1-i2v-14B-720p** | 14B 稠密 | Apache 2.0 ✅ | A100 80GB / 4090 量化 | `Wan2.1-i2v-14B-720p` |
| **Wan2.1-i2v-14B-480p** | 14B 稠密 | Apache 2.0 ✅ | A100 40GB / 4090 量化 | `Wan2.1-i2v-14B-480p` |
| **Wan2.1-flf2v-14B-720p**(首尾帧)| 14B 稠密 | Apache 2.0 ✅ | A100 80GB | `Wan2.1-flf2v-14B-720p` |
| **HunyuanVideo**(腾讯) | 13B | 商用许可 ✅ | A100 80GB / H100 | `HunyuanVideo` |
| **CogVideoX-5b**(智谱) | 5B | Apache 2.0 ✅ | RTX 4090 24GB | `CogVideoX-5b` |
| **CogVideoX-2b**(智谱) | 2B | Apache 2.0 ✅ | RTX 3090 / 4070 | `CogVideoX-2b` |
| **Mochi 1**(Genmo) | 10B | Apache 2.0 ✅ | A100(慢)| 需自行加载 |
| **LTX-Video** | 2B | 开源 ✅ | RTX 4090 | 需自行加载 |

#### Wan 5 个核心模型显存对照(关键)

> 数值含**模型权重 + VAE + Text encoder + Activation**(720P 5 秒推理时);**MoE 模型权重要全部加载**,只是激活计算 14B。

| 模型 | 参数 | BF16 原生 | FP8 量化 | Q5/Q6 量化 | Q4 量化 | **最低可跑卡** |
|------|------|----------|---------|-----------|---------|--------------|
| **Wan2.2-ti2v-5B** | 5B 稠密 | **10-15 GB** | 7-9 GB | 5-6 GB | 4-5 GB | **RTX 3060 12GB** ⭐ |
| **Wan2.1-i2v-14B-480p** | 14B 稠密 | 35-40 GB | 20-24 GB | 16-18 GB | 14-16 GB | RTX 4080 16GB(Q4) |
| **Wan2.1-i2v-14B-720p** | 14B 稠密 | **45-55 GB** | 25-30 GB | 20-22 GB | 17-20 GB | RTX 4090 24GB(Q5) |
| **Wan2.2-A14B**(T2V) | 27B MoE | **50-60 GB** | 28-32 GB | 22-25 GB | 18-22 GB | RTX 4090 24GB(Q5) |
| **Wan2.2-i2v-A14B**(I2V) | 27B MoE | **50-60 GB** | 28-32 GB | 22-25 GB | 18-22 GB | **RTX 4090 24GB**(Q5) ⭐ |

#### GGUF 量化档位详细(适用 A14B 系)

| 量化 | 模型权重 | 总显存(含 VAE 等) | 质量损失 | 推荐? |
|------|---------|-------------------|---------|------|
| BF16 / FP16 原生 | 28-54 GB | 50-60 GB | 0% | ✅ A100 80GB 生产 |
| FP8 | ~14 GB | 28-32 GB | < 2% | ✅ 5090 32GB / 4090 边缘 |
| **Q8_0** | 15.4 GB | ~28 GB | < 3% | ✅ 4090 24GB 推荐 |
| **Q6_K** | 12 GB | ~22 GB | < 5% | ✅ 4090 / 4080 |
| **Q5_K_M** | 10.8 GB | ~20 GB | < 8% | ✅ 4090 / 4070 Ti |
| **Q5_K_S** | 10.1 GB | ~19 GB | ~10% | ⚠️ 视场景 |
| **Q4_K_M** | 9.65 GB | ~18 GB | ~15% | ⚠️ MoE 路由质量下降 |
| Q4_K_S | 8.75 GB | ~17 GB | 20%+ | ❌ MoE 不推荐 |
| Q3 / Q2 | < 8 GB | < 16 GB | 严重劣化 | ❌ **不要用 MoE 模型** |

> ⚠️ **MoE 模型量化共识:** A14B 系不要低于 Q4_K_M,Q3/Q2 会破坏专家路由,生成不稳定。

#### Wan2.2-i2v-A14B 推理速度参考(5 秒 clip)

| 硬件 | 精度 | 480P | 720P | 1080P |
|------|------|------|------|-------|
| RTX 4090 24GB | Q5_K_M | 60-80s | 90-120s | 显存不够 |
| RTX 4090 24GB | FP8 | 50-70s | 80-100s | 显存不够 |
| RTX 5090 32GB | FP8 | 40-55s | 60-90s | 150-200s |
| A100 80GB | BF16 | 40-50s | **60-90s** ⭐ | 150-180s |
| H100 80GB | BF16 | 20-30s | **30-45s** | 90-120s |

> 一部 120 分钟漫剧 = 1,440 个 5 秒 clip:
> - RTX 4090 Q5:**约 36-48 小时**
> - A100 80GB BF16(720P):**约 24-36 小时** ⭐ 推荐生产
> - H100 80GB(720P):**约 12-18 小时**

#### Wan 模型选型决策

```
你想跑什么?
├─ 只是想试试视频生成 / 个人创作
│   → Wan2.2-ti2v-5B
│     硬件:RTX 3060 12GB+ 即可
│     精度:BF16
│     质量:80% 商业场景够用
│
├─ 想要 Wan 系最强质量,有 4090
│   → Wan2.2-i2v-A14B Q5_K_M 量化
│     硬件:RTX 4090 24GB
│     精度:Q5_K_M(MoE 量化下限)
│     速度:90-120s/clip,一部漫剧 36-48 小时
│
├─ 工作室生产,1080P 出片
│   → Wan2.2-i2v-A14B BF16
│     硬件:A100 80GB(第三方租 ¥8/h)
│     精度:BF16 原生
│     单部成本:~¥288
│
├─ 工厂级,极致吞吐
│   → Wan2.2-i2v-A14B BF16 + 多卡 H100 集群
│     硬件:4-8× H100 80GB
│     精度:BF16
│     单部成本:¥150-414(吞吐摊薄)
│
├─ 只能跑 T2V(无图生视频需求)
│   → Wan2.2-A14B(同 i2v-A14B 显存)
│
├─ 老版本 720P,仅 I2V
│   → Wan2.1-i2v-14B-720p(已被 Wan2.2 替代,不推荐新部署)
│
└─ 极致低显存(< 16GB)
    → 仅 Wan2.2-ti2v-5B,放弃 14B 系
```

### TTS 开源(对配音几乎无门槛)

| 模型 | 参数 | 许可 | 单卡 | Xinference 名 |
|------|------|------|------|--------------|
| **CosyVoice2-0.5B**(最新版,推荐) | 0.5B | Apache 2.0 ✅ | < 6GB VRAM | `CosyVoice2-0.5B` |
| **CosyVoice-300M-SFT** | 300M | Apache 2.0 ✅ | **CPU 可跑** ⭐ | `CosyVoice-300M-SFT` |
| **CosyVoice-300M-Instruct** | 300M | Apache 2.0 ✅ | CPU 可跑 | `CosyVoice-300M-Instruct` |
| **CosyVoice-300M** | 300M | Apache 2.0 ✅ | CPU 可跑 | `CosyVoice-300M` |
| **Qwen3-TTS-0.6B / 1.7B** | 0.6B / 1.7B | Apache 2.0 ✅ | < 8GB | `Qwen3-TTS` |
| **Fish Speech 1.5** | — | Apache 2.0 ✅ | < 6GB | `FishSpeech-1.5` |
| **F5-TTS** | — | MIT ✅ | < 8GB | `F5-TTS` |
| **IndexTTS2** | — | 开源 ✅ | < 8GB | `IndexTTS2` |
| **MegaTTS3** | — | 开源 ✅ | < 8GB | `MegaTTS3` |
| **MeloTTS-中文/英文/...** | — | MIT ✅ | < 4GB | `MeloTTS-Chinese` |
| **Kokoro-82M** | 82M | Apache 2.0 ✅ | < 2GB | `Kokoro-82M` |
| **ChatTTS** | — | AGPL-3.0 ⚠️ | < 4GB | `ChatTTS` |

### 许可证速记

| 许可证 | 商用 | 备注 |
|-------|-----|------|
| Apache 2.0 / MIT | ✅ 可商用 | 最宽松 |
| Meta 商业许可 | ⚠️ MAU < 7 亿可免费商用 | Llama 系 |
| FLUX 非商用许可 | ❌ 非商用 | FLUX.1 Dev / FLUX.2 Dev 仅研究 |
| FLUX.1 Schnell / Klein | ✅ 可商用 | FLUX 的开放档 |
| SAI 社区许可 | ⚠️ 年营收 < $1M 可免费 | SD3.5 系 |
| 智谱 / 商汤等 | ⚠️ 各自定义 | 部分需商务申请 |
| AGPL-3.0 | ⚠️ 衍生品也必须开源 | ChatTTS |

> **ManjuForge 商用安全清单(全 Apache 2.0):** Qwen3 / Qwen-Image-2.0 / Wan2.2 系 / CogVideoX / CosyVoice / Fish Speech / F5-TTS / FLUX.1 Schnell / FLUX.2 Klein / DeepSeek。

---

## 🔗 参考链接

### 榜单与基准
- [lmarena Image Generation Leaderboard](https://lmarena.ai/leaderboard)
- [VBench 视频生成评测](https://vchitect.github.io/VBench-project/)
- [DPG-Bench 图像生成基准](https://github.com/TencentQQGYLab/ELLA)

### 配套文档
- [`COST_PER_MODEL.md`](COST_PER_MODEL.md) — 每个模型的单部成本对照
- [`COST_COMPARISON.md`](COST_COMPARISON.md) — 全平台选型决策树
- [`COST_ALIYUN.md`](COST_ALIYUN.md) — 阿里完整方案(含自部署 / Xinference)
- [`COST_BYTEDANCE.md`](COST_BYTEDANCE.md) — 字节豆包
- [`COST_KLING.md`](COST_KLING.md) — 可灵
- [`COST_GOOGLE.md`](COST_GOOGLE.md) — Google
- [`COST_AGGREGATOR.md`](COST_AGGREGATOR.md) — fal.ai 聚合
