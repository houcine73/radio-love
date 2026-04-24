from flask import Flask, request, send_file
import os
import uuid
import wave
import struct
import math
import logging
import asyncio
import edge_tts

app = Flask(__name__)
UPLOAD_FOLDER = "audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logging.basicConfig(level=logging.INFO)

# دالة احتياطية للنغمة
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

async def async_generate_speech(text, lang, output_path):
    # تحديد الصوت حسب اللغة
    if lang == 'ar':
        voice = 'ar-EG-SalmaNeural'  # صوت عربي (مصرية) طبيعي جداً
    elif lang == 'es':
        voice = 'es-ES-ElviraNeural'
    elif lang == 'pt':
        voice = 'pt-BR-FranciscaNeural'
    elif lang == 'fr':
        voice = 'fr-FR-DeniseNeural'
    else:  # الإنجليزية
        voice = 'en-US-JennyNeural'
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

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
        <div id="status"></div>
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
                statusDiv.innerText = '✅ تم البث';
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

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    text = data.get('text', '')
    lang = data.get('lang', 'ar')
    if not text:
        return 'No text', 400

    file_id = str(uuid.uuid4())
    mp3_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.mp3")
    wav_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.wav")

    try:
        # تشغيل الدالة غير المتزامنة بطريقة متزامنة
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_generate_speech(text, lang, mp3_path))
        loop.close()
        return send_file(mp3_path, mimetype='audio/mpeg')
    except Exception as e:
        app.logger.error(f"edge-tts failed: {e}")
        generate_tone_wav(wav_path, frequency=440, duration=2)
        return send_file(wav_path, mimetype='audio/wav')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
