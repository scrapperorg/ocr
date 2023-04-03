import logging
from collections import defaultdict
from io import BytesIO

import fitz
import spacy
import spacy_alignments as tokenizations
from spacy.matcher import PhraseMatcher

from app.services.ocr_evaluation import normalize_word
from app.utils.file_util import read_text_file
from nlp.resources.constants import KEYWORDS_PATH

LOGGER = logging.getLogger(__name__)


def load_keywords():
    keywords = set(read_text_file(KEYWORDS_PATH).split("\n"))
    # TODO: more sophisticated keyword matching
    return keywords


MODEL_NAME = "ro_legal_fl"
if not spacy.util.is_package(MODEL_NAME):
    MODEL_NAME = "ro_core_news_sm"

NLP = spacy.load(MODEL_NAME)  # , disable=["ner", "parser"])

KEYWORDS = load_keywords()
KEYWORDS_AS_DOCS = list(NLP.pipe(KEYWORDS))
MATCHER = PhraseMatcher(NLP.vocab, attr="LEMMA")
for kw in KEYWORDS_AS_DOCS:
    MATCHER.add(kw.text, None, kw)


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


def highlight_keywords_spacy(input_pdf_path, output_pdf_path):
    highlight_meta_results = defaultdict(list)
    statistics = {}
    num_ents = 0
    num_kwds = 0
    num_wds = 0
    with fitz.open(input_pdf_path) as pdfDoc:
        statistics["num_pages"] = pdfDoc.page_count
        for pg in range(pdfDoc.page_count):
            page = pdfDoc[pg]
            word_coordinates = page.get_text_words(fitz.TEXTFLAGS_SEARCH)
            tokens_pdf = [w[4] for w in word_coordinates]
            doc = NLP(" ".join(tokens_pdf))
            num_wds += len(doc)
            tokens_spc = [t.text for t in doc]
            pdf2spc, spc2pdf = tokenizations.get_alignments(tokens_pdf, tokens_spc)
            matches = MATCHER(doc)
            matches = filter_matches(matches)
            for match_id, start, end in matches:
                num_kwds += 1
                string_id = NLP.vocab.strings[match_id]
                span = doc[start:end]
                LOGGER.debug(match_id, string_id, start, end, span.text)
                indecsi = sum(spc2pdf[start:end], [])
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
                LOGGER.debug(string_id, start, end, entity.text)
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


def highlight_keywords(input_pdf_path, output_pdf_path):
    # return highlight_keywords_strlev(input_pdf_path, output_pdf_path)
    return highlight_keywords_spacy(input_pdf_path, output_pdf_path)
