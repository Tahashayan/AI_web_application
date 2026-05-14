import os
import io
import base64
import tempfile
import requests
import cloudinary.uploader
from PIL import Image
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import UserProfile, SystemLog
from .serializers import ImageTaskSerializer

# =====================
# Hugging Face API URLs
# =====================
HF_BG_REMOVE_URL = "https://taha812-background-remover.hf.space/api/predict"
HF_ENHANCE_URL   = "https://taha812-image-upscaler.hf.space/api/predict"


# =====================
# Helper: image path → base64
# =====================
def image_to_base64(image_path, mime="image/jpeg"):
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


# =====================
# Helper: base64 response → save to file
# =====================
def save_base64_to_file(b64_string, output_path):
    # HF returns "data:image/png;base64,XXXX" or just raw base64
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    with open(output_path, "wb") as f:
        f.write(img_bytes)


# =====================
# Helper: Call HF Background Remover
# =====================
def call_remove_bg(input_path, output_path):
    img_b64 = image_to_base64(input_path, mime="image/jpeg")

    response = requests.post(
        "https://taha812-background-remover.hf.space/api/predict", 
        json={
            "data": [img_b64, "u2net", False],
            "fn_index": 0  
        },
        timeout=1800
    )

    if response.status_code != 200:
        raise Exception(f"HF BG Remove API error: {response.status_code} - {response.text}")

    result = response.json()
    output_b64 = result["data"][0]
    save_base64_to_file(output_b64, output_path)


# =====================
# Helper: Call HF Image Enhancer
# =====================
def call_enhance(input_path, output_path):
    img_b64 = image_to_base64(input_path, mime="image/jpeg")

    response = requests.post(
        "https://taha812-image-upscaler.hf.space/api/predict",
        json={
            "data": [img_b64],
            "fn_index": 0   
        },
        timeout=1800
    )

    if response.status_code != 200:
        raise Exception(f"Enhance failed: {response.status_code} - {response.text}")

    result = response.json()
    output_b64 = result["data"][0]
    save_base64_to_file(output_b64, output_path)


# =====================
# Main View
# =====================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_process_image(request, action):
    if action not in ['remove_bg', 'enhance']:
        return Response(
            {'error': 'Invalid action. Use "remove_bg" or "enhance".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if profile.credits_remaining <= 0:
        return Response(
            {'error': "You have 0 credits remaining. Please upgrade your plan."},
            status=status.HTTP_402_PAYMENT_REQUIRED
        )

    serializer = ImageTaskSerializer(data=request.data)

    if serializer.is_valid():
        image_task = serializer.save(user=request.user)

        fd_in, temp_input_path = tempfile.mkstemp(suffix='.jpg')
        fd_out, temp_output_path = tempfile.mkstemp(suffix='.png')
        os.close(fd_out)

        try:
            # Save uploaded image to temp file
            with os.fdopen(fd_in, 'wb') as f:
                f.write(image_task.original_image.read())

            if action == 'remove_bg':
                call_remove_bg(temp_input_path, temp_output_path)
                upload_result = cloudinary.uploader.upload(
                    temp_output_path,
                    folder="processed/bg_removed"
                )
                image_task.bg_removed_image = upload_result['secure_url']

            elif action == 'enhance':
                call_enhance(temp_input_path, temp_output_path)
                upload_result = cloudinary.uploader.upload(
                    temp_output_path,
                    folder="processed/enhanced"
                )
                image_task.enhanced_image = upload_result['secure_url']

            image_task.save()

            profile.credits_remaining -= 1
            profile.total_images_processed += 1
            profile.save()

            response_data = ImageTaskSerializer(image_task).data
            response_data['credits_remaining'] = profile.credits_remaining
            response_data['message'] = 'Image processed successfully!'

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            SystemLog.objects.create(
                task=image_task,
                status='FAILED',
                error_message=str(e)
            )
            return Response(
                {'error': 'AI Processing failed. Our team has been notified.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        finally:
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)
            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)

    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)