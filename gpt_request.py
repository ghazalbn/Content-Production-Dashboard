from googletrans import Translator
import logging
import requests
import json

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TagGeneration:
    
    def __init__(self, model, api_key):
        self.model = model
        self.api_key = api_key

    def ask_gpt(self, default, question):
        logging.debug("Sending request to OpenAI for tag generation")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 1000
        }
        logging.debug("Sending request to OpenAI with data: %s", data)

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            response_json = response.json()
            logging.debug("Received response from OpenAI: %s", response_json)

            if 'choices' in response_json and len(response_json['choices']) > 0:
                result = response_json['choices'][0]['message']['content'].strip()
                logging.debug("Generated response: %s", result)
                return result
            else:
                logging.error("No valid choices in the OpenAI response.")
                return default

        except requests.exceptions.RequestException as e:
            logging.error(f"RequestException: {e}")
            return default
        except KeyError as e:
            logging.error(f"KeyError: {e}")
            return default

    def generate_tags(self, content, existing_tags):
        num_existing_tags = len(existing_tags) if existing_tags else 0
        num_tags_to_generate = max(7 - num_existing_tags, 0)

        if num_tags_to_generate <= 0:
            return existing_tags 

        question = f"Generate total {num_tags_to_generate} relevant and concise tags for the following content. " \
                   f"Return the tags in a comma-separated list:\n\nContent: {content}\n\n" \
                   f"Existing tags: {', '.join(existing_tags)}"

        generated_tags_response = self.ask_gpt(default="", question=question)

        generated_tags = [tag.strip() for tag in generated_tags_response.split(',') if tag.strip()]

        return existing_tags + generated_tags[:num_tags_to_generate]

    def process_item(self, content, existing_tags):
        if content:
            if not existing_tags or len(existing_tags) < 7:
                tags = self.generate_tags(content, existing_tags)
        return tags


class Translation:
    
    def __init__(self, model, api_key):
        self.model = model
        self.api_key = api_key

    @staticmethod
    def googletrans_translate(content, src_lang, dest_lang):
        translator = Translator()
        return translator.translate(content, src=src_lang, dest=dest_lang).text

    def gpt_translate(self, content, src_lang, dest_lang):
        logging.debug(f"Translating text from {src_lang} to {dest_lang}")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        prompt = f"Translate this news from {src_lang} to {dest_lang}, and return only the translated content. Keep the html structure: {content}"

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            response_json = response.json()

            if 'choices' in response_json and len(response_json['choices']) > 0:
                translation = response_json['choices'][0]['message']['content'].strip()
                logging.debug(f"Translation generated: {translation}")
                return translation
            else:
                logging.error("No valid choices in the OpenAI response.")
                return ""

        except requests.exceptions.RequestException as e:
            logging.error(f"RequestException during translation: {e}")
            return ""
        except KeyError as e:
            logging.error(f"KeyError during translation processing: {e}")
            return ""


class ArticleGeneration:
    
    def __init__(self, model, api_key):
        self.model = model
        self.api_key = api_key

    def gpt_generate_article(self, title, source, url, date, news_content, matched_keywords=None):
        keywords_str = ', '.join(matched_keywords) if matched_keywords else ""

        question = f"""
        Write an analytical article in Persian for Tokeniko.com based on the following news content. 
        Provide insights from an economist's perspective and include the following keywords: {keywords_str} (if applicable). 
        The article should be at least 1300 words. Generate an attractive and concise title for it. It can contain images and tables if needed.

        - **Title**: {title}
        - **Source**: {source}
        - **URL**: {url}
        - **Date**: {date}

        **News Content**:
        {news_content}

        Ensure the article is informative and engaging. Avoid unnecessary jargon, and keep it clear for a general audience.
        """

        logging.debug("Sending request to OpenAI for article generation")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 3000
        }
        logging.debug("Sending request to OpenAI with data: %s", data)

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            response_json = response.json()
            logging.debug("Received response from OpenAI: %s", response_json)

            if 'choices' in response_json and len(response_json['choices']) > 0:
                return response_json['choices'][0]['message']['content'].strip()
            else:
                logging.error("No valid choices in the OpenAI response.")
                return "No Article"

        except requests.exceptions.RequestException as e:
            logging.error(f"RequestException: {e}")
            return self.api_key
        except KeyError as e:
            logging.error(f"KeyError: {e}")
            return f"KeyError: {e}"


