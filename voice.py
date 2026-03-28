import os
import re
import tempfile
from typing import Optional

from dotenv import set_key
from elevenlabs import ElevenLabs


def _strip_markdown(text: str) -> str:
    """Remove markdown symbols that would be read aloud literally by TTS."""
    # Bold and italic: ***text***, **text**, *text*, __text__, _text_
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', text)
    # Headers: ## Heading
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Bullet points: - item or * item
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    # Backticks
    text = re.sub(r'`+', '', text)
    return text.strip()

ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

# Fallback list used when the API key lacks voices_read permission.
# These are ElevenLabs' stable built-in voices.
FALLBACK_VOICES = [
    {"name": "Adam",     "voice_id": "pNInz6obpgDQGcFmaJgB", "category": "premade"},
    {"name": "Antoni",   "voice_id": "ErXwobaYiN019PkySvjV", "category": "premade"},
    {"name": "Arnold",   "voice_id": "VR6AewLTigWG4xSOukaG", "category": "premade"},
    {"name": "Callum",   "voice_id": "N2lVS1w4EtoT3dr4eOWO", "category": "premade"},
    {"name": "Charlie",  "voice_id": "IKne3meq5aSn9XLyUdCD", "category": "premade"},
    {"name": "Charlotte","voice_id": "XB0fDUnXU5powFXDhCwa", "category": "premade"},
    {"name": "Clyde",    "voice_id": "2EiwWnXFnvU5JabPnv8n", "category": "premade"},
    {"name": "Daniel",   "voice_id": "onwK4e9ZLuTAKqWW03F9", "category": "premade"},
    {"name": "Dave",     "voice_id": "CYw3kZ02Hs0563khs1Fj", "category": "premade"},
    {"name": "Domi",     "voice_id": "AZnzlk1XvdvUeBnXmlld", "category": "premade"},
    {"name": "Dorothy",  "voice_id": "ThT5KcBeYPX3keUQqHPh", "category": "premade"},
    {"name": "Drew",     "voice_id": "29vD33N1CtxCmqQRPOHJ", "category": "premade"},
    {"name": "Elli",     "voice_id": "MF3mGyEYCl7XYWbV9V6O", "category": "premade"},
    {"name": "Emily",    "voice_id": "LcfcDJNUP1GQjkzn1xUU", "category": "premade"},
    {"name": "Ethan",    "voice_id": "g5CIjZEefAph4nQFvHAz", "category": "premade"},
    {"name": "Fin",      "voice_id": "D38z5RcWu1voky8WS1ja", "category": "premade"},
    {"name": "Freya",    "voice_id": "jsCqWAovK2LkecY7zXl4", "category": "premade"},
    {"name": "Gigi",     "voice_id": "jBpfuIE2acCO8z3wKNLl", "category": "premade"},
    {"name": "Giovanni", "voice_id": "zcAOhNBS3c14rBihAFp1", "category": "premade"},
    {"name": "Grace",    "voice_id": "oWAxZDx7w5VEj9dCyTzz", "category": "premade"},
    {"name": "Harry",    "voice_id": "SOYHLrjzK2X1ezoPC9cr", "category": "premade"},
    {"name": "James",    "voice_id": "ZQe5CZNOzWyzPSCn5a3c", "category": "premade"},
    {"name": "Jeremy",   "voice_id": "bVMeCyTHy58xNoL34h3p", "category": "premade"},
    {"name": "Jessie",   "voice_id": "t0jbNlBVZ17f02VDIeMI", "category": "premade"},
    {"name": "Joseph",   "voice_id": "Zlb1dXrM653N07WRdFW3", "category": "premade"},
    {"name": "Josh",     "voice_id": "TxGEqnHWrfWFTfGW9XjX", "category": "premade"},
    {"name": "Liam",     "voice_id": "TX3LPaxmHKxFdv7VOQHJ", "category": "premade"},
    {"name": "Lily",     "voice_id": "pFZP5JQG7iQjIQuC4Bku", "category": "premade"},
    {"name": "Matilda",  "voice_id": "XrExE9yKIg1WjnnlVkGX", "category": "premade"},
    {"name": "Matthew",  "voice_id": "Yko7PKHZNXotIFUBG7I9", "category": "premade"},
    {"name": "Michael",  "voice_id": "flq6f7ib4F8Rfdo7Am25", "category": "premade"},
    {"name": "Mimi",     "voice_id": "zrHiDhphv9ZnVXBqCLjz", "category": "premade"},
    {"name": "Nicole",   "voice_id": "piTKgcLEGmPE4e6mEKli", "category": "premade"},
    {"name": "Patrick",  "voice_id": "ODq5zmih8GrVes37Dx9K", "category": "premade"},
    {"name": "Paul",     "voice_id": "5Q0t7uMcjvnagumLfvZi", "category": "premade"},
    {"name": "Rachel",   "voice_id": "21m00Tcm4TlvDq8ikWAM", "category": "premade"},
    {"name": "Sam",      "voice_id": "yoZ06aMxZJJ28mfd3POQ", "category": "premade"},
    {"name": "Sarah",    "voice_id": "EXAVITQu4vr4xnSDxMaL", "category": "premade"},
    {"name": "Serena",   "voice_id": "pMsXgVXv3BLzUgSXRplE", "category": "premade"},
    {"name": "Thomas",   "voice_id": "GBv7mTt0atIp3Br8iCZE", "category": "premade"},
]


