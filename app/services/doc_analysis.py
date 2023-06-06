import logging
import os
from collections import defaultdict
from io import BytesIO
from typing import Dict, List, Tuple

import fitz
import numpy as np
import spacy
import spacy_alignments as tokenizations
from sklearn.metrics.pairwise import cosine_similarity
from spacy.language import Language
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc, Span, Token
from spacy.util import filter_spans

from app.config import VECTOR_SEARCH
from app.services.synonyms import get_synonyms
from app.services.text_processing import remove_diacritics
from app.services.vector_searcher import VectorSearcher
from app.utils.file_util import read_text_file
from nlp.resources.constants import KEYWORDS_PATH

logger = logging.getLogger(__name__)
NLP = None
KEYWORDS_AS_DOCS = None
ORTH_MATCHER = None
LAST_KEYWORDS_HASH = "0"
LEMMA_MATCHER = None
VECTOR_SEARCHER = VectorSearcher()


def load_spacy_global_model() -> spacy.language.Language:
    """Load spacy global model"""
    global NLP
    enable_ner = bool(os.environ.get("ENABLE_NER", False))
    pipelines_to_disable = ["attribute_ruler", "ner"]
    if enable_ner:
        pipelines_to_disable = []
    model_name = os.environ.get("SPACY_MODEL", "ro_legal_fl")
    if not spacy.util.is_package(model_name):
        model_name = "ro_core_news_lg"
    NLP = spacy.load(model_name, disable=pipelines_to_disable)
    logger.info(f"Loaded model {model_name}.")
    return NLP


NLP = load_spacy_global_model()
Token.set_extension("synonyms", getter=get_synonyms)


def process_keywords_with_spacy(keywords: List[str], nlp: Language) -> List[Doc]:
    """Process keywords with spacy"""
    keywords_as_docs = list(nlp.pipe(keywords))
    return keywords_as_docs


def make_lemma_matcher(keywords_as_docs: List[Doc], nlp: Language) -> PhraseMatcher:
    """Lemma based matcher"""
    lemma_matcher = PhraseMatcher(nlp.vocab, attr="LEMMA")
    for kw in keywords_as_docs:
        lemma_matcher.add(kw.text, None, kw)
    return lemma_matcher


def make_orth_matcher(keywords_as_docs: List[Doc], nlp: Language) -> PhraseMatcher:
    """Lower case based matcher"""
    orth_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for kw in keywords_as_docs:
        orth_matcher.add(kw.text, None, kw)
    return orth_matcher


def get_token_context(token: Token, window: int = 1):
    """Obtain the context of a token in a document."""
    start = max(token.i - window, 0)
    end = min(token.i + window + 1, len(token.doc))
    return token.doc[start:end]


def filter_synonyms(
    token: Token, synonyms: List[str], nlp: Language, threhsold: float = 0.5
) -> List[str]:
    """Filter synonyms based on cosine similarity with the context.

    :param token: spacy token with synonyms property
    :param synonyms: list of synonyms
    :param nlp: spacy language model
    :param threhsold: cosine similarity threshold, defaults to 0.5
    :return: list of synonyms that are similar to the context
    """
    if not synonyms:
        return []
    vectors = [nlp.vocab[synonym].vector for synonym in synonyms]
    similarity = cosine_similarity([token.doc.vector], vectors)
    locations = np.where(similarity > threhsold)[1]
    return [synonyms[location] for location in locations]


def get_token_variants(keyword_token: Token) -> List[str]:
    """Get all variants of a token with synonyms, diacritics and no diac."""
    variants = [
        keyword_token.text,
        remove_diacritics(keyword_token.text),
        keyword_token.lemma_,
    ]
    synonyms = filter_synonyms(keyword_token, keyword_token._.synonyms, NLP)
    variants.extend(synonyms)
    variants.extend([remove_diacritics(synonym) for synonym in synonyms])
    return list(set(variants))


