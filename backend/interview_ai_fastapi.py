"""
AI Virtual Interviewer - FastAPI Implementation
Behaves like a real human interviewer with adaptive questioning
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import openai
from config import Config

# Initialize OpenAI client
try:
    client = openai.OpenAI(api_key=Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None
except Exception as e:
    print(f"[InterviewAI] OpenAI client initialization error: {e}")
    client = None

# Redis for memory persistence (optional - falls back to in-memory)
_redis_client = None
_memory_cache = {}  # Fallback in-memory cache
MEMORY_TTL = 3600 * 24  # 24 hours TTL for interview memory

try:
    import redis
    if hasattr(Config, 'REDIS_URL') and Config.REDIS_URL:
        _redis_client = redis.from_url(Config.REDIS_URL, decode_responses=True)
        print("[InterviewAI] Redis connected for memory persistence")
    else:
        # Try default localhost Redis
        _redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        _redis_client.ping()  # Test connection
        print("[InterviewAI] Redis connected (localhost)")
except Exception as e:
    print(f"[InterviewAI] Redis not available, using in-memory cache: {e}")
    _redis_client = None


def save_interview_memory(session_id: int, memory_dict: Dict) -> bool:
    """
    Save interview memory to Redis or in-memory cache
    Returns True if successful
    """
    try:
        key = f"interview_memory:{session_id}"
        memory_json = json.dumps(memory_dict)
        
        if _redis_client:
            _redis_client.setex(key, MEMORY_TTL, memory_json)
            return True
        else:
            # Fallback to in-memory cache
            _memory_cache[key] = {
                'data': memory_dict,
                'expires_at': datetime.utcnow() + timedelta(seconds=MEMORY_TTL)
            }
            return True
    except Exception as e:
        print(f"[InterviewAI] Error saving memory: {e}")
        return False


def load_interview_memory(session_id: int) -> Optional[Dict]:
    """
    Load interview memory from Redis or in-memory cache
    Returns memory dict or None if not found
    """
    try:
        key = f"interview_memory:{session_id}"
        
        if _redis_client:
            memory_json = _redis_client.get(key)
            if memory_json:
                return json.loads(memory_json)
        else:
            # Check in-memory cache
            if key in _memory_cache:
                cache_entry = _memory_cache[key]
                if datetime.utcnow() < cache_entry['expires_at']:
                    return cache_entry['data']
                else:
                    # Expired, remove it
                    del _memory_cache[key]
        
        return None
    except Exception as e:
        print(f"[InterviewAI] Error loading memory: {e}")
        return None


def delete_interview_memory(session_id: int) -> bool:
    """
    Delete interview memory from Redis or in-memory cache
    """
    try:
        key = f"interview_memory:{session_id}"
        
        if _redis_client:
            _redis_client.delete(key)
        else:
            if key in _memory_cache:
                del _memory_cache[key]
        
        return True
    except Exception as e:
        print(f"[InterviewAI] Error deleting memory: {e}")
        return False


class InterviewMemory:
    """
    Interview Memory Object - Tracks conversation state and candidate performance
    """
    
    def __init__(self, interview_type: str, resume_data: Dict = None, jd_data: Dict = None):
        self.interview_type = interview_type  # 'TR' or 'HR'
        self.resume_data = resume_data or {}
        self.jd_data = jd_data or {}
        
        # Conversation tracking
        self.questions_asked: List[Dict] = []  # [{question, phase, difficulty, topic}]
        self.answers_given: List[Dict] = []  # [{answer, analysis, scores}]
        self.conversation_history: List[Dict] = []  # Full conversation
        
        # Performance tracking
        self.overall_performance: float = 0.0  # Average score
        self.performance_history: List[float] = []
        self.strong_topics: List[str] = []
        self.weak_topics: List[str] = []
        self.topics_covered: List[str] = []
        self.current_topic: Optional[str] = None
        self.current_phase: str = "introduction"  # introduction, technical, behavioral, etc.
        
        # Difficulty management
        self.current_difficulty: str = "medium"  # easy, medium, hard
        self.difficulty_history: List[str] = []
        
        # Contradiction tracking
        self.contradictions: List[Dict] = []  # [{claim1, claim2, context}]
        self.contradiction_warnings: int = 0
        
        # Follow-up tracking
        self.pending_followups: List[Dict] = []  # [{topic, reason, priority}]
        self.followup_needed: bool = False  # Flag for follow-up requirement
        
        # Confidence tracking
        self.confidence_level: float = 0.5  # 0.0 to 1.0
        self.confidence_history: List[float] = []
        self.confidence_score: float = 0.5  # Overall confidence score
        
        # Candidate level tracking
        self.candidate_level: str = "junior"  # junior, mid, senior, expert
        self.candidate_level_history: List[str] = []
        
        # Asked questions and answers (for summary generation)
        self.asked_questions: List[Dict] = []  # [{question, topic, difficulty, timestamp}]
        self.answers: List[Dict] = []  # [{answer, analysis, timestamp}]
        
        # Interview metadata
        self.start_time: Optional[datetime] = None
        self.question_count: int = 0
        self.total_questions: int = 6  # Default, can be adjusted
        
    def to_dict(self) -> Dict:
        """Convert memory to dictionary for storage"""
        return {
            "interview_type": self.interview_type,
            "resume_data": self.resume_data,
            "jd_data": self.jd_data,
            "questions_asked": self.questions_asked,
            "answers_given": self.answers_given,
            "conversation_history": self.conversation_history,
            "overall_performance": self.overall_performance,
            "performance_history": self.performance_history,
            "strong_topics": self.strong_topics,
            "weak_topics": self.weak_topics,
            "topics_covered": self.topics_covered,
            "current_topic": self.current_topic,
            "current_phase": self.current_phase,
            "current_difficulty": self.current_difficulty,
            "difficulty_history": self.difficulty_history,
            "contradictions": self.contradictions,
            "contradiction_warnings": self.contradiction_warnings,
            "pending_followups": self.pending_followups,
            "followup_needed": self.followup_needed,
            "confidence_level": self.confidence_level,
            "confidence_history": self.confidence_history,
            "confidence_score": self.confidence_score,
            "candidate_level": self.candidate_level,
            "candidate_level_history": self.candidate_level_history,
            "asked_questions": self.asked_questions,
            "answers": self.answers,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "question_count": self.question_count,
            "total_questions": self.total_questions
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Create memory from dictionary"""
        memory = cls(
            interview_type=data.get("interview_type", "TR"),
            resume_data=data.get("resume_data", {}),
            jd_data=data.get("jd_data", {})
        )
        
        memory.questions_asked = data.get("questions_asked", [])
        memory.answers_given = data.get("answers_given", [])
        memory.conversation_history = data.get("conversation_history", [])
        memory.overall_performance = data.get("overall_performance", 0.0)
        memory.performance_history = data.get("performance_history", [])
        memory.strong_topics = data.get("strong_topics", [])
        memory.weak_topics = data.get("weak_topics", [])
        memory.topics_covered = data.get("topics_covered", [])
        memory.current_topic = data.get("current_topic")
        memory.current_phase = data.get("current_phase", "introduction")
        memory.current_difficulty = data.get("current_difficulty", "medium")
        memory.difficulty_history = data.get("difficulty_history", [])
        memory.contradictions = data.get("contradictions", [])
        memory.contradiction_warnings = data.get("contradiction_warnings", 0)
        memory.pending_followups = data.get("pending_followups", [])
        memory.followup_needed = data.get("followup_needed", False)
        memory.confidence_level = data.get("confidence_level", 0.5)
        memory.confidence_history = data.get("confidence_history", [])
        memory.confidence_score = data.get("confidence_score", 0.5)
        memory.candidate_level = data.get("candidate_level", "junior")
        memory.candidate_level_history = data.get("candidate_level_history", [])
        memory.asked_questions = data.get("asked_questions", [])
        memory.answers = data.get("answers", [])
        memory.question_count = data.get("question_count", 0)
        memory.total_questions = data.get("total_questions", 6)
        
        if data.get("start_time"):
            memory.start_time = datetime.fromisoformat(data["start_time"])
        
        return memory


