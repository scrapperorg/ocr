import logging
from collections import defaultdict
from io import BytesIO

import fitz

from app.services.ocr_evaluation import normalize_word
from app.utils.file_util import read_text_file
from nlp.resources.constants import KEYWORDS_PATH

LOGGER = logging.getLogger(__name__)


def load_keywords():
    keywords = set(read_text_file(KEYWORDS_PATH).split("\n"))
    # TODO: more sophisticated keyword matching
    return keywords


KEYWORDS = load_keywords()


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


def highlight_keywords(input_pdf_path, output_pdf_path):
    return highlight_keywords_strlev(input_pdf_path, output_pdf_path)
