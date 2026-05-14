"""
Utility functions for assessment time window validation
"""
from datetime import datetime, date, time
from models import Assessment


def check_assessment_time_window(assessment):
    """
    Check if current server time is within assessment's valid time window.
    Returns: (is_valid, status, message)
    - is_valid: bool - True if within window
    - status: str - 'upcoming', 'active', 'closed'
    - message: str - Human-readable status message
    """
    if not assessment.start_date or not assessment.end_date or not assessment.start_time or not assessment.end_time:
        return False, 'closed', 'Assessment time window not configured'
    
    now = datetime.utcnow()
    start_datetime = datetime.combine(assessment.start_date, assessment.start_time)
    end_datetime = datetime.combine(assessment.end_date, assessment.end_time)
    
    if now < start_datetime:
        return False, 'upcoming', 'Test not started yet'
    elif now > end_datetime:
        return False, 'closed', 'Test closed'
    else:
        return True, 'active', 'Assessment is active'


def validate_assessment_access(assessment, user_id=None, check_submitted=True):
    """
    Validate if a user can access an assessment.
    Returns: (can_access, error_message, status)
    """
    from models import AssessmentAttempt
    
    # Check if assessment is published and active
    if assessment.status != 'published' or not assessment.is_active:
        return False, 'Assessment is not available', 'closed'
    
    # Check time window
    is_valid, status, message = check_assessment_time_window(assessment)
    
    if not is_valid:
        return False, message, status
    
    # Check if user has already submitted (if check_submitted is True)
    if check_submitted and user_id:
        existing_attempt = AssessmentAttempt.query.filter_by(
            user_id=user_id,
            assessment_id=assessment.id,
            submitted_at=None  # Only check for incomplete attempts
        ).first()
        
        if existing_attempt:
            # Allow re-entry if not submitted yet
            return True, 'You can continue your attempt', 'active'
    
    return True, 'Access granted', status

