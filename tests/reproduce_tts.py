import sys
import os
import time

# Add server directory to path so imports work
sys.path.append(os.path.join(os.getcwd(), "server"))

from video.tts_chatterbox import TTSChatterbox

def test_tts():
    print("Initializing TTSChatterbox...")
    tts = TTSChatterbox()
    
    text = "Hello, this is a test of the Chatterbox TTS system."
    output_path = "test_output.wav"
    
    print(f"Generating TTS for text: '{text}'")
    start_time = time.time()
    
    try:
        tts.chatterbox(
            text=text,
            output_path=output_path,
            chunk_chars=1024,
            chunk_silence_ms=350
        )
        end_time = time.time()
        print(f"Success! Generated in {end_time - start_time:.2f} seconds.")
        if os.path.exists(output_path):
            print(f"Output file created: {output_path}")
            os.remove(output_path)
        else:
            print("Error: Output file was not created.")
            
    except Exception as e:
        print(f"Error generating TTS: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tts()
