import os
import re

output_dir = "./output"
txt_file_path = "all_textgrid_timestamps.txt"

if not os.path.exists(output_dir):
    print(f"[ERROR] '{output_dir}' folder not found! Please run mfa align first.")
    exit()

print("\n=== PROCESSING TEXTGRID FILES INTO CLEAN STRUCTURED TEXT FILE ===")

file_count = 0

with open(txt_file_path, mode='w', encoding='utf-8') as f_out:
    # Creating a beautifully aligned text header
    header = f"{'FILE NAME':<25} | {'TIER TYPE':<15} | {'START TIME (sec)':<18} | {'END TIME (sec)':<18} | {'TEXT / SOUND':<15}\n"
    divider = "-" * 98 + "\n"
    
    f_out.write(header)
    f_out.write(divider)
    
    # Scan all files in alphabetical order
    for root, dirs, files in os.walk(output_dir):
        for file in sorted(files):
            if file.endswith(".TextGrid"):
                file_count += 1
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                current_tier = ""
                xmin, xmax, text = None, None, None
                has_content = False
                temp_rows = []
                
                for line in lines:
                    line = line.strip()
                    
                    if 'name =' in line:
                        tier_match = re.search(r'name = "(.*?)"', line)
                        if tier_match:
                            current_tier = tier_match.group(1).upper()
                    
                    if 'xmin =' in line and current_tier:
                        xmin_match = re.search(r'xmin = ([\d\.]+)', line)
                        if xmin_match:
                            xmin = round(float(xmin_match.group(1)), 4)
                    
                    if 'xmax =' in line and current_tier:
                        xmax_match = re.search(r'xmax = ([\d\.]+)', line)
                        if xmax_match:
                            xmax = round(float(xmax_match.group(1)), 4)
                    
                    if 'text =' in line and current_tier:
                        text_match = re.search(r'text = "(.*?)"', line)
                        if text_match:
                            text = text_match.group(1)
                            
                            # Keep track of actual content rows
                            if text != "" and text.lower() != "<silence>":
                                cell_filename = f"{file:<25}"
                                cell_tiertype = f"{current_tier:<15}"
                                cell_start    = f"{xmin:<18.4f}"
                                cell_end      = f"{xmax:<18.4f}"
                                cell_text     = f"{text:<15}"
                                temp_rows.append(f"{cell_filename} | {cell_tiertype} | {cell_start} | {cell_end} | {cell_text}\n")
                                has_content = True
                            
                            xmin, xmax, text = None, None, None
                
                # If a file contains nothing but silence, print one explicit row so the file isn't skipped
                if not has_content:
                    cell_filename = f"{file:<25}"
                    cell_tiertype = f"{'WORDS':<15}"
                    cell_start    = f"{0.0:<18.4f}"
                    cell_end      = f"{0.0:<18.4f}"
                    cell_text     = f"{'<EMPTY_SILENCE>':<15}"
                    f_out.write(f"{cell_filename} | {cell_tiertype} | {cell_start} | {cell_end} | {cell_text}\n")
                else:
                    for row in temp_rows:
                        f_out.write(row)
                
                # Add a clean vertical gap break between files with NO COMMAS
                f_out.write("\n\n")

print(f"\n[SUCCESS] Matrix extraction completed!")
print(f" Total processed files: {file_count}")
print(f" Your data is permanently saved in: '{txt_file_path}'")