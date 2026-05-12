import json
import os
import time
import uuid
import logging
import traceback
import re
from typing import List, Dict, Any, Optional

from .models import Script, Character, Scene, Prop, StoryboardFrame, GenerationStatus


def _strip_markdown_json(content: str) -> str:
    """Strip markdown code fences from LLM JSON output."""
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    return content.strip()

from ...utils import get_logger
from ...i18n import t as _t

logger = get_logger(__name__)

# ── Default system prompts for polish/refine stages ──────────────────────
# These are the built-in defaults. Users can override per-project via PromptConfig.
# Placeholders: {ASSETS} = asset context, {DRAFT} = draft prompt, {SLOTS} = R2V slot context

DEFAULT_STORYBOARD_POLISH_PROMPT = """
# ROLE
You are an expert storyboard artist and prompt engineer. Your task is to rewrite a draft prompt into a high-quality image generation prompt, specifically for a multi-reference image workflow.

# CONTEXT:
The user has selected specific reference images (assets) to compose a scene.
You must refer to these assets by their Image ID (e.g., "Image 1", "Image 2") when describing them in the prompt.

# AVAILABLE ASSETS:
{ASSETS}

# RULES:
1.  **Integrate Assets**: Explicitly mention "Image X" when describing the corresponding character, scene, or prop.
2.  **Natural Flow**: Do not just concatenate. Write a coherent sentence or paragraph describing the visual scene.
3.  **Strict Adherence**: DO NOT hallucinate emotions, actions, or plot details not present in the draft. If the draft says "sitting", do NOT add "sadly" or "happily" unless specified. Keep the narrative neutral and accurate.
4.  **Enhance Detail**: Add visual details (lighting, atmosphere, emotion) based on the draft prompt, but keep the asset references clear.
5.  **No Explanations**: Return ONLY the polished prompt text.
6.  **Bilingual Output**:
    - **Prompt CN**: Fluent Chinese, strictly following the content of the draft.
    - **Prompt EN**: Natural English description, prioritizing visual atmosphere.

# OUTPUT FORMAT
Return STRICTLY a JSON object:
{{
    "prompt_cn": "Chinese description with Image X references...",
    "prompt_en": "English cinematic description with Image X references..."
}}

# EXAMPLES
**Input Draft**: Boy (Image 1) sitting on hospital bed (Image 2).
**Output**:
{{
    "prompt_cn": "图像1中的男孩坐在图像2的病床边缘。病房内光线柔和，自然光从侧面照射在男孩身上，勾勒出真实的轮廓。画面构图稳定，质感写实。",
    "prompt_en": "The boy from Image 1 is seated on the edge of the hospital bed in Image 2. Soft natural light illuminates the scene from the side, highlighting the fabric textures of the bedding and the realistic skin tone of the boy. Cinematic composition, high resolution, photorealistic."
}}

# USER DRAFT PROMPT
{DRAFT}
""".strip()

DEFAULT_VIDEO_POLISH_PROMPT = """You are an expert video prompt engineer. Your task is to optimize a draft prompt for an Image-to-Video generation model.

GUIDELINES:
1.  **Structure**: Prompt = Motion Description + Camera Movement.
2.  **Motion Description**: Describe the dynamic action of elements (characters, objects) in the image. Use adjectives to control speed and intensity (e.g., "slowly", "rapidly", "subtle").
3.  **Camera Movement**: Explicitly state camera moves if needed (e.g., "Zoom in", "Pan left", "Static camera").
4.  **Clarity**: Be concise but descriptive. Focus on visual movement.

EXAMPLES:

*   **Zoom Out**: "A soft, round animated character with a curious expression wakes up to find their bed is a giant golden corn kernel. Camera zooms out to reveal the room is a massive corn silo, with echoes reverberating, corn kernels piled high like walls, and a beam of warm sunlight streaming from a high window, casting long shadows."
*   **Pan Left**: "Camera pans left, slowly sweeping across a luxury store window filled with glamorous models and expensive goods. The camera continues panning left, leaving the window to reveal a ragged homeless man shivering in the corner of the adjacent alley."

TASK:
Rewrite the following draft prompt into a high-quality video generation prompt following the guidelines above.

OUTPUT FORMAT:
Return STRICTLY a JSON object:
{{
    "prompt_cn": "润色后的中文视频提示词，关注运动和镜头",
    "prompt_en": "Polished English video prompt, focusing on motion and camera"
}}"""

DEFAULT_R2V_POLISH_PROMPT = """# Role
You are a prompt engineer for the Wan 2.6 Reference-to-Video model.

# Context
The R2V (Reference-to-Video) model generates video clips by combining reference character videos with a text prompt.
The user has uploaded the following reference videos:
{SLOTS}

# Task
Rewrite the user's input prompt into a structured format strictly following these rules:

1. **REPLACE character names with their ID**: Use "character1" for the first character, "character2" for the second, "character3" for the third.
2. **STRUCTURE**: Use this format:
   - Scene setup (environment, lighting, mood)
   - Character action (what character1/character2/character3 are doing, their expressions, movements)
   - Camera movement (if applicable)
3. **DIALOGUE FORMAT**: If the prompt includes dialogue, format it as: 'character1 says: "dialogue content"'
4. **PRESERVE**: Keep the original intent and emotional tone.
5. **ENHANCE**: Add visual details for dramatic effect (lighting, speed descriptors like "slowly", "rapidly").

# Output Format
Return STRICTLY a JSON object:
{{
    "prompt_cn": "润色后的中文提示词，使用 character1/character2/character3 格式",
    "prompt_en": "Polished English prompt using character1/character2/character3 format"
}}

# Examples

INPUT: 主角从门里跳出来说话
SLOTS: character1 = "White rabbit", character2 = "Robot dog"
OUTPUT:
{{
    "prompt_cn": "character1 从门里猛然跳出，落地时耳朵竖起，充满活力。房间昏暗，温暖的光线从尘土飞扬的窗户中透入。character1 兴奋地环顾四周说道：'我正好赶上了！' 镜头随着跳跃略微倾斜。",
    "prompt_en": "character1 bursts through the door with an exaggerated jump, landing energetically with ears perked up. The room is dimly lit with warm ambient light streaming through dusty windows. character1 looks around excitedly and says: 'I made it just in time!' Camera follows the jump with a slight tilt."
}}""".strip()

