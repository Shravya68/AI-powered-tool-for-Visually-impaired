# =====================================================================
# backend_processing.py - FIXED FOR FLASK FILE SERVING
# Key fix: Save to local directory instead of Drive for serving
# =====================================================================

import os
import re
import math
import csv
import wave
import tempfile
import shutil
from pathlib import Path
from collections import defaultdict

import cv2
import numpy as np
import torch
from ultralytics import YOLO
from openai import OpenAI
from moviepy.editor import VideoFileClip, AudioFileClip, vfx
from transformers import VitsModel, VitsTokenizer

# =====================================================================
# CONFIGURATION
# =====================================================================

# Model paths
CUSTOM_MODEL_PATH = "/content/drive/MyDrive/YOLOv8_Training/MergedTraffic_v1/train/weights/best.pt"
COCO_MODEL_PATH = "yolov8s.pt"

# Processing settings
TARGET_WIDTH, TARGET_HEIGHT = 960, 540
FRAME_SKIP = 1

# Detection thresholds
CONF_COCO, IOU_COCO = 0.35, 0.70
CONF_CUSTOM, IOU_CUSTOM = 0.30, 0.70

# Camera parameters
VFOV_DEG = 49.0
KNOWN_OBJECT_LABEL = "person"
KNOWN_DISTANCE_M = 3.0
CAMERA_HEIGHT_M = 1.50

# Drawing colors
RED, GREEN = (0, 0, 255), (0, 200, 0)
THICK, FS, FT = 2, 0.55, 1

# TTS settings
TTS_MODEL_NAME = "facebook/mms-tts-eng"
EXTRA_SLOW_FACTOR = 1.3
PAUSE_TAIL_S = 0.2

# GPT settings
GPT_MODEL = "gpt-3.5-turbo"
GPT_TEMP = 0.5

# Output directory (LOCAL, not Drive)
OUTPUT_DIR = "/content/AIVISION/processed_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Distance reference dimensions
REF_DIMS = {
    "person": (0.45, 1.70, 'h'),
    "car": (1.80, 1.50, 'w'),
    "bus": (2.50, 3.20, 'w'),
    "truck": (2.50, 3.00, 'w'),
    "bicycle": (0.60, 1.10, 'w'),
    "motorcycle": (0.70, 1.20, 'w'),
    "traffic light": (0.30, 0.40, 'w'),
    "traffic sign": (0.60, 0.60, 'w'),
    "stop": (0.75, 0.75, 'w'),
    "stop sign": (0.75, 0.75, 'w'),
    "regulatory stop": (0.75, 0.75, 'w'),
    "zebra crossing": (None, 1.80, 'auto'),
    "pedestrian crossing": (0.60, 0.60, 'w'),
}

DEFAULT_SIZE_M = 0.60

CLAMP_M = {
    "traffic light": (1.0, 60.0),
    "traffic sign": (1.0, 80.0),
    "stop": (1.0, 80.0),
    "stop sign": (1.0, 80.0),
    "regulatory stop": (1.0, 80.0),
    "zebra crossing": (0.5, 30.0),
}

# EMA smoothing
EMA_A = 0.3
dist_ema = defaultdict(lambda: None)

# Global model cache
_models_cache = {}

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def norm(s: str) -> str:
    return s.lower().replace('_', ' ').strip()