class AnswerAnalyzer:
    """
    Analyzes user answers across multiple dimensions
    """
    
    @staticmethod
    def analyze_answer(
        question: str,
        answer: str,
        interview_memory: InterviewMemory,
        conversation_history: List[Dict]
    ) -> Dict:
        """
        Analyze answer for correctness, confidence, topic, difficulty, contradictions, follow-up needs
        Returns comprehensive analysis
        """
        if not client:
            return AnswerAnalyzer._fallback_analysis(question, answer, interview_memory)
        
        try:
            # Build context from memory
            context = {
                "interview_type": interview_memory.interview_type,
                "current_phase": interview_memory.current_phase,
                "current_topic": interview_memory.current_topic,
                "current_difficulty": interview_memory.current_difficulty,
                "previous_answers": interview_memory.answers_given[-3:],  # Last 3 answers
                "topics_covered": interview_memory.topics_covered,
                "resume_skills": interview_memory.resume_data.get("skills", []),
                "jd_requirements": interview_memory.jd_data.get("required_skills", [])
            }
            
            prompt = f"""
You are a professional human technical interviewer conducting a {interview_memory.interview_type} interview.

INTERVIEW CONTEXT:
- Interview Type: {interview_memory.interview_type}
- Current Phase: {interview_memory.current_phase}
- Current Topic: {interview_memory.current_topic or 'General'}
- Current Difficulty: {interview_memory.current_difficulty}

CURRENT QUESTION:
{question}

CANDIDATE ANSWER:
{answer}

PREVIOUS CONVERSATION:
{json.dumps(conversation_history[-5:], indent=2)}

RESUME SKILLS: {', '.join(interview_memory.resume_data.get('skills', [])[:10])}
JD REQUIREMENTS: {', '.join(interview_memory.jd_data.get('required_skills', [])[:10])}

Analyze this answer as a real human interviewer would. Provide a JSON response with:

{{
  "correctness": float (0.0-10.0),  // How correct is the answer?
  "confidence": float (0.0-10.0),   // How confident does the candidate sound?
  "clarity": float (0.0-10.0),      // How clear and well-structured is the answer?
  "depth": float (0.0-10.0),        // How deep is the technical/domain knowledge?
  "topic": string,                   // What topic/subtopic does this answer relate to?
  "difficulty_level": string,       // "easy", "medium", or "hard" based on answer quality
  "contradiction_detected": boolean, // Does this contradict previous answers?
  "contradiction_details": string,   // If contradiction, explain what contradicts what
  "follow_up_needed": boolean,       // Does this answer need a follow-up question?
  "follow_up_reason": string,        // Why is follow-up needed? (e.g., "unclear explanation", "needs deeper dive")
  "strengths": [string],            // What did the candidate do well?
  "weaknesses": [string],           // What could be improved?
  "overall_score": float (0.0-10.0)  // Overall assessment score
}}

Be strict but fair. A real interviewer would:
- Notice if answers are vague or lack detail
- Detect contradictions with previous statements
- Identify when someone is confident vs. uncertain
- Recognize when deeper exploration is needed
- Adjust difficulty based on performance

Return ONLY valid JSON, no other text.
"""
            
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL or "gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional technical interviewer. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            # Validate and normalize scores (0-1 scale)
            for key in ["correctness", "conceptual_depth", "clarity", "confidence"]:
                if key in analysis:
                    val = float(analysis[key])
                    # Handle if LLM returns 0-10 scale, normalize to 0-1
                    if val > 1.0:
                        val = val / 10.0
                    analysis[key] = max(0.0, min(1.0, val))
            
            # Ensure boolean fields
            analysis["contradiction"] = bool(analysis.get("contradiction", False))
            analysis["needs_followup"] = bool(analysis.get("needs_followup", False))
            
            # Backward compatibility aliases
            analysis["contradiction_detected"] = analysis["contradiction"]
            analysis["follow_up_needed"] = analysis["needs_followup"]
            analysis["depth"] = analysis.get("conceptual_depth", 0.5)  # Alias for backward compatibility
            
            # ===== BACKEND CONFIDENCE FORMULA =====
            # Override LLM confidence with backend formula
            correctness = analysis.get("correctness", 0.5)
            conceptual_depth = analysis.get("conceptual_depth", 0.5)
            language_clarity = analysis.get("clarity", 0.5)
            
            # Backend confidence formula (0-1 scale)
            backend_confidence = (correctness + conceptual_depth + language_clarity) / 3.0
            
            # Blend LLM confidence (30%) with backend formula (70%) for more reliable scoring
            llm_confidence = analysis.get("confidence", 0.5)
            final_confidence = (0.3 * llm_confidence) + (0.7 * backend_confidence)
            
            # Update analysis with calculated confidence
            analysis["confidence"] = final_confidence
            analysis["backend_confidence"] = backend_confidence  # Store for debugging
            # ===== END BACKEND CONFIDENCE FORMULA =====
            
            return analysis
            
        except Exception as e:
            print(f"[AnswerAnalyzer] Error: {e}")
            return AnswerAnalyzer._fallback_analysis(question, answer, interview_memory)
    
    @staticmethod
    def _fallback_analysis(question: str, answer: str, memory: InterviewMemory) -> Dict:
        """Fallback analysis if AI is unavailable"""
        answer_length = len(answer.split())
        
        return {
            "correctness": 5.0,
            "confidence": 5.0,
            "clarity": 5.0,
            "depth": 5.0,
            "topic": memory.current_topic or "general",
            "difficulty_level": memory.current_difficulty,
            "contradiction_detected": False,
            "contradiction_details": "",
            "follow_up_needed": answer_length < 20,
            "follow_up_reason": "Answer seems brief, may need clarification" if answer_length < 20 else "",
            "strengths": [],
            "weaknesses": [],
            "overall_score": 5.0
        }


