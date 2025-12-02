"""
Voice Report NLP Analyzer
Extracts sentiment, subjects, and generates auto-labels from transcribed text
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VoiceReportNLPAnalyzer:
    """
    NLP analyzer for voice reports
    
    Extracts:
    - Sentiment (complaint, compliment, neutral)
    - Subjects (chef, driver, staff, food, service, delivery)
    - Auto-labels (standardized tags like "Complaint Chef", "Compliment Delivery")
    
    Uses keyword matching and simple heuristics for local operation
    In production, could integrate with:
    - Local transformer models (BERT, RoBERTa)
    - LLM API for advanced classification
    """
    
    # Keywords for sentiment detection
    COMPLAINT_KEYWORDS = [
        'complaint', 'complain', 'issue', 'problem', 'bad', 'terrible', 'awful',
        'horrible', 'poor', 'worst', 'unacceptable', 'disappointed', 'unhappy',
        'angry', 'frustrated', 'wrong', 'mistake', 'error', 'late', 'cold',
        'burnt', 'raw', 'spoiled', 'rude', 'unprofessional', 'refund', 'cancel'
    ]
    
    COMPLIMENT_KEYWORDS = [
        'compliment', 'praise', 'excellent', 'amazing', 'great', 'wonderful',
        'perfect', 'delicious', 'fantastic', 'outstanding', 'best', 'awesome',
        'appreciate', 'thank', 'professional', 'polite', 'friendly', 'helpful',
        'impressed', 'satisfied', 'love', 'recommend', 'superb', 'stellar'
    ]
    
    # Subject detection patterns
    SUBJECT_PATTERNS = {
        'chef': [
            r'\bchef\b', r'\bcook\b', r'\bkitchen\b', r'\bprepared?\b',
            r'\bfood quality\b', r'\bseasoning\b', r'\bcooked\b'
        ],
        'driver': [
            r'\bdriver\b', r'\bdelivery person\b', r'\bdelivered\b',
            r'\bdelivery\b', r'\barrived\b', r'\blate\b', r'\bearly\b',
            r'\bon time\b', r'\bdriving\b'
        ],
        'staff': [
            r'\bstaff\b', r'\bemployee\b', r'\bworker\b', r'\bteam\b',
            r'\bservice\b', r'\bcustomer service\b'
        ],
        'food': [
            r'\bfood\b', r'\bmeal\b', r'\bdish\b', r'\border\b',
            r'\btaste\b', r'\bflavor\b', r'\bquality\b', r'\bportion\b',
            r'\btemperature\b', r'\bpresentation\b'
        ],
        'delivery': [
            r'\bdelivery\b', r'\bshipping\b', r'\barrival\b',
            r'\btiming\b', r'\bpackaging\b', r'\bcondition\b'
        ],
        'service': [
            r'\bservice\b', r'\bexperience\b', r'\bresponse\b',
            r'\bcommunication\b', r'\bprofessionalism\b'
        ]
    }
    
    def __init__(self, use_advanced_nlp: bool = False):
        """
        Initialize NLP analyzer
        
        Args:
            use_advanced_nlp: If True, attempt to use transformer models (requires transformers library)
        """
        self.use_advanced_nlp = use_advanced_nlp
        self.sentiment_model = None
        
        if use_advanced_nlp:
            try:
                from transformers import pipeline
                self.sentiment_model = pipeline("sentiment-analysis")
                logger.info("Advanced NLP model loaded successfully")
            except ImportError:
                logger.warning("Transformers not installed, using keyword-based analysis")
                self.use_advanced_nlp = False
            except Exception as e:
                logger.error(f"Failed to load NLP model: {e}, using keyword-based analysis")
                self.use_advanced_nlp = False
    
    def analyze_report(self, transcription: str) -> Dict:
        """
        Analyze transcribed voice report
        
        Args:
            transcription: Transcribed text from voice report
            
        Returns:
            Dictionary with:
            - sentiment: str (complaint, compliment, neutral)
            - confidence: float (0.0-1.0)
            - subjects: List[str] (detected subjects)
            - auto_labels: List[str] (standardized labels)
        """
        if not transcription or not transcription.strip():
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'subjects': [],
                'auto_labels': []
            }
        
        text_lower = transcription.lower()
        
        # Detect sentiment
        sentiment, sentiment_confidence = self._detect_sentiment(text_lower)
        
        # Extract subjects
        subjects = self._extract_subjects(text_lower)
        
        # Generate auto-labels
        auto_labels = self._generate_labels(sentiment, subjects)
        
        return {
            'sentiment': sentiment,
            'confidence': sentiment_confidence,
            'subjects': subjects,
            'auto_labels': auto_labels
        }
    
    def _detect_sentiment(self, text: str) -> Tuple[str, float]:
        """
        Detect sentiment (complaint, compliment, or neutral)
        
        Returns:
            Tuple of (sentiment, confidence_score)
        """
        if self.use_advanced_nlp and self.sentiment_model:
            return self._advanced_sentiment_detection(text)
        else:
            return self._keyword_sentiment_detection(text)
    
    def _keyword_sentiment_detection(self, text: str) -> Tuple[str, float]:
        """
        Keyword-based sentiment detection
        """
        # Count complaint and compliment keywords
        complaint_count = sum(1 for keyword in self.COMPLAINT_KEYWORDS if keyword in text)
        compliment_count = sum(1 for keyword in self.COMPLIMENT_KEYWORDS if keyword in text)
        
        total_keywords = complaint_count + compliment_count
        
        if total_keywords == 0:
            return 'neutral', 0.5
        
        # Determine dominant sentiment
        if complaint_count > compliment_count:
            sentiment = 'complaint'
            confidence = min(0.95, 0.6 + (complaint_count / (total_keywords + 5)))
        elif compliment_count > complaint_count:
            sentiment = 'compliment'
            confidence = min(0.95, 0.6 + (compliment_count / (total_keywords + 5)))
        else:
            # Equal counts - check intensity words
            if any(word in text for word in ['terrible', 'horrible', 'awful', 'worst']):
                sentiment = 'complaint'
                confidence = 0.7
            elif any(word in text for word in ['excellent', 'amazing', 'perfect', 'best']):
                sentiment = 'compliment'
                confidence = 0.7
            else:
                sentiment = 'neutral'
                confidence = 0.6
        
        return sentiment, confidence
    
    def _advanced_sentiment_detection(self, text: str) -> Tuple[str, float]:
        """
        Advanced sentiment detection using transformer models
        """
        try:
            result = self.sentiment_model(text[:512])[0]  # Limit to 512 chars for model
            
            label = result['label'].lower()
            score = result['score']
            
            # Map model labels to our sentiment categories
            if 'positive' in label:
                sentiment = 'compliment'
            elif 'negative' in label:
                sentiment = 'complaint'
            else:
                sentiment = 'neutral'
            
            return sentiment, score
            
        except Exception as e:
            logger.error(f"Advanced sentiment detection failed: {e}")
            return self._keyword_sentiment_detection(text)
    
    def _extract_subjects(self, text: str) -> List[str]:
        """
        Extract subjects mentioned in the text
        
        Returns:
            List of subject strings (e.g., ['chef', 'driver', 'food'])
        """
        detected_subjects = []
        
        for subject, patterns in self.SUBJECT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected_subjects.append(subject)
                    break  # Only add each subject once
        
        # Remove duplicates and sort
        return sorted(list(set(detected_subjects)))
    
    def _generate_labels(self, sentiment: str, subjects: List[str]) -> List[str]:
        """
        Generate standardized auto-labels based on sentiment and subjects
        
        Args:
            sentiment: Detected sentiment (complaint, compliment, neutral)
            subjects: List of detected subjects
            
        Returns:
            List of standardized labels (e.g., ["Complaint Chef", "Food Quality Issue"])
        """
        labels = []
        
        # Capitalize sentiment for labels
        sentiment_label = sentiment.capitalize()
        
        # Generate subject-based labels
        for subject in subjects:
            subject_capitalized = subject.capitalize()
            
            if sentiment == 'complaint':
                # More specific labels for complaints
                if subject == 'chef':
                    labels.append("Complaint Chef")
                    labels.append("Food Quality Issue")
                elif subject == 'driver':
                    labels.append("Complaint Delivery Person")
                    labels.append("Delivery Issue")
                elif subject == 'food':
                    labels.append("Food Quality Issue")
                elif subject == 'delivery':
                    labels.append("Delivery Issue")
                elif subject == 'service':
                    labels.append("Service Issue")
                elif subject == 'staff':
                    labels.append("Staff Issue")
            
            elif sentiment == 'compliment':
                # More specific labels for compliments
                if subject == 'chef':
                    labels.append("Compliment Chef")
                    labels.append("Excellent Food Quality")
                elif subject == 'driver':
                    labels.append("Compliment Delivery Person")
                    labels.append("Excellent Delivery")
                elif subject == 'food':
                    labels.append("Excellent Food Quality")
                elif subject == 'delivery':
                    labels.append("Excellent Delivery")
                elif subject == 'service':
                    labels.append("Excellent Service")
                elif subject == 'staff':
                    labels.append("Excellent Staff")
            
            else:  # neutral
                labels.append(f"Feedback: {subject_capitalized}")
        
        # If no subjects detected, add generic label
        if not labels:
            if sentiment == 'complaint':
                labels.append("General Complaint")
            elif sentiment == 'compliment':
                labels.append("General Compliment")
            else:
                labels.append("General Feedback")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_labels = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                unique_labels.append(label)
        
        return unique_labels


# Singleton instance
_nlp_analyzer: Optional[VoiceReportNLPAnalyzer] = None


def get_nlp_analyzer(use_advanced_nlp: bool = False) -> VoiceReportNLPAnalyzer:
    """
    Get or create singleton NLP analyzer instance
    
    Args:
        use_advanced_nlp: Whether to use transformer models (default False for local dev)
    """
    global _nlp_analyzer
    if _nlp_analyzer is None:
        _nlp_analyzer = VoiceReportNLPAnalyzer(use_advanced_nlp=use_advanced_nlp)
    return _nlp_analyzer
