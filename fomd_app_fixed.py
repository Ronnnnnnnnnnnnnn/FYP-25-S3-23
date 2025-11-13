import gradio as gr
import os
import sys
import uuid
import warnings
import PIL.Image
import imageio
import numpy as np
import skimage.transform
from skimage import img_as_ubyte
import subprocess
from typing import Any

# Suppress warnings
warnings.filterwarnings("ignore")

print("🚀 Starting First Order Motion Model...")

# ========== SETUP REPOSITORIES ==========
def setup_environment():
    """Setup repositories and download model (only once)"""
    if not os.path.exists('first-order-model'):
        print("📥 Cloning first-order-model repository...")
        os.system('git clone -q https://github.com/AliaksandrSiarohin/first-order-model')
    
    if not os.path.exists('demo'):
        print("📥 Cloning demo repository...")
        os.system('git clone -q https://github.com/graphemecluster/first-order-model-demo demo')
    
    # Add to path
    if 'first-order-model' not in sys.path:
        sys.path.insert(0, 'first-order-model')
    if 'demo' not in sys.path:
        sys.path.insert(0, 'demo')
    
    # Download model if needed
    if not os.path.exists('vox-cpk.pth.tar'):
        print("📥 Downloading VoxCeleb model (~360MB)...")
        result = os.system('wget -q https://github.com/graphemecluster/first-order-model-demo/releases/download/checkpoints/vox-cpk.pth.tar')
        if result != 0:
            print("⚠️ wget failed, trying curl...")
            os.system('curl -L -o vox-cpk.pth.tar https://github.com/graphemecluster/first-order-model-demo/releases/download/checkpoints/vox-cpk.pth.tar')
    
    if not os.path.exists('vox-cpk.pth.tar'):
        raise FileNotFoundError("❌ Failed to download model file")
    
    # Create output directories
    os.makedirs("outputs", exist_ok=True)

# Setup once
setup_environment()

# Import after setup
from demo import load_checkpoints, make_animation

# ========== LOAD MODEL ==========
print("🧠 Loading VoxCeleb model...")
try:
    generator, kp_detector = load_checkpoints(
        config_path='first-order-model/config/vox-256.yaml',
        checkpoint_path='vox-cpk.pth.tar'
    )
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    raise

