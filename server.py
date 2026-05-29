from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import re
from typing import Optional
from pydantic import BaseModel
import os
from fastapi.middleware.cors import CORSMiddleware

# Load the flagged words into memory
FLAGGED_FILE = "flagged_words.json"
if os.path.exists(FLAGGED_FILE):
    with open(FLAGGED_FILE, "r", encoding="utf-8") as f:
        flagged_words = set(json.load(f))
else:
    flagged_words = set()

# Group similar sounding consonants and vowels
PHONETIC_GROUPS = [
    {'բ', 'պ', 'փ'}, # B / P / P' sounds
    {'գ', 'կ', 'ք'}, # G / K / K' sounds
    {'դ', 'տ', 'թ'}, # D / T / T' sounds
    {'ձ', 'ծ', 'ց'}, # Dz / Ts / Ts' sounds
    {'ջ', 'ճ', 'չ'}, # J / Ch / Ch' sounds
    {'ր', 'ռ'},      # R sounds
    {'է', 'ե'},      # E sounds
    {'օ', 'ո'},      # O sounds
    {'ւ', 'վ'}
]


def normalize_armenian(text):
    """Standardizes casual and standard 'ev' spellings into a single phonetic path."""
    return text.replace('և', 'եւ').replace('եվ', 'եւ')

# Create a fast lookup dictionary: e.g., FUZZY_MAP['պ'] returns {'բ', 'պ', 'փ'}
FUZZY_MAP = {}
for group in PHONETIC_GROUPS:
    for char in group:
        FUZZY_MAP[char] = group

# 1. Initialize the Web App
app = FastAPI(title="Armenian Rhyme Engine")

# Allow web browsers to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In the future, change "*" to your exact Vercel URL for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. The Reverse Trie Classes
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.words_ending_here = []

class ReverseTrie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, original_word, root_word):
        normalized_root = normalize_armenian(root_word)
        
        # Reverse the normalized word
        reversed_word = normalized_root[::-1]
        node = self.root
        
        for char in reversed_word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            
        node.is_end_of_word = True
        
        # Keep the original spelling for the frontend display
        if root_word not in node.words_ending_here:
            node.words_ending_here.append(root_word)

    def find_node(self, suffix):
        reversed_suffix = suffix[::-1]
        node = self.root
        for char in reversed_suffix:
            if char not in node.children:
                return None
            node = node.children[char]
        return node

    def _collect_all_words(self, node, collected_words):
        if node.is_end_of_word:
            collected_words.extend(node.words_ending_here)
        for child_node in node.children.values():
            self._collect_all_words(child_node, collected_words)

    def search_rhyme(self, suffix, fuzzy=False):
        if fuzzy:
            # Search multiple phonetic branches!
            nodes = self._search_fuzzy_nodes(self.root, suffix[::-1], 0)
        else:
            # Classic exact spelling search
            single_node = self.find_node(suffix)
            nodes = [single_node] if single_node else []
            
        rhymes = []
        for n in nodes:
            if n:
                self._collect_all_words(n, rhymes)
        return list(set(rhymes)) # Remove duplicates
    
    def _search_fuzzy_nodes(self, node, reversed_suffix, index):
        # If we reached the end of the suffix, return the node we landed on!
        if index == len(reversed_suffix):
            return [node]
            
        char = reversed_suffix[index]
        # Get the phonetic family (or just the letter itself if it has no family)
        allowed_chars = FUZZY_MAP.get(char, {char})
        
        found_nodes = []
        for allowed_char in allowed_chars:
            if allowed_char in node.children:
                # Recursively search down every valid phonetic branch
                found_nodes.extend(
                    self._search_fuzzy_nodes(node.children[allowed_char], reversed_suffix, index + 1)
                )
        return found_nodes

# 3. The Optimized Suffix Extractor
def extract_rhyme_suffix(word):
    word = normalize_armenian(word)
    
    match = re.search(r'(.)?((?:եւ|ու|[աեէիօո])[^աեէիօոեւու]*)$', word)
    
    if match:
        preceding_char = match.group(1) or ""
        vowel_block = match.group(2)
        if len(vowel_block) <= 2 and preceding_char:
            return preceding_char + vowel_block
        return vowel_block
    return word

# 4. Global Engine Setup
trie = ReverseTrie()

