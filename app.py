from flask import Flask, request, send_file
import os
import uuid

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

    # إنشاء ملف صوتي بسيط (بيان نصي) بدون FFmpeg
    file_id = str(uuid.uuid4())
    mp3_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.mp3")
    
    # إنشاء ملف MP3 بسيط جدًا (أقل من كيلوبايت)
    # باستخدام بيانات وهمية (static byte array)
    dummy_mp3 = b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    with open(mp3_path, 'wb') as f:
        f.write(dummy_mp3)
    
    return send_file(mp3_path, mimetype='audio/mpeg')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
