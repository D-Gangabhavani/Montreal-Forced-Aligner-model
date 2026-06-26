import os
import re

# Directory Paths
annotations_dir = "./ANNOTATIONS"
output_dir = "./output"
report_txt_path = "red_flag_details.txt"
word_details_file = "all_word_details_output.txt"

if not os.path.exists(annotations_dir) or not os.path.exists(output_dir):
    print("[ERROR] Please make sure both './ANNOTATIONS' and './output' folders exist!")
    exit()

# File Trackers
total_checked_files = 0
red_flag_files_count = 0
perfect_files_count = 0

# Word-Level Trackers
total_dataset_words = 0

# Detailed sub-reason trackers for files
hash_only_file_count = 0  
word_mismatch_count = 0
time_deviation_count = 0

print("PASS 1: Reading annotations and calculating Dynamic Threshold...")

all_start_differences = []
all_end_differences = []
file_data_cache = []

textgrid_files = [f for f in os.listdir(output_dir) if f.endswith(".TextGrid")]

def extract_number(filename):
    numbers = re.findall(r'\d+', filename)
    return numbers[0] if numbers else filename

# --- PASS 1: Collect Data & Compute Mean-based Threshold ---
for file_name in sorted(os.listdir(annotations_dir)):
    if file_name.endswith(".txt"):
        base_name = file_name.replace(".Annotated.txt", "").replace(".txt", "").replace("_Annotated", "")
        
        txt_num = extract_number(base_name)
        manual_path = os.path.join(annotations_dir, file_name)
        total_checked_files += 1
        
        # Exact or Smart Number Match for TextGrid
        matched_tg_name = None
        for tg_file in textgrid_files:
            tg_base = os.path.splitext(tg_file)[0]
            if base_name == tg_base or txt_num == extract_number(tg_base):
                matched_tg_name = tg_file
                break
                
        if not matched_tg_name:
            word_mismatch_count += 1
            file_data_cache.append({
                "base_name": base_name,
                "status": "word_mismatch",
                "reason": "TextGrid alignment file missing for this chunk.",
                "manual_words": []
            })
            continue

        # Parse Manual Annotation Data
        manual_words = []
        has_any_content = False
        has_only_hash_content = True
        
        with open(manual_path, 'r', encoding='utf-8') as f_man:
            for line in f_man:
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    try:
                        start = float(parts[0])
                        end = float(parts[1])
                        raw_word = parts[2].strip()
                        
                        if raw_word != "":
                            has_any_content = True
                            if raw_word != '#':
                                has_only_hash_content = False
                                
                        clean_word = re.sub(r'[\[\]\(\)\{\}#]', '', raw_word).strip().upper()
                        if clean_word:  
                            manual_words.append({"start": start, "end": end, "word": clean_word, "raw": raw_word})
                    except ValueError:
                        continue

        total_dataset_words += len(manual_words)

        if has_any_content and has_only_hash_content and len(manual_words) == 0:
            hash_only_file_count += 1
            file_data_cache.append({"base_name": base_name, "status": "hash_only", "manual_words": []})
            continue

        # Parse MFA TextGrid
        textgrid_path = os.path.join(output_dir, matched_tg_name)
        mfa_words = []
        with open(textgrid_path, 'r', encoding='utf-8') as f_tg:
            tg_content = f_tg.read()
            
        words_tier_match = re.search(r'name\s*=\s*"words".*?(?=name\s*=\s*"phones"|$)', tg_content, re.DOTALL)
        if words_tier_match:
            intervals = re.findall(r'xmin\s*=\s*([\d\.]+)\s+xmax\s*=\s*([\d\.]+)\s+text\s*=\s*"(.*?)"', words_tier_match.group(0))
            for xmin, xmax, text in intervals:
                text_clean = text.strip().upper()
                if text_clean != "" and text_clean != "<SILENCE>":
                    mfa_words.append({"start": float(xmin), "end": float(xmax), "word": text_clean})

        # Smart Alignment Matching Loop
        file_diffs = []
        m_idx, mfa_idx = 0, 0
        has_structural_mismatch = (len(manual_words) != len(mfa_words))
        
        while m_idx < len(manual_words) and mfa_idx < len(mfa_words):
            if manual_words[m_idx]["word"] == mfa_words[mfa_idx]["word"]:
                s_diff = abs(manual_words[m_idx]["start"] - mfa_words[mfa_idx]["start"])
                e_diff = abs(manual_words[m_idx]["end"] - mfa_words[mfa_idx]["end"])
                all_start_differences.append(s_diff)
                all_end_differences.append(e_diff)
                file_diffs.append({
                    "word": manual_words[m_idx]["word"],
                    "h_start": manual_words[m_idx]["start"], "h_end": manual_words[m_idx]["end"],
                    "m_start": mfa_words[mfa_idx]["start"], "m_end": mfa_words[mfa_idx]["end"],
                    "s_diff": s_diff, "e_diff": e_diff
                })
                m_idx += 1
                mfa_idx += 1
            else:
                if m_idx + 1 < len(manual_words) and manual_words[m_idx+1]["word"] == mfa_words[mfa_idx]["word"]:
                    m_idx += 1
                elif mfa_idx + 1 < len(mfa_words) and manual_words[m_idx]["word"] == mfa_words[mfa_idx+1]["word"]:
                    mfa_idx += 1
                else:
                    m_idx += 1
                    mfa_idx += 1

        if has_structural_mismatch and len(file_diffs) == 0:
            word_mismatch_count += 1
            file_data_cache.append({
                "base_name": base_name,
                "status": "word_mismatch",
                "reason": f"Word count mismatch! Manual text items: {len(manual_words)}, MFA items: {len(mfa_words)}",
                "manual_words": manual_words
            })
        else:
            file_data_cache.append({
                "base_name": base_name,
                "status": "process_ready",
                "diffs": file_diffs,
                "had_mismatch": has_structural_mismatch,
                "mismatch_reason": f"Word count mismatch! Manual text items: {len(manual_words)}, MFA items: {len(mfa_words)}"
            })

