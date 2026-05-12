# Google(Veo + Gemini Image)成本核算手册

> 适用范围:ManjuForge Studio 使用 **Google AI / Vertex AI** 的 Veo(视频)+ Gemini Image / Nano Banana(图像)。
> 凭据 `GOOGLE_API_KEY` 或 `GEMINI_API_KEY`,vendor-direct。
> 价格数据更新于:**2026-05**(以 ai.google.dev 官方为准)。
> 汇率:**1 USD ≈ ¥7.2**(本文档统一采用)。

---

## 1. 旗舰模型清单

| 阶段 | 旗舰模型 | model_id | 美元单价 | 人民币 |
|------|---------|---------|---------|--------|
| **I2V / T2V(旗舰)** | Veo 3.1 Standard | `veo-3.1` | $0.40 / 秒 | **¥2.88 / 秒** |
| I2V / T2V(快速档) | Veo 3.1 Fast(含音频) | `veo-3.1-fast` | $0.15 / 秒 | **¥1.08 / 秒** |
| I2V / T2V(无音频) | Veo 3.1 Fast | `veo-3.1-fast` | $0.10 / 秒 | **¥0.72 / 秒** |
| **T2I 旗舰** | Nano Banana Pro(Gemini 3 Pro Image) | `nano-banana-pro` | $0.134 / 张(1K/2K) / $0.24 / 张(4K) | **¥0.96 / ¥1.73** |
| T2I 性价比 | Nano Banana 2(Gemini 3.1 Flash Image) | `nano-banana-2` | $0.067(1K)/ $0.101(2K)/ $0.151(4K) | **¥0.48 / ¥0.73 / ¥1.09** |
| T2I 极轻量 | Gemini 3.1 Flash Image 512px | `gemini-3.1-flash-image` | $0.045 / 张 | **¥0.32** |
| LLM | Gemini 2.5 Pro / Flash | `gemini-2.5-pro` | $1.25 / $0.075 per M tok | **¥9 / ¥0.54** |
| TTS | 无原生 — 需外接 | — | — | — |

### 1.1 Veo 3.1 详细分档

| 模型 | 音频 | 单价 / 秒 |
|------|------|----------|
| Veo 3.1 Standard | ✅ | $0.40($0.10/秒 via 三方代理) |
| Veo 3.1 Fast | ✅ | $0.15(官方);$0.10(fal.ai / Replicate) |
| Veo 3.1 Fast | ❌ 无音频 | $0.10(Vertex AI) |

> 典型 8 秒视频(Veo 3.1 Standard)= **$3.20 ≈ ¥23**(单段),适合**质量旗舰**而非量产。

### 1.2 Nano Banana 系列详细

| 模型 | 分辨率 | 单张 / 批量 |
|------|--------|-----------|
| Gemini 3.1 Flash Image | 512px | $0.045 / $0.034(批量) |
| Gemini 3.1 Flash Image | 1024px | $0.067 / $0.050(批量) |
| Gemini 3.1 Flash Image | 2048px | $0.101 / $0.076(批量) |
| Gemini 3.1 Flash Image | 4096px | $0.151 / — |
| Nano Banana Pro | 1K/2K | $0.134(原生) |
| Nano Banana Pro | 4K | $0.24(原生) |

> **批量折扣(Batch API)直接打 7.5 折**,适合 ManjuForge 分镜图这种大批量场景。

### 1.3 Gemini Image 多参考图能力

| 模型 | 最大参考图数 | 角色一致性 |
|------|------------|----------|
| Gemini 3.1 Flash Image | **14 张** | 业内最强性价比 |
| Nano Banana Pro | 14 张 | 业内最强综合(Elo 1220) |
| Nano Banana 2 | 14 张 | Elo 1261 |

---

## 2. 单部 120 分钟漫剧成本

**项目假设(同 COST_ALIYUN.md):** 1440 帧 / 7200 秒 / 70 静态资产 / 48K 计费字符

### 2.1 方案 A:Veo 3.1 Standard 旗舰(最贵)

| 阶段 | 模型 | 用量 | 成本 |
|------|------|------|------|
| LLM | Gemini 2.5 Pro | ~2M tok | ~¥10 |
| T2I 静态资产 | Nano Banana Pro 2K | 70 张 | **¥67.20** |
| T2I 分镜图(批量) | Gemini 3.1 Flash Image 1024 | 1,440 张 × $0.050 | **¥518.40** |
| **I2V Veo 3.1 Standard** | $0.40/秒 含音频 | 7,200 秒 × ¥2.88 | **¥20,736.00** |
| TTS(外接) | cosyvoice-v3-flash | 48K 字符 | ¥3.84 |
| **合计** | | | **¥21,335** |

### 2.2 方案 B:Veo 3.1 Fast(性价比)

| 阶段 | 模型 | 用量 | 成本 |
|------|------|------|------|
| LLM + T2I + TTS(同上) | | | ¥599 |
| **I2V Veo 3.1 Fast 含音频** | $0.15/秒 | 7,200 × ¥1.08 | **¥7,776** |
| **合计** | | | **¥8,375** |

### 2.3 方案 C:Veo 3.1 Fast 无音频 + 三方代理(最便宜路径)

| 阶段 | 用量 | 成本 |
|------|------|------|
| LLM + T2I + TTS | | ¥599 |
| **I2V Veo 3.1 Fast 无音频** | $0.10/秒 × 7,200 | **¥5,184** |
| **合计** | | **¥5,783** |

