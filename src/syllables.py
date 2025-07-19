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

# print(syllabify(input("Enter text to syllabify: ")))

# Entirely vibecoded manual syllabification for Dutch:
import re
def syllabify_manual(text: str) -> str:
    """
    Dutch syllabification:
      • Trema‑vowels always start new syllables.
      • Recognize trigraphs → digraphs → singles to assign vowel‐unit IDs.
      • Split at any true hiatus (unit_id change).
      • Consonant clusters: single C → onset; multi‐C → heavy‐onset
        (leave first consonant to previous coda, rest to next onset).
    """
    VOWELS = "aeiouàáâåãéèêóòôõùúûìíîAEIOUÀÁÂÅÃÉÈÊÓÒÔÕÙÚÛÌÍÎ"
    TREMA  = "äëïöüÄËÏÖÜ"
    CONS   = "bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ"

    VOWEL_UNITS = {
        # trigraphs
        "aai","eeu","ooi","ieu","oei",
        "AAI","EEU","OOI","IEU","OEI",
        "Aai","Eeu","Ooi","Ieu","Oei",
        # digraphs
        "aa","ee","oo","uu","ui",
        "ie","oe","eu","ei","ij","ou","au",
        "AA","EE","OO","UU","UI",
        "IE","OE","EU","EI","IJ","OU","AU",
        "Aa","Ee","Oo","Uu","Ui",
        "Ie","Oe","Eu","Ei","Ou","Au"
    }

    import re
    words = re.findall(r"[A-Za-zÄËÏÖÜäëïöüÀ-ÖØ-öø-ÿ]+", text)
    out = []

    for word in words:
        L = len(word)
        # 1) Build vowel‐unit IDs
        unit_id = [None]*L
        uid = 0
        i = 0
        while i < L:
            if word[i] in TREMA:
                unit_id[i] = uid
                uid += 1
                i += 1
                continue

            # trigraph
            if i+3 <= L and word[i:i+3] in VOWEL_UNITS:
                for k in range(3):
                    unit_id[i+k] = uid
                uid += 1
                i += 3
                continue
            # digraph
            if i+2 <= L and word[i:i+2] in VOWEL_UNITS:
                unit_id[i] = unit_id[i+1] = uid
                uid += 1
                i += 2
                continue
            # single vowel
            if word[i] in VOWELS:
                unit_id[i] = uid
                uid += 1
            i += 1

        # 2) Syllable splitting
        sylls = []
        last_cut = 0
        i = 1
        while i < L:
            prev, curr = word[i-1], word[i]

            # a) split before trema
            if curr in TREMA:
                sylls.append(word[last_cut:i])
                last_cut = i
                i += 1
                continue

            # b) true V–V hiatus
            if (unit_id[i-1] is not None and unit_id[i] is not None
                and unit_id[i-1] != unit_id[i]):
                sylls.append(word[last_cut:i])
                last_cut = i
                i += 1
                continue

            # c) consonant cluster after vowel → heavy-onset
            if prev in VOWELS+TREMA and curr in CONS:
                j = i
                while j < L and word[j] in CONS:
                    j += 1
                if j < L and word[j] in VOWELS+TREMA:
                    cluster_len = j - i
                    # single C → onset; multi-C → leave first C in coda
                    split_at = i if cluster_len == 1 else (i + 1)
                    sylls.append(word[last_cut:split_at])
                    last_cut = split_at
                    i = split_at + 1
                    continue

            i += 1

        # final syllable
        sylls.append(word[last_cut:])
        out.append("|".join(sylls))

    return ", ".join(out)


# Example usage
while 1:
    print(syllabify_manual(input()))
