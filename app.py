from flask import Flask, request, send_file
import os
import uuid
import wave
import struct
import math
import logging

app = Flask(__name__)
UPLOAD_FOLDER = "audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logging.basicConfig(level=logging.INFO)

# دالة احتياطية للنغمة (تعمل دائماً)
def generate_tone_wav(filename, frequency=440, duration=2):
    sample_rate = 44100
    amplitude = 16000
    num_samples = int(sample_rate * duration)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            value = int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframes(data)

# محاولة استيراد gTTS (في حال فشل، نستخدم التوليد الاحتياطي)
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
    app.logger.info("gTTS loaded successfully")
except ImportError:
    GTTS_AVAILABLE = False
    app.logger.warning("gTTS not available, falling back to tone")

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
                    status.innerText = '✅ تم البث';
                } catch(e) {
                    status.innerText = '❌ خطأ: ' + e.message;
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
    wav_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.wav")

    if GTTS_AVAILABLE:
        try:
            # محاولة gTTS (بالإنجليزية حالياً، يمكن لاحقاً إضافة اختيار اللغة)
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(mp3_path)
            app.logger.info(f"gTTS success for: {text[:30]}")
            return send_file(mp3_path, mimetype='audio/mpeg')
        except Exception as e:
            app.logger.error(f"gTTS failed: {e}")
            # في حال فشل gTTS، نعود للنغمة
            generate_tone_wav(wav_path, frequency=440, duration=2)
            return send_file(wav_path, mimetype='audio/wav')
    else:
        # gTTS غير متوفرة، نستخدم النغمة
        generate_tone_wav(wav_path, frequency=440, duration=2)
        return send_file(wav_path, mimetype='audio/wav')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
