
import glob
import os
from pathlib import Path

path = "/home/base/mengrui/MTSS/evaluation_output/qwen30b_edit/patches"
print(f"Checking {path}")

if not os.path.exists(path):
    print("Path does not exist!")

files = glob.glob(os.path.join(path, "JacksonDatabind*.patch"))
print(f"Glob found {len(files)} files.")
for f in files:
    print(f"File: {f}")
    print(f"Size: {os.path.getsize(f)}")

p = Path(path)
p_files = list(p.glob("JacksonDatabind*.patch"))
print(f"Pathlib found {len(p_files)} files.")
for f in p_files:
    print(f"File: {f}")
