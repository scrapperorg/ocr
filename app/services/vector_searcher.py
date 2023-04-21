import logging

import numpy as np
from sklearn.svm import OneClassSVM
from spacy.util import filter_spans

LOGGER = logging.getLogger(__name__)


def ngram_slices(length, p, q):
    """Utility function to get start:end of an n-gram slice."""
    for start in range(0, length):
        for rng in range(p, q + 1):
            end = rng + start
            yield start, end


class VectorSearcher:
    def __init__(self, fraction_of_training_errors=0.99) -> None:
        self.model = OneClassSVM(kernel="rbf", nu=fraction_of_training_errors)
        self.is_fit = False

    def fit(self, keyword_docs):
        vects = np.array([t.vector for t in keyword_docs])
        self.model.fit(vects)
        self.is_fit = True

    def search(self, doc):
        if not self.is_fit:
            LOGGER.debug("VectorSearcher not fit yet")
            return []
        slices = list(ngram_slices(len(doc), 2, 5))
        query_matrix = np.array([doc[start:end].vector for start, end in slices])
        spans = []
        res = self.model.predict(query_matrix)
        for i, prediction in enumerate(res):
            if prediction > 0:
                # spans.append(Span(doc, slices[i][0], slices[i][1] - 1, label='semantic'))
                spans.append(doc[slices[i][0] : slices[i][1]])
        spans = filter_spans(spans)
        return spans
