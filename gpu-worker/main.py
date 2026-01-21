import os
import time
from typing import List, Optional

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile, Header
from fastapi.responses import JSONResponse

# InsightFace (pipeline detect + embed)
from insightface.app import FaceAnalysis
import cv2

APP_NAME = "gpu-worker-face"
START_TS = time.time()

# Simple auth option (optional)
API_TOKEN = os.getenv("GPU_WORKER_TOKEN", "")  # if set, require header

# InsightFace config
# "CUDAExecutionProvider" uses onnxruntime-gpu under the hood if available
PROVIDERS = ["CUDAExecutionProvider", "CPUExecutionProvider"]

# You can tweak these
DET_SIZE = (640, 640)  # bigger = better detection, slower
MODEL_NAME = os.getenv("INSIGHTFACE_MODEL", "buffalo_l")  # common default

app = FastAPI(title=APP_NAME)

face_app: Optional[FaceAnalysis] = None


def require_token(x_token: Optional[str]):
    if API_TOKEN and x_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.on_event("startup")
def startup():
    global face_app
    try:
        # Try GPU first, fallback to CPU if not available
        force_cpu = os.getenv("FORCE_CPU", "0") == "1"

        if not force_cpu:
            try:
                print("[startup] Attempting to initialize with GPU...")
                fa = FaceAnalysis(name=MODEL_NAME, providers=PROVIDERS)
                fa.prepare(ctx_id=0, det_size=DET_SIZE)  # ctx_id=0 => GPU
                face_app = fa
                print("[startup] ✓ GPU initialization successful")
                return
            except Exception as gpu_error:
                print(f"[startup] GPU initialization failed: {gpu_error}")
                print("[startup] Falling back to CPU mode...")

        # CPU fallback
        print("[startup] Initializing with CPU...")
        fa = FaceAnalysis(name=MODEL_NAME, providers=["CPUExecutionProvider"])
        fa.prepare(ctx_id=-1, det_size=DET_SIZE)  # ctx_id=-1 => CPU
        face_app = fa
        print("[startup] ✓ CPU initialization successful")

    except Exception as e:
        # Keep service up but mark unhealthy
        face_app = None
        print(f"[startup] ✗ Failed to init FaceAnalysis: {e}")


@app.get("/health")
def health():
    ok = face_app is not None
    return {
        "service": APP_NAME,
        "ok": ok,
        "uptime_sec": round(time.time() - START_TS, 2),
        "model": MODEL_NAME,
        "providers": PROVIDERS,
    }


def _read_image_from_upload(upload: UploadFile) -> np.ndarray:
    data = upload.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image format")
    return img


@app.post("/embed_faces")
async def embed_faces(
    image: UploadFile = File(...),
    x_token: Optional[str] = Header(default=None),
    max_faces: int = 0,  # 0 => no limit
):
    require_token(x_token)

    if face_app is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if image.content_type is None or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image")

    img = _read_image_from_upload(image)

    # Detect + embed
    faces = face_app.get(img)

    # Sort by detection score desc
    faces = sorted(faces, key=lambda f: float(getattr(f, "det_score", 0.0)), reverse=True)
    if max_faces and max_faces > 0:
        faces = faces[:max_faces]

    results: List[dict] = []
    for f in faces:
        # bbox: [x1,y1,x2,y2]
        bbox = [float(x) for x in f.bbox.tolist()]
        score = float(getattr(f, "det_score", 0.0))

        emb = getattr(f, "embedding", None)
        if emb is None:
            continue

        emb = np.asarray(emb, dtype=np.float32)
        # Optional: normalize embedding (common for cosine similarity)
        emb_norm = emb / (np.linalg.norm(emb) + 1e-12)

        results.append(
            {
                "bbox": bbox,
                "det_score": score,
                "dim": int(emb_norm.shape[0]),
                # JSON-friendly list
                "embedding": emb_norm.tolist(),
            }
        )

    return JSONResponse(
        {
            "faces_found": len(results),
            "model": MODEL_NAME,
            "results": results,
        }
    )
