import re

# Read text from file
with open("data/jungfraisk.txt", "r", encoding="utf-8") as file:
    text_jungfraisk = file.read()

print("original\n", text_jungfraisk)

replacements = [ # replacement pair, in order (might work idk, tokenising might be smart)
    ("ä", "a"),
    ("sk", "sch"),
    ("ii", "ie"),
]

def transliterate(text):
    for match, sub in replacements:
        text = re.sub(match,sub,text)
    return text

print("\ntransliterated\n",transliterate(text_jungfraisk))