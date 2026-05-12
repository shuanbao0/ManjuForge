# 可灵 AI(Kling)成本核算手册

> 适用范围:ManjuForge Studio 使用 **快手可灵 AI(Kling)** vendor-direct 模式生成视频。
> 凭据 `KLING_ACCESS_KEY` + `KLING_SECRET_KEY`,`KLING_PROVIDER_MODE=vendor`。
> 价格数据更新于:**2026-05**(以可灵开放平台为准)。

---

## 1. 旗舰模型清单

| 模型 | model_id | 能力 | 备注 |
|------|---------|------|------|
| **Kling 3.0(2026 旗舰)** | `kling-v3.0` | I2V / T2V | 多镜头叙事 + 主体一致性 |
| **Kling v3** | `kling-v3` | I2V / T2V | 当前主力 |
| Kling 2.1 Master | `kling-2.1-master` | I2V / T2V | 电影级镜头,多人同框 |
| Kling 2.0 | `kling-2.0` | I2V / T2V | 上一代 |
| Kling-v3-image-generation | — | T2I | 1K / 2K |

> 可灵**只做视频和图像**,没有 LLM / TTS,需外接(LLM 推荐阿里 qwen3-max,TTS 推荐 CosyVoice / ElevenLabs)。

---

## 2. 单价表

### 2.1 vendor-direct(可灵官方 API)

| 模型 / 模式 | 音画同步 | 价格 / 秒(¥) |
|-----------|---------|--------------|
| Kling v3 / std | 关闭 | **0.48** |
| Kling v3 / pro | 关闭 | **0.64** |
| Kling v3 / std | 开启 | **0.72** |
| Kling v3 / pro | 开启 | **0.96** |
| Kling 3.0 / std | 关闭(官方) | ~$0.075 ≈ **¥0.54** |
| Kling 3.0 / pro | (Atlas Cloud) | $0.168 ≈ **¥1.21** |
| Kling 2.1 Master | — | ~¥1.0(估) |

> 表中是 API 直连价。官方 API 比第三方代理贵约 25%,但稳定性更好。

### 2.2 通过聚合平台(fal.ai 等)

| 平台 | Kling 3.0 单价 / 秒 |
|------|--------------------|
| fal.ai | **$0.029**(¥0.21) |
| OpenRouter | ~$0.075 |
| Atlas Cloud | $0.126-0.168 |
| **DashScope(阿里转发)** | **¥0.6-1.0**(走 dashscope backend) |

> fal.ai 价格比官方便宜 ~60%,但是聚合平台限速可能更严。

### 2.3 通过 DashScope 转发(`KLING_PROVIDER_MODE=dashscope`)

| 模型 | 720P | 1080P |
|------|------|-------|
| Kling 系列(via DashScope) | 走万相同价 ¥0.6/秒 | ¥1.0/秒 |

> DashScope 把 Kling 当作万相系列同档定价,**可纳入阿里 AI 通用型节省计划折扣**,这是非常划算的路径。

### 2.4 套餐 / Credits 模式(消费者)

可灵自己也卖 Credits 套餐(面向 C 端用户),企业 API 用按量为主:

| 套餐 | 月费 | Credits | 适合 |
|------|------|---------|------|
| 大师会员 | ~¥66/月 | 660 Credits | 个人创作者 |
| 高级会员 | ~¥666/月 | 8,000 Credits | 工作室 |

> Credits 与 API 不互通,**ManjuForge 后端用 API 不能消费 Credits**。

---

## 3. 单部 120 分钟漫剧成本

**项目假设(同 COST_ALIYUN.md):** 1440 帧 / 7200 秒 / 70 静态资产

### 3.1 方案 A:Kling v3 std 关闭音画(最便宜直连)

| 阶段 | 模型 | 用量 | 成本 |
|------|------|------|------|
| LLM(外接阿里) | qwen3-max | — | ¥0.54 |
| T2I 静态资产(外接 Seedream 4.5) | doubao-seedream-4.5 | 70 张 | ¥20 |
| T2I 分镜图(外接) | doubao-seedream-4.5 | 1,440 张 | ¥418 |
| **I2V** | Kling v3 std 关音画 | 7,200 秒 × ¥0.48 | **¥3,456** |
| TTS(外接) | cosyvoice-v3-flash | 48K 字符 | ¥3.84 |
| **合计** | | | **¥3,898** |

### 3.2 方案 B:Kling 3.0 std 开音画(主流)

| 阶段 | 用量 | 成本 |
|------|------|------|
| LLM + T2I + TTS(外接) | | ¥442 |
| **I2V Kling 3.0 std with audio** | 7,200 秒 × ¥0.72 | **¥5,184** |
| **合计** | | **¥5,626** |

### 3.3 方案 C:走 fal.ai 聚合(Kling 3.0)

| 阶段 | 用量 | 成本 |
|------|------|------|
| LLM + T2I + TTS(外接) | | ¥442 |
| **I2V via fal.ai $0.029/s** | 7,200 秒 × ¥0.21 | **¥1,512** |
| **合计** | | **¥1,954** |

### 3.4 方案 D:走 DashScope 转发 + 阿里节省计划

