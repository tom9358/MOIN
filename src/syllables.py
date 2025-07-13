# splits text into syllables
import pyphen

def syllabify(text: str, lang: str = "nl_NL") -> str:
    """
    Splits the input text into syllables based on the specified language.
    
    :param text: The input text to be syllabified.
    :param lang: The language code for syllabification (default is "nl_NL").
    :return: The syllabified text.
    """
    dic = pyphen.Pyphen(lang=lang)
    return dic.inserted(text)

print(syllabify(input("Enter text to syllabify: ")))
