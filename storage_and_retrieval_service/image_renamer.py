import os

folder_path = "../../datasets/Renal Malignancy_extra/Kidney-Tumor"   # ← change this
folder_name = os.path.basename(folder_path.rstrip(os.sep))

for idx, filename in enumerate(os.listdir(folder_path), start=1):
    old_path = os.path.join(folder_path, filename)

    if not os.path.isfile(old_path):
        continue

    name, ext = os.path.splitext(filename)
    new_name = f"{folder_name}_{idx}{ext}"
    new_path = os.path.join(folder_path, new_name)

    os.rename(old_path, new_path)

print("Renaming completed!")
