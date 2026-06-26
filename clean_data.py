import os
import re
from pydub import AudioSegment

# Folder Paths Config
RAW_TRANS_DIR = "./TRANSCRIPTIONS"
RAW_AUDIO_DIR = "./DATASETS"
CORPUS_DIR = "./corpus"

# Automatically create corpus folder if it doesn't exist
os.makedirs(CORPUS_DIR, exist_ok=True)

def clean_text(text):
    # 1. Convert to lowercase
    text = text.lower()
    # 2. Replace hyphens/underscores with space
    text = text.replace("-", " ").replace("_", " ")
    # 3. Remove punctuations and special characters completely
    text = re.sub(r'[.,!?;:"()\'’‘“”\-\[\]\{\}]', '', text)
    # 4. Collapse multiple spaces into a single space
    text = re.sub(r'\s+', ' ', text).strip()
    return text

print("Starting pipeline: Processing 1710 files...")

# Process each text transcription file
for filename in os.listdir(RAW_TRANS_DIR):
    if filename.endswith(".txt"):
        base_name = os.path.splitext(filename)[0]
        
        raw_text_path = os.path.join(RAW_TRANS_DIR, filename)
        raw_audio_path = os.path.join(RAW_AUDIO_DIR, f"{base_name}.mp3")
        
        # Target output paths inside the corpus folder
        output_text_path = os.path.join(CORPUS_DIR, f"{base_name}.txt")
        output_audio_path = os.path.join(CORPUS_DIR, f"{base_name}.wav")
        
        # Check if the corresponding audio file exists
        if os.path.exists(raw_audio_path):
            # 1. Clean Text and save to corpus
            with open(raw_text_path, 'r', encoding='utf-8') as f:
                content = f.read()
            cleaned_content = clean_text(content)   #this function clean text
            
            with open(output_text_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)      # add that current cleaned text file to the corpus folder
                
            # 2. Convert MP3 to 16kHz Mono WAV and save to corpus
            try:
                audio = AudioSegment.from_mp3(raw_audio_path)
                audio = audio.set_frame_rate(16000).set_channels(1)
                audio.export(output_audio_path, format="wav")
            except Exception as e:
                print(f"Error processing audio for {base_name}: {e}")
        else:
            print(f"Warning: Audio file missing for transcription: {base_name}")

print("Success! All clean .txt and .wav pairs are saved in the './corpus' folder.")