def make_keywords_in_spacy(keywords_as_docs: List[Token], nlp: Language) -> None:
    """Change the NLP pipeline to include the keywords as entities.

    :param keywords_as_docs: list of keywords as spacy docs
    :param nlp: spacy language model
    """
    if "span_ruler" in nlp.pipe_names:
        nlp.remove_pipe("span_ruler")
    ruler = nlp.add_pipe("span_ruler")
    patterns = []
    for kw in keywords_as_docs:
        variants = []
        for token in kw:
            variants.append(get_token_variants(token))
            # kw_patterns.append({"LOWER": {"FUZZY": token.text}})
        kw_patterns = [{"LOWER": {"IN": token_variants}} for token_variants in variants]
        patterns.append({"label": kw.text, "pattern": kw_patterns})
        kw_patterns = [{"LEMMA": {"IN": token_variants}} for token_variants in variants]
        patterns.append({"label": kw.text, "pattern": kw_patterns})
        kw_patterns = [{"ORTH": {"IN": token_variants}} for token_variants in variants]
        patterns.append({"label": kw.text, "pattern": kw_patterns})
    ruler.add_patterns(patterns)


def update_global_kewyord_vars(keywords: List[str]) -> None:
    """Update the global variables used for keyword matching.

    :param keywords: List of string keywords
    """
    global KEYWORDS_AS_DOCS, ORTH_MATCHER, LEMMA_MATCHER, VECTOR_SEARCHER
    KEYWORDS_AS_DOCS = process_keywords_with_spacy(keywords, NLP)
    ORTH_MATCHER = make_orth_matcher(KEYWORDS_AS_DOCS, NLP)
    LEMMA_MATCHER = make_lemma_matcher(KEYWORDS_AS_DOCS, NLP)
    make_keywords_in_spacy(KEYWORDS_AS_DOCS, NLP)
    if VECTOR_SEARCH:
        logger.info("Building vector searcher for keywords...")
        VECTOR_SEARCHER.fit(KEYWORDS_AS_DOCS)


def load_response_keywords(keywords_response: List[dict]) -> List[str]:
    """Utility function to get the keywords as string from the API response."""
    return list(
        set([kwd["name"].strip() for kwd in keywords_response if kwd["name"].strip()])
    )


def load_default_file_keywords() -> List[dict]:
    """Load the default keywords from the file."""
    keywords = [
        word for word in read_text_file(KEYWORDS_PATH).split("\n") if word.strip()
    ]
    keywords = set(keywords)
    return [{"name": keyword} for keyword in keywords]


def do_matching(doc: Doc) -> List[Span]:
    """Do the matching of the keywords in the document.

    :param doc: spacy document
    :return: list of spans with matched keywords
    """
    matches = LEMMA_MATCHER(doc, as_spans=True)
    matches.extend(ORTH_MATCHER(doc, as_spans=True))
    matches.extend(doc.spans["ruler"])
    matches = filter_spans(matches)
    return matches


