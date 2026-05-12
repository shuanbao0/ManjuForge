# 全平台横向对比 + 选型决策手册

> 适用范围:ManjuForge Studio 在阿里 / 字节豆包 / 可灵 / Google / 聚合平台 / 多家 TTS 之间做平台选择时的横向对比与推荐。
> 价格数据更新于:**2026-05**。汇率 1 USD ≈ ¥7.2。
>
> 本文档不重复各平台明细 — 详情见配套文档:
> - [`COST_ALIYUN.md`](COST_ALIYUN.md) — 阿里百炼(全栈一站式 + 节省计划)
> - [`COST_BYTEDANCE.md`](COST_BYTEDANCE.md) — 字节豆包 / 火山引擎(Seedance + Seedream)
> - [`COST_KLING.md`](COST_KLING.md) — 快手可灵(Kling 视频)
> - [`COST_GOOGLE.md`](COST_GOOGLE.md) — Google(Veo + Gemini Image,海外旗舰)
> - [`COST_AGGREGATOR.md`](COST_AGGREGATOR.md) — fal.ai / OpenRouter(聚合)

---

## 1. I2V 视频生成横向对比(120 分钟漫剧 / 7,200 秒)

> I2V 占 ManjuForge 总成本 90%,**这一栏决定全局**。

### 1.1 主流模型单价表

| 模型 | 直连价(720P-1080P) | 走聚合 fal.ai | 通过 DashScope | 含音频 | 备注 |
|------|---------------------|---------------|---------------|--------|------|
| **wan2.7-i2v 1080P** | ¥1.0 / 秒(阿里) | — | — | ✅ | 阿里旗舰,节省计划可降至 ¥0.62 |
| **wan2.6-i2v 720P** | ¥0.6 / 秒(阿里) | ¥0.36-0.72 | — | ✅ | 阿里性价比档 |
| **wan2.2-i2v-flash 480P** | ¥0.1 / 秒(阿里) | — | — | ❌ | 草样档,业界最便宜的高质量品牌模型 |
| **Seedance 2.0 Pro** | ¥1.0 / 秒(字节) | — | — | ✅ | 多镜头叙事业界首发 |
| **Seedance 2.0 Fast** | — | **¥0.16 / 秒** | — | ❌ | **业界最便宜 1080P**,2026 主推 |
| **Seedance 1.5 Pro** | ~¥0.6 / 秒(字节) | ¥0.37 / 秒 | — | ✅ | 稳定生产档 |
| **Kling 3.0** | ¥0.54 / 秒(关音画) / ¥0.96(开音画) | **¥0.21 / 秒** | ¥0.6-1.0 | ✅ / ❌ | 人像运镜业界最强 |
| **Kling v3 std** | ¥0.48 / 秒(关音画) | — | ¥0.6 | ❌ | 上一代主力 |
| **Veo 3.1 Standard** | ¥2.88 / 秒 | ¥1.44 / 秒 | — | ✅ | Google 旗舰,4K 原生 |
| **Veo 3.1 Fast** | ¥1.08 / 秒(含音频) | ¥0.72-1.44 | — | ✅ | Google 性价比 |
| **Hailuo 02 标准 768P** | ¥0.32 / 秒(MiniMax) | ¥0.32 | — | — | MiniMax 海螺,日常向 |
| **Hailuo 02 标准 512P** | ¥0.12 / 秒 | ¥0.12 | — | — | 极致省钱 |
| **Vidu Q3 Pro** | ¥0.43 / 秒 | ¥0.43 | ¥0.6 | ✅ | Vidu 高质量 |
| **Vidu Q3 Turbo** | ¥0.24 / 秒 | ¥0.24 | — | ❌ | Vidu 快速档 |
| **Pixverse v4 1080P** | ¥0.58 / 秒 | ¥0.58 | ¥1.0 | — | — |
| **Pixverse v4 720P** | ¥0.29 / 秒 | ¥0.29 | ¥0.6 | — | — |
| **CogVideoX-5b(开源自部署)** | — | — | — | ❌ | 4090 可跑,¥0.005-0.02 / 秒(电费) |
| **Wan 2.2-5B(开源自部署)** | — | — | — | ❌ | 4090 可跑,见 COST_ALIYUN §7 |