class DecisionEngine:
    """
    Decides what to do next based on analysis and memory
    """
    
    @staticmethod
    def decide_next_action(
        analysis: Dict,
        interview_memory: InterviewMemory
    ) -> Dict:
        """
        Decide what to do next: followup, clarification, harder, easier, topic_change
        Returns decision with reasoning
        """
        correctness = analysis.get("correctness", 5.0)
        confidence = analysis.get("confidence", 5.0)
        overall_score = analysis.get("overall_score", 5.0)
        contradiction = analysis.get("contradiction_detected", False)
        follow_up_needed = analysis.get("follow_up_needed", False)
        
        # Priority 1: Handle contradictions - ACTIVE ENFORCEMENT
        if contradiction:
            interview_memory.contradiction_warnings += 1
            
            # Force clarification decision - no exceptions
            decision_result = {
                "decision": "clarification",
                "reason": analysis.get("contradiction_details", "Contradiction detected with previous answer. Please clarify."),
                "priority": "high",
                "force_clarification": True  # Flag to ensure this is handled
            }
            
            # Penalize confidence score when contradiction detected
            if "confidence" in analysis:
                # Reduce confidence by 20% for each contradiction
                penalty = 0.2 * interview_memory.contradiction_warnings
                analysis["confidence"] = max(0.0, analysis["confidence"] * (1.0 - penalty))
                # Also reduce overall score
                if "overall_score" in analysis:
                    analysis["overall_score"] = max(0.0, analysis["overall_score"] * (1.0 - penalty * 0.5))
            
            return decision_result
        
        # Priority 2: Handle follow-ups
        if follow_up_needed:
            return {
                "decision": "followup",
                "reason": analysis.get("follow_up_reason", "Answer needs deeper exploration"),
                "priority": "medium"
            }
        
        # Priority 3: Adjust difficulty based on performance
        if overall_score >= 8.0 and interview_memory.current_difficulty != "hard":
            return {
                "decision": "harder",
                "reason": f"Strong performance (score: {overall_score:.1f}), increasing difficulty",
                "priority": "medium"
            }
        elif overall_score <= 4.0 and interview_memory.current_difficulty != "easy":
            return {
                "decision": "easier",
                "reason": f"Struggling (score: {overall_score:.1f}), reducing difficulty",
                "priority": "medium"
            }
        
        # Priority 4: Change topic if current topic is exhausted
        if interview_memory.question_count >= interview_memory.total_questions * 0.8:
            return {
                "decision": "topic_change",
                "reason": "Interview nearing completion, moving to final topics",
                "priority": "low"
            }
        
        # Default: Continue with current difficulty
        return {
            "decision": "continue",
            "reason": "Continuing with current difficulty and topic",
            "priority": "low"
        }


