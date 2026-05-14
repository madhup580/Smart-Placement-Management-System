"""
FastAPI Routes for AI Virtual Interview
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from datetime import datetime

from interview_ai_fastapi import process_interview_answer, InterviewMemory
from models import db, InterviewSession, InterviewAnswer, InterviewResult
from utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/interview", tags=["Interview"])
security = HTTPBearer()


class StartInterviewRequest(BaseModel):
    interview_type: str  # 'TR' or 'HR'
    resume_text: Optional[str] = None
    job_description: Optional[str] = None
    resume_data: Optional[Dict] = None
    jd_data: Optional[Dict] = None
    selfie_session_id: Optional[int] = None


class SubmitAnswerRequest(BaseModel):
    session_id: int
    question: str
    answer: str
    time_taken_seconds: int = 0
    interview_memory: Dict  # Current interview memory object


class SubmitAnswerResponse(BaseModel):
    analysis: Dict
    updated_memory: Dict
    decision: str
    decision_reason: str
    next_question: str
    question_number: int
    total_questions: int
    interview_completed: bool = False


@router.post("/start")
async def start_interview(
    request: StartInterviewRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Start a new interview session
    """
    try:
        # Get current user (implement your auth logic)
        # user = await get_current_user(credentials.credentials)
        # For now, using placeholder
        user_id = 1  # Replace with actual user from token
        
        # Create interview memory
        interview_memory = InterviewMemory(
            interview_type=request.interview_type,
            resume_data=request.resume_data or {},
            jd_data=request.jd_data or {}
        )
        interview_memory.start_time = datetime.utcnow()
        
        # Generate first question
        from interview_ai_fastapi import QuestionGenerator
        
        # Create initial decision for first question
        initial_decision = {
            "decision": "continue",
            "reason": "Starting interview",
            "priority": "low"
        }
        
        first_question = QuestionGenerator.generate_next_question(
            decision=initial_decision,
            interview_memory=interview_memory,
            analysis={}  # No previous analysis for first question
        )
        
        # Create session in database
        session = InterviewSession(
            user_id=user_id,
            interview_type=request.interview_type,
            resume_text=request.resume_text or "",
            job_description=request.job_description or "",
            question_number=1,
            total_questions=6,
            conversation=json.dumps([{
                "type": "question",
                "content": first_question,
                "phase": "introduction",
                "timestamp": datetime.utcnow().isoformat()
            }]),
            interview_state=json.dumps(interview_memory.to_dict())
        )
        
        db.session.add(session)
        db.session.commit()
        
        return {
            "session_id": session.id,
            "question": first_question,
            "question_number": 1,
            "total_questions": 6,
            "interview_memory": interview_memory.to_dict()
        }
        
    except Exception as e:
        db.session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    request: SubmitAnswerRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Submit answer and get next question
    Returns: analysis, updated_memory, decision, next_question
    """
    try:
        # Get current user
        # user = await get_current_user(credentials.credentials)
        user_id = 1  # Replace with actual user from token
        
        # Get session
        session = InterviewSession.query.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if session.is_completed:
            raise HTTPException(status_code=400, detail="Interview already completed")
        
        # Process answer using AI
        result = process_interview_answer(
            interview_memory_dict=request.interview_memory,
            current_question=request.question,
            user_answer=request.answer
        )
        
        # Save answer to database
        interview_answer = InterviewAnswer(
            session_id=request.session_id,
            question_number=session.question_number,
            question=request.question,
            answer=request.answer,
            phase=result["updated_memory"].get("current_phase", "introduction"),
            correctness_score=result["analysis"].get("correctness", 5.0),
            clarity_score=result["analysis"].get("clarity", 5.0),
            confidence_score=result["analysis"].get("confidence", 5.0) / 10.0,
            overall_score=result["analysis"].get("overall_score", 5.0),
            feedback=json.dumps(result["analysis"]),
            time_taken_seconds=request.time_taken_seconds,
            depth_score=result["analysis"].get("depth", 5.0),
            contradiction_detected=result["analysis"].get("contradiction_detected", False),
            difficulty_level=result["updated_memory"].get("current_difficulty", "medium"),
            follow_up_needed=result["analysis"].get("follow_up_needed", False),
            follow_up_reason=result["analysis"].get("follow_up_reason", "")
        )
        
        db.session.add(interview_answer)
        
        # Update conversation
        conversation = json.loads(session.conversation) if session.conversation else []
        conversation.append({
            "type": "answer",
            "content": request.answer,
            "timestamp": datetime.utcnow().isoformat()
        })
        conversation.append({
            "type": "question",
            "content": result["next_question"],
            "phase": result["updated_memory"].get("current_phase", "introduction"),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Update session
        session.conversation = json.dumps(conversation)
        session.interview_state = json.dumps(result["updated_memory"])
        session.question_number += 1
        session.total_questions_asked += 1
        
        # Check if interview should complete
        interview_completed = (
            session.question_number > session.total_questions or
            result["updated_memory"].get("question_count", 0) >= result["updated_memory"].get("total_questions", 6)
        )
        
        if interview_completed:
            session.is_completed = True
            # Create result (simplified)
            # In production, calculate final scores from all answers
        
        db.session.commit()
        
        return SubmitAnswerResponse(
            analysis=result["analysis"],
            updated_memory=result["updated_memory"],
            decision=result["decision"],
            decision_reason=result.get("decision_reason", ""),
            next_question=result["next_question"],
            question_number=session.question_number,
            total_questions=session.total_questions,
            interview_completed=interview_completed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
