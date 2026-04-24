from flask import Flask, request, send_file
import os
import uuid
import wave
import struct
import math
import logging
import asyncio
import subprocess
import shutil
import edge_tts

app = Flask(__name__)
UPLOAD_FOLDER = "audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logging.basicConfig(level=logging.INFO)

# ---------------------------
# دالة احتياطية لتوليد نغمة بسيطة (في حال فشل كل شيء)
# ---------------------------
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

# ---------------------------
# توليد الصوت النظيف باستخدام edge-tts
# ---------------------------
async def async_generate_speech(text, lang, output_path):
    # اختيار الصوت حسب اللغة
    voices = {
        'ar': 'ar-EG-SalmaNeural',   # عربية (مصرية، أنثى)
        'es': 'es-ES-ElviraNeural',
        'pt': 'pt-BR-FranciscaNeural',
        'fr': 'fr-FR-DeniseNeural',
        'en': 'en-US-JennyNeural'
    }
    voice = voices.get(lang, 'en-US-JennyNeural')
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

# ---------------------------
# تطبيق تأثير الراديو القديم (يحتاج ffmpeg)
# ---------------------------
def apply_radio_effect(input_path, output_path):
    """
    تستخدم ffmpeg لإضافة:
    - highpass=300 (قطع الترددات المنخفضة جداً)
    - lowpass=3500 (قطع الترددات العالية جداً)
    - تشويش خفيف (white noise amplitude=0.04)
    - تعزيز بسيط للصوت (volume=1.4)
    """
    cmd = [
        "ffmpeg", "-i", input_path,
        "-af", "highpass=f=300, lowpass=f=3500, volume=1.4, anoisesrc=color=white:amplitude=0.04:duration=2, amix=inputs=2",
        "-y", output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        app.logger.error(f"FFmpeg effect failed: {result.stderr}")
        # فشل: ننسخ الصوت النظيف
        shutil.copy(input_path, output_path)
    else:
        app.logger.info("Radio effect applied successfully")

# ---------------------------
# الصفحة الرئيسية (واجهة المستخدم)
# ---------------------------
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>راديو الحب القديم</title>
    <style>
        body { background:#2b1a1a; color:#f0e6d0; text-align:center; padding:50px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .radio-box { background:#3d2a2a; padding:30px; border-radius:20px; max-width:550px; margin:auto; border:1px solid #b8860b; }
        textarea { width:90%; height:120px; margin:20px 0; padding:10px; border-radius:10px; background:#fef7e0; border:1px solid #b8860b; }
        select, button { background:#b8860b; color:white; border:none; padding:12px 25px; margin:10px; border-radius:40px; cursor:pointer; }
        button:hover, select:hover { background:#d4a017; }
        .onair { color:#ff5555; letter-spacing:2px; }
        audio { margin-top:20px; width:100%; }
        .status { margin-top:15px; font-style:italic; }
    </style>
    </head>
    <body>
    <div class="radio-box">
        <div class="onair">🔴 ON AIR</div>
        <h1>📻 راديو الحب القديم</h1>
        <p>ليست كل الرسائل تحتاج أن تُكتب... بعضها يحتاج أن تصل</p>
        <select id="langSelect">
            <option value="ar">🇸🇦 العربية</option>
            <option value="es">🇪🇸 Español</option>
            <option value="pt">🇵🇹 Português</option>
            <option value="en">🇬🇧 English</option>
            <option value="fr">🇫🇷 Français</option>
        </select>
        <textarea id="msg" placeholder="اكتب رسالتك..."></textarea><br/>
        <button id="generateBtn">🎙️ أرسل رسالتك</button>
        <audio id="audio" controls style="display:none;"></audio>
        <div id="status" class="status"></div>
    </div>
    <script>
        const generateBtn = document.getElementById('generateBtn');
        const audioPlayer = document.getElementById('audio');
        const statusDiv = document.getElementById('status');
        let currentAudioUrl = null;

        generateBtn.onclick = async () => {
            const text = document.getElementById('msg').value.trim();
            const lang = document.getElementById('langSelect').value;
            if (!text) return alert('اكتب رسالة');
            statusDiv.innerText = '📡 جاري البث...';
            generateBtn.disabled = true;
            try {
                const res = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text, lang: lang })
                });
                if (!res.ok) throw new Error(await res.text());
                const blob = await res.blob();
                if (currentAudioUrl) URL.revokeObjectURL(currentAudioUrl);
                currentAudioUrl = URL.createObjectURL(blob);
                audioPlayer.src = currentAudioUrl;
                audioPlayer.style.display = 'block';
                audioPlayer.play();
                statusDiv.innerText = '✅ تم البث على موجات الحنين';
            } catch(e) {
                statusDiv.innerText = '❌ خطأ: ' + e.message;
            } finally {
                generateBtn.disabled = false;
            }
        };
    </script>
    </body>
    </html>
    '''

# ---------------------------
# مسار توليد الصوت وتطبيق التأثير
# ---------------------------
@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    text = data.get('text', '')
    lang = data.get('lang', 'ar')
    if not text:
        return 'لا يوجد نص', 400

    file_id = str(uuid.uuid4())
    clean_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_clean.mp3")
    radio_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_radio.mp3")
    wav_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_fallback.wav")

    try:
        # 1. توليد الصوت النظيف باستخدام edge-tts
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_generate_speech(text, lang, clean_path))
        loop.close()

        # 2. التحقق من وجود ffmpeg
        ffmpeg_exists = subprocess.run(['which', 'ffmpeg'], capture_output=True).returncode == 0
        if ffmpeg_exists:
            apply_radio_effect(clean_path, radio_path)
            return send_file(radio_path, mimetype='audio/mpeg')
        else:
            app.logger.warning("FFmpeg not found, returning clean audio")
            return send_file(clean_path, mimetype='audio/mpeg')
    except Exception as e:
        app.logger.error(f"Speech generation failed: {e}")
        generate_tone_wav(wav_path, frequency=440, duration=2)
        return send_file(wav_path, mimetype='audio/wav')

# ---------------------------
# تشغيل التطبيق
# ---------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
