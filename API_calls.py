from gpt_request import TagGeneration, Translation, ArticleGeneration, ImageGeneration
from fpdf import FPDF
import os

# Function to save the generated article to a PDF file with Persian text support
def save_article_to_pdf(article_text, filename="generated_article.pdf"):
    pdf = FPDF()
    pdf.add_page()

    font_dir = "fonts/vazir"
    font_path = os.path.join(font_dir, "Vazir.ttf")
    pdf.add_font('Vazir', '', 'fonts/Vazir.ttf', uni=True)
    pdf.set_font('Vazir', size=12)

    # Since FPDF does not support RTL languages directly, you may need to reverse each line of the text
    # and ensure proper line breaks. Persian text is written right-to-left.
    for line in article_text.split("\n"):
        reversed_line = line[::-1]  # Reverse the text for basic RTL display
        pdf.cell(200, 10, txt=reversed_line.encode('latin-1', 'replace').decode('latin-1'), ln=True)

    # Save the PDF file to memory
    pdf_output = pdf.output(dest='S').encode('latin1')  # 'S' returns the PDF as a string

    return pdf_output

def generate_tags_for_dashboard(content, existing_tags):
    tag_generator = TagGeneration()
    return tag_generator.process_item(content, existing_tags)

def translate_for_dashboard(content, src_lang='en', dest_lang='fa', use_gpt=False):
    translator = Translation()
    if use_gpt:
        return translator.gpt_translate(content, src_lang, dest_lang)
    else:
        return translator.googletrans_translate(content, src_lang, dest_lang)

def generate_article_for_dashboard(title, source, url, date, news_content, matched_keywords=None):
    article_generator = ArticleGeneration()
    return article_generator.gpt_generate_article(title, source, url, date, news_content, matched_keywords)

def generate_images_for_dashboard(prompt, num_images=1):
    image_generator = ImageGeneration()
    return image_generator.gpt_generate_images(prompt, num_images=num_images)