class QuestionGenerator:
    """
    Generates adaptive interview questions
    """
    
    @staticmethod
    def generate_next_question(
        decision: Dict,
        interview_memory: InterviewMemory,
        analysis: Dict
    ) -> str:
        """
        Generate the next interview question based on decision and memory
        """
        if not client:
            return QuestionGenerator._fallback_question(decision, interview_memory)
        
        try:
            decision_type = decision.get("decision", "continue")
            reason = decision.get("reason", "")
            
            # Build context
            context = {
                "interview_type": interview_memory.interview_type,
                "current_phase": interview_memory.current_phase,
                "current_topic": interview_memory.current_topic,
                "current_difficulty": interview_memory.current_difficulty,
                "topics_covered": interview_memory.topics_covered,
                "strong_topics": interview_memory.strong_topics,
                "weak_topics": interview_memory.weak_topics,
                "resume_skills": interview_memory.resume_data.get("skills", []),
                "jd_requirements": interview_memory.jd_data.get("required_skills", []),
                "last_question": interview_memory.questions_asked[-1].get("question", "") if interview_memory.questions_asked else "",
                "last_answer_analysis": analysis
            }
            
            prompt = f"""
You are a professional human {interview_memory.interview_type} interviewer conducting a real interview.

CRITICAL TONE RULES:
- Maintain a CONVERSATIONAL interview tone, NOT an academic or robotic tone
- Sound like a friendly, professional human interviewer having a natural conversation
- Use natural transitions and follow-up phrases
- Avoid formal academic language or overly structured phrasing
- Make it feel like a real conversation, not a test

INTERVIEW CONTEXT:
- Type: {interview_memory.interview_type}
- Phase: {interview_memory.current_phase}
- Topic: {interview_memory.current_topic or 'General'}
- Difficulty: {interview_memory.current_difficulty}
- Topics Covered: {', '.join(interview_memory.topics_covered)}
- Weak Areas: {', '.join(interview_memory.weak_topics)}
- Strong Areas: {', '.join(interview_memory.strong_topics)}

DECISION: {decision_type.upper()}
REASON: {reason}

LAST QUESTION: {context['last_question']}
LAST ANSWER ANALYSIS:
- Correctness: {analysis.get('correctness', 5.0)}/10
- Confidence: {analysis.get('confidence', 5.0)}/10
- Overall: {analysis.get('overall_score', 5.0)}/10
- Follow-up needed: {analysis.get('follow_up_needed', False)}
- Contradiction: {analysis.get('contradiction_detected', False)}

RESUME SKILLS: {', '.join(interview_memory.resume_data.get('skills', [])[:10])}
JD REQUIREMENTS: {', '.join(interview_memory.jd_data.get('required_skills', [])[:10])}

Generate ONE natural, conversational interview question based on the decision:

- If "followup": Ask a clarifying or deeper question on the same topic (e.g., "That's interesting! Can you walk me through a specific example?")
- If "clarification": Ask about the contradiction directly but politely (e.g., "I want to make sure I understand - earlier you mentioned X, but now you're saying Y. Can you help me reconcile that?")
- If "harder": Ask a more challenging question naturally (e.g., "Great! Now let's push this a bit further - how would you handle...")
- If "easier": Ask a simpler question to build confidence (e.g., "Let's take a step back - can you tell me about the basics of...")
- If "topic_change": Move to a new relevant topic smoothly (e.g., "Thanks for that insight! Let's shift gears a bit - I'd like to hear about your experience with...")
- If "continue": Ask the next logical question naturally

The question MUST:
1. Sound like a REAL HUMAN interviewer having a conversation (conversational tone, not academic)
2. Use natural transitions and follow-up phrases
3. Be appropriate for {interview_memory.current_difficulty} difficulty
4. Be relevant to {interview_memory.interview_type} interview type
5. Build on previous conversation naturally
6. Be specific and actionable (not vague)
7. Feel warm and professional, not robotic or test-like

Return ONLY the question text, no JSON, no quotes, just the question.
"""
            
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL or "gpt-4",
                messages=[
                    {"role": "system", "content": "You are a friendly, professional human interviewer having a natural conversation. Generate questions that sound conversational and human-like, not academic or robotic. Return only the question text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,  # Increased for more natural variation
                max_tokens=200
            )
            
            question = response.choices[0].message.content.strip()
            
            # Remove quotes if present
            if question.startswith('"') and question.endswith('"'):
                question = question[1:-1]
            if question.startswith("'") and question.endswith("'"):
                question = question[1:-1]
            
            return question
            
        except Exception as e:
            print(f"[QuestionGenerator] Error: {e}")
            return QuestionGenerator._fallback_question(decision, interview_memory)
    
    @staticmethod
    def _fallback_question(decision: Dict, memory: InterviewMemory) -> str:
        """Fallback question if AI is unavailable"""
        decision_type = decision.get("decision", "continue")
        
        if decision_type == "followup":
            return "Can you elaborate on that? I'd like to understand better."
        elif decision_type == "clarification":
            return "I noticed something that seems inconsistent. Can you clarify?"
        elif decision_type == "harder":
            return "Let's dive deeper. Can you explain how you would handle a more complex scenario?"
        elif decision_type == "easier":
            return "Let's take a step back. Can you tell me about your basic understanding of this topic?"
        elif decision_type == "topic_change":
            return "Let's move to a different topic. Can you tell me about your experience with related technologies?"
        else:
            return "Can you tell me more about your experience in this area?"


def process_interview_answer(
    interview_memory_dict: Dict,
    current_question: str,
    user_answer: str,
    session_id: Optional[int] = None
) -> Dict:
    """
    Main function: Process answer and return analysis, updated memory, decision, and next question
    
    Returns:
    {
        "analysis": {...},
        "updated_memory": {...},
        "decision": "followup / clarification / harder / easier / topic_change / continue",
        "next_question": "..."
    }
    """
    try:
        # Load interview memory
        interview_memory = InterviewMemory.from_dict(interview_memory_dict)
        
        # Get conversation history
        conversation_history = interview_memory.conversation_history
        
        # 1. Analyze the answer
        analysis = AnswerAnalyzer.analyze_answer(
            question=current_question,
            answer=user_answer,
            interview_memory=interview_memory,
            conversation_history=conversation_history
        )
        
        # 2. Update interview memory
        interview_memory.answers_given.append({
            "question": current_question,
            "answer": user_answer,
            "analysis": analysis,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Update performance
        overall_score = analysis.get("overall_score", 5.0)
        interview_memory.performance_history.append(overall_score)
        interview_memory.overall_performance = sum(interview_memory.performance_history) / len(interview_memory.performance_history)
        
        # Update confidence (using backend-calculated confidence)
        confidence = analysis.get("confidence", 5.0) / 10.0
        
        # Additional penalty if contradiction detected
        if analysis.get("contradiction_detected", False):
            # Apply additional penalty to memory confidence
            confidence = confidence * 0.7  # 30% penalty
        
        interview_memory.confidence_history.append(confidence)
        interview_memory.confidence_level = sum(interview_memory.confidence_history) / len(interview_memory.confidence_history)
        
        # Update topics
        topic = analysis.get("topic", "general")
        if topic and topic not in interview_memory.topics_covered:
            interview_memory.topics_covered.append(topic)
        
        # Update current topic
        interview_memory.current_topic = topic
        
        # ===== TOPIC MASTERY RULES =====
        # Check if topic is mastered: same topic asked 3+ times with correctness > 0.75 (0-1 scale)
        topic_question_count = sum(1 for ans in interview_memory.answers_given 
                                  if ans.get("analysis", {}).get("topic") == topic)
        topic_correctness_avg = sum(ans.get("analysis", {}).get("correctness", 0.5) 
                                   for ans in interview_memory.answers_given 
                                   if ans.get("analysis", {}).get("topic") == topic) / max(1, topic_question_count)
        
        # Topic is mastered if: 3+ questions on same topic AND average correctness > 0.75
        topic_mastered = (topic_question_count >= 3) and (topic_correctness_avg > 0.75)
        
        if topic_mastered:
            # Mark as strong topic and remove from weak topics
            if topic and topic not in interview_memory.strong_topics:
                interview_memory.strong_topics.append(topic)
            if topic in interview_memory.weak_topics:
                interview_memory.weak_topics.remove(topic)
            print(f"[InterviewAI] Topic '{topic}' mastered! (3+ questions, {topic_correctness_avg:.2%} avg correctness)")
        elif overall_score >= 0.7 and topic:
            # Strong performance but not yet mastered
            if topic not in interview_memory.strong_topics:
                interview_memory.strong_topics.append(topic)
            if topic in interview_memory.weak_topics:
                interview_memory.weak_topics.remove(topic)
        elif overall_score <= 0.4 and topic:
            # Weak performance
            if topic not in interview_memory.weak_topics:
                interview_memory.weak_topics.append(topic)
        # ===== END TOPIC MASTERY RULES =====
        
        # Update candidate level based on performance trend
        if len(interview_memory.performance_history) >= 3:
            recent_avg = sum(interview_memory.performance_history[-3:]) / 3.0
            if recent_avg >= 0.85:
                new_level = "expert"
            elif recent_avg >= 0.70:
                new_level = "senior"
            elif recent_avg >= 0.50:
                new_level = "mid"
            else:
                new_level = "junior"
            
            if new_level != interview_memory.candidate_level:
                interview_memory.candidate_level_history.append(interview_memory.candidate_level)
                interview_memory.candidate_level = new_level
                print(f"[InterviewAI] Candidate level updated: {interview_memory.candidate_level}")
        
        # Update followup_needed flag
        interview_memory.followup_needed = analysis.get("needs_followup", False) or len(missing_concepts) > 0
        
        # Handle contradictions
        if analysis.get("contradiction", False) or analysis.get("contradiction_detected", False):
            interview_memory.contradictions.append({
                "claim1": current_question,
                "claim2": analysis.get("contradiction_details", ""),
                "context": user_answer,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # 3. Decide what to do next
        decision = DecisionEngine.decide_next_action(analysis, interview_memory)
        
        # Apply decision to memory
        if decision["decision"] == "harder":
            interview_memory.current_difficulty = "hard"
            interview_memory.difficulty_history.append("hard")
        elif decision["decision"] == "easier":
            interview_memory.current_difficulty = "easy"
            interview_memory.difficulty_history.append("easy")
        elif decision["decision"] == "topic_change":
            # Select next topic (simplified - in production, use smarter topic selection)
            available_topics = ["programming", "system_design", "algorithms", "databases", "networking"]
            next_topic = None
            for topic in available_topics:
                if topic not in interview_memory.topics_covered:
                    next_topic = topic
                    break
            if next_topic:
                interview_memory.current_topic = next_topic
                interview_memory.topics_covered.append(next_topic)
        
        # Increment question count
        interview_memory.question_count += 1
        
        # 4. Generate next question
        next_question = QuestionGenerator.generate_next_question(decision, interview_memory, analysis)
        
        # Add next question to memory
        question_entry = {
            "question": next_question,
            "phase": interview_memory.current_phase,
            "difficulty": interview_memory.current_difficulty,
            "topic": interview_memory.current_topic,
            "timestamp": datetime.utcnow().isoformat()
        }
        interview_memory.questions_asked.append(question_entry)
        interview_memory.asked_questions.append(question_entry)  # Also store in asked_questions for summary
        
        # Update conversation history
        interview_memory.conversation_history.append({
            "type": "question",
            "content": current_question,
            "timestamp": datetime.utcnow().isoformat()
        })
        interview_memory.conversation_history.append({
            "type": "answer",
            "content": user_answer,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Save memory to Redis/DB for persistence
        updated_memory_dict = interview_memory.to_dict()
        if session_id:
            save_interview_memory(session_id, updated_memory_dict)
        
        # Format analysis for response (ensure all fields present)
        formatted_analysis = {
            "correctness": analysis.get("correctness", 0.5),
            "conceptual_depth": analysis.get("conceptual_depth", 0.5),
            "clarity": analysis.get("clarity", 0.5),
            "confidence": analysis.get("confidence", 0.5),
            "topic": analysis.get("topic", "general"),
            "difficulty_level": analysis.get("difficulty_level", interview_memory.current_difficulty),
            "missing_concepts": analysis.get("missing_concepts", []),
            "needs_followup": analysis.get("needs_followup", False),
            "contradiction": analysis.get("contradiction", False),
            "analysis_summary": analysis.get("analysis_summary", "Answer analyzed.")
        }
        
        # Format updated memory for response
        formatted_memory = {
            "candidate_level": interview_memory.candidate_level,
            "strong_topics": interview_memory.strong_topics,
            "weak_topics": interview_memory.weak_topics,
            "asked_questions": interview_memory.asked_questions[-10:],  # Last 10 questions
            "answers": interview_memory.answers[-10:],  # Last 10 answers
            "contradictions": interview_memory.contradictions,
            "confidence_score": interview_memory.confidence_score,
            "current_topic": interview_memory.current_topic,
            "followup_needed": interview_memory.followup_needed
        }
        
        # Return result in strict JSON format
        return {
            "analysis": formatted_analysis,
            "updated_memory": formatted_memory,
            "decision": decision["decision"],
            "next_question": next_question
        }
        
    except Exception as e:
        print(f"[process_interview_answer] Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Return error response
        return {
            "analysis": {
                "correctness": 5.0,
                "confidence": 5.0,
                "clarity": 5.0,
                "depth": 5.0,
                "overall_score": 5.0,
                "error": str(e)
            },
            "updated_memory": interview_memory_dict,
            "decision": "continue",
            "decision_reason": "Error occurred, continuing with default flow",
            "next_question": "Let's continue. Can you tell me more about your experience?"
        }
