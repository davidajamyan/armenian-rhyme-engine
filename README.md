This Rhyme Engine uses a Reverse Tree to find the rhymes in Armenian.

At first, it parses the word given and removes any suffixes. It then gets the last vowel of the cleaned word and reverses it.

It traverses the Reverse Tree containing all Armenian words (cleaned, with suffixes removed) starting from the final vowel it stored.
It then goes down the Reverse Tree and tries to find every word possible as it's traversing. It adds the word to the results list, and at the end of the traversal, it returns the list.