def highlight_keywords_spacy(
    input_pdf_path: str, output_pdf_path: str
) -> Tuple[Dict, Dict]:
    """Highlight keywords of a PDF file and write the output.

    :param input_pdf_path: input PDF file
    :param output_pdf_path: output PDF file
    :return: metadata and statistics
    """
    highlight_meta_results = defaultdict(list)
    statistics = {}
    num_ents = 0
    num_kwds = 0
    num_wds = 0
    num_chars = 0
    with fitz.open(input_pdf_path) as pdfDoc:
        statistics["num_pages"] = pdfDoc.page_count
        for pg in range(pdfDoc.page_count):
            page = pdfDoc[pg]
            word_coordinates = page.get_text_words(fitz.TEXTFLAGS_SEARCH)
            tokens_pdf = [w[4] for w in word_coordinates]
            doc = NLP(" ".join(tokens_pdf))
            num_wds += len(doc)
            num_chars += len(doc.text)
            tokens_spc = [t.text for t in doc]
            pdf2spc, spc2pdf = tokenizations.get_alignments(tokens_pdf, tokens_spc)
            matches = do_matching(doc)
            for entity in matches:
                num_kwds += 1
                string_id = entity.label_
                logger.debug(
                    f"{string_id}, {entity.start}, {entity.end}, {entity.text}"
                )
                indecsi = sum(spc2pdf[entity.start : entity.end], [])
                pozitii = [fitz.Rect(word_coordinates[idx][0:4]) for idx in indecsi]
                if pozitii:
                    area = pozitii[0]
                    location_js = {
                        "page": pg,
                        "location": {
                            "x1": area.x0,
                            "x2": area.x1,
                            "y1": area.y0,
                            "y2": area.y1,
                        },
                    }
                    highlight_meta_results[string_id].append(location_js)
                highlight = page.add_highlight_annot(pozitii)
                highlight.set_info(content=string_id)
                highlight.update()

            for entity in VECTOR_SEARCHER.search(doc):
                # num_kwds += 1
                string_id = entity.label_
                logger.debug(
                    f"{string_id}, {entity.start}, {entity.end}, {entity.text}"
                )
                indecsi = sum(spc2pdf[entity.start : entity.end], [])
                pozitii = [fitz.Rect(word_coordinates[idx][0:4]) for idx in indecsi]
                if pozitii:
                    area = pozitii[0]
                    location_js = {
                        "page": pg,
                        "location": {
                            "x1": area.x0,
                            "x2": area.x1,
                            "y1": area.y0,
                            "y2": area.y1,
                        },
                    }
                    # highlight_meta_results[string_id].append(location_js)
                highlight = page.add_highlight_annot(pozitii)
                highlight.set_colors(stroke=[0.8, 1, 1])
                highlight.set_info(content=string_id)
                highlight.update()

            for entity in doc.ents:
                if entity.label_ not in {
                    "LEGAL",
                    "PERSON",
                    "NAT_REL_POL",
                    "GPE",
                    "ORGANIZATION",
                }:
                    continue
                num_ents += 1
                string_id = entity.text
                logger.debug(
                    f"{string_id}, {entity.start}, {entity.end}, {entity.text}"
                )
                indecsi = sum(spc2pdf[entity.start : entity.end], [])
                pozitii = [fitz.Rect(word_coordinates[idx][0:4]) for idx in indecsi]
                if pozitii:
                    area = pozitii[0]
                    location_js = {
                        "page": pg,
                        "location": {
                            "x1": area.x0,
                            "x2": area.x1,
                            "y1": area.y0,
                            "y2": area.y1,
                        },
                    }
                    highlight_meta_results[string_id].append(location_js)
                highlight = page.add_underline_annot(pozitii)
                highlight.set_colors(stroke=[0.5, 1, 1])
                highlight.set_info(content=string_id)
                highlight.update()
        output_buffer = BytesIO()
        pdfDoc.save(output_buffer)

    with open(output_pdf_path, mode="wb") as f:
        f.write(output_buffer.getbuffer())
    statistics["num_ents"] = num_ents
    statistics["num_kwds"] = num_kwds
    statistics["num_wds"] = num_wds
    statistics["num_chars"] = num_chars
    highlight_meta_js = []
    for k in highlight_meta_results:
        highlight_meta_js.append(
            {
                "keyword": k,
                "occs": highlight_meta_results[k],
                "total_occs": len(highlight_meta_results[k]),
            }
        )
    return highlight_meta_js, statistics


def highlight_keywords(
    input_pdf_path: str, output_pdf_path: str, keywords: List[Dict], last_modified: str
) -> Tuple[Dict, Dict]:
    """Highlight keywords of a PDF file and write the output.

    :param input_pdf_path: input PDF file
    :param output_pdf_path: output PDF file
    :param keywords: keywords list from API
    :param last_modified: hash of the keywords list
    :return: metadata and statistics
    """
    global LAST_KEYWORDS_HASH
    logger.debug(
        f"Highlighting with keywords list hash '{last_modified}' of '{len(keywords)}' keywords"
    )
    if last_modified != LAST_KEYWORDS_HASH:
        try:
            keywords = load_response_keywords(keywords)
            update_global_kewyord_vars(keywords)
            LAST_KEYWORDS_HASH = last_modified
        except Exception:
            logger.exception("Failed to update the list of keywords.")
        logger.info(
            f"Highlighting with keywords list hash '{last_modified}' of '{len(keywords)}' keywords"
        )
    return highlight_keywords_spacy(input_pdf_path, output_pdf_path)
