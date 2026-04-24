from flask import Flask, request, send_file
import os
import uuid
import wave
import struct
import math

app = Flask(__name__)
UPLOAD_FOLDER = "audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def generate_tone_wav(filename, frequency=440, duration=2, sample_rate=44100, amplitude=16000):
    """Generates a sine wave WAV file without external dependencies."""
    num_samples = int(sample_rate * duration)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 2 bytes per sample
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            value = int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframes(data)

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
    wav_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.wav")
    
    # توليد نغمة بدون أي أمر خارجي
    generate_tone_wav(wav_path, frequency=440, duration=2)
    
    return send_file(wav_path, mimetype='audio/wav')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
