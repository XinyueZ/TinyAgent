import os

import requests

from tiny_agent.tools.decorator import coding_tool, tool


@coding_tool()
@tool()
def get_voice(select=-1) -> str:
    """Get voice from minimax cloned voice list.

    Args:
        select (int, optional): Select voice. Defaults to -1.

    Returns:
        str: voice_id, a selected voice id

    """
    url = "https://api.minimax.io/v1/get_voice"
    headers = {
        "Authorization": f"Bearer {os.environ.get('MINIMAX_API_KEY')}",
        "Content-Type": "application/json",
    }
    data = {
        "voice_type": "voice_cloning",
    }

    response = requests.post(url, headers=headers, json=data, timeout=3)
    voice_id = response.json()["voice_cloning"][select]["voice_id"]
    return voice_id


@coding_tool()
@tool()
def tts(text: str, lang: str) -> str:
    """Convert text to speech using Minimax API.

    Args:
        text (str): The input text to be synthesized into speech
        lang (str): Target language for synthesis. Supported languages:
            Chinese, 'Chinese,Yue', English, Arabic, Russian, Spanish, French, Portuguese,
            German, Turkish, Dutch, Ukrainian, Vietnamese, Indonesian, Japanese,
            Italian, Korean, Thai, Polish, Romanian, Greek, Czech, Finnish, Hindi,
            Bulgarian, Danish, Hebrew, Malay, Persian, Slovak, Swedish, Croatian,
            Filipino, Hungarian, Norwegian, Slovenian, Catalan, Nynorsk, Tamil,
            Afrikaans

    Returns:
        str: URL of the generated audio file
    """
    voice_id = get_voice(-1)
    url = "https://api.minimax.io/v1/t2a_v2"
    headers = {
        "Authorization": f"Bearer {os.environ.get('MINIMAX_API_KEY')}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "speech-2.8-hd",
        "text": f"{text}",
        "stream": False,
        "voice_setting": {
            "voice_id": f"{voice_id}",
            "speed": 1,
            "vol": 1,
            "pitch": 0,
            "emotion": "fluent",
        },
        # "audio_setting": {
        #     "sample_rate": 32000,
        #     "bitrate": 128000,
        #     "format": "mp3",
        #     "channel": 1
        # },
        "pronunciation_dict": {
            "tone": ["Omg/Oh my god", "btw/By the way", "z.B/wie zum Beispiel"]
        },
        "language_boost": f"{lang}",
        "voice_modify": {
            "pitch": 0,
            "intensity": 0,
            "timbre": 0,
            "sound_effects": "spacious_echo",
        },
        "output_format": "url",
    }

    response = requests.post(url, headers=headers, json=data, timeout=3)
    download_url = response.json()["data"]["audio"]
    return download_url
