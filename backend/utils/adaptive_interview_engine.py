"""
Adaptive Interview Engine
Stateful, decision-driven interview system that behaves like a human interviewer
Replaces linear question-answer flow with adaptive, context-aware conversations
"""
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from utils.openai_client import get_openai_client, OpenAIError
from config import Config

class InterviewState:
    """
    Interview State Object - The brain of the interviewer
    Tracks candidate performance, topics, difficulty, and conversation context
    """
    def __init__(self, interview_type: str = 'TR', resume_data: Dict = None, jd_data: Dict = None):
        self.interview_type = interview_type
        self.resume_data = resume_data or {}
        self.jd_data = jd_data or {}
        
        # Current topic and difficulty
        self.current_topic = None  # e.g., "Java", "OOP", "Data Structures"
        self.difficulty_level = 1  # 1-5 scale (1=Easy, 5=Expert)
        self.confidence_score = 0.5  # 0-1 scale (candidate's overall confidence)
        
        # Performance tracking
        self.weak_areas = []  # Topics where candidate struggles
        self.strong_areas = []  # Topics where candidate excels
        self.contradictions = []  # Detected contradictions
        self.claims_made = []  # Claims/examples mentioned by candidate
        self.topics_covered = []  # Topics already discussed
        
        # Question and answer history
        self.question_history = []  # List of questions asked
        self.answer_history = []  # List of answers given
        self.evaluation_history = []  # List of evaluations
        
        # Conversation flow
        self.follow_up_count = 0  # Number of follow-ups on current topic
        self.max_follow_ups = 2  # Max follow-ups before moving on
        self.total_questions = 0
        self.max_questions = 12
        
        # Topic progression
        self.topic_progression = []  # History of topic changes
        self.current_topic_start_question = 0
        
    def to_dict(self) -> Dict:
        """Convert state to dictionary for storage/transmission"""
        return {
            'interview_type': self.interview_type,
            'current_topic': self.current_topic,
            'difficulty_level': self.difficulty_level,
            'confidence_score': self.confidence_score,
            'weak_areas': self.weak_areas,
            'strong_areas': self.strong_areas,
            'contradictions': self.contradictions,
            'claims_made': self.claims_made,
            'topics_covered': self.topics_covered,
            'question_history': self.question_history[-10:],  # Last 10
            'answer_history': self.answer_history[-10:],  # Last 10
            'evaluation_history': self.evaluation_history[-10:],  # Last 10
            'follow_up_count': self.follow_up_count,
            'total_questions': self.total_questions,
            'topic_progression': self.topic_progression
        }
    
    @classmethod
    def from_dict(cls, data: Dict, resume_data: Dict = None, jd_data: Dict = None):
        """Reconstruct state from dictionary"""
        state = cls(
            interview_type=data.get('interview_type', 'TR'),
            resume_data=resume_data,
            jd_data=jd_data
        )
        state.current_topic = data.get('current_topic')
        state.difficulty_level = data.get('difficulty_level', 1)
        state.confidence_score = data.get('confidence_score', 0.5)
        state.weak_areas = data.get('weak_areas', [])
        state.strong_areas = data.get('strong_areas', [])
        state.contradictions = data.get('contradictions', [])
        state.claims_made = data.get('claims_made', [])
        state.topics_covered = data.get('topics_covered', [])
        state.question_history = data.get('question_history', [])
        state.answer_history = data.get('answer_history', [])
        state.evaluation_history = data.get('evaluation_history', [])
        state.follow_up_count = data.get('follow_up_count', 0)
        state.total_questions = data.get('total_questions', 0)
        state.topic_progression = data.get('topic_progression', [])
        return state


