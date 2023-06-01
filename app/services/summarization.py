import pytextrank  # noqa: F401

from app.config import SUMMARIZATION_METHOD, SUMMARY_PHRASES, SUMMARY_SENTENCES
from app.services.doc_analysis import NLP


def summarize(text):
    if SUMMARIZATION_METHOD not in NLP.pipe_names:
        NLP.add_pipe(SUMMARIZATION_METHOD, last=True)
    doc = NLP(text)
    summary = list(
        doc._.textrank.summary(
            limit_phrases=SUMMARY_PHRASES, limit_sentences=SUMMARY_SENTENCES
        )
    )
    return "\n".join([s.text for s in summary])
