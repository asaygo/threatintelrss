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

# set it to 1 if you want to save a local copy of the news
DEBUG = 0

# min chars to be considered valid content
MIN_CHARS = 150

# define blog titles to ignore
IGNORE_TITLE = ["[dos]", "Threat Intelligence Bulletin", "Cyber Security Webinar", 
                "Security Update Review", "cyberinsurance", "A week in security", "Survey:"]

# define email message subject
SUBJECT = "[Exploit news]"

# list of RSS feeds to check
url_feeds = []

# these will be retrieved from env
SMTPserver = ""
SMTPPort = 465
USERNAME = ""
PASSWORD = ""
DESTINATION = ""
GEMINI_API_KEY = ""

# define the styling
css = """
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f9f9f9;
        }
        .paragraph-container {
            margin-bottom: 40px; /* Ample spacing between paragraphs */
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
        }
        .title {
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .date {
            font-size: 16px;
            color: gray;
            margin-bottom: 10px;
        }
        .text {
            position: relative;
            font-size: 16px;
            padding-bottom: 6px;
        }
        .text::after, .text::before {
            content: "";
            display: block;
            height: 3px;
            width: 100%;
            background: red;
            position: absolute;
            bottom: 0;
        }
        .text::before {
            bottom: 5px;
        }
    </style>"""

# set up the environment variables
def setup_env():
    global SMTPserver
    global SMTPPort
    global USERNAME
    global PASSWORD
    global DESTINATION
    global GEMINI_API_KEY

    # Remove specific environment variables before loading .env
    variables_to_remove = ["EXPL_SMTPserver", "EXPL_SMTPPort", "EXPL_USERNAME"
                           "EXPL_PASSWORD", "EXPL_DESTINATION", "GEMINI_API_KEY"]

    try:
        for var in variables_to_remove:
            os.environ.pop(var, None)

        # Load the .env file
        load_dotenv()

        # Retrieve the SMTP server details
        SMTPserver = os.getenv("EXPL_SMTPserver")
        SMTPPort = os.getenv("EXPL_SMTPPort")

        # Retrieve mail account details
        USERNAME = os.getenv("EXPL_USERNAME")
        PASSWORD = os.getenv("EXPL_PASSWORD")
        DESTINATION = os.getenv("EXPL_DESTINATION")

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
                    {"text": "Please summarize the following content. Ignore the html tags.\n" + query + ""}
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
            text_value = response.text  # Return the content of the webpage as text
        else:
            print(f"[-] Failed to retrieve the webpage. Status code: {response.status_code}")
    except Exception as e:
        print(f"[-] get_web_content(): An error occurred: {e}")
    return text_value

# send the email
def send_email(content, c_time):
    global SMTPserver
    global SMTPPort
    global DESTINATION
    global USERNAME
    global PASSWORD
    global SUBJECT

    c_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # set the content type
    msg = MIMEText(content, 'html')

    # set email from/subject
    msg['Subject'] = SUBJECT + ' - ' + c_time
    msg['From'] = USERNAME

    # login to the mail server
    conn = smtplib.SMTP_SSL(SMTPserver, SMTPPort)
    conn.login(USERNAME, PASSWORD)

    # try sending the email
    try:
        print("[+] Send email")
        conn.sendmail(USERNAME, DESTINATION, msg.as_string())
    finally:
        conn.quit()
    
    return

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

# send the email with the news
def send_news(data, c_time):
    global MIN_CHARS

    # check if we have data to send
    if len(data) >= MIN_CHARS:
        send_email(data, c_time)

    return

# parse the XML message
def extract_feed_info(url, c_time):
    global IGNORE_TITLE
    global MIN_CHARS

    feed_data = ''
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
                    if title.find(word) ==0:
                        can_ignore = 1

                if can_ignore == 0:
                    link = d.entries[i].link.replace('\n', '').replace('\r', '').replace('|', '')

                    # fix the link for rapid7 articles
                    if link.find('/community/') == 0:
                        link = 'https://community.rapid7.com' + link


                    # extract blog article data
                    summary = d.entries[i].summary.replace('\n', '').replace('\r', '').replace('|', '')
                    published = d.entries[i].published.replace('\n', '').replace('\r', '').replace('|', '')
                    summary = re.sub('<[^<]+?>', '', summary)
                    summary = re.sub('\s{2,}', ' ', summary)

                    # if the content is too long
                    # truncate the blog content to MIN_CHARS
                    if len(summary) >= MIN_CHARS:
                        summary = summary[:MIN_CHARS] + "..."

                    # summarize the article using Gemini AI
                    web_content = get_web_content(link)
                    if len(web_content) >= MIN_CHARS:
                        output = query_gemini(str(web_content))
                      
                        # if Gemini couln't summarize the article
                        # use the data extracted from the RSS feed
                        if len(output) > len(summary):
                            print("[*] Use Gemini summary")
                            summary = output
                            print(summary)
                    else:
                        break
                    
                    if len(summary) >= MIN_CHARS:
                        # add the article to the html content
                        feed_data = "<div class=\"paragraph-container\"><div class=\"title\"><a href=\"" + link + "\">" + title + "</a></div>"
                        feed_data += "<div class=\"date\">" + published + "</div><br>"
                        feed_data += "<div class=\"text\"><pre>" + summary + "</pre></div></div>"
                        content_data += feed_data
                    
                    content_data += feed_data

    return content_data

# go through the RSS urls, extract the information
# and send it over email
def parse_feeds(c_time):
    global DEBUG
    global css
    global MIN_CHARS

    counter = 0
    feed_data  = ''
    content_data = css

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

        # sleep for 2 seconds until checking next feed
        time.sleep(2)

    if DEBUG == 1:
        # save to file
        save_data_to_file("news.html", content_data)

    if len(content_data) > (MIN_CHARS + len(css)):
        summary = query_gemini(str(content_data))
        content_data = "<div class=\"paragraph-container\"><div class=\"title\"><h2>Summary</h2></div><div class=\"text\"><pre>" + \
                       summary + "</pre></div></div><br><br>" + content_data
        content_data = content_data.replace("**", "<br>\n**")
  
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

    if len(SMTPserver) < 3 or len(SMTPPort) < 1:
        print("[-] Invalid SMTP server details")
        exit(0)
    
    if int(SMTPPort) <= 0:
        print("[-] Invalid SMTP server port")
        exit(0)

    if len(USERNAME) < 3 or len(PASSWORD) < 3:
        print("[-] Invalid SMTP credentials")
        exit(0)

    if len(DESTINATION) < 3:
        print("[-] Invalid destination")
        exit(0)

    if len(GEMINI_API_KEY) < 3:
        print("[-] Invalid Gemini API key")
        exit(0)

    # parse the feed list and send the news
    if load_feed_list(sys.argv[1]) > 0:
        parse_feeds(c_time)

    print("[+] Done")
