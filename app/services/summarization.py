import logging

import pytextrank  # noqa: F401

# from app.services.doc_analysis import NLP
from spacy.lang.ro import Romanian

from app.config import SUMMARIZATION_METHOD, SUMMARY_PHRASES, SUMMARY_SENTENCES

SNLP = Romanian()
SNLP.add_pipe("sentencizer")
logger = logging.getLogger(__name__)


def summarize(text: str) -> str:
    """Summarize text using PyTextRank."""
    if SUMMARIZATION_METHOD not in SNLP.pipe_names:
        SNLP.add_pipe(SUMMARIZATION_METHOD, last=True)
    logger.info(f"Summarizing text of {len(text)} bytes...")
    doc = SNLP(text)
    summary = list(
        doc._.textrank.summary(
            limit_phrases=SUMMARY_PHRASES, limit_sentences=SUMMARY_SENTENCES
        )
    )
    return "\n".join([s.text for s in summary])
