# Armenian Rhyme Engine

A search tool for finding rhyming words in Armenian using a **Reverse Tree** data structure.

## How the Algorithm Works

This engine finds Armenian rhymes by indexing suffix-cleaned words in a **Reverse Tree** (a trie built from the end of each word toward the beginning) and anchoring lookups at the word's final vowel.

### 1. Building the Reverse Tree (`build_dictionary.py`)
- **Suffix removal:** Words in the dataset are parsed and stripped of suffixes so matching focuses on core word endings rather than surface inflections.
- **Reverse indexing:** Each cleaned word is reversed and inserted into a tree structure, grouping words with shared endings along common branches.

### 2. Finding Rhymes at Query Time (`server.py`)
1. **Normalize & strip suffixes:** The searched word is parsed and cleaned using the same suffix-removal step applied to the dictionary.
2. **Isolate & reverse from the last vowel:** The engine locates the **last vowel** in the cleaned word and reverses the ending segment starting from that vowel.
3. **Traverse & collect matches:** It navigates the Reverse Tree starting from that vowel path and traverses downward to gather matching words into a results list, returning all collected rhymes when traversal completes.

### Project Structure
- `build_dictionary.py` — Prepares the Armenian word dataset and builds the reverse tree structure.
- `server.py` & `templates/` — Serves the web interface for word lookups.
- `data/` — Word and dictionary data files.

**Live Demo: NO LONGER WORKING** [armenian-rhyme-engine.vercel.app](https://armenian-rhyme-engine.vercel.app)
