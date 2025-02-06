from enum import Enum


class SettingsKeys(Enum):
    LOCAL_WHISPER = "Built-in Speech2Text"
    WHISPER_ENDPOINT = "Speech2Text (Whisper) Endpoint"
    WHISPER_SERVER_API_KEY = "Speech2Text (Whisper) API Key"
    WHISPER_REAL_TIME = "Real Time Speech Transcription"
    WHISPER_MODEL = "Built-in Speech2Text Model"
    WHISPER_ARCHITECTURE = "Built-in Speech2Text Architecture"
    WHISPER_CPU_COUNT = "Whisper CPU Thread Count (Experimental)"
    WHISPER_COMPUTE_TYPE = "Whisper Compute Type (Experimental)"
    WHISPER_BEAM_SIZE = "Whisper Beam Size (Experimental)"
    WHISPER_VAD_FILTER = "Use Whisper VAD Filter (Experimental)"
    AUDIO_PROCESSING_TIMEOUT_LENGTH = "Audio Processing Timeout (seconds)"
    SILERO_SPEECH_THRESHOLD = "Silero Speech Threshold"
    USE_TRANSLATE_TASK = "Translate Speech to English Text"
    WHISPER_LANGUAGE_CODE = "Whisper Language Code"
    S2T_SELF_SIGNED_CERT = "S2T Server Self-Signed Certificates"
    LLM_ARCHITECTURE = "Built-in AI Architecture"
    USE_PRESCREEN_AI_INPUT = "Use Pre-Screen AI Input"
    LOCAL_LLM = "Built-in AI Processing"
    LOCAL_LLM_MODEL = "AI Model"
    LLM_ENDPOINT = "AI Server Endpoint"
    LLM_SERVER_API_KEY = "AI Server API Key"


class Architectures(Enum):
    CPU = ("CPU", "cpu")
    CUDA = ("CUDA (Nvidia GPU)", "cuda")

    @property
    def label(self):
        return self._value_[0]

    @property
    def architecture_value(self):
        return self._value_[1]


class FeatureToggle:
    DOCKER_SETTINGS_TAB = False
    DOCKER_STATUS_BAR = False
    POST_PROCESSING = False
    PRE_PROCESSING = False
