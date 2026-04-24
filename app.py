from flask import Flask, request, send_file
import os
import uuid
import subprocess

app = Flask(__name__)
UPLOAD_FOLDER = "audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>راديو الحب القديم</title></head>
    <body style="background:#2b1a1a; color:#f0e6d0; text-align:center; padding:50px;">
        <h1>📻 راديو الحب القديم</h1>
        <textarea id="msg" rows="5" cols="40" placeholder="اكتب شيئاً لم تقله..."></textarea><br/>
        <button onclick="generate()">🎙️ أرسل رسالتك</button>
        <audio id="audio" controls style="display:none;"></audio>
        <p id="status"></p>
        <script>
            async function generate() {
                let text = document.getElementById('msg').value;
                if (!text.trim()) return alert('اكتب رسالة');
                let status = document.getElementById('status');
                status.innerText = 'جاري التجهيز...';
                try {
                    let res = await fetch('/generate', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({text: text})
                    });
                    if (!res.ok) throw new Error(await res.text());
                    let blob = await res.blob();
                    let url = URL.createObjectURL(blob);
                    let audio = document.getElementById('audio');
                    audio.src = url;
                    audio.style.display = 'block';
                    audio.play();
                    status.innerText = 'تم البث';
                } catch(e) {
                    status.innerText = 'خطأ: ' + e.message;
                }
            }
        </script>
    </body>
    </html>
    '''

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return 'No text', 400

    file_id = str(uuid.uuid4())
    mp3_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.mp3")
    
    # توليد نغمة صافية باستخدام FFmpeg
    cmd = f"ffmpeg -f lavfi -i 'sine=frequency=440:duration=2' -acodec libmp3lame -y \"{mp3_path}\""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("FFmpeg error:", result.stderr)
        return "فشل توليد الصوت", 500
    
    return send_file(mp3_path, mimetype='audio/mpeg')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
