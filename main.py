from flask import Flask, request, jsonify
import json
import sys
import os
from datetime import datetime
from serpapi import GoogleSearch
import logging

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def log_debug(message):
    """Helper function to ensure debug messages are logged"""
    logger.debug(message)
    print(message, file=sys.stderr, flush=True)

class GoogleSearchClient:
    def __init__(self):
        self.api_key = None

    def initialize(self):
        """Initialize the API key"""
        self.api_key = os.getenv('SERPAPI_KEY')
        if not self.api_key:
            log_debug("Error: SERPAPI_KEY not found in environment variables")
            raise EnvironmentError('SERPAPI_KEY environment variable is required. Please set it in the Secrets tab.')
        return True

    def search(self, query: str, num_results: int = 5):
        """Perform a Google search and return results"""
        if not self.api_key:
            if not self.initialize():
                return []

        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": num_results,
                "gl": "sg"  # Set to Singapore results
            }
            search = GoogleSearch(params)
            results = search.get_dict()

            # Extract organic results
            if "organic_results" in results:
                return results["organic_results"]
            return []

        except Exception as e:
            logger.error(f"Error performing Google search: {str(e)}")
            return []

class ResearchHandler:
    def __init__(self):
        self.search_client = GoogleSearchClient()

    def handle_market_research(self, query):
        """Handle market research queries using real search results"""
        business_idea = query.get('business_idea', '')

        # Perform multiple targeted searches
        market_size = self.search_client.search(f"{business_idea} market size Singapore statistics")
        competitors = self.search_client.search(f"{business_idea} top competitors Singapore")
        trends = self.search_client.search(f"{business_idea} industry trends Singapore 2024")

        return {
            "market_analysis": {
                "target_market": self._extract_market_info(market_size),
                "competitors": self._extract_competitor_info(competitors),
                "market_trends": self._extract_trend_info(trends),
                "opportunities": self._analyze_opportunities(trends),
                "risks": self._analyze_risks(competitors + market_size)
            }
        }

    def _extract_market_info(self, results):
        """Extract and format market information from search results"""
        info = []
        for result in results[:3]:
            if "snippet" in result:
                info.append(result["snippet"])
        return "\n".join(info) if info else "Information not available"

    def _extract_competitor_info(self, results):
        """Extract and format competitor information"""
        competitors = []
        for result in results[:5]:
            if "title" in result:
                competitors.append(result["title"].split('-')[0].strip())
        return "\n".join(f"{i+1}. {comp}" for i, comp in enumerate(competitors))

    def _extract_trend_info(self, results):
        """Extract and format trend information"""
        trends = []
        for result in results[:3]:
            if "snippet" in result:
                trends.append(result["snippet"])
        return "\n".join(f"- {trend}" for trend in trends)

    def _analyze_opportunities(self, results):
        """Analyze and extract business opportunities"""
        opportunities = []
        for result in results[:3]:
            if "snippet" in result:
                opportunities.append(result["snippet"])
        return "\n".join(f"- {opp}" for opp in opportunities)

    def _analyze_risks(self, results):
        """Analyze and extract potential risks"""
        risks = set()
        for result in results[:5]:
            if "snippet" in result:
                text = result["snippet"].lower()
                if any(word in text for word in ["challenge", "risk", "problem", "difficult"]):
                    risks.add(result["snippet"])
        return "\n".join(f"- {risk}" for risk in risks)

@app.route('/')
def home():
    """Home page route"""
    api_status = "🟢 Ready" if os.getenv('SERPAPI_KEY') else "🔴 API Key not configured"
    return f"""Research Bot is running!
Status: {api_status}
Endpoints:
- GET /: This page
- GET /test: Test endpoint
- POST /webhook: Research request endpoint"""

@app.route('/test')
def test():
    """Test endpoint"""
    return "Test endpoint is working!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests"""
    log_debug("\n=== Research Bot Webhook Request Received ===")

    try:
        if not request.is_json:
            return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

        data = request.get_json()
        log_debug(f"Received webhook data: {data}")

        if 'research_type' not in data:
            return jsonify({"status": "error", "message": "research_type is required"}), 400

        handler = ResearchHandler()
        research_type = data['research_type']
        query = data.get('query', {})

        if research_type == 'market_research':
            result = handler.handle_market_research(query)
            return jsonify({'status': 'success', 'result': result, 'research_type': research_type})
        else:
            return jsonify({'status': 'error', 'message': f'Invalid research type: {research_type}'}), 400

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    log_debug(f"Starting Research Bot on port 8080...")
    app.run(host='0.0.0.0', port=8080)