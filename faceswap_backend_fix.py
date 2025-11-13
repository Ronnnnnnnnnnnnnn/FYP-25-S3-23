# Fix for Hugging Face Space - Face Swap "function has no backend method" error
# This is a complete example of how your app.py should look

import gradio as gr
from typing import Any
import os

# Your face swap function
def swap_faces(source_image: Any, target_image: Any):
    """
    Swap faces between source and target images.
    
    Args:
        source_image: Source image with face to use
        target_image: Target image where face will be placed
    
    Returns:
        Result image with swapped face
    """
    # Extract file paths from Gradio inputs
    def extract_path(file_input):
        if file_input is None:
            return None
        if isinstance(file_input, str):
            return file_input
        if isinstance(file_input, dict):
            return file_input.get('path') or file_input.get('name')
        if hasattr(file_input, 'path'):
            return file_input.path
        return str(file_input) if not str(file_input).startswith('<') else None
    
    source_path = extract_path(source_image)
    target_path = extract_path(target_image)
    
    if not source_path or not os.path.exists(source_path):
        raise gr.Error("❌ Invalid source image")
    
    if not target_path or not os.path.exists(target_path):
        raise gr.Error("❌ Invalid target image")
    
    # TODO: Add your face swap logic here
    # For example, using insightface or other face swap library
    # result_image = your_face_swap_function(source_path, target_path)
    
    # For now, return target image as placeholder
    # Replace this with your actual face swap result
    return target_path

# Create Gradio interface
with gr.Blocks(theme=gr.themes.Soft(), title="Face Swap") as demo:
    gr.Markdown("""
    # 🔄 Face Swap
    
    Swap faces between two images using AI!
    """)
    
    with gr.Row():
        with gr.Column():
            source_input = gr.Image(
                label="📷 Source Image (Face to Use)",
                sources=["upload", "webcam"],
                type="filepath"  # Important: use filepath to avoid format issues
            )
            target_input = gr.Image(
                label="🎯 Target Image (Background/Body)",
                sources=["upload", "webcam"],
                type="filepath"  # Important: use filepath to avoid format issues
            )
            submit_btn = gr.Button(
                "🔄 Swap Faces",
                variant="primary",
                size="lg"
            )
        
        with gr.Column():
            result_output = gr.Image(
                label="✨ Result",
                type="filepath"
            )
    
    # ⚠️ CRITICAL: Connect the button to the function
    # This is what fixes the "function has no backend method" error
    submit_btn.click(
        fn=swap_faces,           # Your function
        inputs=[source_input, target_input],  # Input components
        outputs=result_output    # Output component
    )

# Launch
if __name__ == "__main__":
    demo.queue(max_size=10)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )

