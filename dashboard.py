import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import tldextract
from database import DatabaseManager
from bs4 import BeautifulSoup
import re
from gpt_request import *

# Set page config only once at the start of the script
st.set_page_config(
    page_title="News Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Connect to the database
db_manager = DatabaseManager()
db_manager.connect()
news_data = db_manager.load_content_data()

# Language selection
# language = st.sidebar.radio("انتخاب زبان", ("فارسی", "انگلیسی"))
language = "فارسی"

# Define page names for both languages
page_names = {
    "فارسی": ["همه اخبار", "جزئیات خبر", "آمار"],
}

# Initialize session state for page navigation
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'همه اخبار'
    

# Get the current page from session state
current_page = st.session_state['current_page']

if current_page not in page_names["فارسی"]:
    current_page = "همه اخبار"  # Reset to default if not found

# Sidebar navigation (always visible)
page = st.sidebar.selectbox(
    "رفتن به صفحه" ,
    page_names[language],
    index=page_names[language].index(current_page)
)

# Update session state
st.session_state['current_page'] = page

# Inject CSS dynamically based on the language selection
direction = "rtl"
align = "right"

st.markdown(
    f"""
    <style>
    body {{
        direction: {direction};
        text-align: {align};
        font-family: "IRANSans", sans-serif;
        background-color: #f5f7fa;
    }}
    .css-1d391kg {{  /* Sidebar styling */
        direction: {direction};
        text-align: {align};
    }}
    .stTitle, .stHeader, .stText {{
        color: #343a40;
    }}
    img {{
        max-width: 60%; 
        margin-x:auto
    }}
    </style>
    """,
    unsafe_allow_html=True
)
    # p {{
    #     text-align:{content_align};
    #     direction:{content_direction};
    #     font-family: {content_font_family}
    # }}

def filter_news(data, title_search='', content_keywords='', sources=None, start_date=None, end_date=None):
    """Filter news data based on the user's input criteria."""
    if title_search:
        data = pd.concat([
            data[data['title_persian'].str.contains(title_search, case=False, na=False)],
            data[data['title'].str.contains(title_search, case=False, na=False)]
        ])

    
    if content_keywords:
        # Split keywords by comma, strip whitespaces, and filter
        keywords = [kw.strip() for kw in content_keywords.split(',')]
        if keywords:
            keyword_pattern = '|'.join(keywords)  # Create regex pattern with OR between keywords
            data = pd.concat([
                data[data['content_persian'].str.contains(keyword_pattern, case=False, na=False)],
                data[data['content'].str.contains(keyword_pattern, case=False, na=False)]
            ])

    
    if sources and "همه" not in sources:
        # If specific sources are selected, filter by those sources
        data = data[data['source'].isin(sources)]
    
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        data = data[(data['date'] >= start_date) & (data['date'] <= end_date)]
    
    return data

def extract_domain(url):
    """Extract domain from the URL."""
    domain = tldextract.extract(url).registered_domain
    return domain

def render_content(content, language='fa'):
    if 'language_option' not in st.session_state:
        st.session_state['language_option'] = 'انگلیسی'
        
    language_option = st.session_state['language_option']

    if language_option == "انگلیسی": 
        content_direction = "ltr"
        content_align = "left"
        content_font_family = '"Arial", sans-serif'
    else:
        content_direction = "rtl"
        content_align = "right"
        content_font_family = '"IRANSans", sans-serif'
        
    def render_html(soup):
        for element in soup.children:
            if element.name == 'p':
                text = element.get_text()
                # Apply CSS directly to each <p> tag
                st.markdown(
                    f"""
                    <p style="direction: {content_direction}; text-align: {content_align}; font-family: {content_font_family};">
                    {text}
                    </p>
                    """, 
                    unsafe_allow_html=True
                )
            elif element.name == 'img':
                image_url = element.get('src')
                image_alt = element.get('alt')
                # Apply styles to images
                image_style = f"direction: {content_direction}; text-align: {content_align}; font-family: {content_font_family};"
                
                if image_url.endswith('.svg'):
                    # Display the SVG icon with the text side by side
                    st.markdown(
                        f"""
                        <div style="{image_style}; display: inline-flex; align-items: center;">
                            <img src="{image_url}" width="25px" alt="{image_alt}" style="margin-right: 10px;"/>
                            <span>{image_alt}</span>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                else:
                    # For non-SVG images, style as before
                    st.markdown(
                        f"""
                        <div style="{image_style}">
                            <img src="{image_url}" style="width: 1000px;"/>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            elif element.name == 'ul':
                for li in element.find_all('li'):
                    st.markdown(f"- {li.get_text()}", unsafe_allow_html=True)
            elif element.name == 'blockquote':
                st.markdown(f"> {element.get_text()}", unsafe_allow_html=True)

    # Call render_html with your styles
    soup = BeautifulSoup(content, 'html.parser')
    render_html(soup)



def keyword_weight_input():
    keyword_weight_pairs = []
    st.sidebar.markdown("### فیلتر با کلمات کلیدی و وزن‌ها")
    number_of_keywords = st.sidebar.number_input("تعداد کلمات کلیدی", min_value=1, max_value=10, value=1)
    for i in range(int(number_of_keywords)):
        keyword = st.sidebar.text_input(f"کلمه کلیدی {i+1}")
        weight = st.sidebar.number_input(f"وزن {i+1} (حداقل دفعات مشاهده)", min_value=1, max_value=10, value=1)
        keyword_weight_pairs.append((keyword, weight))
    return keyword_weight_pairs

def clean_content(content):
    # Remove HTML tags
    soup = BeautifulSoup(content, 'html.parser')
    text = soup.get_text()

    # Remove extra spaces and newlines
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def filter_by_keywords(news_data, keyword_weight_pairs):
    news_data['matched_keywords'] = None  # Add a column to store matched keywords

    for index, row in news_data.iterrows():
        content_cleaned = clean_content(row['content'])
        matched_keywords = []

        # Check if each keyword exists in the content with at least the specified weight
        for keyword, weight in keyword_weight_pairs:
            count = content_cleaned.lower().count(keyword.lower())
            if count >= weight:
                matched_keywords.append(keyword)

        # If at least one keyword matches the criteria, update the 'matched_keywords' column
        if matched_keywords:
            news_data.at[index, 'matched_keywords'] = matched_keywords

    # Return the modified news_data
    return news_data.dropna(subset=['matched_keywords'])



    
def all_news_page():
    st.title("📋 همه اخبار")

    # Filtering options
    st.sidebar.header("🔍 فیلتر کردن اخبار")
    title_search = st.sidebar.text_input("جستجو در عنوان")

    # Use the keyword_weight_input function for keyword-weight pair input
    content_keywords = keyword_weight_input()

    # Filtering other options
    unique_sources = news_data['source'].dropna().unique()
    unique_sources = sorted(unique_sources)
    unique_sources.insert(0, "همه")

    news_data['domain'] = news_data['url'].apply(extract_domain)
    unique_domains = news_data['domain'].dropna().unique()
    unique_domains = sorted(unique_domains)
    unique_domains.insert(0, "همه")

    unique_types = news_data['type'].dropna().unique()
    unique_types = sorted(unique_types)
    unique_types.insert(0, "همه")

    # Multi-select for sources
    source_filter = st.sidebar.multiselect("فیلتر بر اساس منبع", unique_sources, default=["همه"])

    domain_filter = st.sidebar.selectbox("فیلتر بر اساس وب‌سایت", unique_domains)
    type_filter = st.sidebar.selectbox("فیلتر بر اساس نوع خبر", unique_types)

    start_date = st.sidebar.date_input("تاریخ شروع", value=datetime.now() - timedelta(days=7))
    end_date = st.sidebar.date_input("تاریخ پایان", value=datetime.now())

    sort_by = st.sidebar.selectbox("مرتب‌سازی بر اساس", 
                                   ["تاریخ", "عنوان", "منبع", "امتیاز نهایی"])
    sort_order = st.sidebar.radio("ترتیب مرتب‌سازی", ["نزولی", "صعودی"])

    # Apply filtering by keywords and other criteria
    filtered_data = filter_by_keywords(news_data, content_keywords)

    filtered_data = filter_news(
        filtered_data,
        title_search,
        None,
        source_filter if "همه" not in source_filter else None,
        start_date,
        end_date
    )
    
    if domain_filter != "همه":
        filtered_data = filtered_data[filtered_data['domain'] == domain_filter]

    if type_filter != "همه":
        filtered_data = filtered_data[filtered_data['type'] == type_filter]

    sort_map = {'تاریخ': 'date', 'عنوان': 'title_persian', 'منبع': 'source', 'امتیاز نهایی': 'final_score'}
    filtered_data = filtered_data.sort_values(by=sort_map[sort_by], ascending=(sort_order == "صعودی"))

    # Display filtered news articles
    for index, row in filtered_data.iterrows():
        with st.expander(f"### {row['title_persian']}" if row['title_persian'] and language == "فارسی" else f"### {row['title']}"):
            st.markdown(f"**تاریخ**: {row['date']} | **منبع**: {row['source']} | **وب‌سایت**: {row['domain']} | **بازدیدها**: {row['views']}")
            st.markdown(f"**خلاصه**: {row['summary_persian'][:200] if row['summary_persian'] and language == 'فارسی' else row['summary'][:200]}...")

            if row['matched_keywords']:
                st.markdown(f"**کلمات کلیدی مطابق**: {', '.join(row['matched_keywords'])}")

            if st.button("مشاهده جزئیات", key=f"btn_{index}"):
                st.session_state['selected_news_id'] = row['id']
                st.session_state['current_page'] = 'جزئیات خبر'
                st.experimental_rerun()




def news_details_page():
    if 'selected_news_id' not in st.session_state:
        st.warning("لطفا یک خبر را از صفحه همه اخبار انتخاب کنید.")
        return

    news_id = st.session_state['selected_news_id']
    selected_news = news_data[news_data['id'] == news_id].iloc[0]

    # Set default language
    if 'language' not in st.session_state:
        st.session_state['language'] = "فارسی"  

    language = st.session_state['language']

    # Set fields based on selected language
    title = selected_news['title_persian'] if selected_news['title_persian'] and language == "فارسی" else selected_news['title']
    summary = selected_news['summary_persian'] if selected_news['summary_persian'] and language == "فارسی" else selected_news['summary']
    content = selected_news['content'] if selected_news['content'] or language == "English" else selected_news['content_persian']
    matched_keywords = selected_news.get('matched_keywords', [])

    st.title(title)
    st.write(f"**تاریخ**: {selected_news['date']}")
    st.write(f"**منبع**: {selected_news['source']}")
    st.write(f"**وب‌سایت**: {extract_domain(selected_news['url'])}")
    st.write(f"**نویسنده**: {selected_news['author']}")
    st.write(f"**بازدیدها**: {selected_news['views']}")
    st.write(f"**امتیاز نهایی**: {selected_news['final_score']}")
    st.write(f"**نوع خبر**: {selected_news['type']}")

    # Display radio buttons for content language selection
    st.markdown("### انتخاب زبان محتوا")
    language_option = st.radio("نمایش محتوا به:", ["انگلیسی", "فارسی"])
    st.session_state['language_option'] = language_option

    # Display English content if selected
    if language_option == "انگلیسی":
        st.markdown("### محتوا (انگلیسی)")
        render_content(content, language='en') 

    # If Persian is selected, check if Persian content exists, otherwise prompt for translation
    if language_option == "فارسی":
        st.markdown("### محتوا (فارسی)")
        
        if selected_news['content_persian']:
            # Display existing Persian content
            render_content(selected_news['content_persian'])
        else:
            # Inform the user that no Persian content exists and prompt for translation
            st.write("محتوای فارسی موجود نیست. لطفا ترجمه کنید.")
            
        translation = ''
        # Step 2: Translation buttons
        if st.button("ترجمه با گوگل"):
            # Perform translation using Googletrans
            translation = googletrans_translate(content, 'en', 'fa')
            if translation:
                db_manager.insert_translation(news_id, translation)
                st.success("ترجمه با موفقیت انجام شد.")
            else:
                st.error("خطا در ترجمه جدید")

        elif st.button("ترجمه با GPT"):
            # Perform translation using GPT
            translation = gpt_translate(content, 'en', 'fa')
            if translation:
                db_manager.insert_translation(news_id, translation)
                st.success("ترجمه با موفقیت انجام شد.")
            else:
                st.error("مشکلی در ارتباط با API رخ داد.")
        
        if translation:
            st.experimental_rerun()

    
    # Display summary
    st.markdown("### خلاصه")
    if summary:
        st.write(summary)
    else:
        st.write("خلاصه ای برای این مقاله یافت نشد.")
    
    # Button for generating article from the news
    if st.button("تولید مقاله از این خبر"):
        # Call GPT to generate an article
        generated_article = gpt_generate_article(
            selected_news['title'], 
            selected_news['source'], 
            selected_news['url'], 
            selected_news['date'], 
            selected_news['content'],
            matched_keywords=matched_keywords
        )
        if generated_article != "No Article":
            st.write(generated_article)
            # db_manager.store_article(news_id, generated_article)
            st.success("مقاله با موفقیت تولید و ذخیره شد.")
        else:
            st.error("خطا در تولید مقاله")

    st.markdown("### لینک اصلی")
    st.write(selected_news['url'])

    # Section for images
    st.markdown("### تصاویر")
    images_df = db_manager.load_images(news_id)
    if not images_df.empty:
        for image_url in images_df['image_url']:
            st.image(image_url, use_column_width=True)
    else:
        st.write("عکسی برای این مقاله یافت نشد.")
    
    # Button for generating images
    if st.button("تولید تصویر"):
        # Call GPT to generate image URLs
        generated_images = gpt_generate_images(prompt=summary)
        if generated_images:
            db_manager.insert_images(news_id, generated_images)
            # for image_url in generated_images:
            #     st.image(image_url, use_column_width=True)
            st.success("تصاویر با موفقیت تولید و ذخیره شدند.")
            st.experimental_rerun()
        else:
            st.error("مشکلی در ارتباط با API رخ داد.")

    # Section for tags
    st.markdown("### برچسب‌ها")
    tags_df = db_manager.load_tags(news_id)
    if not tags_df.empty:
        st.write(' ,'.join(tags_df['tag']))
    else:
        st.write("برچسب‌ها در حال حاضر موجود نیستند.")
    
    if st.button("تولید تگ"):

        generated_tags = gpt_generate_tags(content, selected_news.get('tags', []))
        if generated_tags:
            db_manager.insert_content_tags(news_id, generated_tags)
            st.success("تولید تگ با موفقیت انجام شد.")
            st.experimental_rerun()
        else:
            st.error("مشکلی در ارتباط با API رخ داد.")



def statistics_page():
    st.title("آمار اخبار")

    last_week_data = news_data[news_data['date'] >= (datetime.now() - timedelta(days=7))]

    # Number of news from each source in the last week
    source_count = last_week_data['source'].value_counts().reset_index()
    source_count.columns = ['منبع', 'تعداد اخبار']
    fig1 = px.bar(source_count, x='منبع', y='تعداد اخبار', title="تعداد اخبار از هر منبع (هفته گذشته)", color='منبع', template='plotly_dark')
    st.plotly_chart(fig1, use_container_width=True)

    # Number of news per day
    daily_count = news_data['date'].dt.date.value_counts().reset_index()
    daily_count.columns = ['تاریخ', 'تعداد اخبار']
    daily_count = daily_count.sort_values(by='تاریخ')
    fig2 = px.line(daily_count, x='تاریخ', y='تعداد اخبار', title="تعداد اخبار در هر روز", markers=True, template='plotly_dark')
    st.plotly_chart(fig2, use_container_width=True)
    
    

if st.session_state['current_page'] == ("همه اخبار"):
    all_news_page()
elif st.session_state['current_page'] == ("جزئیات خبر"):
    news_details_page()
elif st.session_state['current_page'] == ("آمار"):
    statistics_page()
# Close the database connection
# db_manager.close()
