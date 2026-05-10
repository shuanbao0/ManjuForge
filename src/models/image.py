from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import base64
import mimetypes
import os
import time
import requests
from http import HTTPStatus
import dashscope
from dashscope import ImageSynthesis
from ..utils import get_logger
from ..utils.endpoints import get_provider_base_url
from ..utils.media_refs import MEDIA_REF_UNKNOWN, classify_media_ref
from ..utils.oss_utils import OSSImageUploader
from ..utils.provider_media import resolve_media_input
from ..utils.provider_registry import resolve_provider_backend

logger = get_logger(__name__)

class ImageGenModel(ABC):
    """Abstract base class for image generation models."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, output_path: str, **kwargs) -> Tuple[str, float]:
        """
        Generates an image from a prompt.
        
        Args:
            prompt: The input text prompt.
            output_path: The path to save the generated image.
            **kwargs: Additional arguments.
            
        Returns:
            A tuple containing:
            - The path to the generated image file.
            - The duration of the API generation process in seconds.
        """
        pass

class WanxImageModel(ImageGenModel):
    def __init__(self, config):
        super().__init__(config)
        self.params = config.get('params', {})

    @property
    def api_key(self):
        from src.runtime import get_cred
        api_key = get_cred("DASHSCOPE_API_KEY")
        if not api_key:
            logger.warning("Dashscope API Key not found in config or environment variables.")
        return api_key

    @staticmethod
    def _classify_dashscope_family(model_name: str) -> str:
        """Map a DashScope image model name to the API family it lives on.

        Returns one of:
          - ``"multimodal_sync"``: ``/api/v1/services/aigc/multimodal-generation/generation``
            (sync). Covers ``wan2.6-t2i`` and the entire ``qwen-image`` line
            (qwen-image, qwen-image-plus, qwen-image-edit, qwen-image-2.0,
            qwen-image-2.0-pro). Both T2I and I2I-edit variants share this.
          - ``"image_gen_async"``: ``/api/v1/services/aigc/image-generation/generation``
            (async, returns task_id and polls). Covers ``wan2.6-image`` and the
            ``wan2.5-*`` preview family.
          - ``"legacy_sdk"``: anything else. Falls through to the deprecated
            ``ImageSynthesis.call()`` path which only serves older models like
            ``wanx-v1``. Modern models routed here will surface DashScope's
            ``"url error"`` / ``InvalidParameter`` rejections.

        See ``CLAUDE.md`` and the DashScope reference docs for the per-family
        endpoint details.
        """
        if not model_name:
            return "legacy_sdk"
        n = model_name.lower()
        # wan2.7-image / wan2.7-image-pro share the same multimodal-generation
        # endpoint + ``input.messages.content`` shape as wan2.6-t2i / qwen-image.
        # Reference image goes in as ``{"image": "<url>"}`` content blocks.
        if n.startswith("wan2.7-image") or n == "wan2.6-t2i" or n.startswith("qwen-image"):
            return "multimodal_sync"
        if n == "wan2.6-image" or n.startswith("wan2.5-"):
            return "image_gen_async"
        return "legacy_sdk"

    def _configure_dashscope_sdk(self) -> None:
        """Apply per-call dashscope SDK globals.

        - ``dashscope.api_key`` always comes from the active ModelInstance
          (or env fallback).
        - ``dashscope.base_http_api_url`` comes from ``instance.base_url`` when
          configured. Without this plumbing, the user-facing "Base URL" field
          in Settings would silently no-op on the SDK path. ``base_http_api_url``
          expects the ``/api/v1`` suffix; we append it if absent so users can
          paste either ``https://dashscope.aliyuncs.com`` or
          ``https://dashscope.aliyuncs.com/api/v1``.
        """
        dashscope.api_key = self.api_key
        try:
            from src.runtime import current_instance
            inst = current_instance()
            base = getattr(inst, "base_url", None) if inst else None
            if base:
                base = base.rstrip("/")
                if not base.endswith("/api/v1"):
                    base = f"{base}/api/v1"
                dashscope.base_http_api_url = base
        except Exception as e:
            logger.debug(f"Could not apply instance.base_url to dashscope SDK: {e}")

    def generate(self, prompt: str, output_path: str, ref_image_path: str = None, ref_image_paths: list = None, model_name: str = None, **kwargs) -> Tuple[str, float]:
        # Determine model based on whether reference image is provided
        # Support both single path (legacy) and list of paths

        all_ref_paths = []
        if ref_image_path:
            all_ref_paths.append(ref_image_path)
        if ref_image_paths:
            all_ref_paths.extend(ref_image_paths)
            
        # Remove duplicates
        all_ref_paths = list(set(all_ref_paths))
        # Model selection: ``model_name`` is resolved upstream from the
        # bound ModelInstance (T2I when no refs, I2I when refs are
        # supplied) and passed in explicitly. No params/literal fallback —
        # if it's missing the call must fail so the user configures an
        # instance.
        from .instance import InstanceType as _IT, required_model_name
        final_model_name = required_model_name(
            _IT.I2I if all_ref_paths else _IT.T2I,
            override=model_name,
        )

        if all_ref_paths:
            logger.info(f"Using I2I model: {final_model_name} with {len(all_ref_paths)} reference images")
        else:
            logger.info(f"Using T2I model: {final_model_name}")

        size = kwargs.pop('size', self.params.get('size', '1280*1280'))
        n = kwargs.pop('n', self.params.get('n', 1))
        negative_prompt = kwargs.pop('negative_prompt', None)
        # model_name is already handled above, remove from kwargs if present
        kwargs.pop('model_name', None)
        
        # Determine reference image limit based on model. wan2.6-image and
        # the qwen-image edit/2.0 variants accept up to 4 refs; legacy models
        # cap at 3.
        if final_model_name == 'wan2.6-image' or final_model_name.startswith('qwen-image'):
            ref_limit = 4
        else:
            ref_limit = 3
        if len(all_ref_paths) > ref_limit:
            logger.warning(f"Limiting reference images from {len(all_ref_paths)} to {ref_limit} for model {final_model_name}")
            all_ref_paths = all_ref_paths[:ref_limit]
        
        logger.info(f"Starting image generation...")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Model: {final_model_name}, Size: {size}, N: {n}")

        # Per-call SDK config: API key + (optional) base URL from the
        # currently-bound ModelInstance. The dashscope SDK reads these as
        # globals, so we must set them right before each call.
        self._configure_dashscope_sdk()

        try:
            api_start_time = time.time()
            family = self._classify_dashscope_family(final_model_name)
            if family == "multimodal_sync":
                # qwen-image*, wan2.6-t2i — sync /multimodal-generation/generation
                # with optional reference images for I2I-edit variants.
                image_url = self._generate_wan26_http(
                    prompt,
                    size,
                    n,
                    negative_prompt,
                    model_name=final_model_name,
                    ref_image_paths=all_ref_paths or None,
                )
            elif family == "image_gen_async":
                # wan2.6-image, wan2.5-t2i-preview, wan2.5-i2i-preview —
                # async /image-generation/generation with task polling.
                image_url = self._generate_wan26_image_http(
                    prompt,
                    size,
                    n,
                    negative_prompt,
                    all_ref_paths,
                    model_name=final_model_name,
                )
            else:
                # Legacy SDK fallback for older DashScope models (wanx-v1 etc.)
                # and any model name we don't explicitly recognize. New models
                # generally live on the multimodal/image-generation endpoints
                # above; this path is mostly here for backward compatibility.
                image_url = self._generate_sdk(prompt, final_model_name, size, n, negative_prompt, all_ref_paths,
                                               kwargs)

            api_end_time = time.time()
            api_duration = api_end_time - api_start_time

            logger.info(f"Generation success. Image URL: {image_url}")
            logger.info(f"API duration: {api_duration:.2f}s")
            
            # Download image
            self._download_image(image_url, output_path)
            return output_path, api_duration

        except Exception as e:
            import traceback
            logger.error(f"Error during generation [model={final_model_name}, size={size}, n={n}, refs={len(all_ref_paths)}]: {e}")
            logger.error(traceback.format_exc())
            raise

    def _generate_wan26_http(
        self,
        prompt: str,
        size: str,
        n: int,
        negative_prompt: str = None,
        model_name: str = "wan2.6-t2i",
        ref_image_paths: list = None,
    ) -> str:
        """Generate image via DashScope's *synchronous* multimodal-generation
        endpoint. Used for ``wan2.6-t2i`` and the entire ``qwen-image`` family
        (qwen-image, qwen-image-plus, qwen-image-edit, qwen-image-2.0,
        qwen-image-2.0-pro). Supports both T2I (no refs) and I2I (with refs
        — qwen-image-edit & qwen-image-2.0-pro) by inserting ``{"image": ...}``
        entries before the text prompt in ``messages.content``.
        """
        base = get_provider_base_url("DASHSCOPE")
        url = f"{base}/api/v1/services/aigc/multimodal-generation/generation"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        content: list = []
        if ref_image_paths:
            ref_limit = 3
            for path in ref_image_paths[:ref_limit]:
                image_input = self._resolve_wan26_reference_image(path, model_name=model_name)
                if image_input:
                    content.append({"image": image_input})
            if not content:
                raise RuntimeError(
                    f"{model_name} I2I requires at least one usable reference image. "
                    "Please provide a valid local image, public URL, or configure OSS."
                )
        content.append({"text": prompt})

        payload = {
            "model": model_name,
            "input": {
                "messages": [
                    {"role": "user", "content": content}
                ]
            },
            "parameters": {
                "prompt_extend": False,  # Disable auto prompt rewriting for consistency
                "watermark": False,
                "n": n,
                "size": size,
            },
        }

        # Add negative_prompt if provided
        if negative_prompt:
            payload["parameters"]["negative_prompt"] = negative_prompt

        logger.info(f"Calling DashScope multimodal-generation HTTP API ({model_name})...")
        logger.info(f"Payload: {payload}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=300)  # 5 minutes for slow API responses
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text[:500]}...")
        
        if response.status_code != 200:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('message', response.text)
            raise RuntimeError(f"Wan 2.6 API failed: {error_msg}")
        
        result = response.json()
        
        # Extract image URL from response
        # Response format: output.choices[].message.content[].image
        choices = result.get('output', {}).get('choices', [])
        if not choices:
            raise RuntimeError(f"No choices in response: {result}")
        
        # Get first image from first choice
        first_choice = choices[0]
        content = first_choice.get('message', {}).get('content', [])
        if not content:
            raise RuntimeError(f"No content in choice: {first_choice}")
        
        image_url = content[0].get('image')
        if not image_url:
            raise RuntimeError(f"No image URL in content: {content}")
        
        return image_url

    def _generate_wan26_image_http(
        self,
        prompt: str,
        size: str,
        n: int,
        negative_prompt: str = None,
        ref_image_paths: list = None,
        model_name: str = "wan2.6-image",
    ) -> str:
        """Generate image via DashScope's *asynchronous* image-generation
        endpoint with task polling. Used for ``wan2.6-image`` (I2I) and the
        ``wan2.5-*`` preview family (``wan2.5-t2i-preview``, ``wan2.5-i2i-preview``).
        Same payload shape across these models — just the ``model`` field varies.
        """
        base = get_provider_base_url("DASHSCOPE")
        create_url = f"{base}/api/v1/services/aigc/image-generation/generation"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-DashScope-Async": "enable"  # Required for async mode
        }
        
        # Build content array with reference images and prompt text
        content = []
        
        # Add reference images (upload to OSS first if local paths)
        if ref_image_paths:
            # Limit is already handled in generate(), but we keep a safety slice here
            # This method is specifically for wan2.6-image which supports 4 images
            ref_limit = 4
            for path in ref_image_paths[:ref_limit]:
                image_input = self._resolve_wan26_reference_image(path)
                if image_input:
                    content.append({"image": image_input})

        if ref_image_paths and not content:
            raise RuntimeError(
                f"{model_name} I2I requires at least one usable reference image. "
                "Please provide a valid local image, public URL, or configure OSS."
            )

        content.append({"text": prompt})

        # ``enable_interleave`` is the I2I-edit toggle; only relevant when
        # we actually have reference images. Skip it for pure T2I calls
        # (e.g. ``wan2.5-t2i-preview``) so DashScope doesn't reject the
        # missing-images precondition.
        parameters: Dict[str, Any] = {
            "prompt_extend": False,  # Disable auto prompt rewriting for consistency
            "watermark": False,
            "n": n,
            "size": size,
        }
        if ref_image_paths:
            parameters["enable_interleave"] = False  # Image editing mode (I2I)

        payload = {
            "model": model_name,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content,
                    }
                ]
            },
            "parameters": parameters,
        }
        
        # Add negative_prompt if provided
        if negative_prompt:
            payload["parameters"]["negative_prompt"] = negative_prompt
        
        logger.info(f"Calling DashScope image-generation HTTP API (async) for {model_name}...")
        logger.info(f"Payload: {payload}")
        
        # Step 1: Create task
        response = requests.post(create_url, headers=headers, json=payload, timeout=120)  # 2 minutes for task creation
        
        logger.info(f"Create task response status: {response.status_code}")
        logger.info(f"Create task response body: {response.text[:500]}")
        
        if response.status_code != 200:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('message', response.text)
            raise RuntimeError(f"DashScope image-generation task creation failed: {error_msg}")
        
        result = response.json()
        task_id = result.get('output', {}).get('task_id')
        if not task_id:
            raise RuntimeError(f"No task_id in response: {result}")
        
        logger.info(f"Task created: {task_id}")
        
        # Step 2: Poll for task completion
        poll_url = f"{base}/api/v1/tasks/{task_id}"
        poll_headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        max_wait_time = 600  # 10 minutes max wait (I2I can take longer)
        poll_interval = 10   # Poll every 10 seconds
        elapsed = 0
        
        while elapsed < max_wait_time:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            poll_response = requests.get(poll_url, headers=poll_headers, timeout=30)
            
            if poll_response.status_code != 200:
                logger.warning(f"Poll request failed: {poll_response.status_code}")
                continue
            
            poll_result = poll_response.json()
            task_status = poll_result.get('output', {}).get('task_status')
            
            logger.info(f"Task {task_id} status: {task_status} (elapsed: {elapsed}s)")
            
            if task_status == 'SUCCEEDED':
                # Extract image URL from choices
                choices = poll_result.get('output', {}).get('choices', [])
                if not choices:
                    raise RuntimeError(f"No choices in completed task: {poll_result}")
                
                first_choice = choices[0]
                content = first_choice.get('message', {}).get('content', [])
                if not content:
                    raise RuntimeError(f"No content in choice: {first_choice}")
                
                image_url = content[0].get('image')
                if not image_url:
                    raise RuntimeError(f"No image URL in content: {content}")
                
                logger.info(f"Task completed. Image URL: {image_url}")
                return image_url
            
            elif task_status == 'FAILED':
                # Log full response for debugging
                logger.error(f"Task {task_id} failed. Full response: {poll_result}")
                
                # Try to extract error message from various possible fields
                error_msg = (
                    poll_result.get('output', {}).get('message', '') or
                    poll_result.get('output', {}).get('code', '') or
                    poll_result.get('message', '') or
                    poll_result.get('code', '') or
                    'Unknown error - check logs for full response'
                )
                
                raise RuntimeError(f"DashScope image-generation task failed: {error_msg}")

            
            elif task_status in ['CANCELED', 'UNKNOWN']:
                raise RuntimeError(f"DashScope image-generation task {task_status}: {poll_result}")
            
            # PENDING or RUNNING - continue polling
        
        raise RuntimeError(f"DashScope image-generation task timed out after {max_wait_time}s")

    def _resolve_wan26_reference_image(self, path: str, model_name: str = "wan2.6-image") -> str:
        uploader = OSSImageUploader()
        backend = self._resolve_provider_backend_for_model(model_name)

        try:
            resolved = resolve_media_input(
                path,
                model_name=model_name,
                modality="image",
                backend=backend,
                uploader=uploader,
            )
            return resolved.value
        except ValueError as e:
            ref_type = classify_media_ref(path)
            if ref_type == MEDIA_REF_UNKNOWN and os.path.isabs(path) and os.path.exists(path):
                # Compatibility fallback: only for legacy absolute local paths
                # outside managed `output/` media refs.
                if uploader.is_configured:
                    object_key = uploader.upload_file(path, sub_path="temp/ref_images")
                    if object_key:
                        signed_url = uploader.sign_url_for_api(object_key)
                        if signed_url:
                            return signed_url

                return self._encode_local_image_as_data_uri(path)

            logger.warning(f"Reference image could not be resolved: {path}, reason: {e}")
            return None

    def _resolve_provider_backend_for_model(self, model_name: str) -> str:
        try:
            return resolve_provider_backend(model_name)
        except (KeyError, ValueError):
            # Keep image flows resilient for models not yet registered.
            return "dashscope"
        except Exception as e:
            logger.warning(
                f"Unexpected error resolving provider backend for model {model_name}: {e}. "
                "Falling back to dashscope."
            )
            return "dashscope"

    def _encode_local_image_as_data_uri(self, path: str) -> str:
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            mime_type = "image/png"

        with open(path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("ascii")

        return f"data:{mime_type};base64,{encoded}"

    def _generate_sdk(self, prompt: str, model_name: str, size: str, n: int, negative_prompt: str, all_ref_paths: list, kwargs: dict) -> str:
        """Generate image using Dashscope SDK (for older models)."""
        call_args = {
            "model": model_name,
            "prompt": prompt,
            "n": n,
            "size": size,
        }
        
        # Add negative_prompt if provided
        if negative_prompt:
            call_args["negative_prompt"] = negative_prompt
        
        # Add remaining kwargs
        call_args.update(kwargs)
        
        logger.info(f"SDK call_args: {dict((k, v) for k, v in call_args.items() if k != 'images')}")
        # Model selection priority: explicit model_name > config params > defaults

        # Handle Reference Images for I2I
        if all_ref_paths:
            ref_image_urls = []
            uploader = OSSImageUploader()
            for path in all_ref_paths:
                if os.path.exists(path):
                    # Upload to OSS and get signed URL
                    if uploader.is_configured:
                        object_key = uploader.upload_file(path, sub_path="temp/ref_images")
                        if object_key:
                            signed_url = uploader.sign_url_for_api(object_key)
                            ref_image_urls.append(signed_url)
                            logger.info(f"Reference image uploaded, signed URL: {signed_url[:80]}...")
                        else:
                            raise RuntimeError(f"Failed to upload reference image to OSS: {path}")
                    else:
                        logger.warning(f"OSS not configured, cannot upload reference image: {path}")
                elif path.startswith("http"):
                    # Already a URL
                    ref_image_urls.append(path)
                else:
                    # Check if it's an OSS Object Key using the utility function
                    from ..utils.oss_utils import is_object_key
                    if is_object_key(path):
                        if uploader.is_configured:
                            signed_url = uploader.sign_url_for_api(path)
                            ref_image_urls.append(signed_url)
                            logger.info(f"Reference image (Object Key), signed URL: {signed_url[:80]}...")
                        else:
                            raise ValueError(f"OSS not configured but Object Key provided: {path}")
                    else:
                        raise ValueError(f"Reference image not found: {path}")
            
            logger.info(f"DEBUG: ref_image_urls count: {len(ref_image_urls)}")
            
            # Limit is already handled in generate(), but we keep a safety slice here
            ref_limit = 4 if model_name == 'wan2.6-image' else 3
            if len(ref_image_urls) > ref_limit:
                logger.warning(f"Limiting reference images from {len(ref_image_urls)} to {ref_limit}")
                ref_image_urls = ref_image_urls[:ref_limit]
            
            call_args['images'] = ref_image_urls

        # Call Dashscope SDK
        rsp = ImageSynthesis.call(**call_args)
        
        logger.info(f"SDK response: {rsp}")

        if rsp.status_code != HTTPStatus.OK:
            logger.error(f"Task failed with status code: {rsp.status_code}, code: {rsp.code}, message: {rsp.message}")
            raise RuntimeError(f"Task failed: {rsp.message}")

        # Extract Image URL
        if hasattr(rsp, 'output'):
            logger.info(f"Response Output: {rsp.output}")
            results = rsp.output.get('results')
            url = rsp.output.get('url')
            
            if results and len(results) > 0:
                 first_result = results[0]
                 if isinstance(first_result, dict):
                     image_url = first_result.get('url')
                 else:
                     image_url = getattr(first_result, 'url', None)
            elif url:
                 image_url = url
            else:
                 logger.error(f"Unexpected response structure. Output: {rsp.output}")
                 raise RuntimeError("Could not find image URL in response.")
        else:
             logger.error(f"Response has no output. Response: {rsp}")
             raise RuntimeError("Response has no output.")
        
        return image_url

    def _download_image(self, url: str, output_path: str):
        logger.info(f"Downloading image to {output_path}...")
        
        # Setup retry strategy
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        http = requests.Session()
        http.mount("https://", adapter)
        http.mount("http://", adapter)

        temp_path = output_path + ".tmp"
        try:
            response = http.get(url, stream=True, timeout=60, verify=False) # verify=False to avoid some SSL issues
            response.raise_for_status()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Atomic rename
            os.rename(temp_path, output_path)
            logger.info("Download complete.")
            
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
