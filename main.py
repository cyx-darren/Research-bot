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

    def get_api_key(self):
        """Get API key from environment, allowing for runtime updates"""
        if not self.api_key:
            self.api_key = os.environ.get('SERPAPI_KEY')
        return self.api_key

    def search(self, query: str, num_results: int = 5):
        """Perform a Google search and return results"""
        self.api_key = self.get_api_key()
        if not self.api_key:
            log_debug("Warning: SERPAPI_KEY not available")
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

        market_size = self.search_client.search(f"{business_idea} market size Singapore statistics")
        competitors = self.search_client.search(f"{business_idea} top competitors Singapore")
        trends = self.search_client.search(f"{business_idea} industry trends Singapore 2024")

        return {
            "market_analysis": {
                "target_market": self._extract_text(market_size),
                "competitors": self._extract_titles(competitors),
                "market_trends": self._extract_text(trends),
                "opportunities": self._extract_text(trends),
                "risks": self._extract_risks(market_size + competitors)
            }
        }

    def handle_recipe_research(self, query):
        """Handle recipe research queries"""
        recipe = query.get('recipe_request', '')

        instructions = self.search_client.search(f"{recipe} recipe how to make step by step")
        ingredients = self.search_client.search(f"{recipe} recipe ingredients list")
        nutrition = self.search_client.search(f"{recipe} nutrition facts calories")

        return {
            "recipe_info": {
                "name": recipe,
                "ingredients": self._extract_text(ingredients),
                "instructions": self._extract_text(instructions),
                "nutrition": self._extract_text(nutrition),
                "cooking_time": "30-45 minutes",  # Default value
                "difficulty": "Medium"  # Default value
            }
        }

    def handle_holiday_itinerary(self, query):
        """Handle holiday itinerary queries"""
        destination = query.get('destination', '')

        attractions = self.search_client.search(f"{destination} top tourist attractions must visit")
        hotels = self.search_client.search(f"{destination} best hotels where to stay")
        travel_tips = self.search_client.search(f"{destination} travel guide tips local customs")
        food = self.search_client.search(f"{destination} best restaurants local food must try")

        return {
            "travel_guide": {
                "attractions": self._extract_titles(attractions),
                "accommodations": self._extract_titles(hotels),
                "dining": self._extract_titles(food),
                "travel_tips": self._extract_text(travel_tips),
                "local_info": self._extract_text(travel_tips[:2])
            }
        }

    def handle_restaurant_research(self, query):
        """Handle restaurant research queries"""
        occasion = query.get('occasion', '')
        location = "Singapore"  # Default to Singapore

        restaurants = self.search_client.search(f"best restaurants {location} {occasion}")
        cuisine = self.search_client.search(f"recommended restaurants {location} {occasion} cuisine")
        reviews = self.search_client.search(f"top rated restaurants {location} {occasion} reviews")

        return {
            "dining_suggestions": {
                "recommendations": self._extract_titles(restaurants),
                "cuisines": self._extract_titles(cuisine),
                "reviews": self._extract_text(reviews),
                "price_range": "$$ - $$$",  # Default value
                "ambiance": self._extract_text(reviews[:1])
            }
        }

    def _extract_text(self, results):
        """Extract and combine text from search results"""
        texts = []
        for result in results[:3]:
            if "snippet" in result:
                texts.append(result["snippet"])
        return "\n".join(texts) if texts else "Information not available"

    def _extract_titles(self, results):
        """Extract titles from search results"""
        titles = []
        for result in results[:5]:
            if "title" in result:
                titles.append(result["title"])
        return titles if titles else ["No information available"]

    def _extract_risks(self, results):
        """Extract risk-related information"""
        risks = []
        risk_keywords = ["challenge", "risk", "problem", "difficult", "competition"]
        for result in results[:5]:
            if "snippet" in result:
                text = result["snippet"].lower()
                if any(keyword in text for keyword in risk_keywords):
                    risks.append(result["snippet"])
        return "\n".join(risks) if risks else "No specific risks identified"

@app.route('/')
def home():
    """Home page route"""
    try:
        api_key = os.environ.get('SERPAPI_KEY')
        api_status = "🟢 Ready" if api_key else "🔸 Waiting for API key"
        response = {
            "status": "running",
            "message": "Research Bot is operational",
            "api_status": api_status,
            "endpoints": {
                "root": "GET /",
                "test": "GET /test",
                "webhook": "POST /webhook"
            }
        }
        return jsonify(response)
    except Exception as e:
        log_debug(f"Error in home route: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/test')
def test():
    """Test endpoint"""
    try:
        api_key = os.environ.get('SERPAPI_KEY')
        return jsonify({
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "api_configured": bool(api_key),
            "message": "Test endpoint is working!"
        })
    except Exception as e:
        log_debug(f"Error in test route: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

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

        handlers = {
            'market_research': handler.handle_market_research,
            'recipe_research': handler.handle_recipe_research,
            'holiday_itinerary': handler.handle_holiday_itinerary,
            'restaurant_research': handler.handle_restaurant_research
        }

        if research_type not in handlers:
            return jsonify({'status': 'error', 'message': f'Invalid research type: {research_type}'}), 400

        result = handlers[research_type](query)
        return jsonify({
            'status': 'success',
            'result': result,
            'research_type': research_type
        })

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 80))
    log_debug(f"Starting Research Bot on port {port}...")
    # Log initial API key status
    api_key = os.environ.get('SERPAPI_KEY')
    log_debug(f"API Key Status: {'Configured' if api_key else 'Not configured'}")
    app.run(host='0.0.0.0', port=port)