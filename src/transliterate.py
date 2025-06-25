import re # lmao we dont even use this

# Read text from file
with open("data/jungfraisk.txt", "r", encoding="utf-8") as file:
    text_jungfraisk = file.read()

print("original\n", text_jungfraisk)

def transliterate(text):
    text = text.replace("ä", "a")
    text = text.replace("sk", "sch")
    text = text.replace("ii", "ie")
    return text

print("\ntransliterated\n",transliterate(text_jungfraisk))