class AnswerAnalyzer:
    """
    Enhanced Answer Analyzer
    Evaluates answers for correctness, confidence, depth, clarity, and consistency
    """
    
    @staticmethod
    def analyze_answer(question: str, answer: str, interview_state: InterviewState, 
                      conversation_history: List[Dict] = None) -> Dict:
        """
        Comprehensive answer analysis
        
        Returns:
        {
            'score': float (0-1),
            'confidence': float (0-1),
            'depth': float (0-1),
            'clarity': float (0-1),
            'correctness': float (0-1),
            'topics_detected': List[str],
            'claims_made': List[str],
            'contradiction_detected': bool,
            'contradiction_details': str,
            'needs_follow_up': bool,
            'follow_up_reason': str,
            'weakness_indicators': List[str],
            'strength_indicators': List[str]
        }
        """
        if not Config.AI_API_KEY:
            # Fallback analysis without AI
            return AnswerAnalyzer._basic_analysis(question, answer, interview_state)
        
        try:
            client = get_openai_client()
            
            # Build context from conversation history
            history_context = ""
            if conversation_history:
                history_context = "\n\nPrevious Q&A Context:\n"
                for msg in conversation_history[-5:]:  # Last 5 messages
                    if msg.get('type') == 'question':
                        history_context += f"Q: {msg.get('content', '')[:150]}\n"
                    elif msg.get('type') == 'answer':
                        history_context += f"A: {msg.get('content', '')[:150]}\n"
            
            # Build claims context
            claims_context = ""
            if interview_state.claims_made:
                claims_context = "\n\nPrevious Claims Made by Candidate:\n"
                for i, claim in enumerate(interview_state.claims_made[-5:], 1):
                    claims_context += f"{i}. {claim[:100]}\n"
            
            prompt = f"""You are analyzing a candidate's answer in a {interview_state.interview_type} interview.

Current Topic: {interview_state.current_topic or 'General'}
Difficulty Level: {interview_state.difficulty_level}/5
{history_context}
{claims_context}

Question: {question}

Answer: {answer}

Analyze this answer comprehensively and return ONLY a valid JSON object with this exact structure:
{{
    "score": 0.75,
    "confidence": 0.7,
    "depth": 0.6,
    "clarity": 0.8,
    "correctness": 0.7,
    "topics_detected": ["OOP", "Java"],
    "claims_made": ["Worked on microservices", "Used Spring Boot"],
    "contradiction_detected": false,
    "contradiction_details": "",
    "needs_follow_up": true,
    "follow_up_reason": "Answer lacks depth - needs example",
    "weakness_indicators": ["Vague explanation", "No examples"],
    "strength_indicators": ["Correct concept", "Good structure"]
}}

Guidelines:
- All scores are 0-1 (0.0 to 1.0)
- topics_detected: Extract technical topics/concepts mentioned
- claims_made: Extract specific claims, examples, or experiences mentioned
- contradiction_detected: Compare with previous claims/answers
- needs_follow_up: True if answer needs clarification, examples, or deeper exploration
- weakness_indicators: List specific weaknesses
- strength_indicators: List specific strengths

Return ONLY the JSON object, no other text."""

            response = client.chat_completion(
                model=Config.AI_MODEL or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert interview answer analyzer. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse JSON response
            content = response.get('content', '').strip()
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            analysis = json.loads(content)
            
            # Validate and normalize scores
            for key in ['score', 'confidence', 'depth', 'clarity', 'correctness']:
                if key in analysis:
                    analysis[key] = max(0.0, min(1.0, float(analysis[key])))
            
            return analysis
            
        except (OpenAIError, json.JSONDecodeError, Exception) as e:
            print(f"[Adaptive Interview] Error in answer analysis: {e}")
            return AnswerAnalyzer._basic_analysis(question, answer, interview_state)
    
    @staticmethod
    def _basic_analysis(question: str, answer: str, interview_state: InterviewState) -> Dict:
        """Fallback basic analysis without AI"""
        answer_lower = answer.lower()
        answer_length = len(answer.split())
        
        # Basic heuristics
        score = min(1.0, answer_length / 100)  # Rough estimate
        confidence = 0.5  # Default
        depth = min(1.0, answer_length / 150)
        clarity = 0.7 if answer_length > 30 else 0.4
        correctness = 0.6  # Default
        
        needs_follow_up = answer_length < 30
        follow_up_reason = "Answer is too short" if needs_follow_up else ""
        
        return {
            'score': score,
            'confidence': confidence,
            'depth': depth,
            'clarity': clarity,
            'correctness': correctness,
            'topics_detected': [],
            'claims_made': [],
            'contradiction_detected': False,
            'contradiction_details': '',
            'needs_follow_up': needs_follow_up,
            'follow_up_reason': follow_up_reason,
            'weakness_indicators': ['Basic analysis only'],
            'strength_indicators': []
        }


class DecisionEngine:
    """
    Decision Engine
    Decides what action to take next based on interview state and answer analysis
    """
    
    @staticmethod
    def decide_next_action(interview_state: InterviewState, analysis: Dict) -> Dict:
        """
        Decide what to do next based on state and analysis
        
        Returns:
        {
            'action': str,  # 'follow_up', 'increase_difficulty', 'decrease_difficulty', 
                           # 'change_topic', 'go_deeper', 'clarify_contradiction', 'next_question'
            'reason': str,
            'new_topic': str (optional),
            'new_difficulty': int (optional),
            'follow_up_type': str (optional)  # 'depth', 'example', 'clarification'
        }
        """
        # Check for contradictions first
        if analysis.get('contradiction_detected'):
            return {
                'action': 'clarify_contradiction',
                'reason': analysis.get('contradiction_details', 'Contradiction detected'),
                'follow_up_type': 'clarification'
            }
        
        # Check if follow-up is needed
        if analysis.get('needs_follow_up') and interview_state.follow_up_count < interview_state.max_follow_ups:
            follow_up_reason = analysis.get('follow_up_reason', '')
            
            # Determine follow-up type
            if 'depth' in follow_up_reason.lower() or 'example' in follow_up_reason.lower():
                follow_up_type = 'example'
            elif 'clarif' in follow_up_reason.lower():
                follow_up_type = 'clarification'
            else:
                follow_up_type = 'depth'
            
            return {
                'action': 'follow_up',
                'reason': follow_up_reason,
                'follow_up_type': follow_up_type
            }
        
        # Check if candidate is struggling (low scores)
        if analysis.get('score', 0.5) < 0.4:
            # Decrease difficulty or change to easier topic
            if interview_state.difficulty_level > 1:
                return {
                    'action': 'decrease_difficulty',
                    'reason': 'Candidate struggling with current difficulty',
                    'new_difficulty': max(1, interview_state.difficulty_level - 1)
                }
            else:
                # Already at easiest, change topic
                return DecisionEngine._decide_topic_change(interview_state, analysis)
        
        # Check if candidate is excelling (high scores)
        if analysis.get('score', 0.5) > 0.8 and analysis.get('depth', 0.5) > 0.7:
            # Increase difficulty or go deeper
            if interview_state.difficulty_level < 5:
                return {
                    'action': 'increase_difficulty',
                    'reason': 'Candidate performing well, increasing challenge',
                    'new_difficulty': min(5, interview_state.difficulty_level + 1)
                }
            else:
                # Already at hardest, go deeper or change topic
                return {
                    'action': 'go_deeper',
                    'reason': 'Candidate excelling, exploring topic in more depth'
                }
        
        # Check if we've asked too many follow-ups on this topic
        if interview_state.follow_up_count >= interview_state.max_follow_ups:
            return DecisionEngine._decide_topic_change(interview_state, analysis)
        
        # Default: move to next question
        return {
            'action': 'next_question',
            'reason': 'Continue with next question'
        }
    
    @staticmethod
    def _decide_topic_change(interview_state: InterviewState, analysis: Dict) -> Dict:
        """Decide which topic to change to"""
        # Identify weak areas that need more coverage
        weak_areas = interview_state.weak_areas
        if weak_areas and len(weak_areas) > 0:
            # Pick a weak area that hasn't been covered recently
            for topic in weak_areas:
                if topic not in interview_state.topics_covered[-3:]:  # Not in last 3 topics
                    return {
                        'action': 'change_topic',
                        'reason': f'Exploring weak area: {topic}',
                        'new_topic': topic
                    }
        
        # If no weak areas, pick from resume/JD skills
        if interview_state.resume_data:
            skills = interview_state.resume_data.get('skills', [])
            programming_languages = interview_state.resume_data.get('programming_languages', [])
            
            # Combine and pick one not recently covered
            all_topics = (skills[:5] + programming_languages[:3])
            for topic in all_topics:
                if topic not in interview_state.topics_covered[-3:]:
                    return {
                        'action': 'change_topic',
                        'reason': f'Exploring skill: {topic}',
                        'new_topic': topic
                    }
        
        # Default: continue with current topic or general
        return {
            'action': 'next_question',
            'reason': 'Continue interview flow',
            'new_topic': interview_state.current_topic or 'General'
        }


class MemoryLayer:
    """
    Memory Layer
    Stores and retrieves conversation context, claims, examples, and contradictions
    """
    
    @staticmethod
    def extract_claims(answer: str, analysis: Dict) -> List[str]:
        """Extract claims, examples, and experiences from answer"""
        claims = []
        
        # Use AI-extracted claims if available
        if 'claims_made' in analysis:
            claims.extend(analysis['claims_made'])
        
        # Also extract from answer text (simple pattern matching)
        answer_lower = answer.lower()
        
        # Patterns that indicate claims
        claim_patterns = [
            r'i (?:worked|developed|built|created|implemented|designed)',
            r'i (?:have|had) (?:experience|worked)',
            r'in my (?:previous|last|current) (?:project|job|role)',
            r'we (?:built|developed|created)',
            r'using (?:technologies|tools|frameworks) (?:like|such as)',
        ]
        
        import re
        for pattern in claim_patterns:
            matches = re.finditer(pattern, answer_lower)
            for match in matches:
                # Extract sentence containing the claim
                start = max(0, match.start() - 50)
                end = min(len(answer), match.end() + 100)
                claim = answer[start:end].strip()
                if len(claim) > 20:  # Meaningful claim
                    claims.append(claim)
        
        return list(set(claims))  # Remove duplicates
    
    @staticmethod
    def detect_contradictions(new_answer: str, new_claims: List[str], 
                              interview_state: InterviewState) -> Tuple[bool, str]:
        """
        Detect contradictions between new answer and previous claims/answers
        
        Returns: (contradiction_detected: bool, details: str)
        """
        if not Config.AI_API_KEY:
            return False, ""
        
        try:
            client = get_openai_client()
            
            # Build previous claims context
            previous_context = ""
            if interview_state.claims_made:
                previous_context = "\n\nPrevious Claims Made:\n"
                for i, claim in enumerate(interview_state.claims_made[-5:], 1):
                    previous_context += f"{i}. {claim}\n"
            
            if interview_state.answer_history:
                previous_context += "\n\nPrevious Answers:\n"
                for i, ans in enumerate(interview_state.answer_history[-3:], 1):
                    previous_context += f"Answer {i}: {ans[:200]}\n"
            
            if not previous_context:
                return False, ""
            
            prompt = f"""Analyze if the new answer contradicts previous claims or answers.

{previous_context}

New Answer: {new_answer}
New Claims: {', '.join(new_claims) if new_claims else 'None'}

Determine if there are contradictions. Return ONLY a JSON object:
{{
    "contradiction_detected": true/false,
    "details": "Specific contradiction explanation or empty string"
}}

Return ONLY the JSON object, no other text."""

            response = client.chat_completion(
                model=Config.AI_MODEL or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You detect contradictions in interview answers. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            
            content = response.get('content', '').strip()
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            return result.get('contradiction_detected', False), result.get('details', '')
            
        except Exception as e:
            print(f"[Adaptive Interview] Error detecting contradictions: {e}")
            return False, ""


class TopicFlowController:
    """
    Topic Flow Controller
    Manages topic transitions, progression, and coverage
    """
    
    @staticmethod
    def initialize_topics(interview_state: InterviewState) -> List[str]:
        """Initialize topic list from resume and JD"""
        topics = []
        
        # From resume
        if interview_state.resume_data:
            topics.extend(interview_state.resume_data.get('skills', [])[:5])
            topics.extend(interview_state.resume_data.get('programming_languages', [])[:3])
        
        # From JD
        if interview_state.jd_data:
            topics.extend(interview_state.jd_data.get('required_skills', [])[:5])
            topics.extend(interview_state.jd_data.get('missing_skills', [])[:3])  # Important to cover
        
        # Remove duplicates and return
        return list(set(topics))
    
    @staticmethod
    def select_next_topic(interview_state: InterviewState, analysis: Dict) -> Optional[str]:
        """Select next topic based on performance and coverage"""
        all_topics = TopicFlowController.initialize_topics(interview_state)
        
        if not all_topics:
            return None
        
        # Priority 1: Weak areas that need more coverage
        for weak_area in interview_state.weak_areas:
            if weak_area in all_topics and weak_area not in interview_state.topics_covered[-2:]:
                return weak_area
        
        # Priority 2: Missing skills from JD (important gaps)
        if interview_state.jd_data:
            missing_skills = interview_state.jd_data.get('missing_skills', [])
            for skill in missing_skills:
                if skill in all_topics and skill not in interview_state.topics_covered[-2:]:
                    return skill
        
        # Priority 3: Uncovered topics
        for topic in all_topics:
            if topic not in interview_state.topics_covered:
                return topic
        
        # Priority 4: Topics detected in current answer (natural progression)
        detected_topics = analysis.get('topics_detected', [])
        for topic in detected_topics:
            if topic in all_topics:
                return topic
        
        # Default: Return first available topic
        return all_topics[0] if all_topics else None


class AdaptiveQuestionGenerator:
    """
    Adaptive Question Generator
    Generates questions based on interview state, not just phase/number
    """
    
    @staticmethod
    def generate_adaptive_question(interview_state: InterviewState, decision: Dict,
                                  conversation_history: List[Dict] = None) -> str:
        """
        Generate adaptive question based on state and decision
        
        Args:
            interview_state: Current interview state
            decision: Decision from DecisionEngine
            conversation_history: Previous Q&A pairs
        
        Returns:
            Generated question string
        """
        if not Config.AI_API_KEY:
            return AdaptiveQuestionGenerator._fallback_question(interview_state, decision)
        
        try:
            client = get_openai_client()
            
            # Build state context
            state_context = f"""
Interview State:
- Current Topic: {interview_state.current_topic or 'General'}
- Difficulty Level: {interview_state.difficulty_level}/5
- Candidate Confidence: {interview_state.confidence_score:.2f}
- Weak Areas: {', '.join(interview_state.weak_areas[:3]) if interview_state.weak_areas else 'None'}
- Strong Areas: {', '.join(interview_state.strong_areas[:3]) if interview_state.strong_areas else 'None'}
- Topics Covered: {', '.join(interview_state.topics_covered[-5:]) if interview_state.topics_covered else 'None'}
- Total Questions: {interview_state.total_questions}
"""
            
            # Build decision context
            decision_context = f"""
Decision: {decision['action']}
Reason: {decision['reason']}
"""
            if 'new_topic' in decision:
                decision_context += f"New Topic: {decision['new_topic']}\n"
            if 'new_difficulty' in decision:
                decision_context += f"New Difficulty: {decision['new_difficulty']}/5\n"
            if 'follow_up_type' in decision:
                decision_context += f"Follow-up Type: {decision['follow_up_type']}\n"
            
            # Build conversation history
            history_context = ""
            if conversation_history:
                history_context = "\n\nRecent Conversation:\n"
                for msg in conversation_history[-3:]:  # Last 3 Q&A pairs
                    if msg.get('type') == 'question':
                        history_context += f"Q: {msg.get('content', '')[:100]}\n"
                    elif msg.get('type') == 'answer':
                        history_context += f"A: {msg.get('content', '')[:100]}\n"
            
            # Build claims context for follow-ups
            claims_context = ""
            if decision['action'] == 'clarify_contradiction' and interview_state.claims_made:
                claims_context = "\n\nPrevious Claims (for contradiction clarification):\n"
                for claim in interview_state.claims_made[-3:]:
                    claims_context += f"- {claim[:100]}\n"
            
            prompt = f"""You are a professional {interview_state.interview_type} interviewer conducting an adaptive interview.

{state_context}
{decision_context}
{history_context}
{claims_context}

Generate the NEXT question based on the decision and state.

Guidelines:
- If action is 'follow_up': Ask a follow-up that addresses the reason (depth, example, clarification)
- If action is 'clarify_contradiction': Ask a clarifying question about the contradiction
- If action is 'increase_difficulty': Ask a more challenging question on the same topic
- If action is 'decrease_difficulty': Ask an easier question or switch to a simpler subtopic
- If action is 'change_topic': Transition naturally to the new topic
- If action is 'go_deeper': Ask a deeper, more advanced question on the current topic
- If action is 'next_question': Continue with appropriate next question

Make the question:
- Natural and conversational (not robotic)
- Appropriate for the difficulty level
- Contextually aware of previous conversation
- Professional and interview-appropriate

Return ONLY the question text, no prefixes, no explanations."""

            response = client.chat_completion(
                model=Config.AI_MODEL or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional interviewer. Generate natural, adaptive interview questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            question = response.get('content', '').strip()
            # Clean up any formatting
            question = question.replace('"', '').replace("'", '').strip()
            if question.startswith('Q:'):
                question = question[2:].strip()
            
            return question
            
        except Exception as e:
            print(f"[Adaptive Interview] Error generating question: {e}")
            return AdaptiveQuestionGenerator._fallback_question(interview_state, decision)
    
    @staticmethod
    def _fallback_question(interview_state: InterviewState, decision: Dict) -> str:
        """Fallback question generation without AI"""
        topic = decision.get('new_topic') or interview_state.current_topic or 'programming'
        action = decision.get('action', 'next_question')
        
        if action == 'follow_up':
            return f"Can you provide more details or an example about {topic}?"
        elif action == 'clarify_contradiction':
            return "Can you clarify this point? There seems to be a contradiction with what you mentioned earlier."
        elif action == 'increase_difficulty':
            return f"Let's go deeper. Can you explain advanced concepts in {topic}?"
        elif action == 'change_topic':
            return f"Let's move to {topic}. Can you tell me about your experience with {topic}?"
        else:
            return f"Tell me about {topic}."


def update_interview_state(interview_state: InterviewState, question: str, answer: str, 
                           analysis: Dict, decision: Dict):
    """
    Update interview state after processing an answer
    
    This is the core state update function that maintains the interview brain
    """
    # Update question and answer history
    interview_state.question_history.append(question)
    interview_state.answer_history.append(answer)
    interview_state.evaluation_history.append(analysis)
    interview_state.total_questions += 1
    
    # Update confidence score (weighted average)
    new_confidence = analysis.get('confidence', interview_state.confidence_score)
    interview_state.confidence_score = (interview_state.confidence_score * 0.7) + (new_confidence * 0.3)
    
    # Extract and store claims
    claims = MemoryLayer.extract_claims(answer, analysis)
    interview_state.claims_made.extend(claims)
    
    # Update topics detected
    topics_detected = analysis.get('topics_detected', [])
    for topic in topics_detected:
        if topic not in interview_state.topics_covered:
            interview_state.topics_covered.append(topic)
    
    # Update weak/strong areas based on scores
    score = analysis.get('score', 0.5)
    if score < 0.4:
        # Weak performance
        if interview_state.current_topic and interview_state.current_topic not in interview_state.weak_areas:
            interview_state.weak_areas.append(interview_state.current_topic)
    elif score > 0.8:
        # Strong performance
        if interview_state.current_topic and interview_state.current_topic not in interview_state.strong_areas:
            interview_state.strong_areas.append(interview_state.current_topic)
    
    # Update contradictions
    if analysis.get('contradiction_detected'):
        contradiction = {
            'question': question,
            'answer': answer,
            'details': analysis.get('contradiction_details', '')
        }
        interview_state.contradictions.append(contradiction)
    
    # Update difficulty if changed
    if 'new_difficulty' in decision:
        interview_state.difficulty_level = decision['new_difficulty']
    
    # Update topic if changed
    if 'new_topic' in decision:
        old_topic = interview_state.current_topic
        interview_state.current_topic = decision['new_topic']
        interview_state.topic_progression.append({
            'from': old_topic,
            'to': decision['new_topic'],
            'question_number': interview_state.total_questions,
            'reason': decision.get('reason', '')
        })
        interview_state.follow_up_count = 0  # Reset follow-up count for new topic
        interview_state.current_topic_start_question = interview_state.total_questions
    else:
        # Same topic, increment follow-up count if it was a follow-up
        if decision.get('action') == 'follow_up':
            interview_state.follow_up_count += 1
