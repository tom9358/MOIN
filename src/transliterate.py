import re
import argparse

def swap_dict(infile: str, outfile: str):
    with open(infile, encoding="utf-8") as f:
        dict_str = f.read()
        dict_str = dict_str.split("\n")
        dict = [tuple(list(reversed(pair.split(" "))) if len(pair.split(" ")) != 1 else (pair,pair)) for pair in dict_str] # if a pair is unmatched, it replaces it with itself
        outf = open(outfile, "w+", encoding="utf-8")
        lines = [" ".join(pair) + "\n" for pair in dict]
        outf.writelines(lines)
        outf.close()

def len_first_i(x: list):
    return -len(x[0])

def load_dict(file: str) -> dict:
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

parser = argparse.ArgumentParser(
                    prog='MOIN',
                    description='Transliterate between low german orthographies',
                    epilog='specify filename and valid dictionary using -d')
parser.add_argument('filename')           # positional argument
parser.add_argument('-d', '--dict')      # option that takes a value
args = parser.parse_args()

# Read text from file
try:
    with open(args.filename, "r", encoding="utf-8") as file:
        text = file.read()

    print("original\n", text)

    # load dictionary from text file
    dictionary = load_dict(args.dict)

    print("\ntransliterated\n",transliterate(text,dictionary))

except Exception as e:
    print(f"An error occurred: {e}")