class Voice:
    def __init__(self):
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        self.enabled = bool(api_key)
        self.available_voices: list = []
        self.needs_voice_selection = False
        self.voice_id: Optional[str] = None
        self.client: Optional[ElevenLabs] = None

        if not self.enabled:
            return

        self.client = ElevenLabs(api_key=api_key)

        env_voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
        if env_voice_id:
            self.voice_id = env_voice_id
        else:
            try:
                response = self.client.voices.get_all()
                fetched = sorted(
                    [
                        {"name": v.name, "voice_id": v.voice_id, "category": v.category}
                        for v in response.voices
                        if v.category in ("premade", "professional")
                    ],
                    key=lambda v: v["name"],
                )
                self.available_voices = fetched if fetched else FALLBACK_VOICES
            except Exception as e:
                print(f"ElevenLabs voice fetch failed ({e}), using built-in voice list.")
                self.available_voices = FALLBACK_VOICES
            self.needs_voice_selection = True

    def list_voices(self) -> list:
        return self.available_voices

    def set_voice(self, voice_id: str) -> None:
        self.voice_id = voice_id
        self.needs_voice_selection = False
        try:
            set_key(ENV_FILE, "ELEVENLABS_VOICE_ID", voice_id)
        except Exception as e:
            print(f"Could not persist voice ID to .env: {e}")

    def speak(self, text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
        resolved_id = voice_id or self.voice_id
        if not self.enabled or resolved_id is None:
            return None
        try:
            audio_iter = self.client.text_to_speech.convert(
                voice_id=resolved_id,
                text=_strip_markdown(text),
                model_id="eleven_turbo_v2",
            )
            return b"".join(audio_iter)
        except Exception as e:
            print(f"ElevenLabs TTS error: {e}")
            return None

    def speak_to_file(self, text: str, voice_id: Optional[str] = None) -> Optional[str]:
        """Write audio to a temporary file. Used for previews and opening scenes."""
        try:
            audio = self.speak(text, voice_id=voice_id)
            if audio is None:
                return None
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio)
                return f.name
        except Exception as e:
            print(f"Error writing audio file: {e}")
            return None

    def speak_to_persistent_file(self, text: str, message_id: int, audio_dir: str) -> Optional[str]:
        """Write audio to a named persistent file keyed to the message ID."""
        try:
            audio = self.speak(text)
            if audio is None:
                return None
            os.makedirs(audio_dir, exist_ok=True)
            path = os.path.join(audio_dir, f"message_{message_id}.mp3")
            with open(path, "wb") as f:
                f.write(audio)
            return path
        except Exception as e:
            print(f"Error writing persistent audio file: {e}")
            return None


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    voice = Voice()
    if voice.needs_voice_selection:
        print("Available voices:")
        for v in voice.list_voices():
            print(f"  {v['name']} ({v['category']}) — {v['voice_id']}")
    else:
        path = voice.speak_to_file("Welcome, brave adventurer. Your quest begins now...")
        if path:
            print(f"Audio written to: {path}")
        else:
            print("No audio (ElevenLabs key not set or call failed).")
