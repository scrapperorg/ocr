import logging
from typing import Generator, List, Tuple

import numpy as np
from sklearn.svm import OneClassSVM
from spacy.tokens import Doc, Span
from spacy.util import filter_spans

logger = logging.getLogger(__name__)


def ngram_slices(length: int, p: int, q: int) -> Generator[Tuple[int, int], None, None]:
    """Utility function to get start:end of an n-gram slice."""
    for start in range(0, length):
        for rng in range(p, q + 1):
            end = rng + start
            yield start, end


class VectorSearcher:
    def __init__(self, fraction_of_training_errors: float = 0.99) -> None:
        """Initialize the vector searcher."""
        self.model = OneClassSVM(kernel="rbf", nu=fraction_of_training_errors)
        self.is_fit = False

    def fit(self, keyword_docs: List[Doc]):
        """Fit the model using the keyword vectors."""
        vects = np.array([t.vector for t in keyword_docs])
        self.model.fit(vects)
        self.is_fit = True

    def search(self, doc: Doc) -> List[Span]:
        """Search for semantic keywords in a document."""
        if not self.is_fit:
            logger.debug("VectorSearcher not fit yet")
            return []
        slices = list(ngram_slices(len(doc), 2, 5))
        query_matrix = np.array([doc[start:end].vector for start, end in slices])
        spans = []
        if query_matrix.shape[0] == 0:
            return []
        res = self.model.predict(query_matrix)
        for i, prediction in enumerate(res):
            if prediction > 0:
                # spans.append(Span(doc, slices[i][0], slices[i][1] - 1, label='semantic'))
                spans.append(doc[slices[i][0] : slices[i][1]])
        spans = filter_spans(spans)
        return spans
