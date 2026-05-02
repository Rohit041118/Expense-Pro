import os
import json
import base64
import requests
import io
from PIL import Image
from django.conf import settings

def extract_receipt_data(image_file):
    """
    Sends an image to NVIDIA's Llama-3.2-90b-vision-instruct model to extract
    receipt information (Title, Amount, Date).
    """
    if not settings.NVIDIA_API_KEY:
        raise ValueError("NVIDIA_API_KEY is not set in the environment.")

    # Determine mime type roughly based on extension
    filename = image_file.name.lower()
    if filename.endswith('.pdf'):
        raise ValueError("PDFs are not currently supported by the OCR scanner. Please upload an image.")

    # Open image with Pillow
    try:
        img = Image.open(image_file)
        
        # Convert RGBA to RGB (to avoid issues when saving as JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Resize image to reduce token usage (max 512x512)
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        
        # Save compressed image to an in-memory buffer
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        image_bytes = buffer.getvalue()
        mime_type = "image/jpeg"
    except Exception as e:
        raise ValueError(f"Invalid image file: {str(e)}")

    b64_image = base64.b64encode(image_bytes).decode('utf-8')

    # API Endpoint for NVIDIA NIM Vision Model
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
        "Accept": "application/json"
    }

    # Concise prompt — fewer input tokens = faster response
    prompt = (
        "Extract receipt info. Reply with ONLY raw JSON, no markdown:\n"
        '{"title":"2-3 word vendor name","amount":0.00,"date":"YYYY-MM-DD","currency":"INR"}\n'
        "Use null for missing fields."
    )

    payload = {
        "model": "meta/llama-3.2-11b-vision-instruct",
        "messages": [
            {
                "role": "user",
                "content": f'{prompt} <img src="data:{mime_type};base64,{b64_image}" />'
            }
        ],
        "max_tokens": 150,   # JSON reply is always small
        "temperature": 0.0,
        "top_p": 1.0
    }

    response = requests.post(invoke_url, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"NVIDIA API Error: {response.text}")

    data = response.json()
    try:
        content = data['choices'][0]['message']['content'].strip()
        # Clean up any potential markdown formatting the LLM might have added despite instructions
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
            
        parsed_data = json.loads(content)
        return parsed_data
    except Exception as e:
        raise Exception(f"Failed to parse OCR response: {str(e)} | Raw: {content}")
