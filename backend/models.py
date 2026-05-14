"""
Database models for the Interview Preparation Platform
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
import json
import pymysql

# Register PyMySQL as MySQLdb for SQLAlchemy compatibility
pymysql.install_as_MySQLdb()

# Initialize SQLAlchemy with engine options support
db = SQLAlchemy()

# Note: SQLALCHEMY_ENGINE_OPTIONS from config.py will be automatically used
# by Flask-SQLAlchemy when db.init_app() is called

class DeviceDetectionLog(db.Model):
    """Log of device detections during interviews"""
    __tablename__ = 'device_detection_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_id = db.Column(db.String(100), nullable=True, index=True)  # Interview session ID
    detected_device = db.Column(db.String(50), nullable=False)  # 'cell phone', 'laptop', etc.
    confidence = db.Column(db.Float, nullable=False)
    warning_count = db.Column(db.Integer, default=1)  # Number of warnings for this session
    detected_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', backref='device_detections', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'detected_device': self.detected_device,
            'confidence': self.confidence,
            'warning_count': self.warning_count,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None
        }

class User(db.Model):
    """User model for Students, Faculty, and Admins"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    reg_no = db.Column(db.String(50), unique=True, nullable=True, index=True)  # Registration number
    college_email = db.Column(db.String(120), unique=True, nullable=False, index=True)  # Must end with @audisankara.ac.in
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)  # Optional, for Google OAuth
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for Google OAuth users
    role = db.Column(db.String(20), nullable=False)  # 'student', 'faculty', 'admin'
    full_name = db.Column(db.String(100))  # Computed from first_name + last_name
    google_id = db.Column(db.String(255), unique=True, nullable=True, index=True)  # For Google OAuth
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True, index=True)  # Batch assignment
    
    # Relationships
    # Specify primaryjoin to avoid ambiguity (CodeSubmission has both user_id and evaluated_by)
    submissions = db.relationship(
        'CodeSubmission',
        primaryjoin='User.id == CodeSubmission.user_id',
        backref=db.backref('user', lazy=True),
        lazy=True,
        cascade='all, delete-orphan'
    )
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True, cascade='all, delete-orphan')
    resources = db.relationship('Resource', backref='user', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    chat_history = db.relationship('ChatHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    usage_stats = db.relationship('UsageStats', backref='user', lazy=True, cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'reg_no': self.reg_no,
            'college_email': self.college_email,
            'email': self.email,
            'role': self.role,
            'full_name': self.full_name or f"{self.first_name} {self.last_name}",
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'batch_id': self.batch_id,
            'batch_name': self.batch.name if self.batch else None
        }

class Company(db.Model):
    """Company model for company-wise interview preparation"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='company', lazy=True)
    resources = db.relationship('Resource', backref='company', lazy=True)
    quizzes = db.relationship('Quiz', backref='company', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'logo_url': self.logo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Question(db.Model):
    """Question model for coding and non-coding questions"""
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'coding', 'mcq', 'fill_blank'
    module_type = db.Column(db.String(50), nullable=False, default='CodePractice', index=True)  # 'CodePractice', 'Non-Technical', 'Interview', 'Resources'
    difficulty = db.Column(db.String(20))  # 'easy', 'medium', 'hard'
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    tags = db.Column(db.String(200))  # Comma-separated tags
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # For coding questions
    test_cases = db.Column(db.Text)  # JSON string of test cases
    starter_code = db.Column(db.Text)
    solution = db.Column(db.Text)
    
    # For MCQ questions
    options = db.Column(db.Text)  # JSON string of options
    correct_answer = db.Column(db.String(10))  # Option index like 'A', 'B', 'C', 'D'
    marks = db.Column(db.Integer, default=1)  # Marks for the question
    
    # For fill-in-the-blank
    blanks = db.Column(db.Text)  # JSON string of blank positions and answers
    
    # Relationships
    submissions = db.relationship('CodeSubmission', backref='question', lazy=True)
    quiz_questions = db.relationship('QuizQuestion', backref='question', lazy=True)
    
    def to_dict(self, hide_test_cases=False):
        """
        Convert question to dictionary
        hide_test_cases is kept for older callers; coding practice now exposes
        the same visible test cases to all roles.
        """
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'module_type': self.module_type,
            'difficulty': self.difficulty,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else None,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }
        
        if self.type == 'coding':
            test_cases = json.loads(self.test_cases) if self.test_cases else []
            data['test_cases'] = test_cases
            data['sample_test_cases'] = [test_cases[0]] if test_cases else []
            data['starter_code'] = self.starter_code
        elif self.type == 'mcq':
            data['options'] = json.loads(self.options) if self.options else []
            data['correct_answer'] = self.correct_answer
            data['marks'] = self.marks if self.marks else 1
        elif self.type == 'fill_blank':
            data['blanks'] = json.loads(self.blanks) if self.blanks else []
        
        return data

class CodeSubmission(db.Model):
    """Code submission model for tracking student coding attempts"""
    __tablename__ = 'code_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    language = db.Column(db.String(20), nullable=False)  # 'c', 'cpp', 'python', 'java'
    code = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text)
    status = db.Column(db.String(20))  # 'accepted', 'wrong_answer', 'runtime_error', 'timeout'
    execution_time = db.Column(db.Float)  # Time in seconds
    memory_used = db.Column(db.Float)  # Memory in MB
    test_cases_passed = db.Column(db.Integer, default=0)
    total_test_cases = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    evaluation_comment = db.Column(db.Text)  # Manual evaluation comment from faculty
    evaluated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Faculty/admin who evaluated
    evaluated_at = db.Column(db.DateTime, nullable=True)  # When manual evaluation was done
    
    # Relationship for evaluator
    evaluator = db.relationship('User', foreign_keys=[evaluated_by], backref='evaluated_submissions', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'question_id': self.question_id,
            'language': self.language,
            'code': self.code,
            'output': self.output,
            'status': self.status,
            'execution_time': self.execution_time,
            'memory_used': self.memory_used,
            'test_cases_passed': self.test_cases_passed,
            'total_test_cases': self.total_test_cases,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'evaluation_comment': self.evaluation_comment,
            'evaluated_by': self.evaluated_by,
            'evaluated_by_name': self.evaluator.full_name if self.evaluator else None,
            'evaluated_at': self.evaluated_at.isoformat() if self.evaluated_at else None
        }

class Assessment(db.Model):
    """Assessment model for creating coding tests and non-technical quizzes"""
    __tablename__ = 'assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assessment_mode = db.Column(db.String(50), nullable=False, default='mixed')  # 'technical_only', 'non_technical_only', 'mixed'
    module_type = db.Column(db.String(50), nullable=False, default='Non-Technical', index=True)  # 'CodePractice', 'Non-Technical', 'Interview', 'Resources'
    start_date = db.Column(db.Date, nullable=False)  # Start date for assessment
    end_date = db.Column(db.Date, nullable=False)  # End date for assessment
    start_time = db.Column(db.Time, nullable=False)  # Start time for assessment
    end_time = db.Column(db.Time, nullable=False)  # End time for assessment
    difficulty = db.Column(db.String(20), nullable=False)  # 'easy', 'medium', 'hard'
    topic_tags = db.Column(db.String(500))  # Comma-separated tags: DSA, OOPS, DBMS, OS, CN, Aptitude, HR, etc.
    status = db.Column(db.String(20), default='draft')  # 'draft', 'published'
    total_marks = db.Column(db.Integer, default=0)  # Total marks for the assessment
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)  # When assessment was published
    is_active = db.Column(db.Boolean, default=True)
    assigned_batches = db.Column(db.Text)  # JSON string of batch IDs: [1, 2] or [1] or [2], null means all batches
    
    # Relationships
    questions = db.relationship('AssessmentQuestion', backref='assessment', lazy=True, cascade='all, delete-orphan', order_by='AssessmentQuestion.order')
    attempts = db.relationship('AssessmentAttempt', backref='assessment', lazy=True)
    
    def to_dict(self):
        technical_count = len([q for q in self.questions if q.question and q.question.type == 'coding']) if self.questions else 0
        non_technical_count = len([q for q in self.questions if q.question and q.question.type in ['mcq', 'fill_blank']]) if self.questions else 0
        
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'assessment_mode': self.assessment_mode,
            'module_type': self.module_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'difficulty': self.difficulty,
            'topic_tags': self.topic_tags.split(',') if self.topic_tags else [],
            'status': self.status,
            'total_marks': self.total_marks,
            'created_by': self.created_by,
            'created_by_name': self.creator.full_name if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'is_active': self.is_active,
            'assigned_batches': json.loads(self.assigned_batches) if self.assigned_batches else None,  # None means all batches
            'question_count': len(self.questions) if self.questions else 0,
            'technical_count': technical_count,
            'non_technical_count': non_technical_count
        }
    
    # Relationship for creator
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_assessments', lazy=True)

class AssessmentQuestion(db.Model):
    """Many-to-many relationship between Assessment and Question"""
    __tablename__ = 'assessment_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    order = db.Column(db.Integer, default=0)  # Order of question in assessment
    marks = db.Column(db.Integer, default=10)  # Marks for this question in the assessment
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'question_id': self.question_id,
            'question': self.question.to_dict() if self.question else None,
            'order': self.order,
            'marks': self.marks
        }
    
    # Relationship
    question = db.relationship('Question', backref='assessment_questions', lazy=True)

class AssessmentAttempt(db.Model):
    """Assessment attempt model for tracking student submissions"""
    __tablename__ = 'assessment_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id'), nullable=False)
    answers = db.Column(db.Text)  # JSON string of answers
    score = db.Column(db.Float, default=0)
    total_marks = db.Column(db.Float)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    time_taken_minutes = db.Column(db.Integer)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'user_email': self.user.college_email if self.user else None,
            'user_reg_no': self.user.reg_no if self.user else None,
            'assessment_id': self.assessment_id,
            'answers': json.loads(self.answers) if self.answers else {},
            'score': self.score,
            'total_marks': self.total_marks,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'time_taken_minutes': self.time_taken_minutes
        }
    
    # Relationship
    user = db.relationship('User', backref='assessment_attempts', lazy=True)

class Quiz(db.Model):
    """Quiz model for creating assessments"""
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    duration_minutes = db.Column(db.Integer, default=60)
    total_marks = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    deadline = db.Column(db.DateTime)  # Deadline for quiz submission
    assignment_type = db.Column(db.String(20), default='entire_batch')  # 'entire_batch' or 'selected_students'
    lock_after_deadline = db.Column(db.Boolean, default=True)  # Lock quiz after deadline
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    questions = db.relationship('QuizQuestion', backref='quiz', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True)
    assignments = db.relationship('QuizAssignment', backref='quiz', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'created_by': self.created_by,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else None,
            'duration_minutes': self.duration_minutes,
            'total_marks': self.total_marks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'assignment_type': self.assignment_type,
            'lock_after_deadline': self.lock_after_deadline,
            'is_active': self.is_active,
            'is_locked': self.is_locked() if hasattr(self, 'is_locked') else False
        }
    
    def is_locked(self):
        """Check if quiz is locked based on deadline"""
        if not self.lock_after_deadline or not self.deadline:
            return False
        from datetime import datetime
        return datetime.utcnow() > self.deadline

class QuizQuestion(db.Model):
    """Many-to-many relationship between Quiz and Question"""
    __tablename__ = 'quiz_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    marks = db.Column(db.Integer, default=10)
    order = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question_id': self.question_id,
            'question': self.question.to_dict() if self.question else None,
            'marks': self.marks,
            'order': self.order
        }

class QuizAssignment(db.Model):
    """Quiz assignment model to track which students are assigned to a quiz"""
    __tablename__ = 'quiz_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='quiz_assignments', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'user_id': self.user_id,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None
        }

class QuizAttempt(db.Model):
    """Quiz attempt model for tracking student quiz submissions"""
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    answers = db.Column(db.Text)  # JSON string of answers
    score = db.Column(db.Float, default=0)
    total_marks = db.Column(db.Float)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    time_taken_minutes = db.Column(db.Integer)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'quiz_id': self.quiz_id,
            'answers': json.loads(self.answers) if self.answers else {},
            'score': self.score,
            'total_marks': self.total_marks,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'time_taken_minutes': self.time_taken_minutes
        }

class InterviewSession(db.Model):
    """AI Interview Session model - Enhanced for TR/HR types"""
    __tablename__ = 'interview_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_text = db.Column(db.Text)
    job_description = db.Column(db.Text)
    interview_type = db.Column(db.String(20), default='TR')  # 'TR' (Technical), 'HR' (HR Interview)
    experience_level = db.Column(db.String(20), default='fresher')  # 'fresher', 'intermediate', 'experienced'
    
    # File paths
    resume_file_path = db.Column(db.String(500))
    jd_file_path = db.Column(db.String(500))
    
    # Interview state
    current_phase = db.Column(db.String(20), default='introduction')  # 'introduction', 'resume', 'programming', 'jd_skills', 'scenario'
    question_number = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=8)  # Default 8 questions
    
    # Results
    total_questions_asked = db.Column(db.Integer, default=0)
    total_answers = db.Column(db.Integer, default=0)
    final_score = db.Column(db.Float, default=0.0)  # Out of 100
    conversation = db.Column(db.Text)  # JSON string of conversation
    evaluation_summary = db.Column(db.Text)  # Final AI summary
    
    # Detailed scoring breakdown (JSON)
    score_breakdown = db.Column(db.Text)  # JSON with component scores
    
    # Selfie Face Verification
    selfie_embedding = db.Column(db.Text)  # Base64 encoded selfie face embedding
    selfie_registered_at = db.Column(db.DateTime)  # When selfie was registered
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    is_completed = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User', backref='interview_sessions')
    resume_data = db.relationship('ResumeData', backref='session', uselist=False, cascade='all, delete-orphan')
    jd_data = db.relationship('JobDescriptionData', backref='session', uselist=False, cascade='all, delete-orphan')
    answers = db.relationship('InterviewAnswer', backref='session', lazy=True, cascade='all, delete-orphan')
    result = db.relationship('InterviewResult', backref='session', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'resume_text': self.resume_text,
            'job_description': self.job_description,
            'interview_type': self.interview_type,
            'experience_level': self.experience_level,
            'resume_file_path': self.resume_file_path,
            'jd_file_path': self.jd_file_path,
            'current_phase': self.current_phase,
            'question_number': self.question_number,
            'total_questions': self.total_questions,
            'total_questions_asked': self.total_questions_asked,
            'total_answers': self.total_answers,
            'final_score': self.final_score,
            'conversation': json.loads(self.conversation) if self.conversation else [],
            'evaluation_summary': self.evaluation_summary,
            'score_breakdown': json.loads(self.score_breakdown) if self.score_breakdown else {},
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'is_completed': self.is_completed
        }

class ResumeData(db.Model):
    """Extracted data from resume"""
    __tablename__ = 'resume_data'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False, unique=True)
    
    # Extracted information
    skills = db.Column(db.Text)  # JSON array of skills
    programming_languages = db.Column(db.Text)  # JSON array of languages
    projects = db.Column(db.Text)  # JSON array of projects
    certificates = db.Column(db.Text)  # JSON array of certificates
    experience_years = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'skills': json.loads(self.skills) if self.skills else [],
            'programming_languages': json.loads(self.programming_languages) if self.programming_languages else [],
            'projects': json.loads(self.projects) if self.projects else [],
            'certificates': json.loads(self.certificates) if self.certificates else [],
            'experience_years': self.experience_years,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class JobDescriptionData(db.Model):
    """Extracted data from job description"""
    __tablename__ = 'jd_data'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False, unique=True)
    
    # Extracted information
    required_skills = db.Column(db.Text)  # JSON array of required skills
    matching_skills = db.Column(db.Text)  # JSON array of skills matching resume
    missing_skills = db.Column(db.Text)  # JSON array of missing/weak skills (HIGH PRIORITY)
    job_title = db.Column(db.String(200))
    experience_required = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'required_skills': json.loads(self.required_skills) if self.required_skills else [],
            'matching_skills': json.loads(self.matching_skills) if self.matching_skills else [],
            'missing_skills': json.loads(self.missing_skills) if self.missing_skills else [],
            'job_title': self.job_title,
            'experience_required': self.experience_required,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class InterviewAnswer(db.Model):
    """Individual interview answer with evaluation"""
    __tablename__ = 'interview_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)
    
    # Question and answer
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    phase = db.Column(db.String(50))  # 'introduction', 'resume', 'programming', 'jd_skills', 'scenario'
    
    # Evaluation scores (out of 10, will be converted to percentage)
    correctness_score = db.Column(db.Float)  # 0-10
    clarity_score = db.Column(db.Float)  # 0-10
    confidence_score = db.Column(db.Float)  # 0-10
    overall_score = db.Column(db.Float)  # 0-10 (weighted average)
    
    # Feedback
    feedback = db.Column(db.Text)
    
    # Time tracking
    time_taken_seconds = db.Column(db.Integer)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'question_number': self.question_number,
            'question': self.question,
            'answer': self.answer,
            'phase': self.phase,
            'correctness_score': self.correctness_score,
            'clarity_score': self.clarity_score,
            'confidence_score': self.confidence_score,
            'overall_score': self.overall_score,
            'feedback': self.feedback,
            'time_taken_seconds': self.time_taken_seconds,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None
        }

class InterviewResult(db.Model):
    """Final interview result with detailed scoring breakdown"""
    __tablename__ = 'interview_results'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False, unique=True)
    
    # Final score (out of 100)
    total_score = db.Column(db.Float, nullable=False)  # 0-100
    
    # Component scores (for TR interviews)
    introduction_score = db.Column(db.Float, default=0.0)  # 0-10 converted to percentage
    projects_resume_score = db.Column(db.Float, default=0.0)
    programming_score = db.Column(db.Float, default=0.0)
    jd_gap_skills_score = db.Column(db.Float, default=0.0)
    communication_score = db.Column(db.Float, default=0.0)
    
    # Component scores (for HR interviews)
    hr_introduction_score = db.Column(db.Float, default=0.0)
    hr_communication_score = db.Column(db.Float, default=0.0)
    hr_confidence_score = db.Column(db.Float, default=0.0)
    hr_behavioral_score = db.Column(db.Float, default=0.0)
    
    # Feedback data (JSON)
    strengths = db.Column(db.Text)  # JSON array
    weaknesses = db.Column(db.Text)  # JSON array
    improvements = db.Column(db.Text)  # JSON array
    suggested_resources = db.Column(db.Text)  # JSON array
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'total_score': self.total_score,
            'introduction_score': self.introduction_score,
            'projects_resume_score': self.projects_resume_score,
            'programming_score': self.programming_score,
            'jd_gap_skills_score': self.jd_gap_skills_score,
            'communication_score': self.communication_score,
            'hr_introduction_score': self.hr_introduction_score,
            'hr_communication_score': self.hr_communication_score,
            'hr_confidence_score': self.hr_confidence_score,
            'hr_behavioral_score': self.hr_behavioral_score,
            'strengths': json.loads(self.strengths) if self.strengths else [],
            'weaknesses': json.loads(self.weaknesses) if self.weaknesses else [],
            'improvements': json.loads(self.improvements) if self.improvements else [],
            'suggested_resources': json.loads(self.suggested_resources) if self.suggested_resources else [],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Resource(db.Model):
    """Learning resources model"""
    __tablename__ = 'resources'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(20), nullable=False)  # 'pdf', 'code_snippet', 'flashcard', 'notes'
    file_path = db.Column(db.String(255))
    content = db.Column(db.Text)  # For flashcards, code snippets, notes
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    tags = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'file_path': self.file_path,
            'content': self.content,
            'user_id': self.user_id,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else None,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_public': self.is_public
        }

class Notification(db.Model):
    """Notification model"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20))  # 'feedback', 'quiz_result', 'assignment', 'general'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    link = db.Column(db.String(255))  # Optional link to related content
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'link': self.link
        }

