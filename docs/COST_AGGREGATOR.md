# 聚合平台(fal.ai / OpenRouter / Atlas Cloud)成本核算手册

> 适用范围:ManjuForge Studio 通过**聚合平台**统一调用 Kling / Veo / Seedance / Hailuo / Vidu 等多家视频模型。
> 凭据 `FAL_API_KEY`(fal.ai),vendor-direct。
> 价格数据更新于:**2026-05**。
> 汇率:**1 USD ≈ ¥7.2**。

---

## 1. 平台概览

| 平台 | 定位 | 接入方式 | ManjuForge 支持 |
|------|------|---------|----------------|
| **fal.ai** | 业内规模最大的聚合(600+ 模型) | OpenAI 兼容 / 自家 SDK | ✅ family `fal-` |
| OpenRouter | LLM 为主,部分图像/视频 | OpenAI 兼容 | ⚠️ 需手动加 family |
| Atlas Cloud | 视频专精,统一 API | OpenAI 兼容 | ⚠️ 需手动加 family |
| Replicate | 老牌,Python-first | REST | ❌ 暂未集成 |
| 多米 API / OpenAI-HK 等 | 国内代理 | 半官方 | ⚠️ 合规风险 |

> ManjuForge 内置 `fal-` family,直接可用;其他聚合需扩展 `provider_registry.py`。

---

## 2. fal.ai 单价表(主力)

### 2.1 视频生成 I2V / T2V

| 模型 | model_id(ManjuForge) | 单价 / 秒(美元) | 人民币 | 对比官方 |
|------|---------------------|-----------------|--------|----------|
| **Kling 3.0** | `fal-kling-3.0` | **$0.029** | **¥0.21** | 官方 ¥0.96,节约 78% |
| Veo 3.1(主力档) | `fal-veo-3.1` | $0.20 | ¥1.44 | 官方 ¥2.88,节约 50% |
| Veo 3.1 Fast | `fal-veo-3.1` | $0.10 | ¥0.72 | 同官方 Fast |
| **Seedance 1.5 Pro 720P 含音频** | `fal-seedance-1.5-pro` | $0.052(¥0.26 / 5s) | **¥0.37** | 火山约 ¥0.6,节约 38% |
| Seedance 2.0 Fast(2026 新) | 不在 ManjuForge | $0.022 | **¥0.16** | **业界最低** |
| Sora 2 | 不在 ManjuForge | $0.087 | ¥0.63 | OpenAI 官方 ~$0.10 |
| Hailuo 02 Standard 768P | 不在 ManjuForge | $0.045 | ¥0.32 | — |
| Hailuo 02 Standard 512P | 不在 ManjuForge | $0.017 | ¥0.12 | — |
| Wan 2.6 I2V | 不在 ManjuForge | $0.05-0.10 | ¥0.36-0.72 | DashScope ¥0.6-1.0 |
| Pixverse v4 1080P | — | $0.40 / 5s | ¥0.58 / 秒 | — |
| Pixverse v4 720P | — | $0.20 / 5s | ¥0.29 / 秒 | — |

### 2.2 图像生成(部分)

| 模型 | 单价 / 张(美元) | 人民币 |
|------|----------------|--------|
| FLUX.1 Dev | $0.025 | ¥0.18 |
| FLUX.2 Pro | $0.04 | ¥0.29 |
| Qwen-Image-2.0 | $0.03 | ¥0.22 |
| Nano Banana 2 1K | $0.067 | ¥0.48 |

### 2.3 计费规则

- **按完成计费**,失败任务不扣费(比官方更友好)
- **并发限制** 默认 5-20,可申请升级
- **批量任务**(Batch API)部分模型支持,折扣 5-15%
- **没有节省计划 / 长期承诺折扣**,纯按量

---

## 3. 单部 120 分钟漫剧 — 走 fal.ai 的成本

**项目假设(同 COST_ALIYUN.md):** 1440 帧 / 7200 秒 / 70 静态资产

### 3.1 方案 A:Kling 3.0 极致省钱

| 阶段 | 模型 | 用量 | 成本 |
|------|------|------|------|
| LLM(外接阿里) | qwen3-max | — | ¥0.54 |
| T2I 静态资产 | Qwen-Image-2.0 via fal | 70 × ¥0.22 | ¥15.40 |
| T2I 分镜图 | Qwen-Image-2.0 via fal | 1,440 × ¥0.22 | ¥316.80 |
| **I2V Kling 3.0** | $0.029/秒 | 7,200 × ¥0.21 | **¥1,512** |
| TTS(外接阿里) | cosyvoice-v3-flash | 48K 字符 | ¥3.84 |
| **合计** | | | **¥1,848** |

### 3.2 方案 B:Seedance 2.0 Fast 业界最低(暂未集成 ManjuForge)

| 阶段 | 用量 | 成本 |
|------|------|------|
| 外接 LLM / T2I / TTS | | ¥336 |
| **I2V Seedance 2.0 Fast** | $0.022/秒 × 7,200 | **¥1,152** |
| **合计** | | **¥1,488** |

### 3.3 方案 C:Veo 3.1 海外平台

| 阶段 | 用量 | 成本 |
|------|------|------|
| 外接 | | ¥336 |
| **I2V Veo 3.1** | $0.20/秒 × 7,200 | **¥10,368** |
| **合计** | | **¥10,704** |