def count_armenian_syllables(word):
    """Counts written syllables by finding all Armenian vowels and digraphs."""
    # Standardize 'և' to 'եւ' for easier processing
    word = word.replace('և', 'եւ')
    
    # This regex finds 'ու', 'եւ', OR any of the single vowels.
    vowels = re.findall(r'(ու|եւ|[աեէըիոօ])', word)
    
    return len(vowels)

# This runs exactly ONCE when the server turns on
@app.on_event("startup")
def load_dictionary():
    print("Waking up server and loading 204,000 words into RAM...")
    with open("production_armenian_dictionary.json", "r", encoding="utf-8") as f:
        word_database = json.load(f)
        
    for original, root in word_database.items():
        trie.insert(original, root)
    print("Engine is locked, loaded, and ready!")

# 5. The Web Endpoint (This is what the frontend will call)
@app.get("/api/rhyme/{word}")
def get_rhymes(word: str, syllables: Optional[int] = None, fuzzy: bool = False):
    suffix = extract_rhyme_suffix(word)
    rhymes = trie.search_rhyme(suffix, fuzzy=fuzzy)
    
    if word in rhymes:
        rhymes.remove(word)
        
    if syllables:
        rhymes = [w for w in rhymes if count_armenian_syllables(w) == syllables]
        
    rich_rhymes = [
        {
            "word": w, 
            "is_flagged": w in flagged_words,
            "syllables": count_armenian_syllables(w)
        } 
        for w in rhymes
    ]
    
    # Sort by syllable count (ascending), then alphabetically
    rich_rhymes.sort(key=lambda x: (x["syllables"], x["word"]))
        
    return {
        "word_searched": word,
        "suffix_matched": suffix,
        "total_found": len(rhymes),
        "rhymes": rich_rhymes[:200]
    }

class FlagRequest(BaseModel):
    word: str

class AdminWordRequest(BaseModel):
    word: str

class EditWordRequest(BaseModel):
    old_word: str
    new_word: str

@app.post("/api/flag")
def flag_rhyme(request: FlagRequest):
    # Add to our set and save to disk immediately
    flagged_words.add(request.word)
    
    with open(FLAGGED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(flagged_words), f, ensure_ascii=False, indent=4)
        
    return {"status": "success", "word": request.word}

# ==========================================
# ADMIN ENDPOINTS
# ==========================================

@app.get("/api/flagged")
def get_flagged_words():
    """Returns the current list of flagged words."""
    return {"flagged_words": list(flagged_words)}

@app.post("/api/flagged/dismiss")
def dismiss_flag(request: AdminWordRequest):
    """Removes the flag without deleting the word from the dictionary."""
    if request.word in flagged_words:
        flagged_words.remove(request.word)
        with open(FLAGGED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(flagged_words), f, ensure_ascii=False, indent=4)
    return {"status": "success", "action": "dismissed"}

@app.post("/api/flagged/delete")
def delete_word(request: AdminWordRequest):
    """Removes the flag AND deletes the word from the main database permanently."""
    word = request.word
    
    # 1. Remove the flag
    if word in flagged_words:
        flagged_words.remove(word)
        with open(FLAGGED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(flagged_words), f, ensure_ascii=False, indent=4)
            
    # 2. Delete from the massive production dictionary
    dict_file = "production_armenian_dictionary.json"
    if os.path.exists(dict_file):
        with open(dict_file, "r", encoding="utf-8") as f:
            db = json.load(f)
            
        if word in db:
            del db[word]
            with open(dict_file, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=4)
                
    return {"status": "success", "action": "deleted"}

@app.post("/api/flagged/edit")
def edit_word(request: EditWordRequest):
    old_word = request.old_word
    new_word = request.new_word
    
    # 1. Remove the old word from the flagged list
    if old_word in flagged_words:
        flagged_words.remove(old_word)
        with open(FLAGGED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(flagged_words), f, ensure_ascii=False, indent=4)
            
    # 2. Update the main dictionary
    dict_file = "production_armenian_dictionary.json"
    if os.path.exists(dict_file):
        with open(dict_file, "r", encoding="utf-8") as f:
            db = json.load(f)
            
        if old_word in db:
            # Delete the old typo and insert the corrected version
            del db[old_word]
            # We set the key and the root to the new word
            db[new_word] = new_word
            
            with open(dict_file, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=4)
                
    return {"status": "success", "action": "edited", "new_word": new_word}