class Post(db.Model):
    """Post model for company-related posts (interview experiences, tips, etc.)"""
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)  # Can be null if file is uploaded
    file_path = db.Column(db.String(500))  # Path to uploaded file (PDF, JPG, PNG)
    file_type = db.Column(db.String(20))  # 'pdf', 'jpg', 'png'
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    post_type = db.Column(db.String(50), default='experience')  # 'experience', 'tip', 'question', 'discussion'
    tags = db.Column(db.String(200))  # Comma-separated tags
    # New fields for MCQ and coding questions
    mcq_questions = db.Column(db.Text)  # JSON string of MCQ questions array
    coding_questions = db.Column(db.Text)  # JSON string of coding questions array
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    company = db.relationship('Company', backref='posts')
    user = db.relationship('User', backref='posts')
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'post_type': self.post_type,
            'tags': self.tags,
            'mcq_questions': json.loads(self.mcq_questions) if self.mcq_questions else [],
            'coding_questions': json.loads(self.coding_questions) if self.coding_questions else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'company_name': self.company.name if self.company else None,
            'user_name': self.user.full_name if self.user else None
        }

class Leaderboard(db.Model):
    """Leaderboard model for tracking rankings"""
    __tablename__ = 'leaderboard'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    total_score = db.Column(db.Float, default=0)
    quiz_score = db.Column(db.Float, default=0)
    coding_score = db.Column(db.Float, default=0)
    accuracy = db.Column(db.Float, default=0)  # Percentage
    total_submissions = db.Column(db.Integer, default=0)
    total_quizzes = db.Column(db.Integer, default=0)
    rank = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='leaderboard_entry')
    
    def to_dict(self):
        user = self.user
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': user.username if user else None,
            'full_name': user.full_name or (f"{user.first_name} {user.last_name}" if user and user.first_name and user.last_name else None) if user else None,
            'reg_no': user.reg_no if user else None,
            'college_email': user.college_email if user else None,
            'total_score': self.total_score,
            'quiz_score': self.quiz_score,
            'coding_score': self.coding_score,
            'accuracy': self.accuracy,
            'total_submissions': self.total_submissions,
            'total_quizzes': self.total_quizzes,
            'rank': self.rank,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ChatHistory(db.Model):
    """Simple chat history for AI chatbot"""
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'assistant'
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'role': self.role,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UsageStats(db.Model):
    """Track OpenAI API usage and costs"""
    __tablename__ = 'usage_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    model = db.Column(db.String(50), nullable=False)  # e.g., 'gpt-3.5-turbo'
    prompt_tokens = db.Column(db.Integer, nullable=False, default=0)
    completion_tokens = db.Column(db.Integer, nullable=False, default=0)
    total_tokens = db.Column(db.Integer, nullable=False, default=0)
    cost_usd = db.Column(db.Numeric(10, 6), nullable=False, default=0.0)  # Cost in USD
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'model': self.model,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'cost_usd': float(self.cost_usd) if self.cost_usd else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Batch(db.Model):
    """Batch model for organizing students into batches"""
    __tablename__ = 'batches'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    students = db.relationship('User', backref='batch', lazy=True, foreign_keys='User.batch_id')
    created_by_user = db.relationship('User', backref='created_batches', lazy=True, foreign_keys=[created_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_by': self.created_by,
            'created_by_name': self.created_by_user.full_name if self.created_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'student_count': len([s for s in self.students if s.role == 'student' and s.is_active]) if self.students else 0
        }

class ActivityLog(db.Model):
    """Activity log model for tracking all test activities and submissions"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    activity_type = db.Column(db.String(50), nullable=False, index=True)  # 'test_created', 'test_attempted', 'test_submitted', 'evaluation', 'comment'
    entity_type = db.Column(db.String(50), nullable=False)  # 'quiz', 'coding_test', 'mcq', 'fill_blank'
    entity_id = db.Column(db.Integer, nullable=False, index=True)  # ID of quiz/question/test
    entity_name = db.Column(db.String(200))  # Name/title for quick reference
    description = db.Column(db.Text)  # Detailed description of activity
    metadata_json = db.Column(db.Text)  # JSON string for additional data (renamed from metadata to avoid SQLAlchemy conflict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        metadata_dict = {}
        if self.metadata_json:
            try:
                metadata_dict = json.loads(self.metadata_json)
            except:
                metadata_dict = {}
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'username': self.user.username if self.user else None,
            'activity_type': self.activity_type,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'entity_name': self.entity_name,
            'description': self.description,
            'metadata': metadata_dict,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

