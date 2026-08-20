# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: cshs_hackathon_2026 (3.12.9)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 環境設定

# %% [markdown]
# ## 確認顯卡 CUDA 可用

# %%
import torch

print("CUDA 可用：", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU：", torch.cuda.get_device_name(0))

# %% [markdown]
# ## 確認資料集路徑正確

# %%
import cv2
import os

project_root = os.getcwd()
print("當前工作目錄：", project_root)
image_path = "./datasets/cat_dog/test/images/cat12_jpeg.rf.8d4c29f2d94b45875358d83db631aa61.jpg"
image = cv2.imread(image_path)

print(image.shape)

# %% [markdown]
# # YOLO 訓練

# %%
from ultralytics import YOLO
from pathlib import Path

model = YOLO("yolo26s.pt")

model.train(
    data="./datasets/cat_dog/data.yaml",
    epochs=200,
    imgsz=640,
    project=Path(project_root) / "yolo_runs" / "detect",
    name="cat_dog",
    exist_ok=True,
    patience=30,
)



# %%
model = YOLO(Path(project_root) / "yolo_runs" / "detect" / "cat_dog" / "weights" / "best.pt")

results = model.predict(
    source="./datasets/cat_dog/test/images/cat4_jpg.rf.a70b88e116636419cfa128c938fd1345.jpg",
    conf=0.25
)

result = results[0]
annotated_image = result.plot()

import cv2

cv2.imshow("Result", annotated_image)

cv2.waitKey(0)
cv2.destroyAllWindows()
