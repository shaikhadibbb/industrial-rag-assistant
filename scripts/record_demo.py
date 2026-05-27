import os

def print_instructions():
    print("\n" + "="*50)
    print("🎥 INSTRUCTIONS FOR RECORDING PROJECT DEMO")
    print("="*50)
    print("1. Open QuickTime Player → File → New Screen Recording")
    print("2. Select only the Chrome window showing localhost:7860")
    print("3. Ask these 3 questions one by one (wait for full response each time):")
    print("   Q1: 'What causes pressure drop in a compressed air system?'")
    print("   Q2: 'What are the recommended oil change intervals for an air compressor?'")
    print("   Q3: 'How do I calculate the pipe diameter for a compressed air network?'")
    print("4. Stop recording, export as demo.gif using any GIF converter")
    print("5. Place demo.gif in the project root")
    print("6. The README already references it - it will auto-display on GitHub")
    print("="*50 + "\n")

if __name__ == "__main__":
    print_instructions()
