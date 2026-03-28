import os
import re
import tempfile
from typing import Optional

from openai import OpenAI


VOICE_INSTRUCTIONS = (
    "Speak as a warm, dramatic narrator for a children's adventure story aged 8-12. "
    "Use natural pacing, emphasise dramatic moments, and speak with wonder and excitement."
)

VOICE = "fable"
MODEL = "gpt-4o-mini-tts"


def _strip_markdown(text: str) -> str:
    """Remove markdown symbols that would be read aloud literally by TTS."""
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'`+', '', text)
    return text.strip()


class Voice:
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        self.enabled = bool(api_key)
        self.client: Optional[OpenAI] = OpenAI(api_key=api_key) if self.enabled else None

    def speak(self, text: str) -> Optional[bytes]:
        if not self.enabled:
            return None
        try:
            response = self.client.audio.speech.create(
                model=MODEL,
                voice=VOICE,
                input=_strip_markdown(text),
                instructions=VOICE_INSTRUCTIONS,
                response_format="mp3",
            )
            return response.content
        except Exception as e:
            print(f"OpenAI TTS error: {e}")
            return None

    def speak_to_file(self, text: str) -> Optional[str]:
        """Write audio to a temporary file. Used for opening scenes."""
        try:
            audio = self.speak(text)
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
    path = voice.speak_to_file("Welcome, brave adventurer. Your quest begins now...")
    if path:
        print(f"Audio written to: {path}")
    else:
        print("No audio (OPENAI_API_KEY not set or call failed).")
