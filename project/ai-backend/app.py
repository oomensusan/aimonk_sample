from fastapi import FastAPI, UploadFile, File, HTTPException
import numpy as np
import torch
import torchvision
from PIL import Image
import io
import logging
import sys
from typing import Dict, List, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize model with error handling
try:
    logger.info("Loading model...")
    model = torchvision.models.detection.fasterrcnn_mobilenet_v3_large_320_fpn(pretrained=True)
    model.eval()
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise

COCO_CLASSES = [
    '__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
    'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign',
    'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A',
    'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
    'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
    'bottle', 'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl',
    'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
    'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'N/A', 'dining table',
    'N/A', 'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
    'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'N/A', 'book',
    'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]

async def process_image(contents: bytes) -> Image.Image:
    """Process image bytes into PIL Image with error handling."""
    try:
        return Image.open(io.BytesIO(contents))
    except Exception as e:
        logger.error(f"Failed to process image: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid image format")

@app.post("/detect")
async def detect_objects(file: UploadFile = File(...)) -> Dict[str, List[Dict[str, Union[str, float, List[float]]]]]:
    try:
        logger.info(f"Processing file: {file.filename}")
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file contents
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Process image
        image = await process_image(contents)
        
        # Convert to tensor
        try:
            image_tensor = torchvision.transforms.functional.to_tensor(image)
        except Exception as e:
            logger.error(f"Failed to convert image to tensor: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to process image")
        
        # Perform inference
        try:
            with torch.no_grad():
                prediction = model([image_tensor])
        except Exception as e:
            logger.error(f"Model inference failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Model inference failed")
        
        # Process results
        boxes = prediction[0]['boxes'].tolist()
        labels = prediction[0]['labels'].tolist()
        scores = prediction[0]['scores'].tolist()
        
        # Filter and format results
        results = []
        for box, label, score in zip(boxes, labels, scores):
            if score > 0.5:
                results.append({
                    "class": COCO_CLASSES[label],
                    "confidence": round(score, 3),
                    "bbox": [round(x, 2) for x in box]
                })
        
        logger.info(f"Successfully processed image. Found {len(results)} objects.")
        return {"detections": results}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": model is not None}