if not all_start_differences:
    print("[ERROR] Words could not be linked. Ensure data format or folder match is correct.")
    exit()

# MATHEMATICAL COMPUTATION OF DYNAMIC THRESHOLD (Max Mean * 2)
mean_start = sum(all_start_differences) / len(all_start_differences)
mean_end = sum(all_end_differences) / len(all_end_differences)
higher_mean = max(mean_start, mean_end)
DYNAMIC_THRESHOLD = higher_mean * 2

print(f"Dynamic Max Mean * 2 Threshold computed: {DYNAMIC_THRESHOLD:.6f} seconds")
print("PASS 2: Evaluating alignment and writing master text files...")

# --- PASS 2: Evaluate and write full detailed logs ---
total_flagged_words_count = 0

with open(report_txt_path, mode='w', encoding='utf-8') as f_out, \
     open(word_details_file, mode='w', encoding='utf-8') as f_word:
     
    f_out.write("====================================================\n")
    f_out.write("          DETAILED RED FLAG AND PROCESS LOGS        \n")
    f_out.write(f"  Mean Start Difference: {mean_start:.6f}s | Mean End Difference: {mean_end:.6f}s\n")
    f_out.write(f"  Dynamic Calculated Threshold (Max Mean * 2): {DYNAMIC_THRESHOLD:.6f}s\n")
    f_out.write("====================================================\n\n")

    f_word.write("=========================================================================================================================\n")
    f_word.write(f"                                   PER-WORD COMPREHENSIVE DIFFERENCE REPORT\n")
    f_word.write(f"  Mean Start Difference: {mean_start:.6f}s | Mean End Difference: {mean_end:.6f}s | Threshold: {DYNAMIC_THRESHOLD:.6f}s\n")
    f_word.write("=========================================================================================================================\n")
    f_word.write(f"{'FILE NAME':<18} | {'WORD':<12} | {'HUMAN START':<12} | {'HUMAN END':<11} | {'MACH START':<11} | {'MACH END':<10} | {'START DIFF':<11} | {'END DIFF':<10} | {'STATUS':<8}\n")
    f_word.write("-" * 123 + "\n")

    for file in file_data_cache:
        b_name = file["base_name"]
        
        if file["status"] == "hash_only":
            red_flag_files_count += 1
            f_out.write(f"RED FLAG: {b_name} -> Manual transcription contains ONLY '#' markers.\n")
            
        elif file["status"] == "word_mismatch":
            red_flag_files_count += 1
            total_flagged_words_count += len(file["manual_words"])
            f_out.write(f"RED FLAG: {b_name} -> {file['reason']}\n")
            
        elif file["status"] == "process_ready":
            if file["had_mismatch"]:
                red_flag_files_count += 1
                word_mismatch_count += 1
                f_out.write(f"RED FLAG: {b_name} -> {file['mismatch_reason']}\n")
                for wd in file["diffs"]:
                    f_word.write(f"{b_name:<18} | {wd['word']:<12} | {wd['h_start']:<11.4f}s | {wd['h_end']:<10.4f}s | {wd['m_start']:<10.4f}s | {wd['m_end']:<9.4f}s | {wd['s_diff']:<10.5f}s | {wd['e_diff']:<9.5f}s | {'MISMATCH':<8}\n")
                continue

            file_has_deviation = False
            for wd in file["diffs"]:
                status = "SAFE"
                if wd["s_diff"] > DYNAMIC_THRESHOLD or wd["e_diff"] > DYNAMIC_THRESHOLD:
                    status = "FLAGGED"
                    total_flagged_words_count += 1
                    file_has_deviation = True
                    
                f_word.write(f"{b_name:<18} | {wd['word']:<12} | {wd['h_start']:<11.4f}s | {wd['h_end']:<10.4f}s | {wd['m_start']:<10.4f}s | {wd['m_end']:<9.4f}s | {wd['s_diff']:<10.5f}s | {wd['e_diff']:<9.5f}s | {status:<8}\n")
                
            if file_has_deviation:
                red_flag_files_count += 1
                time_deviation_count += 1
                for wd in file["diffs"]:
                    if wd["s_diff"] > DYNAMIC_THRESHOLD or wd["e_diff"] > DYNAMIC_THRESHOLD:
                        f_out.write(f"RED FLAG: {b_name} -> Time difference > threshold at word '{wd['word']}' (Start Diff: {wd['s_diff']:.4f}s, End Diff: {wd['e_diff']:.4f}s)\n")
                        break
            else:
                perfect_files_count += 1
                f_out.write(f"PERFECT: {b_name}\n")

