import pyttsx3
engine = pyttsx3.init()
voices = engine.getProperty('voices')
print(f"Total voices found: {len(voices)}")
for i, voice in enumerate(voices):
    print(f"Voice {i}:")
    print(f" - ID: {voice.id}")
    print(f" - Name: {voice.name}")
    print(f" - Languages: {voice.languages}")
    print(f" - Gender: {voice.gender}")
    print(f" - Age: {voice.age}")
    print("-" * 20)
