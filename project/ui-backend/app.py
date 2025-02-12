from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Object Detection Service</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .error-message {
                color: #721c24;
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
                display: none;
            }
            .upload-form {
                text-align: center;
                margin-bottom: 20px;
            }
            .upload-btn {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            .results {
                display: flex;
                gap: 20px;
                margin-top: 20px;
            }
            #preview {
                max-width: 100%;
                height: auto;
            }
            #loading {
                display: none;
                text-align: center;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="text-align: center;">Object Detection Service</h1>
            
            <div class="upload-form">
                <input type="file" id="fileInput" accept="image/*" style="display: none;">
                <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                    Choose Image
                </button>
            </div>
            
            <div id="error-message" class="error-message"></div>
            <div id="loading">Processing image... Please wait.</div>
            
            <div class="results" id="results" style="display: none;">
                <div style="text-align: center;">
                    <img id="preview">
                </div>
                <div id="detections"></div>
            </div>
        </div>

        <script>
            document.getElementById('fileInput').addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                // Reset previous error messages and show loading
                document.getElementById('error-message').style.display = 'none';
                document.getElementById('loading').style.display = 'block';
                document.getElementById('results').style.display = 'none';

                // Display preview
                const reader = new FileReader();
                reader.onload = (e) => {
                    document.getElementById('preview').src = e.target.result;
                };
                reader.readAsDataURL(file);

                // Create form data
                const formData = new FormData();
                formData.append('file', file);

                try {
                    // Send to backend
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to process image');
                    }

                    const data = await response.json();
                    
                    // Hide loading and show results
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('results').style.display = 'block';

                    // Display detections
                    const detectionsDiv = document.getElementById('detections');
                    detectionsDiv.innerHTML = '<h3>Detected Objects:</h3>';
                    if (data.detections && data.detections.length > 0) {
                        data.detections.forEach(det => {
                            detectionsDiv.innerHTML += `
                                <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 4px;">
                                    <strong>${det.class}</strong><br>
                                    Confidence: ${Math.round(det.confidence * 100)}%
                                </div>`;
                        });
                    } else {
                        detectionsDiv.innerHTML += '<p>No objects detected.</p>';
                    }
                } catch (error) {
                    console.error('Error:', error);
                    const errorDiv = document.getElementById('error-message');
                    errorDiv.textContent = error.message || 'Error processing image. Please try again.';
                    errorDiv.style.display = 'block';
                    document.getElementById('loading').style.display = 'none';
                }
            });
        </script>
    </body>
    </html>
    """

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Forward the image to AI backend
        files = {'file': (file.filename, file.file, file.content_type)}
        response = requests.post('http://ai-backend:8001/detect', files=files, timeout=30)
        
        # Check if the response was successful
        if response.status_code != 200:
            logger.error(f"AI backend error: {response.text}")
            return JSONResponse(
                status_code=response.status_code,
                content={"detail": f"AI service error: {response.text}"}
            )
            
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to AI backend service")
        return JSONResponse(
            status_code=503,
            content={"detail": "Unable to connect to AI service. Please try again later."}
        )
    except requests.exceptions.Timeout:
        logger.error("Request to AI backend timed out")
        return JSONResponse(
            status_code=504,
            content={"detail": "Request timed out. Please try again."}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"An unexpected error occurred: {str(e)}"}
        )