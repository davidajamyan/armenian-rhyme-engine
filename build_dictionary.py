import stanza
import json
import re

print("Loading Stanza Armenian model...")
nlp = stanza.Pipeline('hy', processors='tokenize,pos,lemma')

def is_pristine_armenian(word):
    """Strict validator to ensure only pure Armenian words get into the database."""
    # 1. Length check: Armenian words are rarely under 2 or over 22 characters.
    # This automatically drops smashed compound typos like "հանկարծհարյուր"
    if len(word) < 2 or len(word) > 22:
        return False
        
    # 2. Strict Unicode Character Check
    # \u0531-\u0556 are uppercase Armenian letters
    # \u0561-\u0587 are lowercase Armenian letters
    # \u058D is the 'և' ligature
    # This strictly forbids English letters, numbers, and all punctuation (<>.,?!)
    if not re.match(r'^[\u0531-\u0556\u0561-\u0587\u058D\-]+$', word):
        return False
        
    return True

def build_ultimate_dictionary(text_filepath):
    processed_dictionary = {}
    junk_count = 0 
    
    print(f"Reading {text_filepath}...")
    with open(text_filepath, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    print("Feeding text to Stanza... (Letting AI do the heavy lifting)")
    # We pass the raw text to Stanza. It is smart enough to handle punctuation 
    # during its own tokenization phase.
    doc = nlp(raw_text)
    
    print("Extracting and strictly validating roots...")
    for sentence in doc.sentences:
        for word in sentence.words:
            # Skip explicit punctuation or numbers identified by Stanza
            if word.upos not in ['PUNCT', 'NUM', 'SYM', 'X']:
                
                # Sometimes Stanza gets confused and returns None for a lemma
                if not word.lemma:
                    continue
                    
                original = word.text.lower()
                root = word.lemma.lower()
                
                # THE GATEKEEPER: Both the original and the root must be pure
                if is_pristine_armenian(original) and is_pristine_armenian(root):
                    if original not in processed_dictionary:
                        processed_dictionary[original] = root
                else:
                    junk_count += 1
                    
    print("-" * 40)
    print(f"Extraction complete! Found {len(processed_dictionary)} pristine unique words.")
    print(f"Blocked {junk_count} messy/smashed words from entering the database.")
    return processed_dictionary

if __name__ == "__main__":
    final_dict = build_ultimate_dictionary("eanc.txt")
    
    with open("production_armenian_dictionary.json", 'w', encoding='utf-8') as f:
        json.dump(final_dict, f, ensure_ascii=False, indent=4)
        
    print("Success! Pristine dictionary is ready for the web server.")