# ========== HELPER FUNCTIONS ==========
def resize_image(image, size=(256, 256)):
    """Resize and center crop image"""
    w, h = image.size
    d = min(w, h)
    r = ((w - d) // 2, (h - d) // 2, (w + d) // 2, (h + d) // 2)
    return image.resize(size, resample=PIL.Image.LANCZOS, box=r)

def extract_file_path(file_input: Any) -> str:
    """Extract file path from any Gradio input format (handles both FileData and VideoData)"""
    if file_input is None:
        return None
    
    # String path
    if isinstance(file_input, str):
        return file_input
    
    # Dictionary (FileData or VideoData)
    if isinstance(file_input, dict):
        # Try different keys that might contain the path
        for key in ['path', 'name', 'video', 'url', 'file_path', 'file']:
            if key in file_input and file_input[key]:
                path = file_input[key]
                if isinstance(path, str):
                    return path
                # If it's nested, try to extract
                if isinstance(path, dict) and 'path' in path:
                    return path['path']
                # Handle VideoData format: {'video': {'path': '...', 'type': '...'}}
                if isinstance(path, dict):
                    if 'path' in path:
                        return path['path']
                    # Try nested video key
                    if 'video' in path and isinstance(path['video'], dict) and 'path' in path['video']:
                        return path['video']['path']
    
    # Object with attributes
    for attr in ['path', 'video', 'name', 'url', 'file_path', 'file']:
        if hasattr(file_input, attr):
            value = getattr(file_input, attr)
            if value:
                if isinstance(value, str):
                    return value
                if isinstance(value, dict):
                    if 'path' in value:
                        return value['path']
                    # Handle nested video structure
                    if 'video' in value and isinstance(value['video'], dict) and 'path' in value['video']:
                        return value['video']['path']
    
    # Last resort - convert to string if it's not an object representation
    str_repr = str(file_input)
    if not str_repr.startswith('<') and os.path.exists(str_repr):
        return str_repr
    
    return None

# ========== MAIN PROCESSING ==========
def animate_image(source_image: Any, driving_video: Any, progress=gr.Progress()):
    """Animate source image using driving video"""
    
    # Extract paths (handles both VideoData and FileData formats)
    source_path = extract_file_path(source_image)
    video_path = extract_file_path(driving_video)
    
    print(f"\n{'='*50}")
    print(f"📷 Image: {source_path}")
    print(f"🎥 Video: {video_path}")
    print(f"{'='*50}")
    
    if not source_path or not os.path.exists(source_path):
        raise gr.Error(f"❌ Invalid image file: {source_path}")
    
    if not video_path or not os.path.exists(video_path):
        raise gr.Error(f"❌ Invalid video file: {video_path}")
    
    # Validate video file extension (since we removed file_types restriction)
    video_extensions = ['.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv', '.flv', '.wmv']
    video_ext = os.path.splitext(video_path)[1].lower()
    if video_ext not in video_extensions:
        raise gr.Error(f"❌ Invalid video file format: {video_ext}. Supported formats: {', '.join(video_extensions)}")
    
    try:
        request_id = str(uuid.uuid4())[:8]
        
        # Process image
        progress(0.1, desc="Processing image...")
        image = PIL.Image.open(source_path).convert('RGB')
        image = resize_image(image)
        source_array = skimage.transform.resize(np.asarray(image), (256, 256))
        
        # Process video
        progress(0.2, desc="Processing video...")
        reader = imageio.get_reader(video_path)
        
        try:
            fps = reader.get_meta_data()['fps']
        except:
            fps = 25
        
        frames = []
        for i, frame in enumerate(reader):
            frames.append(skimage.transform.resize(frame, (256, 256)))
            if i >= 299:  # Limit to 300 frames
                break
            if i % 20 == 0:
                progress(0.2 + (i / 300) * 0.3, desc=f"Frame {i+1}/300")
        
        reader.close()
        
        if len(frames) == 0:
            raise gr.Error("❌ No frames could be read from video")
        
        # Generate animation
        progress(0.5, desc=f"Generating animation ({len(frames)} frames)...")
        predictions = make_animation(
            source_array,
            frames,
            generator,
            kp_detector,
            relative=True,
            adapt_movement_scale=True
        )
        
        # Save video
        progress(0.8, desc="Saving video...")
        output_no_audio = f'outputs/{request_id}_temp.mp4'
        output_final = f'outputs/{request_id}.mp4'
        
        imageio.mimsave(
            output_no_audio,
            [img_as_ubyte(frame) for frame in predictions],
            fps=fps,
            codec='libx264',
            quality=8
        )
        
        # Try to add audio
        progress(0.9, desc="Adding audio...")
        audio_added = False
        
        try:
            result = subprocess.run([
                'ffmpeg', '-y', '-loglevel', 'error',
                '-i', output_no_audio,
                '-i', video_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                output_final
            ], capture_output=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(output_final):
                os.remove(output_no_audio)
                audio_added = True
        except:
            pass
        
        if not audio_added and os.path.exists(output_no_audio):
            os.rename(output_no_audio, output_final)
        
        progress(1.0, desc="Complete!")
        print(f"✅ Complete! Output: {output_final}")
        
        return output_final
        
    except gr.Error:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise gr.Error(f"Animation failed: {str(e)}")

# ========== GRADIO INTERFACE ==========
with gr.Blocks(theme=gr.themes.Soft(), title="First Order Motion Model") as demo:
    gr.Markdown("""
    # 🎭 First Order Motion Model - Face Animation
    
    Animate faces from photos using driving videos!
    
    **⚡ Processing:** 1-3 minutes per video  
    **💡 Tips:** Use clear portraits and videos with visible facial movements  
    **⚠️ Limit:** 300 frames (~10 seconds at 30fps)
    """)
    
    with gr.Row():
        with gr.Column():
            image_input = gr.Image(
                label="📷 Source Image (Face to Animate)",
                sources=["upload", "webcam"]
            )
            # FIXED: Changed from gr.Video to gr.File to avoid VideoData validation error
            # Removed file_types restriction to avoid strict validation errors
            video_input = gr.File(
                label="🎥 Driving Video (Movements to Apply)",
                file_count="single"
                # Note: file_types=["video"] was removed to avoid validation errors
                # The extract_file_path function will handle validation
            )
            submit_btn = gr.Button(
                "🎬 Create Animation",
                variant="primary",
                size="lg"
            )
        
        with gr.Column():
            video_output = gr.Video(
                label="🎉 Animated Result",
                autoplay=True
            )
    
    gr.Markdown("""
    ### 📖 How it works:
    1. Upload a source image (portrait with clear face)
    2. Upload a driving video (with facial movements to transfer)
    3. Click "Create Animation" and wait 1-3 minutes
    
    ### 💡 Best Practices:
    - ✅ Use high-quality, well-lit images
    - ✅ Ensure faces are clearly visible and front-facing
    - ✅ Keep videos under 10 seconds
    
    ### 📚 Credits:
    [First Order Motion Model](https://github.com/AliaksandrSiarohin/first-order-model) by Aliaksandr Siarohin et al.
    """)
    
    submit_btn.click(
        fn=animate_image,
        inputs=[image_input, video_input],
        outputs=video_output
    )

# ========== LAUNCH ==========
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 LAUNCHING GRADIO")
    print("="*50 + "\n")
    
    demo.queue(max_size=10)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )

