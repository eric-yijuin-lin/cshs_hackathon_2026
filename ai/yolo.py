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
# ## 確認必要套件版本相依

# %%
import sys
import torch
import ultralytics

print("Python executable :", sys.executable)
print("Python version    :", sys.version)

print("PyTorch version   :", torch.__version__)
print("PyTorch location  :", torch.__file__)

print("Ultralytics       :", ultralytics.__version__)
print("Ultralytics path  :", ultralytics.__file__)

print("CUDA available    :", torch.cuda.is_available())
print("CUDA version      :", torch.version.cuda)

if torch.cuda.is_available():
    print("GPU               :", torch.cuda.get_device_name(0))

# %% [markdown]
# ## 確認資料集路徑正確

# %%
import cv2
import os

project_root = os.getcwd()
dataset_name = "輸入 dataset 名稱"
print("當前工作目錄：", project_root)
image_path = f"./datasets/{dataset_name}/test/images/輸入測試照片名稱"
image = cv2.imread(image_path)

print(image.shape)

# %% [markdown]
# # YOLO 訓練

# %% [markdown]
# ## 開始用資料集訓練

# %%
from ultralytics import YOLO
from pathlib import Path

model = YOLO("yolo26s.pt")

model.train(
    data=f"./datasets/{dataset_name}/data.yaml",
    epochs=200,
    imgsz=640,
    project=Path(project_root) / "yolo_runs" / "detect",
    name="cat_dog",
    exist_ok=True,
    patience=30,
)



# %% [markdown]
# ## 測試模型效能

# %% [markdown]
# ### 載入 best model

# %%
from ultralytics import YOLO
from pathlib import Path
# model = YOLO(Path(project_root) / "yolo_runs" / "detect" / f"{dataset_name}" / "weights" / "best.pt")
model = YOLO(Path(project_root) / "best_models" / "sch-pp85c_plate-641xp(20260917).pt")


# %% [markdown]
# ### 指定影像來源並預測

# %%
results = model.predict(
    # source=f"./datasets/{dataset_name}/test/images/輸入測試照片名稱",
    source=f"./datasets/car_2(TW)/test/images/003386_jpg.rf.9112eab8a355143f7ac68818e1ca4a6a.jpg",
    conf=0.25
)

result = results[0]
annotated_image = result.plot()

import cv2

cv2.imshow("Result", annotated_image)

cv2.waitKey(0)
cv2.destroyAllWindows()
