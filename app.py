import os
import gradio as gr
from audio_separator.separator import Separator
import shutil
import threading
import time
import uuid

# Configuration
# Directory where files will be stored temporarily
UPLOAD_DIR = "output_storage"
MAX_FILE_AGE = 300 

# Ensure the storage directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

def cleanup_scheduler():
    """
    Background task that runs forever. 
    It scans the UPLOAD_DIR every minute and deletes folders older than MAX_FILE_AGE.
    """
    while True:
        try:
            current_time = time.time()
            # Iterate over all items in the storage directory
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                
                # Check if it's a directory (we create one folder per request)
                if os.path.isdir(file_path):
                    # Get the folder's creation/modification time
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > MAX_FILE_AGE:
                        print(f"🧹 Cleanup: Removing old folder {filename} ({int(file_age)}s old)")
                        shutil.rmtree(file_path)
                        
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        # Wait for 60 seconds before checking again
        time.sleep(60)

# Start the cleanup thread immediately (Daemon means it dies when the main app dies)
threading.Thread(target=cleanup_scheduler, daemon=True).start()


def separate_audio(input_file, model_name):
    if input_file is None:
        return (None, None, None, None, None, None)

    # Create a unique subfolder for this specific request inside our managed directory
    # Using UUID ensures no filename collisions between users
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    try:
        separator = Separator(
            output_dir=session_dir,
            output_format="MP3",
            output_bitrate="128k",
        )

        separator.load_model(model_filename=model_name)
        output_files = separator.separate(input_file)

        stems = ["Vocals", "Drums", "Bass", "Other", "Guitar", "Piano"]
        results = []

        for stem in stems:
            # Find the file that matches the stem name
            match = next(
                (os.path.join(session_dir, f) for f in output_files if stem in f),
                None,
            )
            results.append(match)

        # Note: We do NOT call a delete function here anymore. 
        # The background scheduler will handle it later.
        return tuple(results)

    except Exception as e:
        # If the actual separation fails, clean up this specific failed folder immediately
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
        raise RuntimeError(f"Separation failed: {e}") from e


# ------------------ UI ------------------

with gr.Blocks() as demo:
    gr.Markdown(
        """
        # 🎵 AI 6-Stem Audio Separator
        Split your music into high-quality individual tracks using **Demucs 6s**.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            input_audio = gr.Audio(
                label="Upload Audio File",
                type="filepath",
                interactive=True,
            )

            model_dropdown = gr.Dropdown(
                choices=["htdemucs_6s.yaml"],
                value="htdemucs_6s.yaml",
                label="Select Model",
            )

            separate_btn = gr.Button("🚀 Separate Stems", variant="primary")

        with gr.Column(scale=2):
            gr.Markdown("### 🔊 Separation Results")

            with gr.Row():
                output_vocals = gr.Audio(label="🎤 Vocals", type="filepath")
                output_drums = gr.Audio(label="🥁 Drums", type="filepath")

            with gr.Row():
                output_bass = gr.Audio(label="🎸 Bass", type="filepath")
                output_guitar = gr.Audio(label="🎸 Guitar", type="filepath")

            with gr.Row():
                output_piano = gr.Audio(label="🎹 Piano", type="filepath")
                output_other = gr.Audio(label="🎼 Other", type="filepath")

    separate_btn.click(
        fn=separate_audio,
        inputs=[input_audio, model_dropdown],
        outputs=[
            output_vocals,
            output_drums,
            output_bass,
            output_other,
            output_guitar,
            output_piano,
        ],
    )

    gr.Markdown(
        "⚠️ **Note:** Processing may take 1–2 minutes. Files are automatically cleaned up after 1 hour."
    )


if __name__ == "__main__":
    demo.launch(
        ssr_mode=False,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="blue",
        ),
    )