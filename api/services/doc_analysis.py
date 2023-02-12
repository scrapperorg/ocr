import logging
import nltk
import fitz
from io import BytesIO

from api.utils.file_util import read_text_file
from nlp.resources.constants import KEYWORDS_PATH

LOGGER = logging.getLogger(__name__)


def load_keywords():
    keywords = set(read_text_file(KEYWORDS_PATH).split('\n'))
    # TODO: more sophisticated keyword matching 
    return keywords


KEYWORDS = load_keywords()


def highlight_keywords(input_pdf_path, output_pdf_path):
	pdfDoc = fitz.open(input_pdf_path)
	for pg in range(pdfDoc.page_count):
		page = pdfDoc[pg]
		for keyword in KEYWORDS:
			# TODO: improved search, at token level, over normalized words, etc
			matching_val_area = page.search_for(keyword)
			highlight = page.add_highlight_annot(matching_val_area)
			highlight.update()
	output_buffer = BytesIO()
	pdfDoc.save(output_buffer)
	pdfDoc.close()
	with open(output_pdf_path, mode='wb') as f:
		f.write(output_buffer.getbuffer())
	# TODO: handle errors