class ImageGeneration:
    
    def __init__(self, api_key, model="dall-e-3"):
        self.model = model
        self.api_key = api_key

    def gpt_generate_images(self, prompt, num_images=1):
        logging.debug("Sending request to OpenAI for image generation")

        url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        if not prompt or not isinstance(prompt, str):
            logging.error("Invalid prompt provided for image generation.")
            return []

        image_urls = []
        for _ in range(num_images):
            image_prompt = f"generate a natural image related to this content news for a gold production website. content summary:{prompt}. \
            Please ensure that no text is included in the image. The theme of the photo should be yellow and purple and its quality should be 1%."

            data = {
                "model": self.model,
                "prompt": image_prompt,
                "size": "1024x1024"
            }
            logging.debug("Sending image generation request with data: %s", json.dumps(data, indent=2))

            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                response_json = response.json()
                logging.debug("Received response from OpenAI: %s", json.dumps(response_json, indent=2))

                if 'data' in response_json and len(response_json['data']) > 0:
                    image_url = response_json['data'][0].get('url')
                    if image_url:
                        image_urls.append(image_url)
                else:
                    logging.error("No images generated or missing data in the OpenAI response.")

            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTPError during image generation: {e}")
                if e.response.status_code == 400:
                    logging.error(f"Bad Request: {e.response.json()}")
            except requests.exceptions.RequestException as e:
                logging.error(f"RequestException during image generation: {e}")
            except KeyError as e:
                logging.error(f"KeyError during image processing: {e}")

        logging.debug("Images generated: %s", image_urls)
        return image_urls










# from googletrans import Translator
# import logging
# from dotenv import load_dotenv
# import os
# import requests
# import json

# load_dotenv()
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# API_KEY = os.getenv("OPENAI_API_KEY")
# MODEL = os.getenv("OPENAI_MODEL")


# class TagGeneration:

#     def ask_gpt(self, default, question, model=MODEL):
#         logging.debug("Sending request to OpenAI for tag generation")

#         url = "https://api.openai.com/v1/chat/completions"
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {API_KEY}"
#         }
#         data = {
#             "model": model,
#             "messages": [{"role": "user", "content": question}],
#             "max_tokens": 1000
#         }
#         logging.debug("Sending request to OpenAI with data: %s", data)

#         try:
#             response = requests.post(url, headers=headers, data=json.dumps(data))
#             response.raise_for_status()
#             response_json = response.json()
#             logging.debug("Received response from OpenAI: %s", response_json)

#             if 'choices' in response_json and len(response_json['choices']) > 0:
#                 result = response_json['choices'][0]['message']['content'].strip()
#                 logging.debug("Generated response: %s", result)
#                 return result
#             else:
#                 logging.error("No valid choices in the OpenAI response.")
#                 return default

#         except requests.exceptions.RequestException as e:
#             logging.error(f"RequestException: {e}")
#             return default
#         except KeyError as e:
#             logging.error(f"KeyError: {e}")
#             return default

#     def generate_tags(self, content, existing_tags):
#         """Generate new tags for content using the OpenAI API."""
#         num_existing_tags = len(existing_tags) if existing_tags else 0
#         num_tags_to_generate = max(7 - num_existing_tags, 0)

#         if num_tags_to_generate <= 0:
#             return existing_tags 

#         question = f"Generate total {num_tags_to_generate} relevant and concise tags for the following content. " \
#                    f"Return the tags in a comma-separated list:\n\nContent: {content}\n\n" \
#                    f"Existing tags: {', '.join(existing_tags)}"

#         # Call ask_gpt to generate tags
#         generated_tags_response = self.ask_gpt(default="", question=question, model=MODEL)

#         # Split the generated response into individual tags
#         generated_tags = [tag.strip() for tag in generated_tags_response.split(',') if tag.strip()]

#         # Return combined existing and generated tags
#         return existing_tags + generated_tags[:num_tags_to_generate]

#     def process_item(self, content, existing_tags):

#         if content:
#             if not existing_tags or len(existing_tags) < 7:
#                 tags = self.generate_tags(content, existing_tags)

#         return tags

# def googletrans_translate(content, src_lang, dest_lang):   
#     translator = Translator()
#     return translator.translate(content, src=src_lang, dest=dest_lang).text


# def gpt_translate(content, src_lang, dest_lang):
#     logging.debug(f"Translating text from {src_lang} to {dest_lang}")

#     url = "https://api.openai.com/v1/chat/completions"
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {API_KEY}"
#     }
#     prompt = f"Translate this news from {src_lang} to {dest_lang}, and return only the translated content. Keep the html structure: {content}"

#     data = {
#         "model": MODEL,
#         "messages": [{"role": "user", "content": prompt}],
#         "max_tokens": 4000,
#     }

#     try:
#         response = requests.post(url, headers=headers, json=data)
#         response.raise_for_status()
#         response_json = response.json()

#         if 'choices' in response_json and len(response_json['choices']) > 0:
#             translation = response_json['choices'][0]['message']['content'].strip()
#             logging.debug(f"Translation generated: {translation}")
#             return translation
#         else:
#             logging.error("No valid choices in the OpenAI response.")
#             return ""

#     except requests.exceptions.RequestException as e:
#         logging.error(f"RequestException during translation: {e}")
#         return ""
#     except KeyError as e:
#         logging.error(f"KeyError during translation processing: {e}")
#         return ""

# def gpt_generate_tags(content, existing_tags):
#     tag_generation_pipeline = TagGeneration()
#     return tag_generation_pipeline.process_item(content, existing_tags)


# def gpt_generate_article(title, source, url, date, news_content, matched_keywords=None):
#     # Prepare the keywords string for the prompt
#     keywords_str = ', '.join(matched_keywords) if matched_keywords else ""

#     question = f"""
#     Write an analytical article in Persian for Tokeniko.com based on the following news content. 
#     Provide insights from an economist's perspective and include the following keywords: {keywords_str} (if applicable). 
#     The article should be at least 1300 words. It can contains images and tables if needed.

#     - **Title**: {title}
#     - **Source**: {source}
#     - **URL**: {url}
#     - **Date**: {date}

#     **News Content**:
#     {news_content}

#     Ensure the article is informative and engaging. Avoid unnecessary jargon, and keep it clear for a general audience.
#     """
    
#     # Focus on explaining the economic implications, and 

#     logging.debug("Sending request to OpenAI for article generation")

#     url = "https://api.openai.com/v1/chat/completions"
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {API_KEY}"
#     }
#     data = {
#         "model": MODEL,
#         "messages": [{"role": "user", "content": question}],
#         "max_tokens": 3000  # Adjust max_tokens based on word count target (~1300 words)
#     }
#     logging.debug("Sending request to OpenAI with data: %s", data)

#     try:
#         response = requests.post(url, headers=headers, json=data)
#         return response.text
#         response.raise_for_status()
#         response_json = response.json()
#         logging.debug("Received response from OpenAI: %s", response_json)

#         if 'choices' in response_json and len(response_json['choices']) > 0:
#             return response_json['choices'][0]['message']['content'].strip()
#         else:
#             logging.error("No valid choices in the OpenAI response.")
#             return "No Article"
    
#     except requests.exceptions.RequestException as e:
#         logging.error(f"RequestException: {e}")
#         # return "No Article"
#         return f"RequestException: {e}"
#     except KeyError as e:
#         logging.error(f"KeyError: {e}")
#         # return "No Article"
#         return f"KeyError: {e}"




# def gpt_generate_images(prompt, model="dall-e-3", num_images=1):
#     logging.debug("Sending request to OpenAI for image generation")

#     url = "https://api.openai.com/v1/images/generations"
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {API_KEY}"
#     }

#     # Ensure the prompt is valid
#     if not prompt or not isinstance(prompt, str):
#         logging.error("Invalid prompt provided for image generation.")
#         return []

#     image_urls = []
#     for _ in range(num_images):
#         # Update prompt to instruct the model not to include text in the images
#         image_prompt = f"generate an image related to this content news for a gold production website. content summary:{prompt}. \
#         Please ensure that no text is included in the image."

#         data = {
#             "model": model,
#             "prompt": image_prompt,
#             "size": "1024x1024"
#         }
#         logging.debug("Sending image generation request with data: %s", json.dumps(data, indent=2))

#         try:
#             response = requests.post(url, headers=headers, json=data)
#             response.raise_for_status()
#             response_json = response.json()
#             logging.debug("Received response from OpenAI: %s", json.dumps(response_json, indent=2))

#             # Validate the structure of the response
#             if 'data' in response_json and len(response_json['data']) > 0:
#                 image_url = response_json['data'][0].get('url')
#                 if image_url:
#                     image_urls.append(image_url)
#             else:
#                 logging.error("No images generated or missing data in the OpenAI response.")

#         except requests.exceptions.HTTPError as e:
#             logging.error(f"HTTPError during image generation: {e}")
#             if e.response.status_code == 400:
#                 logging.error(f"Bad Request: {e.response.json()}")
#         except requests.exceptions.RequestException as e:
#             logging.error(f"RequestException during image generation: {e}")
#         except KeyError as e:
#             logging.error(f"KeyError during image processing: {e}")

#     logging.debug("Images generated: %s", image_urls)
#     return image_urls

