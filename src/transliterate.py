import re

def len_first_i(x: list):
    return -len(x[0])
def load_dict(file: str)->dict:
    with open(file, encoding="utf-8") as f:
        dict_str = f.read()
        dict_str = dict_str.split("\n")
        dict = [tuple(pair.split(" ") if len(pair.split(" ")) != 1 else (pair,pair)) for pair in dict_str] # if a pair is unmatched, it replaces it with itself
        dict = sorted(dict,key=len_first_i) # sort based on length of first element to prevent matches replaces subsets
        return dict

def transliterate(text,dict):
    '''
    This function only does EXACT REPLACES
    '''
    for i, match in enumerate(dict):
        text = re.sub(match[0],chr(10330+i),text) # this fuckery uses the gothic unicode block to enforce EXACT match changes (so that changing a to e doesnt get rid of an a which came from a previous swap)
    for i, match in enumerate(dict):
        text = re.sub(chr(10330+i),match[1],text)
    return text

# Read text from file
with open("data/jungfraisk.txt", "r", encoding="utf-8") as file:
    text_jungfraisk = file.read()

print("original\n", text_jungfraisk)

# load dictionary from text file
oostfraisk = load_dict("./src/fraisk_gronings.txt")

print("\ntransliterated\n",transliterate(text_jungfraisk,oostfraisk))