---

## 3. 与阿里基线对比

| 维度 | 阿里 wan2.7 | **Google Veo 3.1** |
|------|-------------|---------------------|
| I2V 1080P + 音频 单价 | ¥1.0/秒 | **¥2.88/秒(Standard)** / ¥1.08/秒(Fast) |
| I2V 性价比档 | ¥0.6/秒(720P) | ¥0.72/秒(Fast 无音频) |
| T2I 旗舰单价 | ¥0.5/张 | ¥0.96/张(Nano Banana Pro 2K) |
| 多参考图 | wan2.7-pro 支持 | **Gemini 14 张参考(业内最强)** |
| 中文文字渲染 | ✅ 优秀 | ⚠️ 弱于阿里 / 豆包 |
| 4K 原生输出 | ❌ | ✅ Nano Banana Pro / Veo 3.1 |
| 音频原生 | ✅ | ✅ Veo 3.1 含 cinematic 音效 |
| 节省计划 | ✅ 6.2-8 折 | ❌ 无标准化折扣 |
| 国内合规 / 备案 | ✅ 默认合规 | ⚠️ 需海外节点 / VPN / 出海备案 |
| 单部 120 分钟成本(主流档) | ¥6,061(7.6 折) | **¥8,375(Fast)/ ¥21,335(Standard)** |

### 选 Google 的场景

- **海外发布 / 海外平台**(YouTube / TikTok 海外版 / Reddit / Discord)
- 需要 **4K 原生输出 / 业内最强多参考图角色一致性**
- 客户付费意愿高,接受 ¥2.88/秒 旗舰单价
- 已经在 Google Cloud 生态(Vertex AI 集成)

### 不选 Google 的场景

- 中文短剧(中文文字渲染弱于阿里 / 豆包)
- 国内发布(需备案 / 监管要求)
- 量产场景(单价是阿里 / 字节的 2-3 倍)
- 需要全栈一站式(Google 也缺 TTS 旗舰)

---

## 4. 优惠机制

| 渠道 | 折扣 |
|------|------|
| **Batch API**(异步批量) | **7.5 折**(分镜图大批量首选) |
| Google AI Studio 个人套餐 | $7.99-$249.99/月,API 不互通 |
| Vertex AI 企业承诺 | 商务谈判 |
| 三方代理(fal.ai / Replicate / OpenRouter) | Veo 3.1 Fast 可下探至 $0.10/秒(无音频) |

### Batch API 实际效果

ManjuForge 分镜图是天然的 Batch 场景(60 分镜 × 24 帧不需要实时):

| 单批 | 单价 |
|------|------|
| 实时 1K | $0.067 |
| **Batch 1K** | **$0.050(7.5 折)** |
| 实时 2K | $0.101 |
| **Batch 2K** | **$0.076(7.5 折)** |

1,440 张分镜图 × 0.017 美元 节约 = **节省 $24.5 ≈ ¥176 / 部**

---

## 5. ModelInstance 配置

### 5.1 .env

```bash
# 二选一,二者等价
GOOGLE_API_KEY=AIza...
GEMINI_API_KEY=AIza...
```

### 5.2 模型实例

| 类型 | display_name | model_name | base_url |
|------|-------------|-----------|---------|
| LLM | Gemini 2.5 Pro | `gemini-2.5-pro` | `https://generativelanguage.googleapis.com/v1beta/openai` |
| T2I | Nano Banana Pro | `nano-banana-pro` | 同上 |
| I2I | Gemini 3.1 Flash Image | `gemini-3.1-flash-image` | 同上 |
| I2V(质量) | Veo 3.1 Standard | `veo-3.1` | 同上 |
| I2V(快速) | Veo 3.1 Fast | `veo-3.1-fast` | 同上 |
| TTS(外接) | CosyVoice / ElevenLabs | — | — |

### 5.3 走 fal.ai 聚合(单价最低)

```bash
FAL_API_KEY=xxx
```

| 类型 | model_name |
|------|-----------|
| I2V | `fal-veo-3.1` |

---

## 6. 关键判断

| 场景 | 推荐路径 | 单部成本 |
|------|---------|---------|
| 国内中文短剧量产 | ❌ 不推荐用 Google | — |
| 海外英文 / 多语言短剧 | Veo 3.1 Fast + Batch | ~¥8,400 |
| 极致旗舰画质(单部精品) | Veo 3.1 Standard + Nano Banana Pro | ~¥21,300 |
| 单镜头质量测试 / 海报 | Nano Banana Pro 4K | ~¥1.73/张 |
| Veo 3.1 通过 fal.ai 节约 | $0.20/秒 vs $0.40 | 省 50% |

**核心:** Google 是**质量天花板**,不是性价比之选。ManjuForge 用 Google 的合理场景是**海外发行 + 精品制作**,日常量产仍走阿里 / 字节。

---

## 7. 参考链接

- [Gemini API 官方定价](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini 3.1 Flash Image 文档](https://ai.google.dev/gemini-api/docs/image-generation)
- [Veo 3.1 定价指南(2026)](https://www.aifreeapi.com/en/posts/veo-3-1-pricing)
- [Nano Banana Pro 2026 价格](https://pricepertoken.com/pricing-page/model/google-gemini-3-pro-image-preview)
- [Gemini 3.1 Flash 各分辨率单价](https://blog.laozhang.ai/en/posts/gemini-3-1-flash-image-preview)
