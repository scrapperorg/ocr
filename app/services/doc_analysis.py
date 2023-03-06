import logging
from io import BytesIO

import fitz

from app.utils.file_util import read_text_file
from nlp.resources.constants import KEYWORDS_PATH

LOGGER = logging.getLogger(__name__)


def load_keywords():
    keywords = set(read_text_file(KEYWORDS_PATH).split("\n"))
    # TODO: more sophisticated keyword matching
    return keywords


KEYWORDS = load_keywords()


def highlight_keywords(input_pdf_path, output_pdf_path):
    highlight_meta_results = []
    with fitz.open(input_pdf_path) as pdfDoc:
        for pg in range(pdfDoc.page_count):
            page = pdfDoc[pg]
            for keyword in KEYWORDS:
                # TODO: improved search, at token level, over normalized words, etc
                matching_val_areas = page.search_for(keyword)
                highlight_meta_result = {"keyword": keyword, "occs": []} # TODO: parametrize format
                for area in matching_val_areas:
                    location_js = {"page": pg, "location": 
                        {
                            "x1": area.x0, "x2": area.x1, "y1": area.y0, "y2": area.y1}
                        }
                    highlight_meta_result["occs"].append(location_js)
                if matching_val_areas:
                    highlight_meta_results.append(highlight_meta_result)
                highlight = page.add_highlight_annot(matching_val_areas)
                highlight.update()
        output_buffer = BytesIO()
        pdfDoc.save(output_buffer)

    with open(output_pdf_path, mode="wb") as f:
        f.write(output_buffer.getbuffer())

    return highlight_meta_results
    # TODO: handle errors
