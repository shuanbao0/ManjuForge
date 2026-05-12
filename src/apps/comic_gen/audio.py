import os
import time
from typing import Dict, Any, List
from .models import StoryboardFrame, Character, GenerationStatus
from ...utils import get_logger
from ...audio.tts import TTSProcessor

logger = get_logger(__name__)

class AudioGenerator:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.data_root = self.config.get('data_root', 'output')
        self.output_dir = self.config.get('output_dir', os.path.join(self.data_root, 'audio'))
        
        # Initialize TTS Processor
        try:
            self.tts = TTSProcessor()
            logger.info("TTS Processor initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize TTS Processor: {e}. Using mock mode.")
            self.tts = None

    def get_available_voices(self) -> List[Dict[str, str]]:
        """Returns a list of available voices."""
        if self.tts:
            voices_dict = TTSProcessor.list_voices()
            return [
                {"id": key, "name": f"{meta['name']} - CosyVoice", "gender": meta.get('gender', 'Unknown'), "model": meta.get('model', 'cosyvoice-v2')}
                for key, meta in voices_dict.items()
            ]
        else:
            return [
                {"id": "longxiaochun", "name": "龙小淳 (知性女) - CosyVoice", "gender": "Female"},
                {"id": "longyue", "name": "龙悦 (温柔女) - CosyVoice", "gender": "Female"},
                {"id": "longcheng", "name": "龙诚 (睿智青年) - CosyVoice", "gender": "Male"},
                {"id": "longshu", "name": "龙书 (播报男) - CosyVoice", "gender": "Male"},
            ]

    def generate_dialogue(self, frame: StoryboardFrame, character: Character, speed: float = 1.0, pitch: float = 1.0, volume: int = 50) -> StoryboardFrame:
        """Generates TTS audio for the dialogue."""
        if not frame.dialogue:
            return frame

        frame.status = GenerationStatus.PROCESSING

        text = frame.dialogue

        logger.info(f"Generating dialogue for {character.name}: {text} (Speed: {speed}, Pitch: {pitch}, Volume: {volume})")

        if not self.tts:
            frame.status = GenerationStatus.FAILED
            frame.audio_error = "TTS service not available. Check DASHSCOPE_API_KEY configuration."
            logger.warning(f"TTS not initialized, cannot generate audio for frame {frame.id}")
            return frame

        if not character.voice_id:
            frame.status = GenerationStatus.FAILED
            frame.audio_error = f"No voice assigned to character '{character.name}'. Please assign a voice first."
            logger.warning(f"No voice_id for character {character.name}, cannot generate audio")
            return frame

        return self._real_generate_dialogue(frame, character, text, speed, pitch, volume)

    def _real_generate_dialogue(self, frame: StoryboardFrame, character: Character, text: str, speed: float, pitch: float, volume: int) -> StoryboardFrame:
        """Generate dialogue using real TTS, routed by the active instance vendor."""
        try:
            output_path = os.path.join(self.output_dir, 'dialogue', f"{frame.id}.mp3")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            voice = character.voice_id

            # Route by vendor of the currently-scoped TTS ModelInstance.
            # Each vendor's client lives under src/audio/<vendor>_tts.py and
            # exposes the same ``synthesize_*(text, output_path, *, voice,
            # speech_rate, pitch_rate, volume) -> (path, latency_ms,
            # request_id)`` shape so the dispatch is one switch. No vendor
            # default — the user must configure a TTS instance.
            from src.runtime import current_instance
            from src.models.instance import InstanceType, InstanceNotConfiguredError
            inst = current_instance()
            if inst is None:
                raise InstanceNotConfiguredError(InstanceType.TTS)
            vendor = inst.vendor_id

            if vendor == "minimax":
                from src.audio.minimax_tts import synthesize_minimax_tts
                synthesize_minimax_tts(
                    text, output_path,
                    voice=voice, speech_rate=speed, pitch_rate=pitch, volume=volume,
                )
            elif vendor == "elevenlabs":
                from src.audio.elevenlabs_tts import synthesize_elevenlabs_tts
                synthesize_elevenlabs_tts(
                    text, output_path,
                    voice=voice, speech_rate=speed, pitch_rate=pitch, volume=volume,
                )
            elif vendor == "fish-audio":
                from src.audio.fish_tts import synthesize_fish_tts
                synthesize_fish_tts(
                    text, output_path,
                    voice=voice, speech_rate=speed, pitch_rate=pitch, volume=volume,
                )
            elif vendor == "cartesia":
                from src.audio.cartesia_tts import synthesize_cartesia_tts
                synthesize_cartesia_tts(
                    text, output_path,
                    voice=voice, speech_rate=speed, pitch_rate=pitch, volume=volume,
                )
            elif vendor == "dashscope":
                # DashScope CosyVoice. Constructor defaults are ignored at
                # call time — ``TTSProcessor`` resolves the model via the
                # bound instance.
                self.tts.synthesize(text, output_path, voice=voice, speech_rate=speed, pitch_rate=pitch, volume=volume)
            else:
                raise ValueError(
                    f"未支持的 TTS vendor: {vendor!r}。请在 设置 → 模型实例 中"
                    "选择 dashscope / minimax / elevenlabs / fish-audio / cartesia 之一。"
                )

            rel_path = os.path.relpath(output_path, self.data_root)
            frame.audio_url = rel_path
            frame.status = GenerationStatus.COMPLETED

        except Exception as e:
            logger.error(f"TTS generation failed for frame {frame.id}: {e}")
            frame.status = GenerationStatus.FAILED
            frame.audio_error = f"TTS generation failed: {str(e)}"

        return frame

    def _mock_generate_dialogue(self, frame: StoryboardFrame, character: Character, text: str, speed: float, pitch: float, volume: int) -> StoryboardFrame:
        """Mock fallback — marks frame as FAILED instead of writing dummy bytes."""
        frame.status = GenerationStatus.FAILED
        frame.audio_error = "TTS service unavailable (mock mode)"
        logger.warning(f"Mock generate_dialogue called for frame {frame.id} — marking as FAILED")
        return frame

    @staticmethod
    def _fallback_sfx_prompt(frame: StoryboardFrame) -> str:
        """Best-effort fallback when the LLM didn't emit ``sfx_prompt`` — use the
        visible action description so SFX still has *some* anchor text."""
        return frame.sfx_prompt or frame.action_description or ""

    @staticmethod
    def _fallback_bgm_prompt(frame: StoryboardFrame) -> str:
        """Fallback music mood — uses visual atmosphere when no explicit prompt."""
        return frame.bgm_prompt or frame.visual_atmosphere or ""

    def generate_sfx(self, frame: StoryboardFrame) -> StoryboardFrame:
        """Generates sound effects driven by ``frame.sfx_prompt``.

        The SFX generator backend (MMAudio / SeedAudio / etc.) is not wired
        yet — this method records the prompt resolution and writes a marker
        file so the downstream export step can detect "intended but not yet
        rendered" SFX. When a real backend is added it should consume
        ``self._fallback_sfx_prompt(frame)`` as the driving prompt.
        """
        frame.status = GenerationStatus.PROCESSING

        try:
            prompt = self._fallback_sfx_prompt(frame)
            logger.info(f"SFX prompt for frame {frame.id}: {prompt!r}")

            output_path = os.path.join(self.output_dir, 'sfx', f"{frame.id}.mp3")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Marker file — replaced when a real SFX vendor is plugged in.
            with open(output_path, 'wb') as f:
                f.write(b'')

            frame.sfx_url = os.path.relpath(output_path, self.data_root)
            frame.status = GenerationStatus.COMPLETED

        except Exception as e:
            logger.error(f"Failed to generate SFX for frame {frame.id}: {e}")
            frame.status = GenerationStatus.FAILED

        return frame

    def generate_sfx_from_video(self, frame: StoryboardFrame) -> StoryboardFrame:
        """Generates SFX based on video content (Video-to-Audio).

        Like ``generate_sfx`` this is a placeholder until a V2A vendor is
        integrated; it just records intent so the rest of the pipeline keeps
        working.
        """
        if not frame.video_url:
            return frame

        logger.info(f"Generating SFX from video for frame {frame.id}")

        output_path = os.path.join(self.output_dir, 'sfx', f"{frame.id}_v2a.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'wb') as f:
            f.write(b'')

        frame.sfx_url = os.path.relpath(output_path, self.data_root)
        return frame

    def generate_bgm(self, frame: StoryboardFrame) -> StoryboardFrame:
        """Generates BGM driven by ``frame.bgm_prompt``.

        Mirrors ``generate_sfx``: placeholder marker output today, but the
        prompt resolution is already in place so swapping in a real
        MusicGen vendor only changes the file-write step.
        """
        prompt = self._fallback_bgm_prompt(frame)
        logger.info(f"BGM prompt for frame {frame.id}: {prompt!r}")

        output_path = os.path.join(self.output_dir, 'bgm', f"{frame.id}.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'wb') as f:
            f.write(b'')

        frame.bgm_url = os.path.relpath(output_path, self.data_root)
        return frame
