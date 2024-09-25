from gpt_request import TagGeneration, Translation, ArticleGeneration, ImageGeneration
from fpdf import FPDF
import os
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL")

# API_KEY = st.secrets.get("OPENAI_API_KEY")
# MODEL = st.secrets.get("OPENAI_MODEL")

# Function to save the generated article to a PDF file with Persian text support
def save_article_to_pdf(article_text, filename="generated_article.pdf"):
    pdf = FPDF()
    pdf.add_page()

    font_dir = "fonts/vazir/fonts/ttf"
    font_path = os.path.join(font_dir, "Vazirmatn-Medium.ttf")
    pdf.add_font('Vazir', '', font_path, uni=True)
    pdf.set_font('Vazir', size=12)

    # Since FPDF does not support RTL languages directly, you may need to reverse each line of the text
    # and ensure proper line breaks. Persian text is written right-to-left.
    # for line in article_text.split("\n"):
    #     reversed_line = line[::-1]  # Reverse the text for basic RTL display
    #     pdf.cell(200, 10, txt=reversed_line.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    # pdf_output = pdf.output(dest='S').encode('latin1') 

    pdf.multi_cell(0, 10, article_text)

    # Save the PDF to a BytesIO object (in-memory file)
    pdf_output = BytesIO()

    # Output the PDF content to the BytesIO object (not a filename)
    pdf.output(pdf_output, 'S').encode('latin1')

    # IMPORTANT: Ensure you seek to the start of the BytesIO object before returning it
    pdf_output.seek(0)

    return pdf_output

def generate_tags_for_dashboard(content, existing_tags):
    tag_generator = TagGeneration(MODEL, API_KEY)
    return tag_generator.process_item(content, existing_tags)

def translate_for_dashboard(content, src_lang='en', dest_lang='fa', use_gpt=False):
    translator = Translation(MODEL, API_KEY)
    if use_gpt:
        return translator.gpt_translate(content, src_lang, dest_lang)
    else:
        return translator.googletrans_translate(content, src_lang, dest_lang)

def generate_article_for_dashboard(title, source, url, date, news_content, matched_keywords=None):
    article_generator = ArticleGeneration(MODEL, API_KEY)
    return article_generator.gpt_generate_article(title, source, url, date, news_content, matched_keywords)

def generate_images_for_dashboard(prompt, num_images=1):
    image_generator = ImageGeneration(api_key=API_KEY)
    return image_generator.gpt_generate_images(prompt, num_images=num_images)
