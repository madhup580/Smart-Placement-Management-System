"""
Leaderboard calculation utilities
"""
from models import Leaderboard, User, CodeSubmission, QuizAttempt, InterviewSession, db
from sqlalchemy import func

def update_leaderboard(user_id):
    """Update leaderboard entry for a user - using normalized Placement Readiness Score (0-100)"""
    user = User.query.get(user_id)
    if not user or user.role != 'student':
        return
    
    # Calculate normalized scores (0-100) similar to Placement Readiness Score
    
    # 1. Calculate Code Practice Score (percentage based on test cases passed)
    coding_submissions = CodeSubmission.query.filter_by(user_id=user_id).all()
    code_practice_scores = []
    total_submissions = len(coding_submissions)
    correct_submissions = 0
    
    for submission in coding_submissions:
        if submission.status == 'accepted':
            correct_submissions += 1
        if (submission.total_test_cases and submission.total_test_cases > 0 and 
            submission.test_cases_passed is not None):
            percentage = (submission.test_cases_passed / submission.total_test_cases) * 100
            code_practice_scores.append(percentage)
    
    code_practice_score = sum(code_practice_scores) / len(code_practice_scores) if code_practice_scores else 0
    
    # 2. Calculate Non-Technical Score (average of quiz scores, already percentages)
    quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).all()
    non_technical_scores = []
    for attempt in quiz_attempts:
        if attempt.score is not None and attempt.score >= 0:
            non_technical_scores.append(attempt.score)
    
    non_technical_score = sum(non_technical_scores) / len(non_technical_scores) if non_technical_scores else 0
    
    # 3. Calculate AI Virtual Interview Score (from completed interviews)
    completed_interviews = InterviewSession.query.filter_by(
        user_id=user_id, 
        is_completed=True
    ).all()
    interview_scores = []
    for interview in completed_interviews:
        if interview.final_score is not None:
            interview_scores.append(interview.final_score)
    interview_score = sum(interview_scores) / len(interview_scores) if interview_scores else 0
    
    # Calculate overall Placement Readiness Score (simple average) - normalized to 0-100
    # Formula: (Code Practice + Non-Technical + AI Interview) / 3
    # Always include all 3 components, even if score is 0
    total_score = (code_practice_score + non_technical_score + interview_score) / 3
    
    # Calculate accuracy
    accuracy = (correct_submissions / total_submissions * 100) if total_submissions > 0 else 0
    
    # Store raw scores for reference (but use normalized total_score for ranking)
    # Calculate raw coding score for reference
    raw_coding_score = 0
    for submission in coding_submissions:
        if submission.status == 'accepted':
            question = submission.question
            if question:
                base_score = 10 if question.difficulty == 'easy' else (20 if question.difficulty == 'medium' else 30)
                efficiency_bonus = max(0, 10 - submission.execution_time) if submission.execution_time else 0
                raw_coding_score += base_score + efficiency_bonus
    
    raw_quiz_score = sum(attempt.score for attempt in quiz_attempts)  # This is already percentage, but keep for reference
    
    # Update or create leaderboard entry
    leaderboard_entry = Leaderboard.query.filter_by(user_id=user_id).first()
    if not leaderboard_entry:
        leaderboard_entry = Leaderboard(user_id=user_id)
        db.session.add(leaderboard_entry)
    
    # Store normalized score (0-100) as total_score
    leaderboard_entry.total_score = round(total_score, 2)
    leaderboard_entry.coding_score = round(code_practice_score, 2)  # Normalized percentage
    leaderboard_entry.quiz_score = round(non_technical_score, 2)  # Normalized percentage
    leaderboard_entry.accuracy = round(accuracy, 2)
    leaderboard_entry.total_submissions = total_submissions
    leaderboard_entry.total_quizzes = len(quiz_attempts)
    
    db.session.commit()
    
    # Update ranks
    update_ranks()

def update_ranks():
    """Update ranks for all users - only students"""
    # Only rank students
    leaderboard_entries = Leaderboard.query.join(User).filter(
        User.role == 'student',
        User.is_active == True
    ).order_by(
        Leaderboard.total_score.desc(),
        Leaderboard.accuracy.desc()
    ).all()
    
    for rank, entry in enumerate(leaderboard_entries, start=1):
        entry.rank = rank
    
    db.session.commit()

def get_leaderboard(limit=100):
    """Get top users from leaderboard - only students"""
    # Join with User table and filter only students
    entries = Leaderboard.query.join(User).filter(
        User.role == 'student',
        User.is_active == True
    ).order_by(
        Leaderboard.total_score.desc(),
        Leaderboard.accuracy.desc()
    ).limit(limit).all()
    
    # Update ranks based on current order
    for rank, entry in enumerate(entries, start=1):
        entry.rank = rank
    
    db.session.commit()
    
    return [entry.to_dict() for entry in entries]

