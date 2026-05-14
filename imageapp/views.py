import os
import io
import tempfile
import traceback
from PIL import Image

from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.core.files.uploadedfile import InMemoryUploadedFile

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

import cloudinary.uploader

from .models import ImageTask, SystemLog
from .forms import ImageUploadForm
from .removebg import remove_background
from .enhance import enhance_image


# =========================
# 🔥 IMAGE COMPRESSION FUNCTION
# =========================
def compress_image(uploaded_file):
    image = Image.open(uploaded_file)

    # Convert to RGB (important for PNG)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Resize to max 512x512
    image.thumbnail((512, 512))

    # Compress
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=70)
    buffer.seek(0)

    return InMemoryUploadedFile(
        buffer,
        None,
        uploaded_file.name,
        "image/jpeg",
        buffer.getbuffer().nbytes,
        None
    )


def home(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        action = request.POST.get('action')

        if form.is_valid():

            # ✅ COMPRESS IMAGE BEFORE SAVING
            uploaded_file = request.FILES['original_image']
            compressed_image = compress_image(uploaded_file)

            image_task = form.save(commit=False)
            image_task.original_image = compressed_image

            # ✅ Credit check
            if request.user.is_authenticated:
                profile = request.user.userprofile
                if profile.credits_remaining <= 0:
                    messages.error(request, "You have 0 credits left. please upgrade your plan.")
                    return redirect('home')
                image_task.user = request.user

            image_task.save()

            # Temp files
            fd_in, temp_input_path = tempfile.mkstemp(suffix='.jpg')
            fd_out, temp_output_path = tempfile.mkstemp(suffix='.png')
            os.close(fd_out)

            try:
                # Write compressed image to temp
                with os.fdopen(fd_in, 'wb') as f:
                    for chunk in image_task.original_image.chunks():
                        f.write(chunk)

                # =========================
                # PROCESSING
                # =========================
                if action == 'remove_bg':
                    remove_background(temp_input_path, temp_output_path)

                    upload_result = cloudinary.uploader.upload(
                        temp_output_path,
                        folder="processed/bg_removed"
                    )
                    image_task.bg_removed_image = upload_result['secure_url']

                elif action == 'enhance':
                    enhance_image(temp_input_path, temp_output_path)

                    upload_result = cloudinary.uploader.upload(
                        temp_output_path,
                        folder="processed/enhanced"
                    )
                    image_task.enhanced_image = upload_result['secure_url']

                image_task.save()

                # =========================
                # CREDIT UPDATE
                # =========================
                if request.user.is_authenticated:
                    profile.credits_remaining -= 1
                    profile.total_images_processed += 1
                    profile.save()

            except Exception as e:
                print("\n--- AI CRASHED ---")
                traceback.print_exc()
                print("------------------\n")

                SystemLog.objects.create(
                    task=image_task,
                    status='FAILED',
                    error_message=str(e)
                )

                messages.error(request, "AI Processing failed. Our AI team has been notified")
                return redirect('home')

            finally:
                if os.path.exists(temp_input_path):
                    os.remove(temp_input_path)
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)

            return render(request, 'imageapp/result.html', {
                'image_task': image_task,
                'action': action
            })

    else:
        form = ImageUploadForm()

    return render(request, 'imageapp/home.html', {'form': form})


# =========================
# AUTH
# =========================
def register_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful")
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'imageapp/register.html', {'form': form})


def login_user(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}")
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'imageapp/login.html', {'form': form})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_api_token(request):
    token, created = Token.objects.get_or_create(user=request.user)
    return Response({
        'token': token.key,
        'message': 'Use this token in Authorization header as: Token <your_token>'
    })


# =========================
# USER FEATURES
# =========================
@login_required(login_url='login')
def user_history(request):
    tasks = ImageTask.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'imageapp/history.html', {'tasks': tasks})


@login_required(login_url='login')
def delete_task(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(ImageTask, id=task_id, user=request.user)
        task.delete()
    return redirect('history')


def logout_user(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('home')