def mul32(n):
    return int((n + 31) // 32) * 32

def focal_from_vfov(img_h, vfov_deg=VFOV_DEG):
    return (img_h / 2.0) / math.tan(math.radians(vfov_deg / 2.0))

def draw_label(img, text, x, y, color):
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, FS, FT)
    cv2.rectangle(img, (x, y - th - 4), (x + tw + 6, y), color, -1)
    cv2.putText(img, text, (x + 3, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 
                FS, (255, 255, 255), FT, cv2.LINE_AA)

def to_dets(res, names):
    out = []
    if res.boxes is None:
        return out
    for b in res.boxes:
        x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
        cls = int(b.cls)
        conf = float(b.conf)
        out.append((x1, y1, x2, y2, names[cls], conf))
    return out

def pick_real_and_pixels(label, w_px, h_px):
    k = norm(label)
    
    if "zebra" in k and "cross" in k:
        return None, max(1, int(h_px * 0.35))
    
    if "traffic light" in k:
        return 0.30, max(1, w_px)
    if "traffic" in k and "sign" in k:
        return 0.60, max(1, w_px)
    if "stop" in k:
        return 0.75, max(1, w_px)
    
    if k in REF_DIMS:
        rw, rh, axis = REF_DIMS[k]
        if axis == 'w':
            return (rw or DEFAULT_SIZE_M), max(1, w_px)
        if axis == 'h':
            return (rh or DEFAULT_SIZE_M), max(1, h_px)
    
    if any(t in k for t in ["car", "bus", "truck", "bicycle", "motorcycle"]):
        return 1.8, max(1, w_px)
    if "person" in k:
        return 1.70, max(1, h_px)
    
    return DEFAULT_SIZE_M, max(1, h_px)

def estimate_distance_focal(real_m, pix_px, focal_px_value, clamp=None):
    if not real_m or pix_px <= 0:
        return None
    d = (real_m * focal_px_value) / float(pix_px)
    d = max(0.1, min(d, 300.0))
    if clamp:
        lo, hi = clamp
        d = max(lo, min(d, hi))
    return d

def distance_ground_from_bottom(y_bottom_px, fy_px, cy_px, cam_h=CAMERA_HEIGHT_M):
    denom = (y_bottom_px - cy_px)
    if denom <= 1e-6:
        return None
    z = (cam_h * fy_px) / denom
    return max(0.1, min(z, 200.0))

def smooth(key, d):
    if d is None:
        return None
    prev = dist_ema[key]
    if prev is None:
        dist_ema[key] = d
        return d
    val = EMA_A * d + (1 - EMA_A) * prev
    dist_ema[key] = val
    return val

# =====================================================================
# MODEL INITIALIZATION
# =====================================================================

def load_models():
    global _models_cache
    
    if 'yolo_loaded' not in _models_cache:
        print("🔄 Loading YOLO models...")
        _models_cache['coco'] = YOLO(COCO_MODEL_PATH)
        _models_cache['custom'] = YOLO(CUSTOM_MODEL_PATH)
        _models_cache['yolo_loaded'] = True
        print("✅ YOLO models loaded")
    
    if 'tts_loaded' not in _models_cache:
        print("🔄 Loading TTS model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _models_cache['tts_tokenizer'] = VitsTokenizer.from_pretrained(TTS_MODEL_NAME)
        _models_cache['tts_model'] = VitsModel.from_pretrained(TTS_MODEL_NAME).to(device)
        _models_cache['tts_device'] = device
        _models_cache['tts_loaded'] = True
        print("✅ TTS model loaded")
    
    return _models_cache

# =====================================================================
# MAIN PROCESSING FUNCTION
# =====================================================================

def process_video_backend(input_path):
    """Complete video processing - saves to LOCAL directory for Flask serving"""
    
    print(f"\n{'='*70}")
    print(f"🎬 AI VISION - Complete Video Processing")
    print(f"{'='*70}")
    print(f"📹 Input: {input_path}\n")
    
    temp_dir = Path(tempfile.mkdtemp(prefix="aivision_"))
    annotated_video = temp_dir / "annotated.mp4"
    narration_wav = temp_dir / "narration.wav"
    csv_path = temp_dir / "detections.csv"
    
    try:
        models = load_models()
        coco = models['coco']
        custom = models['custom']
        
        # STEP 1: VIDEO DETECTION
        print("🔍 Step 1: Running object detection...")
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        PROCESS_W = mul32(TARGET_WIDTH)
        PROCESS_H = mul32(TARGET_HEIGHT)
        CY = PROCESS_H / 2.0
        
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        outv = cv2.VideoWriter(str(annotated_video), fourcc, fps, (PROCESS_W, PROCESS_H))
        
        print(f"   📊 {PROCESS_W}x{PROCESS_H} @ {fps:.2f}fps, {n_frames} frames")
        
        # Focal calibration
        ret, first = cap.read()
        if not ret:
            raise RuntimeError("Failed to read first frame")
        
        first_r = cv2.resize(first, (PROCESS_W, PROCESS_H))
        res0 = coco.predict(first_r, imgsz=PROCESS_H, conf=0.40, iou=0.65, verbose=False)[0]
        
        focal_px_val = None
        for b in (res0.boxes or []):
            lbl = coco.names[int(b.cls)]
            if norm(lbl) == norm(KNOWN_OBJECT_LABEL):
                x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
                h_px = max(1, y2 - y1)
                focal_px_val = (h_px * KNOWN_DISTANCE_M) / 1.70
                break
        
        if focal_px_val is None:
            focal_px_val = focal_from_vfov(PROCESS_H, VFOV_DEG)
        
        FY = focal_from_vfov(PROCESS_H, VFOV_DEG)
        print(f"   🔧 Focal: {focal_px_val:.2f}px | FY: {FY:.2f}px")
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        with open(csv_path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(["frame", "model", "label", "distance_m", "x1", "y1", "x2", "y2", "conf"])
        
        frame_idx = 0
        printed_lines = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % FRAME_SKIP != 0:
                frame_idx += 1
                continue
            
            fr = cv2.resize(frame, (PROCESS_W, PROCESS_H))
            
            rb = coco.predict(fr, imgsz=PROCESS_H, conf=CONF_COCO, iou=IOU_COCO, 
                            verbose=False, max_det=100)[0]
            rc = custom.predict(fr, imgsz=PROCESS_H, conf=CONF_CUSTOM, iou=IOU_CUSTOM,
                              verbose=False, max_det=100)[0]
            
            base_dets = to_dets(rb, coco.names)
            raw_custom = to_dets(rc, custom.names)
            
            custom_keep = []
            for (x1, y1, x2, y2, lbl, cf) in raw_custom:
                k = norm(lbl)
                if any(kw in k for kw in ["zebra", "pedestrian", "stop", "traffic"]):
                    custom_keep.append((x1, y1, x2, y2, lbl, cf))
            
            zebras = [d for d in custom_keep if "zebra" in norm(d[4])]
            others = [d for d in custom_keep if "zebra" not in norm(d[4])]
            if len(zebras) > 1:
                zebras.sort(key=lambda d: (d[2] - d[0]) * (d[3] - d[1]), reverse=True)
                zebras = zebras[:1]
            custom_dets = zebras + others
            
            summary = []
            
            for (x1, y1, x2, y2, lbl, cf) in base_dets:
                w_px, h_px = x2 - x1, y2 - y1
                if w_px < 10 or h_px < 10:
                    continue
                
                k = norm(lbl)
                clamp = CLAMP_M.get(k)
                
                if "zebra" in k:
                    d = distance_ground_from_bottom(y2, FY, CY)
                else:
                    real_m, pix_px = pick_real_and_pixels(lbl, w_px, h_px)
                    d = estimate_distance_focal(real_m, pix_px, focal_px_val, clamp)
                
                d = smooth("coco_" + k, d)
                if d is None:
                    continue
                
                txt = f"{lbl} ({d:.1f} m)"
                summary.append(txt)
                cv2.rectangle(fr, (x1, y1), (x2, y2), RED, THICK)
                draw_label(fr, txt, x1, y1, RED)
                
                with open(csv_path, 'a', newline='') as f:
                    w = csv.writer(f)
                    w.writerow([frame_idx, "coco", lbl, f"{d:.2f}", x1, y1, x2, y2, f"{cf:.3f}"])
            
            for (x1, y1, x2, y2, lbl, cf) in custom_dets:
                w_px, h_px = x2 - x1, y2 - y1
                if w_px < 10 or h_px < 10:
                    continue
                
                k = norm(lbl)
                clamp = CLAMP_M.get(k)
                
                if "zebra" in k:
                    d = distance_ground_from_bottom(y2, FY, CY)
                else:
                    real_m, pix_px = pick_real_and_pixels(lbl, w_px, h_px)
                    d = estimate_distance_focal(real_m, pix_px, focal_px_val, clamp)
                
                d = smooth("custom_" + k, d)
                if d is None:
                    continue
                
                txt = f"{lbl} ({d:.1f} m)"
                summary.append(txt)
                cv2.rectangle(fr, (x1, y1), (x2, y2), GREEN, THICK)
                draw_label(fr, txt, x1, y1, GREEN)
                
                with open(csv_path, 'a', newline='') as f:
                    w = csv.writer(f)
                    w.writerow([frame_idx, "custom", lbl, f"{d:.2f}", x1, y1, x2, y2, f"{cf:.3f}"])
            
            outv.write(fr)
            
            if summary:
                line = f"Frame {frame_idx}: " + ", ".join(summary[:8])
                printed_lines.append(line)
            
            frame_idx += 1
        
        cap.release()
        outv.release()
        
        print(f"   ✅ Processed {frame_idx} frames")
        print(f"   📁 Annotated video: {annotated_video}")
        
        # STEP 2: NARRATION
        print("\n🗣️ Step 2: Generating narration...")
        
        frame_line_re = re.compile(r"^Frame\s+(\d+):\s*(.*)$")
        frames = []
        for line in printed_lines:
            m = frame_line_re.match(line)
            if m:
                frames.append(m.group(2))
        
        scene_summary = "; ".join(frames[:200])
        api_key = os.getenv("OPENAI_API_KEY", "")
        
        if api_key and api_key.startswith("sk-"):
            try:
                client = OpenAI(api_key=api_key)
                prompt = f"""We are describing a short video at a busy intersection with traffic lights, cars, people, and zebra crossings.
Write a simple, natural narration in first-person plural ("we"), about what is happening throughout the video.
Use normal words. Keep it calm and realistic, not poetic. Describe the flow of the scene in a way that helps someone visualize it.
Here are object detections to guide you:
{scene_summary}"""
                
                resp = client.chat.completions.create(
                    model=GPT_MODEL,
                    temperature=GPT_TEMP,
                    max_tokens=200,
                    messages=[
                        {"role": "system", "content": "You are a simple and kind narrator describing a real scene for blind users."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                narration = resp.choices[0].message.content.strip()
                print(f"   📝 GPT Narration: {narration[:100]}...")
            
            except Exception as e:
                print(f"   ⚠️ GPT failed ({e}), using fallback")
                narration = generate_fallback_narration(printed_lines)
        else:
            print("   ⚠️ No OpenAI key, using fallback narration")
            narration = generate_fallback_narration(printed_lines)
        
        # STEP 3: TTS
        print("\n🔊 Step 3: Generating audio...")
        
        device = models['tts_device']
        tokenizer = models['tts_tokenizer']
        tts_model = models['tts_model']
        
        inputs = tokenizer(narration, return_tensors="pt")
        with torch.no_grad():
            wav = tts_model(**{k: v.to(device) for k, v in inputs.items()}).waveform.squeeze(0).cpu().numpy()
        
        sr = int(tts_model.config.sampling_rate) if hasattr(tts_model.config, "sampling_rate") else 16000
        wav = wav / (np.max(np.abs(wav)) + 1e-9)
        wav16 = (wav * 32767).astype(np.int16)
        wav16 = np.concatenate([wav16, np.zeros(int(PAUSE_TAIL_S * sr), dtype=np.int16)])
        
        with wave.open(str(narration_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(wav16.tobytes())
        
        print(f"   ✅ Audio saved: {narration_wav}")
        
        # STEP 4: MERGE
        print("\n🎞️ Step 4: Merging video and audio...")
        
        base = VideoFileClip(str(annotated_video))
        audio_clip = AudioFileClip(str(narration_wav))
        
        speech_dur = audio_clip.duration
        new_duration = speech_dur * EXTRA_SLOW_FACTOR
        factor = base.duration / new_duration
        
        print(f"   📊 Original: {base.duration:.2f}s | Speech: {speech_dur:.2f}s | Factor: {factor:.2f}")
        
        slowed = base.fx(vfx.speedx, factor=factor)
        final = slowed.set_audio(audio_clip)
        
        # SAVE TO LOCAL DIRECTORY (not Drive)
        import time
        timestamp = int(time.time())
        input_name = Path(input_path).stem
        output_filename = f"ai_vision_{input_name}_{timestamp}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        print(f"   💾 Saving to: {output_path}")
        
        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=base.fps or 25,
            verbose=False,
            logger=None
        )
        
        if not os.path.exists(output_path):
            raise RuntimeError(f"Output video was not created: {output_path}")
        
        # Cleanup
        base.close()
        slowed.close()
        audio_clip.close()
        final.close()
        
        # Optional: Backup to Drive
        try:
            drive_backup = f"/content/drive/MyDrive/{output_filename}"
            shutil.copy2(output_path, drive_backup)
            print(f"   ☁️ Backup saved to Drive")
        except Exception as e:
            print(f"   ⚠️ Drive backup skipped: {e}")
        
        print(f"\n{'='*70}")
        print(f"✅ PROCESSING COMPLETE!")
        print(f"{'='*70}")
        print(f"📹 Final video: {output_path}")
        print(f"🗣️ Narration: {narration}")
        print(f"{'='*70}\n")
        
        transcript = f"Narration: {narration}\n\nDetection Summary ({len(printed_lines)} frames):\n"
        transcript += "\n".join(printed_lines[:50])
        
        return {
            "success": True,
            "video_path": output_path,  # LOCAL path Flask can serve
            "transcript": transcript,
            "narration": narration
        }
    
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"\n❌ ERROR:\n{error_msg}")
        
        return {
            "success": False,
            "error": str(e),
            "details": error_msg
        }
    
    finally:
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as cleanup_err:
            print(f"⚠️ Cleanup warning: {cleanup_err}")

def generate_fallback_narration(detection_lines):
    if not detection_lines:
        return "Video processing complete. No objects detected in the scene."
    
    objects = defaultdict(int)
    for line in detection_lines:
        parts = line.split(": ", 1)
        if len(parts) == 2:
            detections = parts[1].split(", ")
            for det in detections:
                obj_name = det.split("(")[0].strip().lower()
                objects[obj_name] += 1
    
    parts = []
    priority = ["person", "car", "traffic light", "stop sign", "zebra crossing"]
    
    for obj in priority:
        if obj in objects:
            count = objects[obj]
            if count > 3:
                parts.append(f"multiple {obj}s")
            elif count > 1:
                parts.append(f"{count} {obj}s")
            else:
                parts.append(f"a {obj}")
    
    if not parts:
        return "We see a busy street scene with various objects and vehicles."
    
    narration = "In this video, we can see " + ", ".join(parts[:-1])
    if len(parts) > 1:
        narration += f", and {parts[-1]}"
    else:
        narration += parts[0]
    
    narration += ". Please proceed with caution and stay alert to your surroundings."
    
    return narration

print("✅ Backend processing module loaded successfully!")
print("📋 Available function: process_video_backend(input_path)")
print(f"📁 Output directory: {OUTPUT_DIR}")