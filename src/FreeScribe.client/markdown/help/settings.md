# Settings Documentation

## General Settings

### Show Welcome Message

**Description**: Display a welcome message on application startup.  
**Default**: `true`  
**Type**: boolean

### Show Scrub PHI

**Description**: Enable or disable PHI (Protected Health Information) scrubbing. This feature applies to local LLMs (Large Language Models) and private networks. It is used to remove potentially sensitive data before sending it to the model. For internet-facing endpoints, this feature is always enabled regardless of the setting.  
**Default**: `false`  
**Type**: boolean

---

## Speech-to-Text Settings (Whisper)

### Built-in Speech2Text

**Description**: Enable the built-in Speech-to-Text feature.  
**Default**: `true`  
**Type**: boolean

### Real-time Speech Transcription

**Description**: Enable real-time transcription of speech to text.  
**Default**: `true`  
**Type**: boolean

### Built-in Speech2Text Model

**Description**: Select the model size for Whisper transcription. Options include small, medium, and large model sizes.  
**Default**: `medium`  
**Type**: dropdown

### Built-in Speech2Text Architecture

Note: Available only if GPU selected while installing

**Description**: Specify the hardware architecture used for Whisper Speech-to-Text processing. Options include `CUDA (Nvidia GPU)` and `CPU` available architectures.  
**Default**: `CPU`  
**Type**: dropdown

### Speech2Text (Whisper) Endpoint

**Description**: API endpoint for Whisper service. This endpoint processes audio files from the client. By default, it points to the local Whisper container provided by ClinicianFOCUS.  
**Default**: `https://localhost:2224/whisperaudio`  
**Type**: string

### Speech2Text (Whisper) API Key

**Description**: API key for accessing the Whisper endpoint.  
**Default**: (empty)  
**Type**: string

### Speech2Text Server Self-Signed Certificates

**Description**: Allow self-signed certificates for the Speech-to-Text server connection.  
**Default**: `false`  
**Type**: boolean

---

## AI Settings (LLM)

### Built-in AI processing

**Description**: Enable or disable the use of a local large language model. This will run on your device if enabled.  
**Default**: `true`  
**Type**: boolean

### Built-in AI Architecture

Note: Available only if GPU selected while installing

**Description**: Choose the hardware architecture for running the local LLM. Options may include `CUDA (Nvidia GPU)` and `CPU`.  
**Default**: `CPU`  
**Type**: dropdown

### AI Model

**Description**: Select the local LLM model to use.  
**Default**: `gemma-2-2b-it-Q8_0.gguf`  
**Type**: dropdown

### AI Server Endpoint

**Description**: Endpoint for the local AI model server.  
**Default**: `https://localhost:3333`  
**Type**: string

### AI Server Self-Signed Certificates

**Description**: Allow self-signed certificates for the AI model server connection.  
**Default**: `false`  
**Type**: boolean

### AI Server API Key

**Description**: API key for accessing the OpenAI API if a remote model is used.  
**Default**: `None`  
**Type**: string

---

## Advanced Settings

### Audio Processing Timeout (seconds)

**Description**: Timeout in seconds for audio processing tasks.  
**Default**: `180`  
**Type**: integer

### Whisper Beam Size (Experimental)

**Description**: Set the beam search size for Whisper's transcription process.  
**Default**: `5`  
**Type**: integer

### Whisper CPU Thread Count (Experimental)

**Description**: Number of CPU threads allocated for Whisper processing.  
**Default**: `Auto (Detects based on machine)`  
**Type**: integer

### Use Whisper VAD Filter (Experimental)

**Description**: Enable the use of Voice Activity Detection (VAD) to improve transcription accuracy.  
**Default**: `false`  
**Type**: boolean

### Whisper Compute Type (Experimental)

**Description**: Specify the data type for Whisper's computations (e.g., `float16`, `float32`). Note that your selected compute type may be automatically overridden and forced to a different type if it's not compatible with your system's hardware or configuration.
**Default**: `float16`  
**Type**: string

### Translate Speech to English Text

**Description**: Enable automatic translation of transcribed speech to English.  
**Default**: `false`  
**Type**: boolean

### Whisper Language Code

**Description**: Specify the language code for transcription. If left empty, the language is auto-detected.  
**Default**: `None (Auto Detect)`  
**Type**: string

### Use Pre-Screen AI Input

**Description**: Pre-screen input data before processing by the AI model.  
**Default**: `true`  
**Type**: boolean

<!-- ### Use best_of

**Description**: Enable the use of multiple result candidates and choose the best output.
**Default**: `false`
**Type**: boolean -->

### Temperature

**Description**: Control randomness in model output. Lower values produce more deterministic results.  
**Default**: `0.1`  
**Type**: float

### tfs

**Description**: Truncated frequency sampling parameter for controlling model output diversity.  
**Default**: `0.97`  
**Type**: float

### top_k

**Description**: Limit the number of top tokens considered during generation.  
**Default**: `30`  
**Type**: integer

### top_p

**Description**: Control the probability threshold for top-p (nucleus) sampling.  
**Default**: `0.4`  
**Type**: float

### AI Context Window

**Description**: Specify the Context Window Size (in tokens).
**Default**: `4096`  
**Type**: string

### Enable Word Count Validation

**Description**: When generating a note, check if the text is more than 50 words, as it might create invalid results.
**Default**: `true`  
**Type**: boolean

### Enable AI Conversation Validation

**Description**: When generating a note, check if the text is related to a clinical context, as it might create invalid results.
**Default**: `false`  
**Type**: boolean

---

## Prompting Settings

### Pre Conversation Instruction

**Description**: Template prompt for generating SOAP notes based on conversations.  
**Default**: See predefined text in settings.  
**Type**: string

### Post Conversation Instruction

**Description**: Additional instructions on how the AI should structure generated notes, ensuring accuracy and proper formatting in SOAP format.  
**Default**: See predefined text in settings.  
**Type**: string
