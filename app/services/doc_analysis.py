import logging
import os
from collections import defaultdict
from io import BytesIO

import fitz
import numpy as np
import spacy
import spacy_alignments as tokenizations
from sklearn.metrics.pairwise import cosine_similarity
from spacy.matcher import PhraseMatcher
from spacy.tokens import Token
from spacy.util import filter_spans

from app.services.synonyms import get_synonyms
from app.services.text_processing import remove_diacritics
from app.services.vector_searcher import VectorSearcher
from app.utils.file_util import read_text_file
from nlp.resources.constants import KEYWORDS_PATH

LOGGER = logging.getLogger(__name__)
VECTOR_SEARCH = bool(os.environ.get("VECTOR_SEARCH", False))
NLP = None
KEYWORDS_AS_DOCS = None
ORTH_MATCHER = None
LAST_KEYWORDS_HASH = "0"
LEMMA_MATCHER = None
VECTOR_SEARCHER = VectorSearcher()


def load_spacy_global_model():
    """Load spacy global model"""
    global NLP
    enable_ner = bool(os.environ.get("ENABLE_NER", False))
    pipelines_to_disable = ["ner", "parser"]
    if enable_ner:
        pipelines_to_disable = []
    model_name = os.environ.get("SPACY_MODEL", "ro_legal_fl")
    if not spacy.util.is_package(model_name):
        model_name = "ro_core_news_lg"
    NLP = spacy.load(model_name, disable=pipelines_to_disable)
    LOGGER.info(f"Loaded model {model_name}.")
    return NLP


NLP = load_spacy_global_model()
Token.set_extension("synonyms", getter=get_synonyms)


def process_keywords_with_spacy(keywords, nlp):
    """Process keywords with spacy"""
    keywords_as_docs = list(nlp.pipe(keywords))
    return keywords_as_docs


def make_lemma_matcher(keywords_as_docs, nlp):
    """Lemma based matcher"""
    lemma_matcher = PhraseMatcher(nlp.vocab, attr="LEMMA")
    for kw in keywords_as_docs:
        lemma_matcher.add(kw.text, None, kw)
    return lemma_matcher


def make_orth_matcher(keywords_as_docs, nlp):
    """Lower case based matcher"""
    orth_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for kw in keywords_as_docs:
        orth_matcher.add(kw.text, None, kw)
    return orth_matcher


def get_token_context(token, window=1):
    start = max(token.i - window, 0)
    end = min(token.i + window + 1, len(token.doc))
    return token.doc[start:end]


def filter_synonyms(token, synonyms, nlp, threhsold=0.5):
    if not synonyms:
        return []
    vectors = [nlp.vocab[synonym].vector for synonym in synonyms]
    similarity = cosine_similarity([token.doc.vector], vectors)
    locations = np.where(similarity > threhsold)[1]
    return [synonyms[location] for location in locations]


def get_token_variants(keyword_token):
    variants = [
        keyword_token.text,
        remove_diacritics(keyword_token.text),
        keyword_token.lemma_,
    ]
    synonyms = filter_synonyms(keyword_token, keyword_token._.synonyms, NLP)
    variants.extend(synonyms)
    variants.extend([remove_diacritics(synonym) for synonym in synonyms])
    return list(set(variants))


def make_keywords_in_spacy(keywords_as_docs, nlp):
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


def update_global_kewyord_vars(keywords):
    global KEYWORDS_AS_DOCS, ORTH_MATCHER, LEMMA_MATCHER, VECTOR_SEARCHER
    KEYWORDS_AS_DOCS = process_keywords_with_spacy(keywords, NLP)
    ORTH_MATCHER = make_orth_matcher(KEYWORDS_AS_DOCS, NLP)
    LEMMA_MATCHER = make_lemma_matcher(KEYWORDS_AS_DOCS, NLP)
    make_keywords_in_spacy(KEYWORDS_AS_DOCS, NLP)
    if VECTOR_SEARCH:
        LOGGER.info("Building vector searcher for keywords...")
        VECTOR_SEARCHER.fit(KEYWORDS_AS_DOCS)


def load_response_keywords(keywords_response):
    return set(
        [kwd["name"].strip() for kwd in keywords_response if kwd["name"].strip()]
    )


def load_default_file_keywords():
    keywords = [
        word for word in read_text_file(KEYWORDS_PATH).split("\n") if word.strip()
    ]
    keywords = set(keywords)
    return [{"name": keyword} for keyword in keywords]