### 1.2 单部 120 分钟漫剧成本对照

| 方案 | I2V 模型 + 路径 | 单部总成本(含 LLM/T2I/TTS) |
|------|---------------|---------------------------|
| 极致省钱 | Hailuo 02 512P via fal | **¥1,217** |
| 业界最便宜 1080P | Seedance 2.0 Fast via fal | **¥1,488** |
| 性价比首选 | Kling 3.0 via fal | **¥1,848** |
| 自部署 4090 | Wan2.2-5B 720P | **¥43** |
| 稳定生产(国内) | Seedance 1.5 Pro via fal | ~¥3,000 |
| 阿里草样 | wan2.2-i2v-flash 480P | **¥52** |
| 阿里 720P 平价 | wan2.7-i2v 720P + 节省 7.6 折 | **¥3,500** |
| **阿里全旗舰 + 节省计划** | **wan2.7-i2v 1080P + 7.6 折** | **¥6,061** |
| 阿里全旗舰按量 | wan2.7-i2v 1080P | ¥7,974 |
| Kling 直连主流 | Kling 3.0 含音画 | ¥5,626 |
| 字节豆包旗舰 | Seedance 2.0 Pro | ¥7,657 |
| Veo 3.1 Fast | Veo 3.1 Fast 含音频 | ¥8,375 |
| Veo 3.1 旗舰 | Veo 3.1 Standard | **¥21,335** |

> **节约最大杠杆:I2V 模型选择**。同一片源走 Seedance 2.0 Fast(¥1,488)vs 走 Veo 3.1 Standard(¥21,335),差 **14×**。

---

## 2. T2I 图像生成横向对比

| 模型 | 单价(¥/张) | 分辨率 | 多参考 | 中文文字 | 角色一致性 |
|------|------------|--------|--------|---------|----------|
| wan2.7-image(阿里) | ¥0.20 | 4K | ✅ | ✅✅ | ✅ |
| **wan2.7-image-pro**(阿里) | ¥0.50 | 4K | ✅✅ | ✅✅✅ | ✅✅ |
| **qwen-image-plus**(阿里) | ¥0.20 | 2K 原生 | — | ✅✅✅ | ✅ |
| **Seedream 5.0**(字节) | ~¥0.40 | 4K | ✅ | ✅✅✅ | ✅✅ |
| **Seedream 4.5**(字节) | ¥0.29 | — | ✅ | ✅✅ | ✅ |
| FLUX.1 Schnell | ¥0.18(fal) | — | ❌ | ❌ | ✅ |
| FLUX.2 Pro(BFL) | ¥0.22(BFL) | 高 | ✅(10 张) | ❌ | ✅✅✅(写实业内顶) |
| **Nano Banana Pro 1K/2K**(Google) | ¥0.96 | 4K 原生 | ✅(14 张) | ⚠️ | ✅✅✅✅(业内最强综合) |
| Gemini 3.1 Flash Image 1K | ¥0.48 / ¥0.36(batch) | 4K | ✅(14 张) | ⚠️ | ✅✅✅ |
| GPT Image 2(OpenAI) | $0.07-0.15 / 张 ≈ ¥0.50-1.08 | — | ✅ | ⚠️ | ✅✅✅(Elo 1338 业内顶) |

### 选 T2I 的决策

| 场景 | 推荐 |
|------|------|
| **中文文字 / 中文海报** | **Seedream 5.0** > Qwen-Image-Plus > wan2.7-image-pro |
| **角色一致性 / 多参考图** | **Nano Banana Pro / Gemini 3.1 Flash Image** > FLUX.2 Pro |
| **写实摄影** | **FLUX.2 Pro / Nano Banana Pro** |
| **快速量产 + 低价** | wan2.7-image / Seedream 4.5 |
| 国内合规优先 | wan2.7-image-pro / Seedream 5.0 |

---

## 3. TTS 配音横向对比

