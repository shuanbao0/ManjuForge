# 字节豆包 / 火山引擎成本核算手册

> 适用范围:ManjuForge Studio 使用 **字节跳动豆包(火山引擎方舟)** 的 Seedance(视频)+ Seedream(图像)端到端出片。
> 走 vendor-direct,凭据 `DOUBAO_API_KEY`,`DOUBAO_PROVIDER_MODE=vendor`。
> 价格数据更新于:**2026-05**(以火山引擎官方为准)。

---

## 1. 旗舰模型清单

| 阶段 | 旗舰模型 | model_id | 单价 |
|------|---------|---------|------|
| **I2V / T2V** | Seedance 2.0(2026 旗舰) | `doubao-seedance-2.0-pro` | **¥1.0 / 秒**(参考标价) |
| I2V 稳定档 | Seedance 1.5 Pro | `doubao-seedance-1.5-pro` | 估 ¥0.6-0.8 / 秒 |
| I2V 入门 | Seedance 1.0 Pro | `doubao-seedance-1.0-pro` | 估 ¥0.6 / 秒 |
| **T2I / I2I** | Seedream 5.0(集成实时联网搜索)| `doubao-seedream-5.0` | 估 ¥0.4 / 张 |
| T2I 性价比 | Seedream 4.5 | `doubao-seedream-4.5` | **~¥0.29 / 张**($0.04 × 7.2) |
| **LLM** | Doubao-1.5-Pro / Doubao-Seed-2.0 | `doubao-seed-2.0-pro` 等 | 见 §1.2 |
| TTS | 无原生 TTS — 需走第三方(CosyVoice / MiniMax)| | — |

> ⚠️ 火山引擎 **没有自家 TTS 旗舰**,配音需另接 阿里 CosyVoice / MiniMax Speech / ElevenLabs / Fish Audio。

### 1.1 Seedance 2.0 Token 计费规则

Seedance 2.0 按 token 计费,**视频 token 数与生成时长 / 分辨率挂钩**:

| 模式 | 单价 |
|------|------|
| **纯视频生成**(不含视频输入) | **¥46 / 百万 tokens** |
| **视频编辑**(含视频输入) | **¥28 / 百万 tokens** |
| 参考换算 | 15 秒视频 ≈ 30.888 万 tokens ≈ **¥1.0 / 秒** |

### 1.2 LLM 定价

| 模型 | 输入价 | 输出价 |
|------|--------|--------|
| Doubao-Seed-2.0-Pro | 约 ¥2-4 / 百万 tok | 约 ¥6-12 / 百万 tok |
| Doubao-1.5-Pro-32k | 约 ¥0.8 / 百万 tok | 约 ¥2 / 百万 tok |

> 实际定价以火山方舟控制台为准,本文档作预估参考。

---

## 2. 单部 120 分钟漫剧成本

**项目假设(与 COST_ALIYUN.md 一致):** 60 集 × 2 分钟 / 1440 帧 / 7200 秒 / 70 静态资产 / 48,000 计费字符配音

| 阶段 | 模型 | 用量 | 成本 |
|------|------|------|------|
| LLM 剧本/分镜 | Doubao-Seed-2.0-Pro | ~2M tok | ~¥15 |
| T2I 静态资产 | Seedream 4.5 | 70 张 | ¥20.30 |
| T2I 分镜图 | Seedream 4.5 | 1,440 张 | ¥417.60 |
| **I2V 1080P** | **Seedance 2.0 Pro** | **7,200 秒** | **¥7,200.00** |
| TTS(外接 CosyVoice) | `cosyvoice-v3-flash` | 48K 字符 | ¥3.84 |
| **合计** | | | **¥7,656.74** |

> 与阿里全旗舰 ¥7,973 几乎打平,**I2V 同价 ¥1/秒**。

#### 改用 Seedream 5.0(海报级)

把 1,440 分镜图换成 Seedream 5.0(估 ¥0.4/张):
- 分镜图:¥576(+¥158)
- 总成本 ≈ **¥7,815**

---

## 3. 与阿里基线对比

