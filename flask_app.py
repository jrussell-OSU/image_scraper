# AUTHOR: Jacob Russell
# DATE: 02/17/2022
# CLASS: CS361 Software Engineering I

# DESCRIPTION: A wikimedia commons image scraper microservice. Gets valid image
# URLs based on a given word. If no wikimedia category found for that word,
# this program uses thesaurus API to find synonyms and tries those.
# See: README, if the program doesn't work. config.py must be created by user.

# REFERENCES: https://www.geeksforgeeks.org/image-scraping-with-python/,
# https://stackabuse.com/deploying-a-flask-application-to-heroku/
# thesaurus API is at https://words.bighugelabs.com/site/api


import requests
from bs4 import BeautifulSoup
import random
from flask import Flask, jsonify, request
from flask_cors import cross_origin
# import config  # uncomment to run on localhost
import os  # uncomment to run on Heroku


app = Flask(__name__)


class ImageScraper:
    """Take a word and return valid image source url from wikimedia"""

    def __init__(self):
        self._word = ""
        self._raw_image_urls = []
        self._valid_image_urls = []
        self._synonyms = []
        self._html_data = ""
        self._image_exts = [".jpg", ".png"]
        self._wiki_url = "https://commons.wikimedia.org/wiki/Category:" + self._word + "/json"
        self._synonym_url = ""

    def set_word(self, word):
        """Set word to find images for"""
        self._word = word
        self.set_wiki_url()

    def set_synonym_url(self):
        """
        Uncomment first line if running on Heroku
        Uncomment second line if running on localhost
        """
        self._synonym_url = "https://words.bighugelabs.com/api/2/" + os.environ["api_key"] + self._word + "/json"
        # self._synonym_url = "https://words.bighugelabs.com/api/2/" + config.api_key + self._word + "/json"

    def set_wiki_url(self):
        """Adds word to wiki url to find images related to that word"""
        self._wiki_url = "https://commons.wikimedia.org/wiki/Category:" + self._word

    def retrieve_page_data(self):
        """takes a URL and returns the HTML data from that page"""
        self._html_data = requests.get(self._wiki_url).text

    def raw_image_urls(self):
        """Takes HTML raw data and returns list of image source urls"""
        soup = BeautifulSoup(self._html_data, 'lxml')
        for url in soup.find_all('img'):
            self._raw_image_urls.append(url['src'])

    def valid_image_urls(self):
        """
        Takes list of wikimedia commons thumbnail image urls and returns list of jpg source urls
        NOTE: only works with wikimedia commons category pages. Thumbnail url is similar to real image url
        so some string manipulation is all that is needed to produce valid urls.
        """
        for raw_url in self._raw_image_urls:  # go through and transform urls to thumb images into urls for actual jpgs
            temp = raw_url.replace("thumb/", "")
            if temp[0:4] == "http":
                for ext in self._image_exts:
                    i = temp.find(ext)
                    if -1 < i < len(temp) - 5:  # if it is an accepted image file type
                        p = temp.find("/", i)
                        fixed_url = temp[0:p]
                        self._valid_image_urls.append(fixed_url)

    def retrieve_synonyms(self):
        """
        Takes a word and uses API to get list of synonyms
        Thesaurus API: https://words.bighugelabs.com/site/api
        """
        self.set_synonym_url()
        try:
            # Use thesaurus API to get synonyms for the words
            response = requests.get(self._synonym_url).json()
            words = None
            word_types = [t for t in response]  # gets all word types for this word (e.g. noun, adjective, verb)
            for word_type in word_types:  # iterates through all words from all word types
                words = response[word_type]['syn']  # ['syn'] is where synonyms stored (vs ['ant'] for antonym)
                for word in words:
                    self._synonyms.append(word)
            if not words:
                print("No synonyms found.")
        except:
            print("Invalid JSON response from thesaurus API.")

    def get_random_valid_image(self):
        """Returns random url from a list of urls"""
        i = random.randint(0, len(self._valid_image_urls) - 1)
        return self._valid_image_urls[i]

    def try_synonyms(self):
        """
        Try to find valid image urls using synonyms of original word
        Return True if one is found, otherwise False
        """
        self.retrieve_synonyms()  # get word's synonyms from thesaurus API
        if not self._synonyms:
            print("No synonyms found.")
            return False
        count = 0
        while not self._valid_image_urls and count < len(self._synonyms):
            self._word = self._synonyms[count]
            self.image_scraper(self._word)
            print("Trying synonym: ", self._word)  # for DEBUGGING
            # self.set_wiki_url()
            # self.retrieve_page_data()
            # self.raw_image_urls()
            # self.valid_image_urls()
            count += 1
        # If we have tried every synonym but still couldn't find a valid image
        if count >= len(self._synonyms):
            return False
        return True

    def check_valid_image_urls(self):
        """Checks if we found a valid image url. Returns True if so, else False"""
        if self._valid_image_urls:
            return True
        else:
            return False

    def image_scraper(self, word):
        """
        Main image scraper function.
        """
        self.set_word(word)  # set the keyword
        self.retrieve_page_data()  # get the wikimedia page data
        self.raw_image_urls()  # get the raw image urls from the wikimedia page
        self.valid_image_urls()  # turn those raw urls into useable full-size image urls


@app.route('/')
def index():
    print("Index accessed..")
    return"<h1>Welcome to my image scraper!</h1>"


# Reference: https://stackabuse.com/deploying-a-flask-application-to-heroku/
@app.route('/get_image_url/', methods=['GET'])
@cross_origin()  # for CORS
def respond():

    # extract the word from the url
    word = request.args.get("word", None)
    print("Word received: ", word)

    # Set response as Error by default until image URL found
    response = {"IMAGE_URL": "ERROR"}

    # Verify if a word was received
    if not word:
        return jsonify(response)

    scraper = ImageScraper()
    scraper.image_scraper(word)  # Main function

    # If no valid image urls found, try synonyms
    if not scraper.check_valid_image_urls():
        if not scraper.try_synonyms():
            print("No results using synonyms")
            return jsonify(response)

    # If a valid results found, print a random one
    image_url = scraper.get_random_valid_image()
    if image_url:
        response["IMAGE_URL"] = image_url
    return jsonify(response)


if __name__ == "__main__":
    app.run()
