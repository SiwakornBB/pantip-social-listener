# Pantip Social Listener 👂

🚀 [Open the App](https://pantipsociallistener.streamlit.app/)

A Streamlit-based social listening application that scrapes and analyzes Pantip forum discussions using Google's Gemini AI for sentiment analysis and aspect-based summarization.

## Features

- 🔍 **Smart Search**: Search Pantip threads by keywords with customizable sorting
- 📊 **AI Summarization**: Generate aspect-based summaries using Google Gemini models
- 📈 **Sentiment Analysis**: Analyze comments for positive, negative, and neutral sentiments
- 🎯 **Thread Selection**: Choose specific threads for focused analysis
- 📋 **Interactive Dashboard**: Visualize sentiment distribution with charts and graphs
- 📅 **Date Filtering**: Filter threads by publication date
- 💾 **Export Data**: Download analysis results as CSV files

## Project Structure

```
mrta_social_listener/
├── MAIN.py                 # Main application (home page)
├── pages/
│   └── DASHBOARD.py        # Dashboard with visualizations
├── requirements.txt        # Python dependencies
├── LICENSE                 # MIT License
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mrta_social_listener
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Chrome WebDriver**
   - Download ChromeDriver from [official site](https://chromedriver.chromium.org/)
   - Place `chromedriver.exe` in the project root directory
   - Or ensure ChromeDriver is in your system PATH

## Setup

### 1. Get Google Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the API key for use in the application

### 2. Run the Application

```bash
streamlit run MAIN.py
```

The application will open in your default web browser at `http://localhost:8501`

## Usage

### Main Page (MAIN.py)

1. **Configuration**
   - Enter your Google Gemini API Key in the sidebar
   - Select your preferred AI model (gemini-2.5-flash recommended for balance)
   - Enable/disable sentiment analysis toggle

2. **Search Parameters**
   - Enter keywords to search for
   - Choose sorting method (relevance or newest first)
   - Set maximum number of threads to analyze (1-30)
   - Optional: Set date filter for recent threads only

3. **Analysis**
   - Click "สรุปกระทู้ Pantip" to start scraping and analysis
   - View AI-generated summary with aspects and sentiments
   - Select specific threads for re-analysis if needed

### Dashboard Page

1. **Thread Overview**
   - View summary statistics of scraped threads
   - See comment counts per thread in table and chart format

2. **Aspect & Sentiment Analysis**
   - Click "INITIALIZE" to perform detailed comment-level analysis
   - View pie charts showing sentiment distribution for each aspect
   - Examine stacked bar charts and overall sentiment trends
   - Browse comments by aspect with sorting options

3. **Data Export**
   - Download analysis results as CSV files
   - View detailed comment-level data in tables

## Supported AI Models

| Model | Description | Use Case |
|-------|-------------|----------|
| `gemini-2.5-pro` | 🎯 High accuracy, deep analysis | Complex analysis tasks |
| `gemini-2.5-flash` | ⚡ Fast and token-efficient (default) | Balanced performance |
| `gemini-2.5-flash-lite-preview` | 🧪 Experimental, very token-efficient | Cost optimization |
| `gemini-2.0-flash` | ⚡ Fast and token-efficient | General usage |
| `gemini-2.0-flash-lite` | 🧪 Experimental, very token-efficient | Cost optimization |

## Dependencies

- **streamlit** (>=1.28.0) - Web application framework
- **selenium** (>=4.15.0) - Web scraping automation
- **beautifulsoup4** (>=4.12.0) - HTML parsing
- **pandas** (>=2.0.0) - Data manipulation
- **plotly** (>=5.15.0) - Interactive visualizations
- **google-generativeai** (>=0.3.0) - Google Gemini AI integration
- **urllib3** (>=2.0.0) - HTTP client
- **lxml** (>=4.9.0) - XML/HTML processing

## Configuration Options

### Chrome WebDriver Options
The application runs Chrome in headless mode with optimized settings:
- Headless operation (no GUI)
- Disabled images and plugins for faster loading
- Optimized memory usage
- Background processing disabled

### Session State Management
The application maintains state across pages:
- API keys and model selection
- Scraped thread data
- Analysis results
- User preferences

## Limitations

- Requires stable internet connection for scraping
- Google Gemini API has usage quotas and rate limits
- Chrome WebDriver must be compatible with installed Chrome version

## Troubleshooting

### Common Issues

1. **ChromeDriver not found**
   - Ensure ChromeDriver is in project directory or system PATH
   - Verify ChromeDriver version matches your Chrome browser

2. **API Key errors**
   - Verify API key is correct and active
   - Check quota usage at [Google AI Studio](https://makersuite.google.com/app/apikey)

3. **Scraping failures**
   - Check internet connection
   - Pantip may be blocking requests (try again later)
   - Verify search keywords return results on Pantip website
   - Selenium may fail due to browser or driver incompatibility, missing dependencies, or unexpected website changes (try again later)

4. **Memory issues**
   - Reduce number of threads to analyze
   - Clear session state by refreshing the page

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Copyright (c) 2025 Siwakorn Bubphasawan

## Disclaimer

This tool is for educational and research purposes only. Please respect Pantip's terms of service and robots.txt when using this application. The authors are not responsible for misuse of this tool.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Verify your setup matches the requirements
3. Create an issue with detailed error messages and system information