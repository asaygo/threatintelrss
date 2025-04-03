# threatintelrss
An automated tool that collects, summarizes, and delivers the latest cybersecurity news directly to your inbox.

## Overview
The tool monitors a customizable list of RSS feeds from security blogs and websites. It parses new articles, uses the Google Gemini AI to generate concise summaries, and delivers them in a clean, formatted HTML email.


## Features
Monitors multiple RSS feeds for new content
Uses Google Gemini AI to summarize articles
Filters out promotional content and non-technical posts
Delivers formatted HTML emails with article summaries and links
Configurable time-based filtering (recent articles only)
Debug mode for local testing

### Requirements

Python 3.x
Internet connection
Google Gemini API key
SMTP email account for sending updates

### Installation

Clone the repository

Install required dependencies: `pip3 install -r requirements.txt`

Create a .env file with the following variables:
```
EXPL_SMTPserver=your_smtp_server
EXPL_SMTPPort=your_smtp_port
EXPL_USERNAME=your_email@example.com
EXPL_PASSWORD=your_email_password
EXPL_DESTINATION=recipient@example.com
GEMINI_API_KEY=your_gemini_api_key
```

## Usage
Run the script with the path to your RSS feed list file:

`python3 threatintelrss.py path/to/feeds.txt`

The feeds.txt file should contain one RSS feed URL per line. Lines starting with '#' will be ignored.


## Configuration Options
You can customize the script behavior by modifying these variables:

```
DEBUG: Set to 1 to save a local copy of the email content
MIN_CHARS: Minimum character count for valid content
IGNORE_TITLE: List of title prefixes to ignore
SUBJECT: Email subject line prefix
```

## How It Works

- Loads environment variables for SMTP and API credentials
- Reads the list of RSS feeds from the input file
- Parses each feed for recent articles (within the last 3 days)
- Filters out promotional or irrelevant content
- Fetches the full article content from each URL
- Uses Gemini AI to generate a summary of each article
- Formats the summaries into an HTML email
- Sends the email to the configured recipient

## License
This project is available under the MIT License.
