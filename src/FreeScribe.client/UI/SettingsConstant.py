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
    LOCAL_LLM = "Built-in AI Processing"
    LOCAL_LLM_MODEL = "AI Model"
    LOCAL_LLM_CONTEXT_WINDOW = "AI Context Window"
    LLM_ENDPOINT = "AI Server Endpoint"
    LLM_SERVER_API_KEY = "AI Server API Key"
    Enable_Word_Count_Validation = "Enable Word Count Validation"
    Enable_AI_Conversation_Validation = "Enable AI Conversation Validation"
    USE_LOW_MEM_MODE = "Use Low Memory Mode"
    ENABLE_HALLUCINATION_CLEAN = "Enable Hallucination Cleaning (Experimental)"
    ENABLE_FILE_LOGGER = "Enable File Log (Encrypted)"
    STORE_NOTES_LOCALLY ="Store Notes Locally (Encrypted)"
    STORE_RECORDINGS_LOCALLY = "Store Recordings Locally (Encrypted)"
    USE_PRE_PROCESSING = "Use Pre-Processing"
    WHISPER_INITIAL_PROMPT = "Whisper Initial Prompt"
    BEST_OF = "best_of"
    FACTUAL_CONSISTENCY_VERIFICATION = "Factual Consistency Verification (Experimental)"
    GOOGLE_MAPS_API_KEY = "Google Maps API Key"

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
    INTENT_ACTION = False
    HALLUCINATION_CLEANING = False
    FACTS_CHECK = False
    BEST_OF = False
    LLM_CONVO_PRESCREEN = False
    FACTUAL_CONSISTENCY_VERIFICATION = False


DEFAULT_CONTEXT_WINDOW_SIZE = 4096