"""
def highlight_keywords_semantic(input_pdf_path, output_pdf_path):
    # Under construction
    highlight_meta_results = []
    with fitz.open(input_pdf_path) as pdfDoc:
        for pg in range(pdfDoc.page_count):
            page = pdfDoc[pg]
            word_coordinates = page.get_text_words()
            word_coordinates_index = {}
            for coord in word_coordinates:
                word = coord[4]
                stem = normalize_word(word)
                if word not in word_coordinates_index:
                    word_coordinates_index[stem] = []
                    word_coordinates_index[stem].append(
                        coord[1:4]
                    )  # rectangle coordinates indexed by stem
            for keyword in KEYWORDS:
                # TODO: currently able to match based on individual stems
                # TODO: extend to multiword expressions
                # TODO: use spacy to match based on lemmas instead of stems
                keyword_stem = normalize_word(keyword)
                if keyword_stem in word_coordinates_index:
                    highlight_meta_result = {
                        "keyword": keyword,
                        "occs": [],
                    }  # TODO: parametrize format
                    for area in word_coordinates_index[keyword_stem]:
                        location_js = {
                            "page": pg,
                            "location": {
                                "x1": area[1],
                                "x2": area[2],
                                "y1": area[0],
                                "y2": area[4],
                            },
                        }
                        highlight_meta_result["occs"].append(location_js)
                    highlight_meta_results.append(highlight_meta_result)

                    highlight = page.add_highlight_annot(fitz.Rect(area[0:4]))
                    highlight.update()
        output_buffer = BytesIO()
        pdfDoc.save(output_buffer)

    with open(output_pdf_path, mode="wb") as f:
        f.write(output_buffer.getbuffer())

    return highlight_meta_results
    # TODO: handle errors


def highlight_keywords_strlev(input_pdf_path, output_pdf_path):
    highlight_meta_results = defaultdict(list)
    with fitz.open(input_pdf_path) as pdfDoc:
        for pg in range(pdfDoc.page_count):
            page = pdfDoc[pg]
            for keyword in KEYWORDS:
                matching_val_areas = page.search_for(keyword)
                for area in matching_val_areas:
                    # TODO: handle multiword expressions to only return one occurrence (first word only)
                    location_js = {
                        "page": pg,
                        "location": {
                            "x1": area.x0,
                            "x2": area.x1,
                            "y1": area.y0,
                            "y2": area.y1,
                        },
                    }
                    highlight_meta_results[keyword].append(location_js)

                highlight = page.add_highlight_annot(matching_val_areas)
                highlight.set_colors(stroke=[0.5, 1, 1])
                highlight.update()
        output_buffer = BytesIO()
        pdfDoc.save(output_buffer)

    with open(output_pdf_path, mode="wb") as f:
        f.write(output_buffer.getbuffer())

    highlight_meta_js = []
    for k in highlight_meta_results:
        highlight_meta_js.append(
            {
                "keyword": k,
                "occs": highlight_meta_results[k],
                "total_occs": len(highlight_meta_results[k]),
            }
        )
    return highlight_meta_js
    # TODO: handle errors
"""


def filter_matches(matches):
    """Filter a sequence of spans and remove duplicates or overlaps. Useful for
    creating named entities (where one token can only be part of one entity) or
    when merging spans with `Retokenizer.merge`. When spans overlap, the (first)
    longest span is preferred over shorter spans.
    """

    def get_sort_key(match):
        return (match[2] - match[1], -match[1])

    sorted_matches = sorted(matches, key=get_sort_key, reverse=True)
    result = []
    seen_tokens = set()
    for match_id, start, end in sorted_matches:
        # Check for end - 1 here because boundaries are inclusive
        if start not in seen_tokens and end - 1 not in seen_tokens:
            result.append((match_id, start, end))
            seen_tokens.update(range(start, end))
    result = sorted(result, key=lambda match: match[0])
    return result


def do_matching(doc):
    matches = LEMMA_MATCHER(doc, as_spans=True)
    matches.extend(ORTH_MATCHER(doc, as_spans=True))
    matches.extend(doc.spans["ruler"])
    matches = filter_spans(matches)
    return matches


def highlight_keywords_spacy(input_pdf_path, output_pdf_path):
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
                LOGGER.debug(
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
                LOGGER.debug(
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
                highlight.set_colors(stroke=[0.5, 1, 1])
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
                LOGGER.debug(
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
    # TODO: handle errors


def highlight_keywords(input_pdf_path, output_pdf_path, keywords, last_modified):
    global LAST_KEYWORDS_HASH
    LOGGER.info(
        f"Highlighting with keywords list hash '{last_modified}' of '{len(keywords)}' keywords"
    )
    if last_modified != LAST_KEYWORDS_HASH:
        LAST_KEYWORDS_HASH = last_modified
        keywords = load_response_keywords(keywords)
        update_global_kewyord_vars(keywords)
    return highlight_keywords_spacy(input_pdf_path, output_pdf_path)
