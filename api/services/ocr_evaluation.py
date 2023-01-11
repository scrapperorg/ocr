import logging
import re

import nltk

from api.utils.file_util import read_text_file, remove_diacritics
from nlp.resources.constants import RO_CHARS, VOCAB_PATH, WORDLIST_PATH

LOGGER = logging.getLogger(__name__)

nltk.download("punkt")
nltk.download("stopwords")

STEMMER = nltk.stem.snowball.SnowballStemmer("romanian")


def normalize_word(token):
    # TODO: stem
    return remove_diacritics(STEMMER.stem(token))


def load_vocabulary_words():
    vocab_words = set(read_text_file(VOCAB_PATH).split())
    custom_words = set(read_text_file(WORDLIST_PATH).split())
    vocab_words = vocab_words.union(custom_words)
    # TODO: do this once, or change file directly
    vocab_words_normalized = [normalize_word(w) for w in vocab_words]
    vocab_words = vocab_words.union(set(vocab_words_normalized))
    stopwords_words = nltk.corpus.stopwords.words("romanian")
    vocab_words = vocab_words.union(set(stopwords_words))
    return vocab_words


# TODO: compile better list of user words based on data
VOCABULARY_WORDS = load_vocabulary_words()


def validate_text(text):
    if text.startswith("[OCR skipped on page(s)"):
        return False
    if len(text.strip()) == 0:
        return False
    return True


def cer(text):
    """Character error rate (the higher the better score)"""
    total_chars = len(text)
    correct_chars = len([c for c in text.lower() if c in RO_CHARS])
    LOGGER.debug(
        f"[CER] Atypical characters: {set([c for c in text.lower() if c not in RO_CHARS])}; CER={correct_chars/total_chars * 100}"
    )
    return correct_chars / total_chars


def wer(text):
    """Word error rate (the higher the better score)"""
    # Tokenize and normalize text
    tokenized_text = nltk.word_tokenize(text.lower())
    # tokenized_text = re.split(r'[^a-zăâîșşțţ\-]+', text.lower())
    correct_words = 0
    all_words = 1
    for word in tokenized_text:
        normalized_word = normalize_word(word)
        if not normalized_word or re.fullmatch(r"[^a-z]+", normalized_word):
            continue
        if normalized_word in VOCABULARY_WORDS:
            correct_words += 1
        else:
            LOGGER.debug(
                f'[WER] Incorrect word: "{word}" (normalized as "{normalized_word}")'
            )
        all_words += 1
    if all_words == 0:
        LOGGER.warning("[WER] No words found in text.")
        return 0
    LOGGER.info(f"[WER] WER={correct_words / all_words * 100}%")
    return correct_words / all_words


def estimate_quality(text):
    """Estimate output quality based on plausible characters and words in the dictionary."""
    # TODO: also leverage already implemented "confidence" score from Tesseract
    if not validate_text(text):
        return 100
    return (cer(text) + wer(text)) / 2 * 100
