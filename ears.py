import whisper
import speech_recognition as sr
import os

# 1. โหลด Model (ครั้งแรกจะนานหน่อยเพราะมันจะโหลดมาเก็บในเครื่อง)
# แนะนำ 'base' หรือ 'small' สำหรับภาษาไทยที่รันบน 4060 ได้เร็วจัด
model = whisper.load_model("base", device="cuda") 

def listen_and_transcribe():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("--- พร้อมรับคำสั่ง (พูดได้เลย) ---")
        # ปรับจูนเสียงรบกวนรอบข้าง (ทุ่งนาบ้านคุณน่าจะเงียบอยู่แล้ว สบาย)
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source)

    try:
        # บันทึกเสียงชั่วคราว
        with open("input.wav", "wb") as f:
            f.write(audio.get_wav_data())

        # ใช้ Whisper แปลงเป็นข้อความ
        print("กำลังประมวลผลเสียง...")
        result = model.transcribe("input.wav", language="th")
        return result["text"]
    except Exception as e:
        return f"Error: {str(e)}"

# ทดสอบรัน
if __name__ == "__main__":
    text = listen_and_transcribe()
    print(f"หุ่นยนต์ได้ยินว่า: {text}")