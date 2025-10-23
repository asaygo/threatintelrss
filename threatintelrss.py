#! python
from dotenv import load_dotenv
import feedparser
from datetime import datetime
import re
import requests
import smtplib, ssl
from email.mime.text import MIMEText
import os
import requests
import time
import sys
import json
from bs4 import BeautifulSoup

# set it to 1 if you want to save a local copy of the news
DEBUG = 1

# min chars to be considered valid content
MIN_CHARS = 50

# define blog titles to ignore
IGNORE_TITLE = ["[dos]", "Threat Intelligence Bulletin", "Cyber Security Webinar",  "Cybersecurity",
                "Security Update Review", "cyberinsurance", "A week in security", "Survey:", "Education", "Academy", 
		"Ransomware", "Best Practice", "Top Cyber", "AI SOC", "patch update", "availability", "pwn2own", " scam",
                "telemetry", "scam text", "security gap", "cloud security", "market report", "phishing"]

# list of RSS feeds to check
url_feeds = []

# list of blog titles
titles = []

# these will be retrieved from env
GEMINI_API_KEY = ""
WEBHOOK_URL = ""

CONTENT_FILE = "content.dat"

def send_discord_message(webhook_url, message_content):
    """
    Posts a simple text message to a Discord webhook.

    Args:
        webhook_url (str): The full URL of your Discord webhook.
        message_content (str): The text message you want to send.
    """
    if len(message_content) > 1990:
        message_content = message_content[:1990]

    # Discord requires the message to be sent as a JSON payload
    payload = {
        'content': message_content
    }

    # Send the POST request to the webhook URL
    try:
        response = requests.post(
            webhook_url, 
            data=json.dumps(payload), 
            headers={'Content-Type': 'application/json'}
        )
        
        # Check the response status code
        if response.status_code == 204:
            print("Successfully sent message to Discord.")
        else:
            print(f"Failed to send message. Status Code: {response.status_code}")
            print(f"Response Text: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    return

# set up the environment variables
def setup_env():
    global GEMINI_API_KEY
    global WEBHOOK_URL

    # Remove specific environment variables before loading .env
    variables_to_remove = ["GEMINI_API_KEY", "WEBHOOK_URL"]

    try:
        for var in variables_to_remove:
            os.environ.pop(var, None)

        # Load the .env file
        load_dotenv()

        # Retrieve Discord webhook
        WEBHOOK_URL = os.getenv("WEBHOOK_URL")

        # Retrieve Gemini API key
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    except:
        return 0

    return 1

# query the AI model and return the result
def query_gemini(query):
    global GEMINI_API_KEY

    print("[*] Query Gemini")
    text_value = ""

    # Replace GEMINI_API_KEY with your actual API key
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Summarize the following content and ignore the html tags. If it sounds like a sales pitch and is not about an exploit, a vulnerability, a malware, firmware, or about reverse engineering, just return 'N/A'.\n" + query + ""}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=35)

        # Check if the request was successful
        if response.status_code == 200:
            response_data = response.json()
            text_value = response_data['candidates'][0]['content']['parts'][0]['text']
        else:
            print("[-] Error:", response.status_code, response.text)

    except Exception as e:
        return f"An error occurred: {e}"

    return text_value

# returns the content of the web page
def get_web_content(url):
    text_value = ""
    try:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
        headers = {
            "User-Agent": user_agent
        }
        # Send an HTTP GET request to the URL
        response = requests.get(url, headers=headers, timeout=5)
        
        # Check if the request was successful
        if response.status_code == 200:
             # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'aside', 'footer', 'header', 'noscript']):
                tag.decompose()

            # Extract all text
            text_value = soup.body.get_text(separator='\n', strip=True)

            # Try to find the main article content
            article = soup.find('article')
            if article:
                text_value = article.get_text(separator='\n', strip=True)
            else:
                # Fallback: try common content containers
                main = soup.find('main') or soup.find('div', class_='content') or soup.find('div', id='content')
                text_value = main.get_text(separator='\n', strip=True) if main else soup.body.get_text(separator='\n', strip=True)

        else:
            print(f"[-] Failed to retrieve the webpage. Status code: {response.status_code}")
    except Exception as e:
        print(f"[-] get_web_content(): An error occurred: {e}")
    return text_value


# load the feed list
# return the number of loaded RSS feeds
def load_feed_list(fname):
    global url_feeds

    counter = 0
    print("[*] Load feeds")

    if not os.path.exists(fname):
        print("Error: The file " + fname + " does not exist.")
        return counter
    
    if not os.path.isfile(fname):
        print("Error: " + fname + " is not a file.")
        return counter

    with open(fname, 'r') as f:
        for line in f:
            line = line.replace('\n', '')
            line = line.replace('\r', '')
            if "#" not in line and len(line) > 10:
                url_feeds.append(line)
                counter = counter+1

    print("[+] Loaded " + str(counter) + " feeds")

    return counter

def send_news(data, c_time):
    global MIN_CHARS
    global WEBHOOK_URL

    # check if we have data to send
    if len(data) >= MIN_CHARS:
        #send_email(data, c_time)
        send_discord_message(WEBHOOK_URL, data)

    return


def save_content(text):
    global CONTENT_FILE
    with open(CONTENT_FILE, "a") as f:
        f.write(text + "\n\n")
        f.close()
    return

# parse the XML message
def extract_feed_info(url, c_time):
    global IGNORE_TITLE
    global MIN_CHARS
    global titles

    content_data = ''

    # check if we have a valid url and creation time
    if len(url) > 6 and len(c_time) > 7:

        # parse the blog's creation time
        m = re.match(r'(\d{4})\-(\d+)\-(\d+)', c_time)
        if m:
            year = int(m.group(1))
            month = int(m.group(2))
            day = int(m.group(3))
        else:
            return ""

        print("[*] Get feed " + url)
        try:
    	    d = feedparser.parse(url)
        except:
            return ""
        
        # go through all the blogs listed in the XML file
        for i in range(len(d['entries'])):
            e_year = 0
            e_month = 0
            e_day = 0
            try:
                e_year = int(d.entries[i].published_parsed.tm_year)
                e_month = int(d.entries[i].published_parsed.tm_mon)
                e_day = int(d.entries[i].published_parsed.tm_mday)
            except:
                pass

            if  e_year == year and (e_month == month and e_day >= day-3): #or (e_month == month-1 and e_day >= 27)):
                title = d.entries[i].title.replace('\n', '').replace('\r', '').replace('|', '')

                # check if we can ignore the article (example: sales-pitch)
                can_ignore = 0
                for word in IGNORE_TITLE:
                    if word.lower() in title.lower():
                        can_ignore = 1

                if title in titles:
                    can_ignore = 1

                if can_ignore == 0:
                    titles.append(title)
                    link = d.entries[i].link.replace('\n', '').replace('\r', '').replace('|', '')

                    # fix the link for rapid7 articles
                    if link.find('/community/') == 0:
                        link = 'https://community.rapid7.com' + link


                    # extract blog article data
                    summary = d.entries[i].summary.replace('\n', '').replace('\r', '').replace('|', '')
                    published = d.entries[i].published.replace('\n', '').replace('\r', '').replace('|', '')
                    summary = re.sub(r'<[^<]+?>', '', summary)
                    summary = re.sub(r'\s{2,}', ' ', summary)

                    # if the content is too long
                    # truncate the blog content to MIN_CHARS
                    #if len(summary) >= MIN_CHARS:
                    #    summary = summary[:MIN_CHARS] + "..."

                    # summarize the article using Gemini AI
                    #web_content = get_web_content(link)
                    #if len(web_content) >= MIN_CHARS:
                    #    save_content(web_content)
                        #output = query_gemini(str(web_content))
                        #summary = output
                        # if Gemini couln't summarize the article
                        # use the data extracted from the RSS feed
                        #if len(output) > len(summary):
                        #    print("[*] Use Gemini summary")
                        #    summary = output
                        #    print(summary)
                    #else:
                    #    break

                    if len(summary) >= MIN_CHARS:
                        # add the article to the html content
                        content_data = link + " - " + title + "\n"
                    else:
                        print("Sales pitch: " + link + " - " + title)

    return content_data

# go through the RSS urls, extract the information
# and send it over email
def parse_feeds(c_time):
    global DEBUG
    global MIN_CHARS

    counter = 0
    feed_data  = ''
    content_data = ""

    for url in url_feeds:
        try:
          feed_data = extract_feed_info(url, c_time)
        except:
          # if there is an error, go to the next url/feed
          continue
          
        # add each entry to a table
        if len(feed_data) >= MIN_CHARS:
            content_data += feed_data
            counter += 1
        else:
            continue

        # sleep for 2 seconds until checking next feed
        time.sleep(2)

    if len(content_data) > MIN_CHARS:
        if DEBUG == 1:
            # save to file
            save_data_to_file("news.txt", content_data)

        # send the news
        send_news(content_data, c_time)

    return counter

def save_data_to_file(fname, data):
    try:
        with open(fname, "w") as f:
            f.write(data)
            f.close()

    except Exception as e:
        print(f"[-] save_data_to_file(): An error occurred: {e}")

    return

if __name__ == "__main__":
    c_time = datetime.now().strftime('%Y-%m-%d')

    if len(sys.argv) != 2:
        print("Usage: python script.py <path/to/rss/feeds>")
        exit(0)

    if setup_env() == 0:
        print("[-] Error retrieving environment data")
        exit(0)

    if len(WEBHOOK_URL) < 10:
        print("[-] Invalid Discord webhook")
        exit(0)

    if len(GEMINI_API_KEY) < 10:
        print("[-] Invalid Gemini API key")
        exit(0)

    # parse the feed list and send the news
    if load_feed_list(sys.argv[1]) > 0:
        parse_feeds(c_time)

    print("[+] Done")