| 维度 | 阿里(wan2.7) | 豆包(Seedance 2.0) |
|------|---------------|---------------------|
| I2V 1080P 单价 | ¥1.0 / 秒 | ¥1.0 / 秒 |
| T2I 旗舰单价 | ¥0.5 / 张(wan2.7-image-pro) | ¥0.4 / 张(Seedream 5.0) |
| TTS 是否自家 | ✅ CosyVoice | ❌ 需外接 |
| 节省计划 | ✅ AI 通用 6.2-8 折 | ❓ 火山有"先享后付"年度折扣 |
| 中文文字渲染 | wan2.7-pro 较强 | Seedream 5.0 业内最强 |
| 多镜头叙事 | wan2.7 较弱 | **Seedance 2.0 多镜头业内首发** |
| 唇音同步 | ✅ wan2.7-i2v 有声 | ✅ Seedance 2.0 原生音画 |

### 选豆包的场景

- 需要**多镜头叙事**(同一帧切换机位)— Seedance 2.0 是 2026 唯一原生支持
- **海报 / 中文文字渲染**为核心 — Seedream 5.0 业界第一
- 已经在火山引擎生态(其他业务也在火山上)
- 不依赖自家 TTS(可接 ElevenLabs / CosyVoice / Fish)

### 选阿里的场景

- 需要**全栈一站式**(LLM + T2I + I2V + TTS 一个凭据)
- 需要 **AI 通用型节省计划**深度折扣(6.2-8 折)
- 有 OSS 镜像 / CDN 需求

---

## 4. 火山引擎的优惠机制

火山引擎方舟提供:

| 机制 | 说明 | 折扣 |
|------|------|------|
| **新用户免费额度** | Seedance 2.0 / Seedream 5.0 各 50 万 tokens | 一次性 |
| **TPS 套餐包** | 按 token 包预付 | 8-9 折 |
| **企业框架协议** | 商务谈判,年度承诺 | 6-7 折(参考) |
| 春节 / 双十一 等促销 | 不定期 | 5-7 折 |

> 火山没有像阿里那样标准化的"AI 通用型节省计划"档位表,**主要靠商务谈判**。月用量 ≥ ¥10K 建议联系火山销售。

---

## 5. ModelInstance 配置

### 5.1 .env

```bash
DOUBAO_API_KEY=xxx
DOUBAO_PROVIDER_MODE=vendor
# TTS 外接阿里
DASHSCOPE_API_KEY=sk-xxx
```

### 5.2 模型实例

| 类型 | display_name | model_name | base_url |
|------|-------------|-----------|---------|
| LLM | Doubao Seed 2.0 Pro | `doubao-seed-2.0-pro` | 火山方舟 OpenAI 兼容端点 |
| T2I | Seedream 5.0 | `doubao-seedream-5.0` | 同上 |
| I2I | Seedream 5.0 | `doubao-seedream-5.0` | 同上 |
| I2V | Seedance 2.0 Pro | `doubao-seedance-2.0-pro` | 同上 |
| TTS(外接) | CosyVoice v3 Flash | `cosyvoice-v3-flash` | DashScope |

---

## 6. 关键判断

- **I2V 单价与阿里持平**,选豆包主要是为了 Seedance 2.0 的**多镜头 + 原生音画**和 Seedream 5.0 的**海报级中文渲染**
- **TTS 是短板**,必须外接(推荐 CosyVoice 走阿里,或 ElevenLabs / Fish Audio 走海外)
- **节省机制不如阿里成熟**,需要商务对接
- 不适合**完全自助、小规模、追求开箱即用**的场景 → 此时选阿里更省心

---

## 7. 参考链接

- [火山引擎方舟模型价格](https://www.volcengine.com/docs/82379/1544106)
- [Seedance 2.0 API 接入指南](https://www.volcengine.com/article/42387)
- [Seedance 2.0 / Seedream 5.0 免费体验](https://exp.volcengine.com/ark?launch=seedance-2-0)
- [字节 Seedance 2.0 ¥1/秒 定价](https://news.qq.com/rain/a/20260304A07QZ400)
