# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

VoiceAgent is a real-time voice-driven AI assistant with a Kaltsit persona (知性温柔的二次元角色). Pipeline:

```
Microphone → ASR (DashScope Qwen3) → LLM (DeepSeek) → TTS (DashScope Qwen3 voice clone) → Speaker
```

Two interaction modes: console (PTT with Space bar) and GUI (PyQt6 frameless overlay with character portrait + subtitles).

## Run commands

```bash
# Console mode (PTT: hold Space to speak, Esc to quit, type text + Enter to chat)
python main.py

# GUI mode (PyQt6 window with portrait, subtitles, input bar, PTT button)
python app.py

# Latency benchmarks
python test/test_latency.py
```

No build/lint/test tooling exists. Python 3.13, no `pyproject.toml`, `requirements.txt`, or `setup.py`.

## Architecture

### Client registry pattern (`clients/`)

`clients/client.py` defines a `Client` ABC with a class-level `registry` dict. Implementations register via `@Client.register("name")`:

| Name | File | What it wraps |
|------|------|---------------|
| `LLM` | `clients/LLM.py` | DeepSeek API via OpenAI SDK (`deepseek-v4-pro`). Streaming + non-streaming. Maintains `self.memory` list for conversation context. |
| `STT` | `clients/STT.py` | DashScope `qwen3-asr-flash-realtime` WebSocket. PyAudio mic capture (16kHz mono PCM) → queue → Base64 → WebSocket. Transcribed text lands in `transcript_queue`. |
| `TTS` | `clients/TTS.py` | DashScope `qwen3-tts-vc-realtime` WebSocket. Accumulates text, splits on punctuation, streams audio to PyAudio speaker (24kHz PCM). Voice profiles in `config.json`. |
| `TTS_COMMIT` | `clients/TTS_commit.py` | Alternate batch-oriented TTS (commit mode). Unused by the GUI; only `main.py` references it. |

`factory/ClientFactory.py` does `Client.get_factory(name)` lookup and instantiation.

### Two entry points, two Agent/Worker classes

**Console mode** (`main.py`):
- `Worker` — owns LLM + TTS, background thread with interruptible `_task_queue` (new tasks discard old ones)
- `KeyboardController` — `pynput` listener: Space press/release toggles STT pause/resume; Esc sets stop_event
- `InputReader` — stdin thread forwarding typed text to Worker

**GUI mode** (`app.py`):
- `Agent` class (defined in `app.py`) — same orchestrator role but with callback hooks (`on_state_change`, `on_transcript`, `on_response_chunk`, `on_response_done`, `on_error`) for Qt signal bridging
- `gui/window.py` — `VoiceAgentWindow(QMainWindow)`, frameless transparent always-on-top
- `gui/chat_display.py` — `ChatDisplay(QLabel)`, floating subtitle overlay, mouse-passthrough
- `gui/input_bar.py` — `InputBar(QWidget)`, glassmorphism input bar with Send + PTT button
- `gui/worker.py` — `AgentWorker(QObject)` bridges Agent callbacks → Qt signals for thread-safe UI

### Concurrency model

```
Main thread
  ├── STT: PyAudio callback thread → audio_queue → send_loop thread → WebSocket
  ├── Worker/Agent thread: task_queue → LLM streaming → TTS feed (tts_lock)
  └── Input/keyboard threads (console mode) or Qt event loop (GUI mode)
```

### State machine

```
IDLE → (submit text) → THINKING → (LLM streaming) → SPEAKING → (TTS done) → IDLE
IDLE → (PTT press) → LISTENING → (PTT release) → (transcript) → THINKING → ...
```

### Key dependencies

| Package | Purpose |
|---------|---------|
| `openai` | DeepSeek LLM API (OpenAI-compatible) |
| `dashscope` | Alibaba DashScope SDK (ASR/TTS WebSocket) |
| `PyAudio` | Mic capture / speaker output |
| `PyQt6` | GUI (frameless overlay window) |
| `pynput` | Global keyboard hooks (console mode only) |
| `python-dotenv` | `.env` loading |

## Configuration

- `.env` — `DASHSCOPE_API_KEY` and `DEEPSEEK_API_KEY`
- `config.json` — voice profile name → `voice_id` mappings (populated by `voice_init.py`)

## Known issues

- **Duplicate Kaltsit prompt** — identical ~40-line system prompt in both `main.py` and `app.py`. Should be a shared constant.
- **Module-level globals in STT** — `clients/STT.py` uses module-level `audio_queue` and `stop_event`, preventing multiple STT instances.
- **No memory truncation** — `LLM.memory` grows unboundedly. No token limit or sliding window.
- **Broken logger path** — `logger.py` expects `configs/logging_config.yaml` which does not exist.
- **Orphan scripts** — `chat.py` and `test/chat.py` import a nonexistent `clone` module.
- **No tests** — `test/test.py` is a trivial placeholder; `test/test_latency.py` is a manual benchmark.
- **Multiple TTS implementations** — `TTS.py` and `TTS_commit.py` share significant duplicated code.

## Refactoring plan

`plans/reconstruction.md` defines a target modular architecture (`voice_agent/` package) with:
- `config.py` — dataclass-based config, loaded from `.env`
- `base.py` — `BaseASR`, `BaseTTS`, `BaseLLM` ABCs + custom exceptions
- `audio.py` — `Microphone`/`Speaker` classes (instance-level state, no globals)
- `asr.py`, `tts.py`, `llm.py` — provider implementations with retry logic
- `conversation.py` — `ConversationHistory` with max-message truncation
- `agent.py` — single `Agent` orchestrator replacing both `main.py:Worker` and `app.py:Agent`
- Old files become deprecation shims

Implementation order is specified in the plan. The existing `clients/` and `factory/` modules would be replaced by this new package.
