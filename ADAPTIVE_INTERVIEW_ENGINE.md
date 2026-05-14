# Adaptive Interview Engine

## Overview

The Adaptive Interview Engine transforms the linear question-answer flow into a stateful, decision-driven interview system that behaves like a human interviewer.

## Architecture

### 1. Interview State Object (`InterviewState`)

The brain of the interviewer that tracks:
- **Current Topic**: What topic is being discussed
- **Difficulty Level**: 1-5 scale (1=Easy, 5=Expert)
- **Confidence Score**: Candidate's overall confidence (0-1)
- **Weak Areas**: Topics where candidate struggles
- **Strong Areas**: Topics where candidate excels
- **Contradictions**: Detected contradictions in answers
- **Claims Made**: Specific claims/examples mentioned
- **Topics Covered**: History of topics discussed
- **Question/Answer History**: Full conversation context

### 2. Answer Analyzer (`AnswerAnalyzer`)

Comprehensive answer analysis that evaluates:
- **Score** (0-1): Overall answer quality
- **Confidence** (0-1): How confident the candidate sounds
- **Depth** (0-1): Technical depth and detail
- **Clarity** (0-1): Communication clarity
- **Correctness** (0-1): Technical accuracy
- **Topics Detected**: Technical topics mentioned
- **Claims Made**: Specific claims/examples extracted
- **Contradiction Detection**: Comparison with previous answers
- **Follow-up Needs**: Whether answer needs clarification

### 3. Decision Engine (`DecisionEngine`)

Decides what action to take next based on state and analysis:

| Condition | Action |
|-----------|--------|
| Contradiction detected | Ask clarification question |
| Low depth/score | Ask follow-up question |
| High confidence + depth | Increase difficulty |
| Low score | Decrease difficulty or change topic |
| Too many follow-ups | Change topic |
| Strong performance | Go deeper or increase difficulty |
| Weak topic identified | Change to weak area |

### 4. Memory Layer (`MemoryLayer`)

Stores and retrieves:
- **Claims Extraction**: Extracts specific claims, examples, experiences
- **Contradiction Detection**: Compares new answers with previous claims
- **Context Building**: Maintains conversation context

### 5. Topic Flow Controller (`TopicFlowController`)

Manages topic transitions:
- **Topic Initialization**: From resume and JD
- **Topic Selection**: Based on performance and coverage
- **Topic Progression**: Natural flow between topics

### 6. Adaptive Question Generator (`AdaptiveQuestionGenerator`)

Generates questions based on:
- Current interview state
- Decision from Decision Engine
- Conversation history
- Topic and difficulty level

## New Interview Flow

```
Ask Question
    ↓
Receive Answer
    ↓
Analyze Answer (AnswerAnalyzer)
    ↓
Detect Contradictions (MemoryLayer)
    ↓
Update Interview State
    ↓
Decide Next Action (DecisionEngine)
    ↓
Generate Adaptive Question (AdaptiveQuestionGenerator)
    ↓
Repeat
```

## Key Features

### ✅ Follow-up Questions
- Automatically asks follow-ups when answers lack depth
- Follow-up types: depth, example, clarification
- Max 2 follow-ups per topic before moving on

### ✅ Dynamic Difficulty Adjustment
- Increases difficulty when candidate excels
- Decreases difficulty when candidate struggles
- Adapts in real-time (1-5 scale)

### ✅ Contradiction Detection
- Compares new answers with previous claims
- Asks clarifying questions when contradictions detected
- Maintains memory of all claims made

### ✅ Topic Transitions
- Natural topic flow based on performance
- Prioritizes weak areas for coverage
- Covers missing skills from JD
- Tracks topic progression

### ✅ Memory & Context
- Remembers all previous answers
- Tracks claims and examples
- Maintains full conversation context
- Can reference earlier answers: "Earlier you mentioned X, but now you said Y..."

## State Update Process

After each answer:

1. **Extract Claims**: Identify specific claims/examples
2. **Detect Contradictions**: Compare with previous claims
3. **Update Performance**: Update weak/strong areas
4. **Update Confidence**: Weighted average of confidence scores
5. **Update Topics**: Track topics detected and covered
6. **Update Difficulty**: Adjust based on performance
7. **Update Topic**: Change topic if needed

## API Response Format

The `/api/interview/submit-answer` endpoint now returns:

```json
{
    "session_id": 123,
    "feedback": "...",
    "scores": {
        "correctness": 7.5,
        "clarity": 8.0,
        "depth": 6.5,
        "confidence": 7.0,
        "overall": 7.25
    },
    "contradiction_detected": false,
    "difficulty_level": "Medium",
    "follow_up_needed": true,
    "follow_up_reason": "Answer lacks depth - needs example",
    "next_question": "Can you provide a specific example?",
    "adaptive_metadata": {
        "action": "follow_up",
        "reason": "Answer lacks depth - needs example",
        "current_topic": "Java",
        "difficulty_level": 2,
        "confidence_score": 0.65,
        "weak_areas": ["OOP", "Collections"],
        "strong_areas": ["Basic Syntax"]
    }
}
```

## Benefits

### Before (Linear)
- ❌ Form-like experience
- ❌ Static questions
- ❌ No memory
- ❌ Same for all candidates
- ❌ Predictable flow

### After (Adaptive)
- ✅ Human-like conversation
- ✅ Adaptive questions
- ✅ Full context awareness
- ✅ Personalized experience
- ✅ Dynamic flow

## Implementation Files

- `backend/utils/adaptive_interview_engine.py` - Core adaptive engine
- `backend/routes/interview.py` - Integration with API routes

## Usage

The adaptive engine is automatically used when submitting answers. No changes needed in frontend - it works seamlessly with existing API.

## Example Scenarios

### Scenario 1: Weak Answer
1. Candidate gives vague answer
2. **Analysis**: Low depth (0.3), needs follow-up
3. **Decision**: Follow-up (example type)
4. **Question**: "Can you provide a specific example of when you used this?"

### Scenario 2: Strong Answer
1. Candidate gives excellent answer with examples
2. **Analysis**: High score (0.9), high depth (0.85)
3. **Decision**: Increase difficulty
4. **Question**: More challenging question on same topic

### Scenario 3: Contradiction
1. Candidate says "I have 5 years experience with Java"
2. Later says "I'm new to Java"
3. **Analysis**: Contradiction detected
4. **Decision**: Clarify contradiction
5. **Question**: "Earlier you mentioned 5 years of Java experience, but now you said you're new to Java. Can you clarify?"

### Scenario 4: Topic Transition
1. Candidate struggles with OOP (low scores)
2. **Analysis**: Weak area identified
3. **Decision**: Change topic to explore weak area
4. **Question**: Question about OOP fundamentals

## Performance

- **Latency**: < 2 seconds per answer analysis
- **Memory**: Efficient state management
- **Scalability**: Stateless API with state in database
- **Accuracy**: AI-powered analysis with fallbacks

## Future Enhancements

- Real-time difficulty visualization
- Topic coverage visualization
- Performance trends
- Adaptive interview length
- Multi-topic questions