| 模型 | 单价 | 单部漫剧成本(48K 字符) | 多语言 | 情感 | 克隆 |
|------|------|----------------------|--------|------|------|
| **cosyvoice-v3-plus**(阿里) | ¥1.5 / 万字符 | **¥7.20** | ✅ | ✅✅ | ✅(3s 极速) |
| cosyvoice-v3-flash(阿里) | ¥0.8 / 万字符 | **¥3.84** | ✅ | ✅ | ✅ |
| **MiniMax Speech 2.6 HD** | ~¥10 / 万字符 | ¥48 | ✅✅✅(40+ 种) | ✅✅✅ | ✅ |
| MiniMax Speech 2.6 Turbo | 估 ¥5 / 万字符 | ¥24 | ✅ | ✅ | ✅ |
| **ElevenLabs Multilingual v2** | $0.30 / 千字符 ≈ ¥2.16/万 | ¥10.40 | ✅✅(32 语言) | ✅✅✅(业内基准) | ✅✅✅ |
| ElevenLabs Turbo v2.5 | 估 $0.18 / 千字符 | ¥6.20 | ✅ | ✅✅ | ✅✅ |
| **Fish Audio S2** | $15 / 百万字符 ≈ ¥0.11/万 | **¥0.52** | ✅(80+ 语言) | ✅✅ | ✅(15s 克隆,Elo #1) |
| Cartesia Sonic 3 | $0.03/分钟 ≈ ¥0.22/分钟 | ¥0.44(2 分钟对白) | ✅ | ✅✅ | ✅ |
| OpenAI tts-1 | $15 / 百万字符 ≈ ¥0.11/万 | ¥0.52 | ✅ | ⚠️ | ❌ |
| OpenAI tts-1-hd | $30 / 百万字符 ≈ ¥0.22/万 | ¥1.04 | ✅ | ✅ | ❌ |

### 选 TTS 的决策

| 场景 | 推荐 |
|------|------|
| **国内中文短剧 / 性价比** | **cosyvoice-v3-flash**(¥3.84/部) |
| **中文情感最强** | cosyvoice-v3-plus 或 MiniMax Speech 2.6 HD |
| **海外多语言发行** | ElevenLabs Multilingual v2 |
| **极致省钱 + 多语言** | **Fish Audio S2**(便宜 30 倍) |
| **实时对话 Agent** | Cartesia Sonic 3(40-90ms 首字节) |

> **TTS 占总成本不到 0.5%**,选最贴合场景的即可,不必为省钱降档。

---

## 4. LLM 横向对比

| 模型 | 输入 / 输出(¥ / 百万 tok) | 上下文 | 单部漫剧成本(2M tok) | 用途 |
|------|--------------------------|--------|--------------------|------|
| qwen3-max(阿里) | 2.5 / 10 | 32K | ¥11.4 | **国内主力** |
| qwen3.6-plus(阿里) | 2 / 12 | 256K | ¥11.6 | 长上下文 |
| qwen-flash(阿里) | ~0.4 / 1.6 | 32K | ¥1.84 | 轻量 |
| Doubao-Seed-2.0-Pro(字节) | ~2-4 / 6-12 | 32K | ~¥15 | 国内备选 |
| Gemini 2.5 Pro(Google) | ¥9 / ¥45 | 1M | ¥69 | 海外旗舰 |
| Gemini 2.5 Flash | ¥0.54 / ¥2.16 | 1M | ¥3.42 | 海外性价比 |
| DeepSeek V3.2 | ¥1 / ¥2(估) | 64K | ¥4 | 三方 |
| Kimi K2.6 | ~¥2 / ¥10 | 128K | ¥12 | 长上下文 |
| Claude Opus 4.7(via 代理) | ¥108 / ¥540 | 1M | ¥864 | 海外旗舰(贵) |
| Claude Sonnet 4.6 | ¥21.6 / ¥108 | 1M | ¥172 | 海外性价比 |

### LLM 选型

| 场景 | 推荐 |
|------|------|
| 中文剧本量产 | **qwen3-max** 或 DeepSeek V3.2 |
| 长篇小说一次性 ingest(> 32K tokens) | qwen3.6-plus(256K)或 Gemini Flash |
| 海外英文 / 多语言 | Gemini 2.5 Pro / Claude Sonnet 4.6 |

> **LLM 占总成本 < 0.5%**,质量优先,价格其次。

---

## 5. 全平台单部 120 分钟漫剧成本汇总

| 方案 | I2V | T2I | LLM | TTS | **单部** |
|------|-----|-----|-----|-----|---------|
| 自部署 4090(开源 5B) | Wan2.2-5B | Qwen-Image | Qwen3-7B | CosyVoice 3 | **¥43** |
| Hailuo 02 512P + 阿里外接 | Hailuo 02 | Seedream 4.5 | qwen3-max | cosyvoice-flash | **¥1,217** |
| **Seedance 2.0 Fast(fal)** | Seedance 2.0 Fast | Qwen-Image fal | qwen3-max | cosyvoice-flash | **¥1,488** |
| 混合(API + 自部署) | wan2.7 关键帧 + 自部署过渡 | API | API | 自部署 | **¥1,741** |
| **Kling 3.0 via fal** | Kling 3.0 | Qwen-Image fal | qwen3-max | cosyvoice-flash | **¥1,848** |
| 阿里 720P 节省计划 | wan2.7-i2v 720P + 7.6 折 | wan2.7 + 7.6 折 | qwen3-max + 8 折 | cosyvoice + 7.6 折 | **¥3,400** |
| 直连 Kling 3.0 std 关音画 | Kling v3 | Seedream 4.5 | qwen3-max | cosyvoice-flash | **¥3,898** |
| Vidu Q3 Pro 直连 | Vidu Q3 Pro | — | — | — | **¥4,400** |
| 直连 Kling 3.0 主流 | Kling 3.0 含音画 | Seedream 4.5 | qwen3-max | cosyvoice-flash | **¥5,626** |
| **阿里全旗舰 + 节省计划 7.6 折** | wan2.7-i2v 1080P | wan2.7-image-pro | qwen3-max | cosyvoice-plus | **¥6,061** |
| 字节豆包旗舰 | Seedance 2.0 Pro | Seedream 5.0 | Doubao Seed 2.0 | cosyvoice + 外接 | **¥7,815** |
| 阿里全旗舰按量 | wan2.7-i2v 1080P | wan2.7-image-pro | qwen3-max | cosyvoice-plus | **¥7,974** |
| **Veo 3.1 Fast** | Veo 3.1 Fast | Nano Banana Pro | Gemini 2.5 Pro | ElevenLabs | **¥8,400** |
| **Veo 3.1 Standard 旗舰** | Veo 3.1 Standard | Nano Banana Pro 4K | Gemini 2.5 Pro | ElevenLabs Multilingual | **¥21,335** |

---

## 6. 选型决策树

### 6.1 按发行渠道

```
发行渠道?
├─ 国内抖音 / 快手 / 视频号
│   ├─ 量产(50+ 部/月)→ 阿里全栈 + 节省计划 7.6 折(¥6,061/部)
│   ├─ 性价比 → Kling 3.0 via fal + 阿里外接 LLM/TTS(¥1,848/部)
│   └─ 中文海报为主 → 字节豆包 Seedream 5.0 + Seedance 1.5(¥3,000/部)
│
├─ 海外 TikTok / YouTube / Reels
│   ├─ 旗舰(精品) → Veo 3.1 Standard + Nano Banana Pro(¥21,335/部)
│   ├─ 量产 → Veo 3.1 Fast 或 Seedance 2.0 Fast(¥1,488-8,400/部)
│   └─ 多语言配音 → ElevenLabs Multilingual + Veo 3.1 Fast
│
└─ 双渠道
    └─ 阿里基线 + 海外渠道走 fal/Google 同模型不同 instance
```

### 6.2 按月出片量

| 量级 | 最佳方案 | 单部成本 |
|------|---------|---------|
| 试运行 / < 5 部 | fal.ai Kling 3.0 | ~¥1,850 |
| 5-30 部 | fal.ai 主力 / 阿里按量 | ¥1,850-6,000 |
| 30-100 部 | 阿里节省计划 7.6 折 | ¥6,061 |
| 100-500 部 | 阿里节省计划 7.0 折 + 自部署 TTS/分镜图 | ~¥3,500 |
| 500-2000 部 | 全自部署 + 关键帧 API | ~¥500-1,700 |
| > 2000 部 | 全自部署 + 集群 | ¥43-414 |

### 6.3 按场景类型

| 场景 | I2V 推荐 | T2I 推荐 | TTS 推荐 |
|------|---------|---------|---------|
| 都市言情 / 人像运镜 | **Kling 3.0** | Seedream 5.0 | CosyVoice |
| 仙侠 / 奇幻 / 大场景 | Seedance 2.0 / wan2.7 | wan2.7-image-pro | CosyVoice |
| 校园 / 日常 | Hailuo 02 / Seedance 1.5 | Seedream 4.5 | CosyVoice flash |
| 时尚 / 海报感 | Veo 3.1 / Nano Banana | Nano Banana Pro | ElevenLabs |
| 草样 / 内审 | wan2.2-i2v-flash 480P | wan2.7-image | cosyvoice-flash |

---

## 7. 关键判断

1. **I2V 决定全局** — 总成本 90% 在这里,选型必须慎重
2. **TTS / LLM 不必降档** — 占比 < 1%,直接用最贵的没影响
3. **聚合平台(fal.ai)是中小规模最优解** — 单点接入 600+ 模型,Kling/Veo 节约 50-80%
4. **阿里 + 节省计划是国内合规量产首选** — 6.2-8 折 + 全栈 + OSS + 备案
5. **海外发行才需要 Google / ElevenLabs** — 国内场景不要为了"旗舰"付海外溢价
6. **自部署是 > 200 部/月 的终极方案** — 但要算上 ML 工程师人力成本
7. **跨平台混搭最划算** — 比如 fal 跑 I2V + 阿里跑 LLM/TTS + 自部署跑分镜图,成本可拉到 ¥1,700/部

---

## 8. ManjuForge 内置 family 支持矩阵

| 平台 | family 前缀 | 内置 | 凭据 env | 通过 DashScope |
|------|------------|------|---------|---------------|
| 阿里万相 | `wan2.7-` / `wan2.6-` / `wan2.5-` / `wan2.2-` | ✅ | DASHSCOPE_API_KEY | 默认 |
| 阿里千问图像 | `qwen-image` | ✅ | 同上 | 默认 |
| 阿里 CosyVoice | `cosyvoice` | ✅ | 同上 | 默认 |
| 可灵 | `kling-` | ✅ | KLING_ACCESS_KEY + KLING_SECRET_KEY | 可选 |
| Vidu | `vidu` | ✅ | VIDU_API_KEY | 可选 |
| Pixverse | `pixverse-` | ✅ | PIXVERSE_API_KEY | 可选 |
| 豆包 Seedance | `doubao-seedance-` | ✅ | DOUBAO_API_KEY | ❌ vendor only |
| 豆包 Seedream | `doubao-seedream-` | ✅ | 同上 | ❌ |
| MiniMax Hailuo | `hailuo-` / `minimax-hailuo-` | ✅ | MINIMAX_API_KEY / HAILUO_API_KEY | ❌ |
| Google Gemini | `gemini-` / `nano-banana` / `veo-` | ✅ | GOOGLE_API_KEY / GEMINI_API_KEY | ❌ |
| BFL FLUX.2 | `flux-2` | ✅ | BFL_API_KEY | ❌ |
| OpenAI GPT Image | `gpt-image-` | ✅ | OPENAI_API_KEY | ❌ |
| ElevenLabs | `eleven_` | ✅ | ELEVENLABS_API_KEY | ❌ |
| Fish Audio | `fish-` | ✅ | FISH_AUDIO_API_KEY | ❌ |
| Cartesia | `sonic-` | ✅ | CARTESIA_API_KEY | ❌ |
| fal.ai 聚合 | `fal-` | ✅ | FAL_API_KEY | ❌ |

> **添加新供应商:** 见 CLAUDE.md "Adding a new vendor" 段。

---

## 9. 参考链接

- 各平台单独文档见顶部"配套文档"
- [AI Video API 价格对比 2026(DevTk)](https://devtk.ai/en/blog/ai-video-generation-pricing-2026/)
- [Cheapest AI Video Generation APIs 2026(Atlas)](https://www.atlascloud.ai/blog/guides/cheapest-ai-video-generation-api-2026)
- [Best AI Video Models 2026(TeamDay)](https://www.teamday.ai/blog/best-ai-video-models-2026)
- [AI Video Generation Pricing(BuildMVPFast)](https://www.buildmvpfast.com/api-costs/ai-video)
