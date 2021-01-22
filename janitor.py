import operator
import re
import string
from pprint import pprint


# Implementation from nltk source
def ngrams(sequence, n):
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

        # Constants for use below
        self.delete_chars_set = frozenset(delete_chars)

        # We'll translate uppercase to lowercase and delete naughty characters. This is fast
        # https://stackoverflow.com/questions/638893/what-is-the-most-efficient-way-in-python-to-convert-a-string-to-all-lowercase-st
        self.translation_table = str.maketrans(
            string.ascii_lowercase + string.ascii_uppercase,  # These characters
            string.ascii_lowercase * 2,  # Become these characters
            delete_chars  # These are deleted
        )

    def normalize_string(self, s):
        return s.translate(self.translation_table)

    def word_ngrams(self, s):
        """Splits a string into ngram words"""
        tokens = s.split()
        # tokens = nltk.word_tokenize(s) # This is annoying, you have to download nltk stuff
        # If this doesn't evaluate a generator, we should give it one instead
        # TODO: Should remove this so there are no dependencies
        ngram_seq = ngrams(tokens, self.ngram_n)
        return (" ".join(ngram) for ngram in ngram_seq)

    def register_contaminant(self, dirt_string):
        """Register a string as contamination to be removed, e.g. a test set"""
        self.dirt_ngrams.update(self.word_ngrams(self.normalize_string(dirt_string)))

    def clean(self, dirty_string):
        """Split the source string by contamination and return clean chunks. Returns an empty list if too dirty"""
        source_ngrams = self.word_ngrams(self.normalize_string(dirty_string))

        # Other approaches: loop over the dirt_ngrams and use regex, reverse the hash set comparison
        match_indices = ((i, i+len(ngram)) for i, ngram in enumerate(source_ngrams) if ngram in self.dirt_ngrams)

        # FIXME The following is slow. We could drop this to C, but the problem is probably the approach
        #   We could remove punctuation as we create ngrams so the indices match?
        #   We should leverage the fact that we only need to consider cases where <10 ngrams match

        match = next(match_indices, None)
        # Not so dirty after all ;)
        if match is None:
            return [dirty_string]
        matches_considered = 1

        # Loop over the dirty string and build substrings which exclude any matched ngrams. This is
        # necessary because the ngram matches are in normalized string indices, NOT dirty string indices
        building_words = [[]]
        index_in_normalized = 0
        final_index = None
        for i, c in enumerate(dirty_string):
            # When we have passed the current match, get the next one
            # This must be calculated using the index in the normalized string, not the dirty one
            if index_in_normalized > match[1] + self.window_to_remove:
                match = next(match_indices, None)
                matches_considered += 1

                # If there are no more matches, stop
                if match is None:
                    final_index = i
                    break
                # If we've considered more than the limit, return empty
                if matches_considered > self.too_dirty_cutoff:
                    return []

                # Start building a new word
                building_words.append([])

            # While we're before the current match, add characters to our string builder
            if index_in_normalized < match[0] - self.window_to_remove:
                building_words[-1].append(c)

            # Our index in the normalized string is only used when the character
            if c not in self.delete_chars_set:
                index_in_normalized += 1

        # If we broke out early, add the remainder of the string to the last chunk
        if final_index is not None:
            building_words[-1].append(dirty_string[final_index:])

        return [''.join(char_list) for char_list in building_words]


    # Notes:

    # Alternative ngram impl
    # def ngrams(s, n=3):
    #     split = s.split()
    #     ngrams = zip(*[split[i:] for i in range(n)])
    #     return [' '.join(ngram) for ngram in ngrams]


    # Another attempt at clean
    # def clean(self, dirty_string):
    #     cleaner_string = self.normalize_text(dirty_string)
    #     total_splits = 0
    #
    #     for ngram in self.dirt_ngrams:
    #         # Replace match and surrounding
    #         window_match = r""  # TODO Regex for match and window surrounding it
    #         cleaner_string, match_count = re.subn(window_match, repl=self._splitter_string, string=ngram)
    #         total_splits += match_count
    #         # Suspiciously dirty. Abort.
    #         if total_splits > 10:
    #             return []
    #     # TODO This is wrong. We need to split the original string, not the normalized version.
    #     #   Would need loops.../
    #     return cleaner_string.split(self._splitter_string)

    # Another attempt at clean
    # def clean(self, dirty_string):
    #     """Split the source string by contamination and return clean chunks. Returns an empty list if too dirty"""
    #     # List of (start_idx, end_idx) for matches
    #     matches = []
    #
    #     # FIXME This will be too slow. Many ngrams.
    #     normalized = self.normalize_text(dirty_string)
    #     for ngram in self.dirt_ngrams:
    #         matches.extend([m.span() for m in re.finditer(pattern=ngram, string=normalized)])
    #         if len(matches) > self.too_dirty_cutoff:
    #             return []
    #
    #     # Sort matches by first index
    #     matches.sort(key=operator.itemgetter(0))
    #
    #     # FIXME Also too slow? If no better algo, this would be easy to go into C
    #     # Because the matches are in the index of the normalized string, we need to loop
    #     # over the original string and count non punctuation
    #     index_in_normalized = 0
    #     for c in dirty_string:
    #         # TODO
    #         if c not in self.delete_chars_set:
    #             index_in_normalized += 1



# TODO List edge cases to consider:
#   two whitespaces in a row
def test():

    jan = Janitor()

    s = """I'm a very !dirty,, dirty boy. Clean me daddy. he he he hehe heh."""
    print(jan.normalize_string(s))
    jan.register_contaminant(s)
    pprint(jan.dirt_ngrams)




if __name__ == "__main__":
    test()




