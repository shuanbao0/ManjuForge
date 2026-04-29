# Provider endpoint registry: {provider_key: default_base_url}
PROVIDER_DEFAULTS = {
    "DASHSCOPE": "https://dashscope.aliyuncs.com",
    "KLING": "https://api-beijing.klingai.com/v1",
    "VIDU": "https://api.vidu.cn/ent/v2",
}


def get_provider_base_url(provider: str, default: str = None) -> str:
    """Get base URL for a provider. Convention: reads ``{PROVIDER}_BASE_URL``
    from the current request's credentials, falling back to env / default.
    """
    from src.runtime import get_cred  # local import keeps import cycle safe
    env_key = f"{provider.upper()}_BASE_URL"
    fallback = default or PROVIDER_DEFAULTS.get(provider.upper(), "")
    return (get_cred(env_key) or fallback).rstrip("/")