class ScriptProcessor:
    def __init__(self, api_key: str = None):
        self._api_key = api_key
        from .llm_adapter import LLMAdapter
        self.llm = LLMAdapter()

    @property
    def is_configured(self):
        return self.llm.is_configured

    def parse_novel(self, title: str, text: str) -> Script:
        """
        Parses the raw novel text into a structured Script object using an LLM.
        """
        logger.info(f"Parsing novel: {title}...")
        
        if not self.is_configured:
             logger.error("LLM API key not configured.")
             raise ValueError(_t("errors.llm_api_key_missing"))

        prompt = self._construct_prompt(text)

        try:
            content = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
            )
            logger.debug(f"LLM Response Content:\n{content}")

            content = _strip_markdown_json(content)
            data = json.loads(content)
            return self._create_script_from_data(title, text, data)
                
        except json.JSONDecodeError as e:
            error_msg = _t("errors.llm_json_parse_failed", error=str(e))
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)
        except ValueError:
            # Re-raise ValueError (e.g., API key not set)
            raise
        except Exception as e:
            error_msg = _t("errors.llm_script_parse_failed", error=str(e))
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

    def _create_script_from_data(self, title: str, original_text: str, data: Dict[str, Any]) -> Script:
        script_id = str(uuid.uuid4())
        
        characters = []
        name_to_char = {} # For variant linking
        llm_id_to_uuid = {} # For ID resolution

        # Pass 1: Create all characters
        for char_data in data.get("characters", []):
            char_uuid = str(uuid.uuid4())
            llm_id = char_data.get("id")
            if llm_id:
                llm_id_to_uuid[llm_id] = char_uuid
            
            char = Character(
                id=char_uuid,
                name=char_data.get("name", "Unknown"),
                description=char_data.get("description", ""),
                age=char_data.get("age"),
                gender=char_data.get("gender"),
                clothing=char_data.get("clothing"), # Might be merged into description in new prompt, but keeping for compatibility
                visual_weight=char_data.get("visual_weight", 3),
                status=GenerationStatus.PENDING
            )
            characters.append(char)
            name_to_char[char.name] = char
            
        # Pass 2: Link variants to base characters (Logic remains valid even with new prompt if naming convention holds)
        for char in characters:
            if "(" in char.name and ")" in char.name:
                base_name = char.name.split("(")[0].strip()
                if base_name in name_to_char and name_to_char[base_name].id != char.id:
                    char.base_character_id = name_to_char[base_name].id
            
        scenes = []
        for scene_data in data.get("scenes", []):
            scene_uuid = str(uuid.uuid4())
            llm_id = scene_data.get("id")
            if llm_id:
                llm_id_to_uuid[llm_id] = scene_uuid

            scenes.append(Scene(
                id=scene_uuid,
                name=scene_data.get("name", "Unknown"),
                description=scene_data.get("description", ""),
                time_of_day=scene_data.get("time_of_day"),
                lighting_mood=scene_data.get("lighting_mood"),
                visual_weight=scene_data.get("visual_weight", 3),
                status=GenerationStatus.PENDING
            ))
            
        props = []
        for prop_data in data.get("props", []):
            prop_uuid = str(uuid.uuid4())
            llm_id = prop_data.get("id")
            if llm_id:
                llm_id_to_uuid[llm_id] = prop_uuid

            props.append(Prop(
                id=prop_uuid,
                name=prop_data.get("name", "Unknown"),
                description=prop_data.get("description", ""),
                status=GenerationStatus.PENDING
            ))
            
        frames = []
        for frame_data in data.get("frames", []):
            # Resolve Character IDs
            char_ids = []
            for cid in frame_data.get("character_ids", []):
                if cid in llm_id_to_uuid:
                    char_ids.append(llm_id_to_uuid[cid])
            
            # Resolve Prop IDs
            prop_ids = []
            for pid in frame_data.get("prop_ids", []):
                if pid in llm_id_to_uuid:
                    prop_ids.append(llm_id_to_uuid[pid])

            # Resolve Scene ID
            scene_llm_id = frame_data.get("scene_id")
            scene_id = llm_id_to_uuid.get(scene_llm_id)
            if not scene_id and scenes:
                scene_id = scenes[0].id # Fallback
            elif not scene_id:
                scene_id = str(uuid.uuid4()) # Fallback if no scenes

            # Handle Dialogue
            dialogue_data = frame_data.get("dialogue")
            dialogue_text = None
            speaker_name = None
            if isinstance(dialogue_data, dict):
                dialogue_text = dialogue_data.get("text")
                speaker_name = dialogue_data.get("speaker")
            elif isinstance(dialogue_data, str):
                dialogue_text = dialogue_data # Fallback for old format

            frames.append(StoryboardFrame(
                id=str(uuid.uuid4()),
                scene_id=scene_id,
                character_ids=char_ids,
                prop_ids=prop_ids,
                action_description=frame_data.get("action_description", ""),
                facial_expression=frame_data.get("facial_expression"),
                dialogue=dialogue_text,
                speaker=speaker_name,
                camera_angle=frame_data.get("camera_angle", "Medium Shot"),
                camera_movement=frame_data.get("camera_movement"),
                composition=frame_data.get("composition"),
                atmosphere=frame_data.get("atmosphere"),
                image_prompt=f"{frame_data.get('action_description')} {frame_data.get('facial_expression', '')} {frame_data.get('camera_angle')} {frame_data.get('lighting_mood', '')} {frame_data.get('atmosphere', '')}", 
                status=GenerationStatus.PENDING
            ))
            
        return Script(
            id=script_id,
            title=title,
            original_text=original_text,
            characters=characters,
            scenes=scenes,
            props=props,
            frames=frames,
            created_at=time.time(),
            updated_at=time.time()
        )

    def create_draft_script(self, title: str, text: str) -> Script:
        """
        Creates a draft script object without LLM analysis.
        """
        return Script(
            id=str(uuid.uuid4()),
            title=title,
            original_text=text,
            characters=[],
            scenes=[],
            props=[],
            frames=[],
            created_at=time.time(),
            updated_at=time.time()
        )

    def split_into_episodes(self, text: str, suggested_episodes: int = 3) -> List[Dict[str, Any]]:
        """
        Uses LLM to split a long text into episodes by narrative rhythm.
        Returns a list of episode dicts with title, summary, start/end markers, etc.
        """
        if not self.is_configured:
            raise ValueError("LLM API Key 未配置。请在 API 配置中设置对应的 API Key 后重试。")

        MAX_TEXT_LENGTH = 80000
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH] + "\n\n[文本已截断，请基于已有内容进行划分]"

        prompt = f"""你是一名专业的剧本编剧和分集策划师。

请将以下小说/剧本文本按叙事节奏划分为约 {suggested_episodes} 集。

划分原则：
1. 每集应有完整的叙事弧（开端/发展/高潮或悬念）
2. 在自然的情节转折点或场景切换处分集
3. 各集内容量大致均衡，但优先保证叙事完整性
4. 实际集数可以在建议集数 ±2 范围内浮动

输出纯 JSON（不要 markdown 代码块）:
{{
  "episodes": [
    {{
      "episode_number": 1,
      "title": "集标题",
      "summary": "50字以内的内容摘要",
      "start_marker": "该集起始的原文前20字",
      "end_marker": "该集结束的原文后20字",
      "estimated_duration": "预估时长（分钟）"
    }}
  ]
}}

原文如下：

{text}"""

        try:
            content = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
            )
            content = _strip_markdown_json(content)
            data = json.loads(content)
            episodes = data.get("episodes", [])
            if not episodes:
                raise RuntimeError("LLM 未返回任何分集数据")
            return episodes
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM 返回的分集数据格式错误: {e}")
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"分集划分失败: {str(e)}")

    def _mock_parse(self, title: str, text: str) -> Script:
        # ... (Existing mock logic moved here) ...
        script_id = str(uuid.uuid4())
        
        # Mock Characters
        char1 = Character(
            id=str(uuid.uuid4()),
            name="Alex",
            description="A young adventurer with messy brown hair and a determined look.",
            age="20",
            gender="Male",
            clothing="Leather jacket, jeans",
            visual_weight=5,
            status=GenerationStatus.PENDING
        )
        char2 = Character(
            id=str(uuid.uuid4()),
            name="Luna",
            description="A mysterious mage with silver hair and glowing blue eyes.",
            age="Unknown",
            gender="Female",
            clothing="Dark robe with silver embroidery",
            visual_weight=4,
            status=GenerationStatus.PENDING
        )
        
        # Mock Scene
        scene1 = Scene(
            id=str(uuid.uuid4()),
            name="Ancient Ruins",
            description="Crumbling stone walls covered in moss, illuminated by shafts of sunlight breaking through the canopy.",
            visual_weight=3,
            status=GenerationStatus.PENDING
        )
        
        # Mock Props
        prop1 = Prop(
            id=str(uuid.uuid4()),
            name="Glowing Crystal",
            description="A jagged crystal pulsing with a faint purple light.",
            status=GenerationStatus.PENDING
        )
        
        # Mock Frames
        frames = []
        
        # Frame 1
        frames.append(StoryboardFrame(
            id=str(uuid.uuid4()),
            scene_id=scene1.id,
            character_ids=[char1.id],
            action_description="Alex steps cautiously into the ruins, looking around.",
            camera_angle="Wide Shot",
            camera_movement="Pan Left",
            image_prompt="Wide shot of Alex stepping into ancient ruins, mossy stone walls, sunlight beams, cinematic lighting, pan left.",
            status=GenerationStatus.PENDING
        ))
        
        # Frame 2
        frames.append(StoryboardFrame(
            id=str(uuid.uuid4()),
            scene_id=scene1.id,
            character_ids=[char1.id, char2.id],
            action_description="Luna appears from the shadows, surprising Alex.",
            dialogue="Luna: You shouldn't be here.",
            camera_angle="Medium Shot",
            camera_movement="Static",
            image_prompt="Medium shot of Luna emerging from shadows behind Alex, mysterious atmosphere, static camera.",
            status=GenerationStatus.PENDING
        ))
        
        # Frame 3
        frames.append(StoryboardFrame(
            id=str(uuid.uuid4()),
            scene_id=scene1.id,
            character_ids=[char2.id],
            prop_ids=[prop1.id],
            action_description="Luna holds up the glowing crystal.",
            camera_angle="Close Up",
            camera_movement="Zoom In",
            image_prompt="Close up of Luna holding a glowing purple crystal, magical effects, zoom in.",
            status=GenerationStatus.PENDING
        ))
        
        script = Script(
            id=script_id,
            title=title,
            original_text=text,
            characters=[char1, char2],
            scenes=[scene1],
            props=[prop1],
            frames=frames,
            created_at=time.time(),
            updated_at=time.time()
        )
        
        return script

    def _construct_prompt(self, text: str) -> str:
        """
        Prompt A: Entity Extractor
        Constructs the system prompt for extracting characters, scenes, and props ONLY.
        Frames are generated separately via analyze_to_storyboard (Prompt B).
        """
        return f"""
        You are a professional storyboard artist and scriptwriter.
        Analyze the following novel text and extract structured data for a comic/video production.
        
        IMPORTANT: 
        - All descriptive content (names, descriptions) MUST be in CHINESE (Simplified Chinese).
        - Extract ONLY characters, scenes, and props.
        
        Output strictly in valid JSON format with the following structure:
        {{
            "characters": [
                {{
                    "id": "char_001",
                    "name": "Character Name (e.g. '叶墨', '叶墨 (古装)')",
                    "description": "Visual description (hair, eyes, build, distinct features). DO NOT include specific facial expressions (e.g. sad, angry) or temporary actions (e.g. running, crying). Focus on permanent physical traits.",
                    "age": "Age estimate (e.g. '25')",
                    "gender": "Gender",
                    "clothing": "Default outfit description. If a character changes outfits significantly (e.g. from casual to wedding dress), create a separate character entry for each outfit variant with a distinct name (e.g. 'Name (Outfit)').",
                    "visual_weight": 5  // 1-5 importance
                }}
            ],
            "scenes": [
                {{
                    "id": "scene_001",
                    "name": "Location Name (e.g. '咖啡店', '古代遗迹')",
                    "description": "Visual description (lighting, mood, key elements)",
                    "visual_weight": 3
                }}
            ],
            "props": [
                {{
                    "id": "prop_001",
                    "name": "Prop Name",
                    "description": "Visual description"
                }}
            ]
        }}

        Text:
        {text}
        """

    def analyze_script_for_styles(self, script_text: str) -> List[Dict[str, Any]]:
        """使用 LLM 分析剧本并推荐视觉风格"""
        
        logger.info("Analyzing script for visual style recommendations...")
        
        if not self.is_configured:
            logger.warning("DASHSCOPE_API_KEY not set. Returning default recommendations.")
            return self._mock_style_recommendations()
        
        system_prompt = """你是一个专业的电影美术指导和视觉风格顾问。
请根据提供的剧本内容，分析其题材、情绪和氛围，推荐3种截然不同但都适合的视觉风格。

对于每种风格，请提供：
1. 风格名称（简洁、专业，使用英文）
2. 风格描述（1-2句话，用中文）
3. 推荐理由（为什么这个风格适合这个剧本，用中文，50字以内）
4. Stable Diffusion 正向提示词（详细的风格关键词，英文，逗号分隔，不超过50个词）
5. Stable Diffusion 负向提示词（避免的视觉元素，英文，逗号分隔，不超过30个词）

IMPORTANT: 
- 你的回复必须是严格的JSON格式。
- 不要包含任何解释性文字。
- 所有文本中的引号必须使用转义符号 (例如 \")。
- 确保JSON完整，不要被截断。
- 保持内容精炼，避免过长的描述。
- 严禁重复生成相同的内容，不要陷入循环。
- 只返回3个推荐风格，不要多也不要少。

CRITICAL STYLE GUIDELINES:
- 正向提示词必须只描述：光影、色调、材质、艺术媒介、氛围、镜头语言 (e.g., "cinematic lighting, film grain, watercolor texture, dark atmosphere").
- 严禁描述具体实体：不要包含人物、服装、具体物品、环境细节 (e.g., 禁止 "cracked helmet", "blood stains", "monster", "forest", "sword").
- 风格必须是通用的，能套用到任何角色或场景上，而不会改变其原本的物理结构。

返回格式：
{
  "recommendations": [
    {
      "name": "风格名称",
      "description": "风格描述",
      "reason": "推荐理由",
      "positive_prompt": "正向提示词",
      "negative_prompt": "负向提示词"
    }
  ]
}"""

        user_prompt = f"剧本内容：\n\n{script_text[:2000]}"  # 限制长度避免 token 限制
        
        try:
            content = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={'type': 'json_object'},
            )
            logger.debug(f"Style Analysis Response:\n{content}")

            # Clean up markdown code blocks if present
            content = _strip_markdown_json(content)

            # Safety check: if content is suspiciously long, truncate it
            # This prevents issues where the model gets stuck in a loop
            if len(content) > 5000:
                logger.warning(f"Response too long ({len(content)} chars), truncating...")
                content = content[:5000]
                # Find the last closing brace of a recommendation object to make truncation cleaner
                last_brace = content.rfind("}")
                if last_brace != -1:
                    content = content[:last_brace+1]

            def repair_json(json_str):
                """Attempt to repair truncated or malformed JSON."""
                json_str = json_str.strip()

                # If truncated, try to close it
                if not json_str.endswith("}"):
                    # Count open braces/brackets
                    open_braces = json_str.count("{") - json_str.count("}")
                    open_brackets = json_str.count("[") - json_str.count("]")
                    open_quotes = json_str.count('"') % 2

                    if open_quotes:
                        json_str += '"'

                    json_str += "]" * open_brackets
                    json_str += "}" * open_braces

                # Ensure the root object is closed
                if json_str.count("{") > json_str.count("}"):
                     json_str += "}" * (json_str.count("{") - json_str.count("}"))

                return json_str

            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Raw content length: {len(content)}")

                # Try to fix common JSON issues
                try:
                    # 1. Attempt to extract JSON object from text using regex
                    import re
                    # Look for the outermost JSON object
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        content = json_match.group(0)

                    # 2. Try to repair if it looks truncated
                    content = repair_json(content)

                    data = json.loads(content)
                except Exception as inner_e:
                    logger.error(f"Failed to recover JSON: {inner_e}")
                    # Last resort: try to parse partially using regex for fields
                    try:
                        logger.debug("Attempting regex extraction of fields...")
                        recommendations = []
                        # Regex to find style objects - improved to be non-greedy and handle newlines
                        style_matches = re.finditer(r'\{\s*"name":\s*"(.*?)",\s*"description":\s*"(.*?)".*?\}', content, re.DOTALL)

                        # If that fails, try a simpler regex that just looks for the array items
                        if not list(style_matches):
                            # Fallback manual parsing
                            pass

                        if not recommendations:
                            # Construct a basic valid JSON if we have at least some content
                            if "recommendations" in content:
                                # Try to close it forcefully
                                fixed_content = content + "}]}"
                                try:
                                    data = json.loads(fixed_content)
                                    recommendations = data.get("recommendations", [])
                                except:
                                    pass

                        if not recommendations:
                            raise ValueError("Regex extraction failed")
                    except:
                        return self._mock_style_recommendations()

            recommendations = data.get("recommendations", [])

            # Add unique IDs
            for i, rec in enumerate(recommendations):
                rec["id"] = f"ai-rec-{i+1}-{str(uuid.uuid4())[:8]}"
                rec["is_custom"] = False

            return recommendations

        except Exception as e:
            logger.error(f"Error analyzing script for styles: {e}", exc_info=True)
            return self._mock_style_recommendations()
    
    def _mock_style_recommendations(self) -> List[Dict[str, Any]]:
        """返回默认的风格推荐"""
        return [
            {
                "id": f"mock-cinematic-{str(uuid.uuid4())[:8]}",
                "name": "Cinematic Realism",
                "description": "电影级写实风格，专业打光",
                "reason": "适合大多数叙事性内容，提供专业的视觉质感",
                "positive_prompt": "cinematic, photorealistic, 8k, volumetric lighting, film grain, dramatic lighting",
                "negative_prompt": "cartoon, anime, low quality, blurry",
                "is_custom": False
            },
            {
                "id": f"mock-anime-{str(uuid.uuid4())[:8]}",
                "name": "Anime Style",
                "description": "日式动漫风格，明快色彩",
                "reason": "适合充满情感表现的故事",
                "positive_prompt": "anime style, cel shading, vibrant colors, expressive, detailed character design",
                "negative_prompt": "photorealistic, 3d, blurry, washed out",
                "is_custom": False
            },
            {
                "id": f"mock-noir-{str(uuid.uuid4())[:8]}",
                "name": "Film Noir",
                "description": "黑色电影风格，高对比度",
                "reason": "适合悬疑、神秘题材的叙事",
                "positive_prompt": "black and white, film noir, high contrast, dramatic shadows, moody lighting",
                "negative_prompt": "colorful, bright, happy, modern",
                "is_custom": False
            }
        ]
    
    def rewrite_to_screenplay(self, text: str) -> str:
        """Rewrite a novel-style passage into a normalized screenplay format.

        The downstream ``analyze_to_storyboard`` prompt already
        describes a specific script format (``1-1 地点 [时间] [内/外]``
        / ``人物： 角色名``/ ``△`` action / ``角色名（情绪）：`` dialogue).
        Users typically import raw novel prose, so the analyzer wastes
        capacity guessing structure. This method runs an LLM pre-pass
        that emits exactly that format, so storyboard analysis can
        focus on visual atomization instead of parsing.

        Constraints (mirrored from huobao's ``script_rewriter``):

        * Each scene targets 30–60 seconds of on-screen time.
        * Structural expansion only — do not invent plot beats.
        * Emphasise visual/audible action, avoid cinematography jargon
          (no "推镜", "升格" etc. — those belong in storyboard prompts).
        * Output in Simplified Chinese.

        Returns the formatted screenplay text. On configuration miss,
        returns the input unchanged so callers can chain safely.
        """
        if not text:
            return text
        if not self.is_configured:
            logger.warning("LLM not configured, rewrite_to_screenplay returning input unchanged")
            return text

        system_prompt = self._build_screenplay_rewrite_prompt()
        try:
            content = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            ).strip()
            # The rewriter outputs plain text, but defensively strip
            # markdown fences in case the model wraps anyway.
            if "```" in content:
                content = _strip_markdown_json(content)
            return content
        except Exception as e:
            logger.warning(f"rewrite_to_screenplay failed, returning input unchanged: {e}")
            return text

    @staticmethod
    def _build_screenplay_rewrite_prompt() -> str:
        return (
            "你是一名短剧编剧。把下面的小说原文改写成**短剧拍摄格式**,严格遵守:\n\n"
            "# 格式规范\n"
            "- 场景标题行: `1-1 地点名称 [时间] [内/外]` (按出现顺序自增编号)\n"
            "- 人物行: `人物： 角色名1，角色名2` (本场出场的角色,逗号分隔)\n"
            "- 动作行: 以 `△` 开头,单独一行,描述画面里发生的视觉/可听动作\n"
            "- 对话行: `角色名（情绪）: 对话内容` 或 `角色名 (V.O.):` 表示画外音\n\n"
            "# 内容约束\n"
            "1. **每场 30-60 秒拍摄时长**,过长就拆场。\n"
            "2. **保留核心剧情**,不要添加原文没有的情节、人物、对话。\n"
            "3. **结构性扩写**:把「心想/独白」等不可见内容转成动作 + 表情 + 道具反应;扩写比例 ≤ 30%。\n"
            "4. **强化画面感**:让每一行动作描述都「看得见、听得到」。\n"
            "5. **禁用镜头术语**:不要「推/拉/摇/移/升格/慢动作」这类词,那些是分镜阶段的事。\n"
            "6. 简体中文输出,不要 Markdown 代码块,直接输出剧本正文。"
        )

    def extract_entities(
        self,
        text: str,
        existing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Entity-only extraction with optional reuse hints.

        Used by :mod:`apps.comic_gen.extraction` strategies. Returns a
        dict shaped like::

            {
              "characters": [
                {"name": "叶墨", "match_id": "<uuid-or-null>",
                 "description": "...", "gender": "男", "age": "25", ...},
                ...
              ],
              "scenes":  [{"name": "卧室", "match_id": ..., "time_of_day": "夜", ...}, ...],
              "props":   [{"name": "手机", "match_id": ..., "description": "..."}, ...],
            }

        When ``existing`` is provided (incremental mode), the LLM is shown
        the catalog summary and instructed to set ``match_id`` whenever a
        candidate refers to an already-known entity. Without ``existing``
        (full mode), all entities come back with ``match_id=null``.
        """
        if not self.is_configured:
            return self._mock_extract_entities(text, existing)

        reuse_block = self._render_reuse_block(existing) if existing else ""
        system_prompt = self._build_extraction_prompt(reuse_block)

        try:
            content = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
            ).strip()
            content = _strip_markdown_json(content)
            data = json.loads(content)
            # Normalise shape: always present all three keys
            for key in ("characters", "scenes", "props"):
                data.setdefault(key, [])
            return data
        except json.JSONDecodeError as e:
            logger.error(f"extract_entities JSON parse failed: {e}")
            raise RuntimeError(
                "实体提取 LLM 输出不是合法 JSON。请重试或检查模型配置。"
            )
        except Exception as e:
            logger.error(f"extract_entities failed: {e}", exc_info=True)
            raise RuntimeError(f"实体提取失败: {e}")

    @staticmethod
    def _render_reuse_block(existing: Dict[str, Any]) -> str:
        """Format the catalog summary as a "already-known" hint block."""
        return (
            "# 已存在的实体（必须优先复用，不要重复创建）\n"
            "如果你识别出的角色/场景/道具与下列任一项指向同一实体，"
            "**必须**在输出中把 `match_id` 设为对应的 id 字符串。"
            "只有真正全新的实体才创建,且 `match_id` 留 `null`。\n\n"
            f"```json\n{json.dumps(existing, ensure_ascii=False, indent=2)}\n```"
        )

    @staticmethod
    def _build_extraction_prompt(reuse_block: str) -> str:
        return (
            "你是一名专业的剧本分析师。从下面的剧本片段中提取角色、场景、道具，"
            "全部用简体中文,严格输出 JSON。\n\n"
            f"{reuse_block}\n\n"
            "# 输出格式\n"
            "```json\n"
            "{\n"
            '  "characters": [\n'
            '    {"match_id": null,'
            ' "name": "叶墨",'
            ' "description": "短发，瘦削，眼神疲惫",'
            ' "age": "25",'
            ' "gender": "男",'
            ' "clothing": "灰色卫衣",'
            ' "visual_weight": 5}\n'
            "  ],\n"
            '  "scenes": [\n'
            '    {"match_id": null,'
            ' "name": "卧室",'
            ' "description": "昏暗，单人床，乱",'
            ' "time_of_day": "夜",'
            ' "lighting_mood": "冷蓝月光",'
            ' "visual_weight": 3}\n'
            "  ],\n"
            '  "props": [\n'
            '    {"match_id": null,'
            ' "name": "手机",'
            ' "description": "黑色直板"}\n'
            "  ]\n"
            "}\n"
            "```\n"
            "规则:\n"
            "1. 不输出 Markdown 代码块标记。\n"
            "2. 缺失字段用 null,不要省略键。\n"
            "3. 与已存在实体匹配时,`match_id` 必须等于对应 id 字符串。\n"
        )

    def match_voice_for_character(
        self,
        character: Character,
        candidates: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Ask the LLM to pick one voice id from ``candidates`` for a character.

        Lives on ``ScriptProcessor`` so the LLM adapter / instance scope
        is reused — voice matching is just another LLM call routed by
        ``script.model_settings.llm_instance_id``. Returns ``None`` if
        the LLM emits anything unparseable (the caller falls through to
        the next rule).
        """
        if not self.is_configured or not candidates:
            return None
        voice_lines = [
            f"- id: {c.get('id')!r}, name: {c.get('name')!r}, gender: {c.get('gender')!r}"
            for c in candidates
        ]
        system_prompt = (
            "你是一名配音导演。下面给你一个角色的资料和一组可用音色,"
            "请挑出**唯一最匹配**的音色 id,只输出 JSON: {\"voice_id\": \"...\"}\n"
            "不要解释,不要 Markdown 代码块。\n\n"
            f"# 角色资料\n"
            f"姓名: {character.name}\n"
            f"性别: {character.gender or '未知'}\n"
            f"年龄: {character.age or '未知'}\n"
            f"描述: {character.description or '无'}\n\n"
            f"# 可用音色\n" + "\n".join(voice_lines)
        )
        try:
            content = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请选择最匹配的音色。"},
                ],
                response_format={"type": "json_object"},
            ).strip()
            content = _strip_markdown_json(content)
            picked = json.loads(content).get("voice_id")
            if isinstance(picked, str) and any(c.get("id") == picked for c in candidates):
                return picked
            return None
        except Exception as e:
            logger.warning(f"match_voice_for_character LLM call failed: {e}")
            return None

    @staticmethod
    def _mock_extract_entities(
        text: str, existing: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Offline fallback — returns a stable, tiny payload for tests."""
        return {
            "characters": [
                {"match_id": None, "name": "叶墨", "description": "短发青年", "gender": "男", "age": "25"}
            ],
            "scenes": [
                {"match_id": None, "name": "卧室", "description": "昏暗", "time_of_day": "夜"}
            ],
            "props": [
                {"match_id": None, "name": "手机", "description": "黑色直板"}
            ],
        }

    def analyze_to_storyboard(
        self,
        text: str,
        entities_json: Dict[str, Any],
        *,
        with_audio: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Analyzes script text and generates storyboard frames using Prompt B (Storyboard Director).

        Returns a list of frame dictionaries with visual atoms. When
        ``with_audio`` is True (default), each frame also carries
        ``bgm_prompt`` and ``sfx_prompt`` keys to drive downstream audio
        generation — set to False only for tests / dry-runs that need a
        smaller LLM payload.
        """
        from .prompts import StoryboardPromptBuilder

        logger.info(f"Analyzing text to storyboard: {text[:100]}...")

        if not self.is_configured:
            logger.warning("DASHSCOPE_API_KEY not set. Returning mock frames.")
            return self._mock_storyboard_frames(text)

        builder = (
            StoryboardPromptBuilder()
            .with_role()
            .with_script_format()
            .with_entities(entities_json)
            .with_visual_atoms()
        )
        if with_audio:
            builder.with_audio_atoms()
        system_prompt = builder.build(text)

        try:
            content = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请开始生成分镜帧列表，确保覆盖剧本中的所有内容。"}
                ],
            ).strip()
            logger.debug(f"Storyboard Analysis Raw Response: {content[:500]}...")

            frames = self._parse_storyboard_json(content)
            if frames is not None:
                return frames

            # First parse failed — retry once with response_format constraint
            logger.warning("Storyboard JSON parse failed, retrying with response_format=json_object...")
            retry_content = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请开始生成分镜帧列表，确保覆盖剧本中的所有内容。请务必输出合法的JSON格式。"}
                ],
                response_format={'type': 'json_object'},
            ).strip()
            logger.debug(f"Storyboard Analysis Retry Response: {retry_content[:500]}...")
            frames = self._parse_storyboard_json(retry_content)
            if frames is not None:
                return frames

            raise RuntimeError(
                "AI 模型输出的 JSON 格式不合规，自动重试后仍然失败。请重新点击生成按钮再试一次。"
            )

        except RuntimeError:
            raise  # Re-raise our own descriptive errors
        except Exception as e:
            logger.error(f"Error in storyboard analysis: {e}", exc_info=True)
            raise RuntimeError(f"分镜分析过程出错: {str(e)}")
    
    def _parse_storyboard_json(self, content: str):
        """Try to parse storyboard JSON from LLM output. Returns frames list or None on failure."""
        content = _strip_markdown_json(content)

        try:
            result = json.loads(content.strip())
            frames = result.get("frames", [])
            if not frames:
                logger.warning("Parsed JSON successfully but 'frames' array is empty")
                return None
            logger.info(f"Storyboard Analysis generated {len(frames)} frames")
            return frames
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse storyboard analysis JSON: {e}")
            return None

    def _mock_storyboard_frames(self, text: str) -> List[Dict[str, Any]]:
        """Returns mock storyboard frames for testing when API is unavailable."""
        return [
            {
                "scene_ref_name": "卧室",
                "character_ref_names": ["叶墨"],
                "prop_ref_names": ["手机"],
                "visual_atmosphere": "昏暗的卧室，窗外透进冷色调月光",
                "character_acting": "叶墨眉头紧锁，眼神迷离",
                "key_action_physics": "手机在柜上剧烈震动",
                "shot_size": "中景",
                "camera_angle": "平视",
                "camera_movement": "Static",
                "dialogue": None,
                "speaker": None,
                "bgm_prompt": "低频环境氛围",
                "sfx_prompt": "手机震动声",
            }
        ]

    def polish_storyboard_prompt(self, draft_prompt: str, assets: List[Dict[str, Any]], feedback: str = "", custom_system_prompt: str = "") -> Dict[str, str]:
        """
        Polishes the storyboard prompt using Qwen-Plus, incorporating asset references.
        Returns a dict with 'prompt_cn' and 'prompt_en'.
        """
        logger.debug(f"Polishing prompt: {draft_prompt}")

        fallback_result = {"prompt_cn": draft_prompt, "prompt_en": draft_prompt}

        if not self.is_configured:
             return fallback_result

        # Construct context about assets
        asset_context = []
        for i, asset in enumerate(assets):
            asset_type = asset.get('type', 'Unknown')
            name = asset.get('name', 'Unknown')
            desc = asset.get('description', '')
            # Map index to "Image X"
            asset_context.append(f"Image {i+1}: {asset_type} - {name} ({desc})")

        context_str = "\n".join(asset_context)

        # Use custom prompt or default, substituting placeholders
        template = custom_system_prompt.strip() if custom_system_prompt and custom_system_prompt.strip() else DEFAULT_STORYBOARD_POLISH_PROMPT
        system_prompt = template.replace("{ASSETS}", context_str).replace("{DRAFT}", draft_prompt)

        # Build user message with optional feedback (injected in user content, not system prompt)
        user_content = system_prompt
        if feedback and feedback.strip():
            user_content += f"""
[用户反馈]
{feedback.strip()}

请根据用户反馈修改提示词，只修改用户指出的问题，保持其他部分不变。
"""

        try:
            content = self.llm.chat(
                messages=[{"role": "user", "content": user_content}],
                response_format={'type': 'json_object'},
            ).strip()
            logger.debug(f"Polished Prompt Raw: {content}")

            # Parse JSON response
            content = _strip_markdown_json(content)

            try:
                result = json.loads(content.strip())
                if "prompt_cn" in result and "prompt_en" in result:
                    logger.debug(f"Polished Prompt CN: {result['prompt_cn'][:100]}...")
                    logger.debug(f"Polished Prompt EN: {result['prompt_en'][:100]}...")
                    return result
                else:
                    logger.warning("LLM response missing prompt_cn or prompt_en")
                    return fallback_result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse polish response JSON: {e}")
                return fallback_result
                
        except Exception as e:
            logger.error(f"Error polishing prompt: {e}", exc_info=True)
            return fallback_result
    def polish_video_prompt(self, draft_prompt: str, feedback: str = "", custom_system_prompt: str = "") -> Dict[str, str]:
        """
        Polishes a video generation prompt using Qwen-Plus.
        Returns bilingual prompts {prompt_cn, prompt_en}.
        """
        fallback = {"prompt_cn": draft_prompt, "prompt_en": draft_prompt}

        if not self.is_configured:
            return fallback

        system_prompt = custom_system_prompt.strip() if custom_system_prompt and custom_system_prompt.strip() else DEFAULT_VIDEO_POLISH_PROMPT

        try:
            # Build user message with optional feedback
            user_message = draft_prompt
            if feedback and feedback.strip():
                user_message = f"""[当前提示词]
{draft_prompt}

[用户反馈]
{feedback.strip()}

请根据用户反馈修改提示词，只修改用户指出的问题，保持其他部分不变。"""

            content = self.llm.chat(
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message}
                ],
                response_format={'type': 'json_object'},
            ).strip()
            logger.debug(f"Video Prompt Polish Raw: {content[:200]}...")

            # Parse JSON
            content = _strip_markdown_json(content)

            try:
                result = json.loads(content.strip())
                if "prompt_cn" in result and "prompt_en" in result:
                    return result
                else:
                    logger.warning("Video polish missing bilingual keys")
                    return fallback
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse video polish JSON: {e}")
                return fallback

        except Exception:
            logger.exception("Failed to polish video prompt")
            return fallback

    def slice_video_prompt_timeline(
        self,
        video_prompt: str,
        duration_s: int,
        *,
        segment_seconds: int = 3,
        location: Optional[str] = None,
        characters: Optional[List[str]] = None,
        sound: Optional[str] = None,
    ) -> str:
        """Slice a continuous video prompt into per-segment instructions.

        Long-shot I2V backends (Seedance 2 / Veo / future Wan
        long-form) produce noticeably better motion when the prompt
        carries explicit per-second direction instead of one sentence
        for the whole clip. This method asks the LLM to redistribute
        the action across ``ceil(duration_s / segment_seconds)`` time
        windows and wrap each window in an ``<nA-B>...</nA-B>`` tag,
        mirroring the convention popularised by huobao-drama.

        Output shape::

            <location>卧室</location><role>叶墨</role>
            <n0-3>叶墨眉头紧锁，烦躁地翻身</n0-3>
            <n3-6>手机震动声变大，叶墨睁眼</n3-6>
            <sound>手机震动声</sound>

        On any failure the original ``video_prompt`` is returned
        unchanged — the caller's existing video gen call still works
        even if the slicer's LLM call falls over.
        """
        if not video_prompt or duration_s <= 0:
            return video_prompt or ""
        if not self.is_configured:
            return self._mock_slice_video_prompt_timeline(
                video_prompt, duration_s, segment_seconds,
                location, characters, sound,
            )

        segments = self._segment_windows(duration_s, segment_seconds)
        meta_block = self._render_timeline_meta(location, characters, sound)
        system_prompt = self._build_timeline_prompt(segments, meta_block)

        try:
            content = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": video_prompt},
                ],
            ).strip()
            sliced = _strip_markdown_json(content) if "```" in content else content
            # Sanity check: must contain at least one <n...> tag.
            if "<n" not in sliced:
                logger.warning("Timeline slicer output missing <n> tags, returning original")
                return video_prompt
            return sliced
        except Exception as e:
            logger.warning(f"slice_video_prompt_timeline failed, returning original: {e}")
            return video_prompt

    @staticmethod
    def _segment_windows(duration_s: int, segment_seconds: int) -> List[tuple]:
        """Generate (start, end) windows covering ``[0, duration_s]``.

        Last window may be shorter than ``segment_seconds`` so the sum
        equals exactly ``duration_s`` (no rounding-up overshoot).
        """
        windows = []
        start = 0
        while start < duration_s:
            end = min(start + segment_seconds, duration_s)
            windows.append((start, end))
            start = end
        return windows

    @staticmethod
    def _render_timeline_meta(
        location: Optional[str],
        characters: Optional[List[str]],
        sound: Optional[str],
    ) -> str:
        parts = []
        if location:
            parts.append(f"<location>{location}</location>")
        if characters:
            for ch in characters:
                parts.append(f"<role>{ch}</role>")
        if sound:
            parts.append(f"<sound>{sound}</sound>")
        return "".join(parts)

    @staticmethod
    def _build_timeline_prompt(segments: List[tuple], meta_block: str) -> str:
        seg_template = "\n".join(f"<n{a}-{b}>...</n{a}-{b}>" for a, b in segments)
        return (
            "你是视频导演,把一个连续的视频提示词重新分配到固定时间窗口里。\n"
            "**严格输出纯文本**,不要 JSON,不要 Markdown 代码块。\n\n"
            f"# 元数据(原样保留在输出最前面)\n{meta_block or '(无)'}\n\n"
            "# 时间窗口骨架(必须用且只用这些标签)\n"
            f"{seg_template}\n\n"
            "# 规则\n"
            "1. 标签数量必须与上面骨架一致,不增不减。\n"
            "2. 每个窗口里描述该时段画面里发生的主要动作 + 微表情/物理细节。\n"
            "3. 用户给的提示词内容必须完整覆盖,不要丢失情节。\n"
            "4. 全部使用简体中文。\n"
            "5. 元数据放在第一行,然后换行,然后是按顺序的时间窗口。"
        )

    @staticmethod
    def _mock_slice_video_prompt_timeline(
        video_prompt: str,
        duration_s: int,
        segment_seconds: int,
        location: Optional[str],
        characters: Optional[List[str]],
        sound: Optional[str],
    ) -> str:
        """Offline fallback — produces a deterministic skeleton so tests
        can exercise the field-write paths without needing an LLM."""
        windows = ScriptProcessor._segment_windows(duration_s, segment_seconds)
        meta = ScriptProcessor._render_timeline_meta(location, characters, sound)
        body = "\n".join(f"<n{a}-{b}>{video_prompt}</n{a}-{b}>" for a, b in windows)
        return f"{meta}\n{body}" if meta else body

    def polish_r2v_prompt(self, draft_prompt: str, slots: List[Dict[str, str]], feedback: str = "", custom_system_prompt: str = "") -> Dict[str, str]:
        """
        Polishes a R2V (Reference-to-Video) prompt using Qwen-Plus.
        R2V requires explicit character references using character1, character2, character3 tags.
        Returns bilingual prompts {prompt_cn, prompt_en}.
        """
        fallback = {"prompt_cn": draft_prompt, "prompt_en": draft_prompt}

        if not self.is_configured:
            return fallback

        # Build slot context - using character1/2/3 format
        slot_context = []
        for i, slot in enumerate(slots):
            char_id = f"character{i + 1}"
            slot_context.append(f"- {char_id}: {slot['description']}")
        slot_context_str = "\n".join(slot_context) if slot_context else "No reference videos provided."

        # Use custom prompt or default, substituting {SLOTS} placeholder
        template = custom_system_prompt.strip() if custom_system_prompt and custom_system_prompt.strip() else DEFAULT_R2V_POLISH_PROMPT
        system_prompt = template.replace("{SLOTS}", slot_context_str)

        try:
            # Build user message with optional feedback
            user_message = draft_prompt
            if feedback and feedback.strip():
                user_message = f"""[当前提示词]
{draft_prompt}

[用户反馈]
{feedback.strip()}

请根据用户反馈修改提示词，只修改用户指出的问题，保持其他部分不变。"""

            content = self.llm.chat(
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message}
                ],
                response_format={'type': 'json_object'},
            ).strip()
            logger.debug(f"R2V Polished Raw: {content[:200]}...")

            # Parse JSON
            content = _strip_markdown_json(content)

            try:
                result = json.loads(content.strip())
                if "prompt_cn" in result and "prompt_en" in result:
                    return result
                else:
                    logger.warning("R2V polish missing bilingual keys")
                    return fallback
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse R2V polish JSON: {e}")
                return fallback

        except Exception:
            logger.exception("Failed to polish R2V prompt")
            return fallback
