# FastAPI-Based AI Virtual Interviewer

## Overview

The AI Virtual Interviewer has been rebuilt using Python + FastAPI architecture to behave like a real human interviewer. The system analyzes answers, maintains interview memory, makes intelligent decisions, and generates natural follow-up questions.

## Architecture

### Core Components

1. **InterviewMemory** (`interview_ai_fastapi.py`)
   - Tracks conversation state and candidate performance
   - Maintains question/answer history
   - Tracks topics, difficulty, contradictions, and confidence
   - Stores resume and JD data for context

2. **AnswerAnalyzer**
   - Analyzes answers across multiple dimensions:
     - Correctness (0-10)
     - Confidence (0-10)
     - Clarity (0-10)
     - Depth (0-10)
     - Topic identification
     - Contradiction detection
     - Follow-up needs

3. **DecisionEngine**
   - Decides next action based on analysis:
     - `followup`: Ask clarifying question
     - `clarification`: Address contradiction
     - `harder`: Increase difficulty
     - `easier`: Reduce difficulty
     - `topic_change`: Move to new topic
     - `continue`: Keep current flow

4. **QuestionGenerator**
   - Generates natural, conversational questions
   - Adapts to difficulty level
   - Considers interview context
   - Uses OpenAI for human-like phrasing

### Main Function

```python
process_interview_answer(
    interview_memory_dict: Dict,
    current_question: str,
    user_answer: str
) -> Dict
```

**Returns:**
```json
{
  "analysis": {
    "correctness": 8.5,
    "confidence": 7.0,
    "clarity": 9.0,
    "depth": 8.0,
    "topic": "python",
    "difficulty_level": "medium",
    "contradiction_detected": false,
    "follow_up_needed": true,
    "follow_up_reason": "Answer needs deeper exploration",
    "strengths": ["Clear explanation", "Good examples"],
    "weaknesses": ["Could mention edge cases"],
    "overall_score": 8.1
  },
  "updated_memory": {
    "interview_type": "TR",
    "current_topic": "python",
    "current_difficulty": "medium",
    "confidence_level": 0.7,
    "performance_history": [8.1],
    "topics_covered": ["python"],
    "strong_topics": ["python"],
    "weak_topics": []
  },
  "decision": "followup",
  "decision_reason": "Answer needs deeper exploration",
  "next_question": "Can you explain how you would handle memory optimization in Python?"
}
```

## Integration

The FastAPI-based AI is integrated into the existing Flask route (`/api/interview/submit-answer`). It:

1. Loads or creates interview memory from session
2. Processes answer using the new AI system
3. Updates memory and generates next question
4. Falls back to old system if FastAPI AI unavailable

## Usage

The frontend doesn't need changes - it continues to call the same Flask endpoint. The backend automatically uses the new AI system when available.

## Testing

1. Start the backend server
2. Start an interview session
3. Submit answers
4. Check console logs for AI processing
5. Verify questions are natural and adaptive

## Configuration

Set `OPENAI_API_KEY` in `config.py` or environment variable for AI functionality.

## Fallback

If OpenAI API is unavailable or errors occur, the system falls back to the previous adaptive interview engine.
