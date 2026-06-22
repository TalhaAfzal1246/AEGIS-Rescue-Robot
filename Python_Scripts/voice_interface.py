import whisper
import pyttsx3
import sounddevice as sd
import numpy as np
import tempfile
import os
import wave
import win32com.client
import re
import time

# ── Import all chatbot logic from chatbot_core ──
from chatbot_core import (
    detect_command,
    read_data,
    handle_hello,
    handle_bye,
    handle_help,
    handle_summary,
    handle_victims,
    handle_environment,
    handle_zone
)

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
WHISPER_MODEL  = "base"
SAMPLE_RATE    = 16000
RECORD_SECONDS = 5
CHANNELS       = 1

# Wake words — any of these will activate AEGIS
WAKE_WORDS = [
    "hello aegis", "hi aegis", "hey aegis",
    "hello robot", "aegis wake up", "aegis activate",
    "wake up aegis", "yo aegis", "aegis online",
    "start aegis", "aegis start", "activate aegis"
]

# ──────────────────────────────────────────────
# TTS ENGINE SETUP
# ──────────────────────────────────────────────
def setup_tts():
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    engine.setProperty("volume", 1.0)

    voices = engine.getProperty("voices")
    for voice in voices:
        if "english" in voice.name.lower() or "david" in voice.name.lower():
            engine.setProperty("voice", voice.id)
            break

    return engine


def speak(engine_placeholder, text):
    # Clean the text using our existing regex rules
    spoken_text = shorten_for_speech(text)
    print(f"\n[VOICE DEBUG]: {spoken_text}\n")
    
    try:
        # Connect directly to the native Windows Voice API
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        
        # Optional: Adjust speed (-10 to 10). 0 is normal, 1 is slightly faster.
        speaker.Rate = 1 
        
        # Speak the text (This inherently locks the thread until finished!)
        speaker.Speak(spoken_text)
        
    except Exception as e:
        print(f"\n[FATAL AUDIO ERROR]: {e}\n")
        
    # Mandatory dead-air buffer before the mic turns back on
    time.sleep(1)


def shorten_for_speech(text):
    # 1. Translate vital symbols into words
    text = text.replace("°C", " degrees Celsius")
    text = text.replace("%", " percent")
    
    # 2. THE NUCLEAR OPTION: Erase ANY character that isn't a letter, number, or basic punctuation
    text = re.sub(r'[^a-zA-Z0-9\s.,!?]', '', text)
    
    # 3. Collapse all weird line breaks and massive gaps into single spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 4. Limit the length so the robot doesn't ramble for 3 minutes
    sentences = text.split('.')
    if len(sentences) > 8:
        sentences = sentences[:8]
        sentences.append(" Check the terminal for full details")
        
    return ".".join(sentences)


# ──────────────────────────────────────────────
# AUDIO RECORDING
# ──────────────────────────────────────────────
def record_audio(seconds=RECORD_SECONDS):
    print(f"[MIC] 🎙  Listening... ({seconds} seconds)")
    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32"
    )
    sd.wait()
    print("[MIC] Recording done.")
    return audio


def save_audio_to_temp(audio):
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        audio_int16 = (audio * 32767).astype(np.int16)
        wf.writeframes(audio_int16.tobytes())
    return tmp.name

# ──────────────────────────────────────────────
# SPEECH TO TEXT
# ──────────────────────────────────────────────
def transcribe(model, audio_file):
    result = model.transcribe(audio_file, language="en", fp16=False)
    return result["text"].strip()

# ──────────────────────────────────────────────
# PRINT WHAT WAS HEARD
# Always prints clearly what the user said
# before any response is given
# ──────────────────────────────────────────────
def print_heard(text):
    print("\n" + "─" * 55)
    print(f"  YOU SAID : \"{text}\"")
    print("─" * 55)

# ──────────────────────────────────────────────
# WAKE WORD DETECTION
# ──────────────────────────────────────────────
def is_wake_word(text):
    text_lower = text.lower()
    for wake_word in WAKE_WORDS:
        if wake_word in text_lower:
            return True
    return False

# ──────────────────────────────────────────────
# QUERY PROCESSOR
# ──────────────────────────────────────────────
def process_query(user_text):
    command = detect_command(user_text.lower())

    if command == "hello":
        return handle_hello(), False

    if command == "bye":
        return handle_bye(), True

    if command == "help":
        return handle_help(), False

    if command == "unknown":
        return "I only respond to rescue operation queries. Say help for available commands.", False

    df, error = read_data()

    if error:
        return f"Data error. {error}", False

    if command == "summary":
        return handle_summary(df), False
    elif command == "victims":
        return handle_victims(df), False
    elif command == "environment":
        return handle_environment(df), False
    elif command == "zone":
        return handle_zone(df, user_text), False

    return "I only respond to rescue operation queries. Say help for available commands.", False

# ──────────────────────────────────────────────
# MAIN VOICE LOOP
# ──────────────────────────────────────────────
def run_voice_interface():
    print("=" * 55)
    print("   AEGIS Tactical Chatbot — Voice Mode")
    print("=" * 55)

    print("\n[LOADING] Loading Whisper model... please wait.")
    model = whisper.load_model(WHISPER_MODEL)
    print("[READY] Whisper model loaded.\n")

    # engine = setup_tts()
    engine=None

    print("[STANDBY] Waiting for wake word...")
    print(f"[TIP] Say 'Hello Aegis' to activate.\n")

    # ── Phase 1: Wake word loop ──
    while True:
        audio    = record_audio(seconds=4)
        tmp_file = save_audio_to_temp(audio)
        text     = transcribe(model, tmp_file)
        os.unlink(tmp_file)

        # Always print what was heard, even during wake word listening
        print_heard(text)

        if is_wake_word(text):
            print("\n  ✅ Wake word detected! AEGIS is now ACTIVE.\n")
            activation_msg = "AEGIS online. Awaiting your query."
            print(f"AEGIS: {activation_msg}\n")
            speak(engine, activation_msg)

            # ── Phase 2: Active query loop ──
            while True:
                audio    = record_audio(seconds=RECORD_SECONDS)
                tmp_file = save_audio_to_temp(audio)
                text     = transcribe(model, tmp_file)
                os.unlink(tmp_file)

                # Always print what was heard before responding
                print_heard(text)

                if not text.strip():
                    msg = "I did not catch that. Please repeat your query."
                    print(f"\nAEGIS: {msg}\n")
                    speak(engine, msg)
                    continue

                # Process and get response
                response, should_exit = process_query(text)

                # Print full response to terminal
                print(f"\nAEGIS:\n{response}\n")

                # Speak response
                speak(engine, response)

                # If bye — go back to wake word standby
                if should_exit:
                    print("\n[STANDBY] AEGIS deactivated. Waiting for wake word...\n")
                    break

        else:
            print("  ⏳ No wake word detected. Still in standby...\n")


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    run_voice_interface()
