# Model weights

Place your trained YOLO weights here as `best.pt`.

In the original Colab pipeline this was:

```
/content/drive/MyDrive/BTP/runs/final_model_safe_v2/weights/best.pt
```

Either copy the file into this folder, or set `MODEL_PATH` in `.env` to an
absolute path (or a path relative to `backend/`).

The file is **not** committed to git — see the project `.gitignore`.
