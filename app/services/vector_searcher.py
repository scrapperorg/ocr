import logging

import nmslib
import numpy as np
from spacy.util import filter_spans

LOGGER = logging.getLogger(__name__)


def ngram_slices(length, p, q):
    """Utility function to get start:end of an n-gram slice."""
    for start in range(0, length):
        for rng in range(p, q + 1):
            end = rng + start
            yield start, end


class VectorSearcher:
    def __init__(self) -> None:
        M = 15
        efC = 20
        num_threads = 2
        # Number of neighbors
        self.index_time_params = {
            "M": M,
            "indexThreadQty": num_threads,
            "efConstruction": efC,
            "post": 0,
        }
        # Intitialize the library, specify the space, the type of the vector and add data points
        self.index = nmslib.init(
            method="hnsw", space="cosinesimil", data_type=nmslib.DataType.DENSE_VECTOR
        )
        self.is_fit = False

    def fit(self, keyword_docs):
        vects = np.array([t.vector for t in keyword_docs])
        self.index.addDataPointBatch(vects)
        self.index.createIndex(self.index_time_params, print_progress=True)
        # Setting query-time parameters
        efS = 10
        query_time_params = {"efSearch": efS}
        self.index.setQueryTimeParams(query_time_params)
        self.is_fit = True

    def search(self, doc, thresh=0.0666):
        if not self.is_fit:
            LOGGER.debug("VectorSearcher not fit yet")
            return []
        slices = list(ngram_slices(len(doc), 2, 5))
        query_matrix = np.array([doc[start:end].vector for start, end in slices])
        spans = []
        meta_info = []
        res = self.index.knnQueryBatch(query_matrix, 10, 2)
        for i, (ids, dists) in enumerate(res):
            if any(dists < thresh):
                # spans.append(Span(doc, slices[i][0], slices[i][1] - 1, label='semantic'))
                spans.append(doc[slices[i][0] : slices[i][1]])
                meta_info.append((ids, dists))
        spans = filter_spans(spans)
        return spans