# Terminal UI Summary (Emojis completely removed)
print("\n====================================================")
print("              PROJECT FINAL RED FLAG REPORT          ")
print("====================================================")
print(f"Mean Start Difference               : {mean_start:.6f} seconds")
print(f"Mean End Difference                 : {mean_end:.6f} seconds")
print(f"Configured Difference Threshold     : {DYNAMIC_THRESHOLD:.6f} seconds (Max Mean * 2)")
print("-" * 52)
print(f"Total Input Annotation Files Checked : {total_checked_files}")
print(f"Total Perfectly Aligned Files        : {perfect_files_count}")
print(f"TOTAL RED FLAG FILES                 : {red_flag_files_count}")
print("-" * 52)
print("WORD-LEVEL ALIGNMENT METRICS:")
print(f"  - Total Words in Dataset          : {total_dataset_words}")
print(f"  - Total Flagged Words             : {total_flagged_words_count}")
print("-" * 52)
print("Detailed Breakdown of why files got Red Flagged:")
print(f"  - Contains ONLY '#' markers       : {hash_only_file_count}")
print(f"  - Word Count / Audio Text Mismatch: {word_mismatch_count}")
print(f"  - Time Difference Exceeded Threshold: {time_deviation_count}")
print("====================================================")
print(f"Detailed red flag list is saved in: '{report_txt_path}'")
print(f"Per-word timing data table saved in: '{word_details_file}'")
print("====================================================")