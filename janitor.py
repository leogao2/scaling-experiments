import itertools
import re
import string
from pprint import pprint


# Implementation from nltk source
# https://www.nltk.org/_modules/nltk/util.html
def form_ngrams(sequence, n):
    history = []
    while n > 1:
        # PEP 479, prevent RuntimeError from being raised when StopIteration bubbles out of generator
        try:
            next_item = next(sequence)
        except StopIteration:
            # no more data, terminate the generator
            return
        history.append(next_item)
        n -= 1
    for item in sequence:
        history.append(item)
        yield tuple(history)
        del history[0]


def word_ngrams(s, n):
    """Splits a string into ngram words"""
    tokens = s.split()  # not a generator :(
    ngram_seqs = form_ngrams(iter(tokens), n)
    return (" ".join(ngram) for ngram in ngram_seqs)


# https://stackoverflow.com/questions/13734451/string-split-with-indices-in-python
def split_indices(s):
    """Splits a string on whitespaces and records the indices of each in the original string.
    @:return generator((word, (start_idx, end_idx)), ...)
    """
    return ((m.group(0), (m.start(), m.end() - 1)) for m in re.finditer(r'\S+', s))


def word_ngrams_indices(s, n):
    """Splits a string into pairs of (ngram words, their start/end indices)"""
    tokens_with_indices = split_indices(s)

    # Generator of ngrams of (word, idx_pairs)
    # (
    #   [(word, (start,end)), (word, (start, end))...],
    #   [(word, (start, end)), ...],
    #   ...
    # )
    ngram_seqs_with_indices = form_ngrams(tokens_with_indices, n)

    # Generator of pairs of word and index ngrams
    # (
    #   ([word, word, ...], [(start,end), (start,end), ...]),
    #   ...
    # )
    ngram_indices_pairs = (zip(*ngram_with_indices) for ngram_with_indices in ngram_seqs_with_indices)

    # Generator of ( (word_ngram, (start, end)), (word_ngram, (start, end)), ...)
    return ((" ".join(ngram_seq), (indices[0][0], indices[-1][1])) for ngram_seq, indices in ngram_indices_pairs)


class Janitor:

    # FIXME delete_chars: Should anything else go here? Special chars? Why should we remove anything at all?
    def __init__(self,
                 ngram_n=13,
                 window_to_remove=200,
                 too_dirty_cutoff=10,
                 delete_chars=string.punctuation):
        self.ngram_n = ngram_n
        self.window_to_remove=window_to_remove
        self.too_dirty_cutoff = too_dirty_cutoff

        self.dirt_ngrams = set()

        # We'll translate uppercase to lowercase and delete naughty characters. This is fast by python standards
        # https://stackoverflow.com/questions/638893/what-is-the-most-efficient-way-in-python-to-convert-a-string-to-all-lowercase-st
        self.translation_table = str.maketrans(
            string.ascii_lowercase + string.ascii_uppercase,  # These characters
            string.ascii_lowercase * 2,  # Become these characters
            delete_chars  # These are deleted
        )

        # Constants for use below
        self.ngram_missing_chars = frozenset(delete_chars + string.whitespace)

    def normalize_string(self, s):
        return s.translate(self.translation_table)

    def register_contaminant(self, dirt_string):
        """Register a string as contamination to be removed, e.g. a test set"""
        self.dirt_ngrams.update(word_ngrams(self.normalize_string(dirt_string), self.ngram_n))

    def clean(self, dirty_string):
        contamination_indices = (
            idx_pair
            for dirty_ngram, idx_pair in word_ngrams_indices(dirty_string, self.ngram_n)
            if self.normalize_string(dirty_ngram) in self.dirt_ngrams
        )

        clean_chunks = []
        splice_idx = 0
        for i, (start, end) in enumerate(contamination_indices):
            if i > self.too_dirty_cutoff:
                return []
            start = max(0, start - self.window_to_remove)
            end = min(len(dirty_string), end + self.window_to_remove)

            if start > splice_idx:
                clean_chunks.append(dirty_string[splice_idx: start])
            splice_idx = end
        return clean_chunks


# TODO List edge cases to consider:
#   multiple whitespaces in a row
#   very long document
#   'contamination' that appears very frequently
#   very long strings/sequences so ngrams are absurdly long
def test():
    jan = Janitor(window_to_remove=10)

    s = """I'm a very !dirty,, dirty boy. Clean me daddy. he he he hehe heh."""
    jan.register_contaminant(s)
    print(jan.normalize_string(s))
    pprint(jan.dirt_ngrams)
    pprint(list(word_ngrams_indices(s, 5)))
    print(jan.clean("""
    I'm a very !dirty,, dirty boy.            \n\n\n\n    Clean me daddy. he he he hehe heh. dsfsdfgdsfgesrtejhgfd
    """*5))

if __name__ == "__main__":
    test()