### 3.4 方案 D:Hailuo 02 Standard 512P(极致省钱)

| 阶段 | 用量 | 成本 |
|------|------|------|
| 外接 | | ¥336 |
| **I2V Hailuo 02 512P** | $0.017/秒 × 7,200 | **¥881** |
| **合计** | | **¥1,217** |

---

## 4. 与直连官方对比

| I2V 模型 | 官方直连 | fal.ai 聚合 | 节约 |
|---------|---------|------------|------|
| Kling 3.0 | ¥0.96/秒(含音画) | ¥0.21/秒 | **78%** |
| Veo 3.1 Standard | ¥2.88/秒 | ¥1.44/秒 | **50%** |
| Seedance 1.5 Pro | 火山按 token 计 ¥0.6/秒 | ¥0.37/秒 | 38% |
| Hailuo 02 | MiniMax 直连 / 第三方 | ¥0.32/秒(768P) | 视基线 |
| Wan 2.6 I2V 720P | 阿里 ¥0.6/秒 | ¥0.36-0.72/秒 | 不显著 |

> 总结:**Kling / Veo 等海外重模型走 fal.ai 节约 50-80%**,阿里万相走 fal.ai 没显著优势。

---

## 5. 何时该用聚合平台

### ✅ 适合 fal.ai 的场景

1. **跨多模型 A/B 测试** — 一个凭据测 Kling / Veo / Seedance / Hailuo
2. **海外重模型走 fal 省钱** — Kling 3.0 / Veo 3.1
3. **国内合规要求低,海外发行** — fal.ai 在新加坡 / 美东
4. **快速 PoC**,不想开多个账号
5. **失败重试容忍度低** — fal.ai 失败不扣费

### ❌ 不适合 fal.ai 的场景

1. **国内合规优先**(短视频内审 / 备案)— 走阿里 / 字节
2. **量产 > 200 部/月** — 直连官方 + 节省计划 / 商务谈判更划算
3. **依赖 OSS / CDN / 中文内审** — 阿里全栈更顺
4. **数据合规要求严** — 海外节点存在出海合规风险

---

## 6. 聚合平台间对比

| 维度 | **fal.ai** | OpenRouter | Atlas Cloud |
|------|----------|------------|-------------|
| 模型覆盖 | 600+(视频 / 图像 / 音频 / LLM) | 200+(主要 LLM,少量图像) | 视频 / 图像专精 |
| 价格 | 最透明,按秒/张 | 透明 | 中等 |
| Kling 3.0 单价 | $0.029/秒 | ~$0.075/秒 | $0.126-0.168/秒 |
| 接入难度 | OpenAI 兼容 + 自家 SDK | OpenAI 兼容 | OpenAI 兼容 |
| ManjuForge 内置 | ✅ family `fal-` | ❌ | ❌ |
| 失败计费 | 不计 | 视模型 | 视模型 |
| 中国 IP 访问 | 需海外节点 | 需海外节点 | 部分国内可访问 |

---

## 7. ModelInstance 配置

### 7.1 .env

```bash
FAL_API_KEY=fal-xxx
```

### 7.2 模型实例

| 类型 | display_name | model_name | base_url |
|------|-------------|-----------|---------|
| I2V | fal · Kling 3.0 | `fal-kling-3.0` | `https://fal.run/v1` |
| I2V | fal · Veo 3.1 | `fal-veo-3.1` | 同上 |
| I2V | fal · Seedance 1.5 Pro | `fal-seedance-1.5-pro` | 同上 |
| T2I | fal · Qwen-Image-2.0 | `fal-qwen-image-2.0` | 同上 |

> 仅这 3 个 I2V 是 ManjuForge 内置;Hailuo / Vidu / Seedance 2.0 Fast 需扩展 `provider_registry.py`。

---

## 8. 关键判断

| 月出片量 | 推荐路径 |
|---------|---------|
| < 10 部 | fal.ai + Kling 3.0(单部 ~¥1,850) — 一个凭据全搞定,无需谈判 |
| 10 – 50 部 | fal.ai 主力 + 阿里 LLM/TTS | ~¥1,850 / 部 |
| 50 – 200 部 | 选一家直连官方 + 节省计划(阿里 6,061 / 直连 Kling 3,900) | 比 fal 高但失败率低 |
| > 200 部 | 直连 + 商务协议 / 自部署 | fal 受并发限制,需协商 |

**fal.ai 是中小规模生产 + 海外重模型的最佳跳板**,生产稳定性优于直连小厂(因为 fal 做了重试 / 失败不计费 / 统一限速)。

---

## 9. 参考链接

- [fal.ai 模型与价格](https://fal.ai/pricing)
- [fal.ai 10 Best Image-to-Video Generators 2026](https://fal.ai/learn/tools/ai-image-to-video-generators)
- [DevTk.AI 视频 API 价格对比 2026](https://devtk.ai/en/blog/ai-video-generation-pricing-2026/)
- [Atlas Cloud 最便宜 AI 视频 API 对比](https://www.atlascloud.ai/blog/guides/cheapest-ai-video-generation-api-2026)
- [TeamDay AI API 对比 2026](https://www.teamday.ai/blog/ai-image-video-api-providers-comparison-2026)
