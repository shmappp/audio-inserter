from flask import Flask, render_template, request, jsonify, send_from_directory
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
import os
import psutil

input_dir = os.path.join(os.getcwd(), 'input')
output_dir = os.path.join(os.getcwd(), 'output')
if not os.path.exists(input_dir):
    os.makedirs(input_dir)
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    def combine_disparate_audio(video_audio_clip, audio_path, composite_scale):
        # Handle overlay audio with MoviePy (use AudioFileClip)
        overlay_audio = AudioFileClip(audio_path)
        overlay_audio = overlay_audio.volumex(composite_scale)  # Adjust the volume
        combined_audio = CompositeAudioClip([video_audio_clip, overlay_audio])
        return combined_audio
    import psutil

    def terminate_ffmpeg_process(file_path):
        """Terminate any process holding the file open."""
        for proc in psutil.process_iter(['pid', 'name', 'open_files']):
            for file in proc.info['open_files'] or []:
                if file.path == file_path:
                    print(f"Found {proc.info['name']} (PID {proc.info['pid']}) holding {file_path}. Terminating...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)  # Wait for the process to exit
                    except psutil.TimeoutExpired:
                        proc.kill()  # Forcefully kill the process if it doesn't exit in time
                    print(f"Process {proc.info['pid']} terminated.")
                    break  # Break if the process is terminated

    if request.method == 'POST':
        # Ensure video and audio are provided
        if 'video' not in request.files or 'audio' not in request.files:
            return jsonify({"error": "Both video and audio file required"}), 400
        
        video_file = request.files['video']
        audio_file = request.files['audio']
        
        # Handle the overlay audio and volume if needed
        composite_scale = 1
        if 'overlayAudio' in request.form and request.form['overlayAudio'] == 'true':
            composite_scale = float(request.form['overlayVolume']) / 100
        
        if video_file.filename == '':
            return jsonify({"error": "No video file selected"}), 400
        if audio_file.filename == '':
            return jsonify({"error": "No audio file selected"}), 400

        try:
            video_path = os.path.join(input_dir, 'temp_video.mp4')
            audio_path = os.path.join(input_dir, 'temp_audio.m4a')
            video_file.save(video_path)
            audio_file.save(audio_path)
            video = VideoFileClip(video_path)
        except Exception as e:
            return jsonify({"error": f"First step fail: {str(e)}"}), 400

        try:
            # Process audio as a file-like object (for AudioFileClip)
            new_audio = combine_disparate_audio(video.audio, audio_path, composite_scale) if 'overlayAudio' in request.form and request.form['overlayAudio'] == 'true' else AudioFileClip(audio_path)
            new_audio = new_audio.subclip(0, video.duration)
        except Exception as e:
            return jsonify({"error": f"Error occurred during audio splice: {str(e)}"}), 400
        
        try:
            # Set new audio to the video
            video = video.set_audio(new_audio)
        except:
            return jsonify({"error": f"Audio set fail:"}), 400

        try:
            # Output to BytesIO
            output_path = os.path.join(output_dir, 'output_video.mp4')
            video.write_videofile(output_path, codec='libx264', audio_codec='aac', temp_audiofile="temp_audio.m4a", remove_temp=True)
        except Exception as e:
            return jsonify({"error": f"Error loading video: {str(e)}"}), 400
        
        
        # os.remove(video_path)
        # terminate_ffmpeg_process(audio_path) # find a better way to do this
        # os.remove(audio_path)
        
        # return jsonify({"download_url": f'{request.host_url}download/{output_path}'})
        return send_from_directory(directory = './output', path='output_video.mp4', as_attachment = True) 

    return render_template('index.html')

# @app.route('/download/<filename>')
# def download_file(filename):
#     return send_from_directory(directory = '.', filename=filename, as_attachment = True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5100)