| 阶段 | 用量 | 成本 |
|------|------|------|
| 全部 via DashScope(单一凭据) | | |
| LLM + T2I + 分镜图 + TTS | | ~¥83 |
| **I2V Kling via DashScope 1080P** | 7,200 × ¥1.0 | ¥7,200 |
| 子合计 | | ¥7,283 |
| **应用 AI 通用型节省计划 7.6 折** | | **¥5,535** |

---

## 4. 与阿里万相 / 字节豆包对比

| 维度 | 阿里 wan2.7 | 字节 Seedance 2.0 | **可灵 Kling v3** | **可灵 Kling 3.0** |
|------|--------------|-------------------|--------------------|---------------------|
| I2V 1080P 直连价 | ¥1.0/秒 | ¥1.0/秒 | ¥0.96/秒(pro+音画) | ¥1.21/秒 |
| I2V 主流档 | ¥0.6/秒(720P) | ¥1.0/秒 | **¥0.48/秒(std 无音画)** | ¥0.54/秒 |
| 走 fal.ai 最低 | — | — | — | **¥0.21/秒** |
| 走 DashScope | — | — | ¥0.6/秒(720P)+ 节省计划 | 同 |
| 多人同框 | 一般 | 一般 | **2.1 Master 最强** | **3.0 最强** |
| 人像运镜 | 一般 | 优 | **业内基准** | **业内基准** |
| 节省计划 | ✅ 阿里 AI 通用 | ❓ 商务谈 | ❌ 直连无 | ✅ via DashScope |
| 文档 / 工具 / 生态 | 阿里齐全 | 火山齐全 | 文档相对薄弱 | 同 |

### 选可灵的场景

- **人像 / 运镜 / 多人同框**是核心 — 可灵在这些维度业内最强,尤其 2.1 Master 和 3.0
- 走 **fal.ai 渠道**,单价能下探到 ¥0.21/秒(节约 80%+)
- 风格上需要**电影感 / 大片质感**

### 不选可灵的场景

- 需要全栈一站式 → 可灵只做视频 + 图像
- 需要节省计划深度折扣 → 直连可灵没有,转走 DashScope 才有

---

## 5. 优惠 / 折扣

### 直连可灵

| 机制 | 说明 |
|------|------|
| 新用户试用 | 注册即送 Credits / API 试用额度 |
| 大客户折扣 | 商务谈判 |
| 套餐(C 端) | 不适用 API 调用 |

### 通过 DashScope 转发(强烈推荐)

把 `KLING_PROVIDER_MODE` 设为 `dashscope`(默认),Kling 调用由阿里 DashScope 转发,享受:
- ✅ 阿里 AI 通用型节省计划(B 类 6.2-7.4 折)
- ✅ 单一凭据 `DASHSCOPE_API_KEY`
- ✅ 与万相 / qwen / cosyvoice 同账单
- ⚠️ 单价按阿里万相档(¥0.6/720P,¥1.0/1080P),并不比直连便宜

**性价比最高路径:**通过 fal.ai 调用 Kling 3.0,¥0.21/秒,比直连节约 80%,但无节省计划。

### 通过 fal.ai

| 套餐 | 折扣 |
|------|------|
| Pay-as-you-go | 单价 ~ $0.029/秒 (Kling 3.0) |
| Subscription | 月度套餐 / 大客户协商 |

---

## 6. ModelInstance 配置

### 6.1 方案:vendor-direct(直连可灵)

```bash
KLING_ACCESS_KEY=xxx
KLING_SECRET_KEY=xxx
KLING_PROVIDER_MODE=vendor
# 外接 LLM / TTS / T2I
DASHSCOPE_API_KEY=sk-xxx
```

### 6.2 方案:via DashScope(享节省计划)

```bash
DASHSCOPE_API_KEY=sk-xxx
# 不设 KLING_PROVIDER_MODE,默认走 dashscope
```

### 6.3 方案:via fal.ai(单价最低)

```bash
FAL_API_KEY=xxx
```

| 类型 | model_name | base_url |
|------|-----------|---------|
| I2V | `fal-kling-3.0` | https://fal.run/v1 |

---

## 7. 关键判断

| 出片量 | 推荐路径 | 单部成本 |
|--------|---------|---------|
| 小规模 / 创意试验 | fal.ai → Kling 3.0 | ~¥2,000 |
| 中等(50-200 部/月) | DashScope 转发 + 节省计划 | ~¥5,500(同价位画质 vs 万相) |
| 大规模 + 追求 Kling 独特画风 | 直连 vendor-direct + 商务谈折扣 | ~¥3,900-5,600 |

**核心结论:** Kling 不是最便宜,但**人像 / 运镜场景质量业内最强**,值得在关键剧目用。

---

## 8. 参考链接

- [Kling AI 官方文档](https://klingai.com/document-api/apiReference/)
- [可灵 AI 套餐价格(2026)](https://www.photonpay.com/hk/blog/article/kling-ai-pricing)
- [Kling 3 API 定价与集成指南](https://evolink.ai/zh/blog/kling-3-api-pricing-integration-guide)
- [fal.ai Kling 3.0 单价](https://fal.ai/models)
