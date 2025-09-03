import logging
import os
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("HRAnalyzer")

# === ENVIRONMENT SETUP ===
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv not installed. Using system environment variables only.")

# === CONFIGURATION ===
GEMINI_API_KEY = "AIzaSyB0C1-3CRSG9GxAjkXSrAmCPvSGqOf5vps"
QDRANT_URL = os.getenv("QDRANT_URL", "https://d5001293-a8e5-4622-bc57-86c69005c632.us-west-2-0.aws.cloud.qdrant.io")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.fDwHFUttXub77IymhYo-B2sWMFzQRifSx56k1FlCCRM")

# MySQL settings
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "rootroot")
MYSQL_DB = os.getenv("MYSQL_DB", "fortai_employees")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))

# === OPTIONAL DEPENDENCIES ===
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("Google Gemini AI SDK not found. Install with: pip install google-generativeai")
    GEMINI_AVAILABLE = False

try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    logger.warning("Qdrant client not found. Install with: pip install qdrant-client")
    QDRANT_AVAILABLE = False


# === HR ANALYZER CLASS ===
class HRAnalyzer:
    """
    HR Sentiment Analysis with AI + Qdrant + MySQL (SQLAlchemy)
    """

    def __init__(self,
                 gemini_api_key: Optional[str] = None,
                 qdrant_url: Optional[str] = None,
                 qdrant_api_key: Optional[str] = None):

        self.api_key = gemini_api_key or GEMINI_API_KEY
        self.qdrant_url = qdrant_url or QDRANT_URL
        self.qdrant_api_key = qdrant_api_key or QDRANT_API_KEY

        self.gemini_model = None
        self.qdrant_client = None
        self.collection_name = "hr_analysis"
        self.data: List[Dict[str, Any]] = []
        self.engine: Optional[Engine] = None

        self._setup_gemini()
        self._setup_qdrant()
        self._setup_db()

    # === DATABASE ===
    def _setup_db(self):
        try:
            self.engine = create_engine(
                f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
            )
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection established via SQLAlchemy")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")

    # === GEMINI ===
    def _setup_gemini(self):
        if not GEMINI_AVAILABLE:
            logger.info("ℹ️ Gemini SDK not available.")
            return
        if not self.api_key:
            logger.error("❌ Gemini API key not provided.")
            return
        try:
            genai.configure(api_key=self.api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")  # ✅ corrected model name
            logger.info("✅ Gemini AI initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini AI: {e}")

    # === QDRANT ===
    def _setup_qdrant(self):
        if not QDRANT_AVAILABLE:
            logger.info("ℹ️ Qdrant not available. Vector search disabled.")
            return
        if not self.qdrant_url or not self.qdrant_api_key:
            logger.error("❌ Qdrant URL or API key not provided.")
            return
        try:
            self.qdrant_client = QdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key,
                prefer_grpc=False
            )
            self.qdrant_client.get_collections()
            logger.info("✅ Qdrant connected successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")

    # === LOAD DATA ===
    def load_data(self) -> bool:
        """Load HR data directly from MySQL sentiment_reports table"""
        if not self.engine:
            logger.error("❌ Database engine not initialized")
            return False

        try:
            query = "SELECT * FROM sentiment_reports"
            df = pd.read_sql(query, self.engine)

            if df.empty:
                logger.warning("⚠️ No data found in MySQL table `sentiment_reports`")
                return False

            self.data = []
            for idx, row in df.iterrows():
                score = float(row.get("positive_percentage", 50.0))
                record = {
                    "id": int(row.get("employee_id", idx)),
                    "employee_id": int(row.get("employee_id", idx)),
                    "employee_name": str(row.get("employee_name", f"Employee {idx}")),
                    "content": str(row.get("full_analysis", row.get("comment", "")) or ""),
                    "role": str(row.get("employee_role", "Unknown")),
                    "sentiment_score": score,
                    "quadrant": str(row.get("quadrant", self._classify_quadrant(score)))
                }
                self.data.append(record)

            logger.info(f"✅ Loaded {len(self.data)} employee records from MySQL")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load data from MySQL: {e}")
            return False

    def _classify_quadrant(self, sentiment_score: float) -> str:
        if sentiment_score >= 70:
            return "Champion"
        elif sentiment_score >= 50:
            return "Concerned but active"
        elif sentiment_score >= 30:
            return "Potentially Isolated"
        return "At Risk"

    # === ANALYTICS ===
    def get_average_sentiment(self) -> float:
        return sum(r["sentiment_score"] for r in self.data) / len(self.data) if self.data else 0.0

    def get_quadrant_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for r in self.data:
            dist[r["quadrant"]] = dist.get(r["quadrant"], 0) + 1
        return dist

    def get_sentiment_by_role(self) -> Dict[str, float]:
        totals, counts = {}, {}
        for r in self.data:
            role, sentiment = r["role"], r["sentiment_score"]
            totals[role] = totals.get(role, 0) + sentiment
            counts[role] = counts.get(role, 0) + 1
        return {role: totals[role] / counts[role] for role in totals}

    def get_analytics_summary(self) -> Dict[str, Any]:
        return {
            "total_employees": len(self.data),
            "average_sentiment": self.get_average_sentiment(),
            "quadrant_distribution": self.get_quadrant_distribution(),
            "sentiment_by_role": self.get_sentiment_by_role(),
        }

    # === HELPER: SAFE AI TEXT EXTRACTION ===
    def _extract_ai_text(self, response) -> str:
        """Safely extract text from Gemini API response"""
        if not response:
            return "⚠️ No response from Gemini."

        if not hasattr(response, "candidates") or not response.candidates:
            return "⚠️ Gemini returned no candidates."

        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", "unknown")
        logger.info(f"Gemini finish_reason = {finish_reason}")

        if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
            texts = [p.text for p in candidate.content.parts if hasattr(p, "text")]
            if texts:
                return "\n".join(texts).strip()

        return f"⚠️ Gemini returned no usable text (finish_reason={finish_reason})."

    # === AI ANALYSIS ===
    def analyze_with_ai(self, query: str, context: str) -> str:
        """Perform AI analysis using Gemini AI client."""
        if not self.gemini_model:
            return "⚠️ Gemini AI not initialized or API key missing."

        try:
            prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nProvide a detailed analysis."
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 512,
                }
            )
            return self._extract_ai_text(response)
        except Exception as e:
            logger.error(f"❌ AI analysis failed: {e}")
            return f"❌ AI analysis failed: {e}"


# === STANDALONE EXECUTION ===
if __name__ == "__main__":
    print("HR Sentiment Analyzer - Demo (MySQL)")
    print("=" * 40)

    analyzer = HRAnalyzer()
    if analyzer.load_data():
        summary = analyzer.get_analytics_summary()
        print(f"Loaded {summary['total_employees']} employees from MySQL")
        print(f"Average sentiment: {summary['average_sentiment']:.1f}%")
        print(f"Quadrant distribution: {summary['quadrant_distribution']}")

        test_context = "\n".join([
            f"Employee {d['employee_name']} ({d['role']}): {d['sentiment_score']}% sentiment - {d['quadrant']}"
            for d in analyzer.data[:3]
        ])
        test_query = "What are the overall sentiment trends?"
        print("\nTesting AI analysis...")
        print(f"AI Response: {analyzer.analyze_with_ai(test_query, test_context)}")
    else:
        print("❌ No data loaded from MySQL.")
