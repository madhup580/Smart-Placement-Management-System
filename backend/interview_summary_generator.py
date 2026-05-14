"""
Interview Summary Generator
Generates professional interview summary reports with hire probability and improvement roadmap
"""

import json
from typing import Dict, List, Optional
import openai
from config import Config

# Initialize OpenAI client
try:
    client = openai.OpenAI(api_key=Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None
except Exception as e:
    print(f"[InterviewSummary] OpenAI client initialization error: {e}")
    client = None


def generate_interview_summary(interview_memory: Dict) -> Dict:
    """
    Generate professional interview summary report
    
    Returns:
    {
        "candidate_level": "",
        "strengths": [],
        "weaknesses": [],
        "communication_quality": "",
        "learning_ability": "",
        "hire_probability": 0,
        "improvement_roadmap": []
    }
    """
    if not client:
        return _fallback_summary(interview_memory)
    
    try:
        # Extract key metrics from memory
        answers = interview_memory.get("answers", [])
        asked_questions = interview_memory.get("asked_questions", [])
        strong_topics = interview_memory.get("strong_topics", [])
        weak_topics = interview_memory.get("weak_topics", [])
        contradictions = interview_memory.get("contradictions", [])
        confidence_score = interview_memory.get("confidence_score", 0.5)
        candidate_level = interview_memory.get("candidate_level", "junior")
        
        # Calculate average scores
        if answers:
            avg_correctness = sum(ans.get("analysis", {}).get("correctness", 0.5) for ans in answers) / len(answers)
            avg_depth = sum(ans.get("analysis", {}).get("conceptual_depth", 0.5) for ans in answers) / len(answers)
            avg_clarity = sum(ans.get("analysis", {}).get("clarity", 0.5) for ans in answers) / len(answers)
        else:
            avg_correctness = avg_depth = avg_clarity = 0.5
        
        prompt = f"""
You are an interview evaluation expert analyzing a completed technical interview.

INTERVIEW MEMORY DATA:
{json.dumps(interview_memory, indent=2)}

KEY METRICS:
- Candidate Level: {candidate_level}
- Average Correctness: {avg_correctness:.2f}
- Average Conceptual Depth: {avg_depth:.2f}
- Average Clarity: {avg_clarity:.2f}
- Confidence Score: {confidence_score:.2f}
- Strong Topics: {', '.join(strong_topics)}
- Weak Topics: {', '.join(weak_topics)}
- Contradictions: {len(contradictions)}
- Total Questions: {len(asked_questions)}
- Total Answers: {len(answers)}

Generate a professional interview summary report. Provide a JSON response with:

{{
  "candidate_level": string,  // "junior", "mid", "senior", or "expert" based on overall performance
  "strengths": [string],  // List of technical strengths (3-5 items)
  "weaknesses": [string],  // List of technical weaknesses (3-5 items)
  "communication_quality": string,  // "excellent", "good", "average", or "needs improvement"
  "learning_ability": string,  // "fast learner", "moderate", or "slow" based on improvement trend
  "hire_probability": int,  // 0-100% probability of being hired
  "improvement_roadmap": [string]  // Bullet points for skill improvement (5-7 items)
}}

Evaluation Guidelines:
- Candidate Level: Based on correctness, depth, and consistency across topics
- Strengths: Technical areas where candidate performed well
- Weaknesses: Areas needing improvement
- Communication Quality: Based on clarity scores and answer structure
- Learning Ability: Based on improvement trend (if answers got better over time)
- Hire Probability: Overall assessment (0-100%)
- Improvement Roadmap: Actionable, specific recommendations

Tone: Professional, neutral, recruiter-friendly, clear and concise.

Return ONLY valid JSON, no other text.
"""
        
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL or "gpt-4",
            messages=[
                {"role": "system", "content": "You are an interview evaluation expert. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        summary = json.loads(response.choices[0].message.content)
        
        # Validate and normalize
        summary["hire_probability"] = max(0, min(100, int(summary.get("hire_probability", 50))))
        summary["candidate_level"] = summary.get("candidate_level", candidate_level)
        
        # Ensure arrays
        for key in ["strengths", "weaknesses", "improvement_roadmap"]:
            if key not in summary or not isinstance(summary[key], list):
                summary[key] = []
        
        return summary
        
    except Exception as e:
        print(f"[InterviewSummary] Error: {e}")
        import traceback
        traceback.print_exc()
        return _fallback_summary(interview_memory)


def _fallback_summary(interview_memory: Dict) -> Dict:
    """Fallback summary if AI is unavailable"""
    answers = interview_memory.get("answers", [])
    strong_topics = interview_memory.get("strong_topics", [])
    weak_topics = interview_memory.get("weak_topics", [])
    candidate_level = interview_memory.get("candidate_level", "junior")
    
    # Calculate basic metrics
    if answers:
        avg_correctness = sum(ans.get("analysis", {}).get("correctness", 0.5) for ans in answers) / len(answers)
        avg_clarity = sum(ans.get("analysis", {}).get("clarity", 0.5) for ans in answers) / len(answers)
    else:
        avg_correctness = avg_clarity = 0.5
    
    # Determine hire probability (0-100)
    hire_probability = int((avg_correctness * 0.6 + avg_clarity * 0.4) * 100)
    
    # Determine communication quality
    if avg_clarity >= 0.8:
        comm_quality = "excellent"
    elif avg_clarity >= 0.6:
        comm_quality = "good"
    elif avg_clarity >= 0.4:
        comm_quality = "average"
    else:
        comm_quality = "needs improvement"
    
    return {
        "candidate_level": candidate_level,
        "strengths": strong_topics[:5] if strong_topics else ["No strong areas identified"],
        "weaknesses": weak_topics[:5] if weak_topics else ["No specific weaknesses identified"],
        "communication_quality": comm_quality,
        "learning_ability": "moderate",  # Default, would need trend analysis
        "hire_probability": hire_probability,
        "improvement_roadmap": [
            f"Focus on improving {topic}" for topic in weak_topics[:5]
        ] if weak_topics else ["Continue practicing interview questions"]
    }
