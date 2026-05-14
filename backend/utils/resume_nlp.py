"""
Advanced Resume NLP Processing
Uses spaCy, Sentence-BERT, KeyBERT for intelligent extraction and matching
"""

import re
import json
from typing import Dict, List, Tuple, Optional
import numpy as np
from datetime import datetime

# Try to import advanced NLP libraries
try:
    import spacy
    SPACY_AVAILABLE = True
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("[Resume NLP] spaCy model not found. Install: python -m spacy download en_core_web_sm")
        nlp = None
        SPACY_AVAILABLE = False
except (ImportError, TypeError, AttributeError) as e:
    # Handle import errors and pydantic compatibility issues
    SPACY_AVAILABLE = False
    nlp = None
    # Silent fallback - spacy is optional
    # print(f"[Resume NLP] spaCy not available (compatibility issue: {type(e).__name__}). Using fallback methods.")

# Lazy loading for Sentence-BERT to avoid blocking app startup
SENTENCE_BERT_AVAILABLE = False
sentence_model = None
_sentence_model_loading = False  # Flag to prevent multiple simultaneous loads

def _load_sentence_model():
    """Lazy load Sentence-BERT model only when needed"""
    global sentence_model, SENTENCE_BERT_AVAILABLE, _sentence_model_loading
    
    # Return if already loaded or currently loading
    if sentence_model is not None:
        return sentence_model
    
    if _sentence_model_loading:
        return None  # Don't load multiple times
    
    # Check if library is available
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        SENTENCE_BERT_AVAILABLE = False
        return None
    
    # Try to load model
    _sentence_model_loading = True
    try:
        import os
        # Disable warnings and set timeout environment variables
        os.environ['HF_HUB_DISABLE_EXPERIMENTAL_WARNING'] = '1'
        os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '30'  # 30 second timeout
        
        print("[Resume NLP] Loading Sentence-BERT model (this may take a moment on first run)...")
        print("[Resume NLP] If download times out, the app will continue with fallback methods.")
        
        # Load model - this will download if not cached
        sentence_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        SENTENCE_BERT_AVAILABLE = True
        print("[Resume NLP] Sentence-BERT model loaded successfully")
        
    except Exception as e:
        print(f"[Resume NLP] Sentence-BERT model loading failed: {e}")
        print("[Resume NLP] Will use fallback similarity methods.")
        sentence_model = None
        SENTENCE_BERT_AVAILABLE = False
    finally:
        _sentence_model_loading = False
    
    return sentence_model

# Check if library is available (but don't load model yet)
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_BERT_AVAILABLE = True
except ImportError:
    SENTENCE_BERT_AVAILABLE = False
    print("[Resume NLP] Sentence-BERT not installed. Using fallback similarity.")

# Lazy loading for KeyBERT to avoid blocking app startup
KEYBERT_AVAILABLE = False
keybert_model = None
_keybert_model_loading = False

def _load_keybert_model():
    """Lazy load KeyBERT model only when needed"""
    global keybert_model, KEYBERT_AVAILABLE, _keybert_model_loading
    
    # Return if already loaded or currently loading
    if keybert_model is not None:
        return keybert_model
    
    if _keybert_model_loading:
        return None
    
    # Check if library is available
    try:
        from keybert import KeyBERT
    except ImportError:
        KEYBERT_AVAILABLE = False
        return None
    
    # Try to load model
    _keybert_model_loading = True
    try:
        print("[Resume NLP] Loading KeyBERT model...")
        keybert_model = KeyBERT()
        KEYBERT_AVAILABLE = True
        print("[Resume NLP] KeyBERT model loaded successfully")
    except Exception as e:
        print(f"[Resume NLP] KeyBERT model loading failed: {e}")
        print("[Resume NLP] Will use fallback keyword extraction.")
        keybert_model = None
        KEYBERT_AVAILABLE = False
    finally:
        _keybert_model_loading = False
    
    return keybert_model

# Check if library is available (but don't load model yet)
try:
    from keybert import KeyBERT
    KEYBERT_AVAILABLE = True
except ImportError:
    KEYBERT_AVAILABLE = False
    print("[Resume NLP] KeyBERT not installed. Using fallback keyword extraction.")

# Common skills database
PROGRAMMING_LANGUAGES = [
    'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C', 'C#', 'PHP', 'Ruby', 'Go', 
    'Rust', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'Perl', 'Lua', 'Dart',
    'SQL', 'HTML', 'CSS', 'SCSS', 'SASS', 'Bash', 'Shell', 'PowerShell', 'Dart'
]

FRAMEWORKS_TECHNOLOGIES = [
    'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Django', 'Flask', 'Spring', 
    'Spring Boot', '.NET', 'ASP.NET', 'Laravel', 'Symfony', 'Ruby on Rails',
    'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn', 'Pandas', 'NumPy', 'SciPy',
    'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Elasticsearch', 'Cassandra',
    'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'Jenkins', 'Git', 'GitHub',
    'Linux', 'Unix', 'Windows', 'MacOS', 'Apache', 'Nginx', 'GraphQL', 'REST API'
]

SOFT_SKILLS = [
    'Communication', 'Leadership', 'Teamwork', 'Problem Solving', 'Time Management',
    'Adaptability', 'Creativity', 'Critical Thinking', 'Project Management', 'Agile', 'Scrum'
]

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)]', ' ', text)
    
    # Normalize line breaks
    text = re.sub(r'\n+', '\n', text)
    
    return text.strip()

def extract_name_spacy(text: str) -> Optional[str]:
    """Extract name using spaCy NER"""
    if not SPACY_AVAILABLE or not nlp:
        return extract_name_regex(text)
    
    try:
        doc = nlp(text[:2000])  # Process first 2000 chars for speed
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                # Usually name appears at the beginning
                if ent.start_char < 200:
                    return ent.text.strip()
    except Exception as e:
        print(f"[Resume NLP] Error extracting name with spaCy: {e}")
    
    return extract_name_regex(text)

def extract_name_regex(text: str) -> Optional[str]:
    """Fallback: Extract name using regex patterns"""
    # Look for name at the beginning (usually first line or first 100 chars)
    first_lines = text[:200].split('\n')
    
    for line in first_lines[:3]:  # Check first 3 lines
        line = line.strip()
        # Name usually has 2-4 words, starts with capital, no numbers
        if 2 <= len(line.split()) <= 4 and re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$', line):
            if not any(char.isdigit() for char in line):
                return line
    
    return None

def extract_education(text: str) -> List[Dict]:
    """Extract education information"""
    education = []
    
    # Education keywords
    edu_keywords = ['education', 'academic', 'degree', 'university', 'college', 'bachelor', 'master', 'phd', 'diploma']
    
    # Find education section
    lines = text.split('\n')
    in_education_section = False
    edu_section = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in edu_keywords):
            in_education_section = True
            edu_section = []
        
        if in_education_section:
            edu_section.append(line)
            # Stop after 10 lines or when we hit another major section
            if len(edu_section) > 10 or (i < len(lines) - 1 and any(
                keyword in lines[i+1].lower() for keyword in ['experience', 'skills', 'projects', 'certification']
            )):
                break
    
    # Extract degree information
    degree_patterns = [
        r'(?:Bachelor|B\.?S\.?|B\.?E\.?|B\.?Tech|Master|M\.?S\.?|M\.?E\.?|M\.?Tech|PhD|Ph\.?D\.?|Doctorate)',
        r'(?:B\.?A\.?|B\.?Sc\.?|M\.?A\.?|M\.?Sc\.?)',
    ]
    
    edu_text = '\n'.join(edu_section)
    for pattern in degree_patterns:
        matches = re.finditer(pattern, edu_text, re.IGNORECASE)
        for match in matches:
            # Get context around match
            start = max(0, match.start() - 50)
            end = min(len(edu_text), match.end() + 100)
            context = edu_text[start:end]
            
            # Extract degree name
            degree_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', context)
            if degree_match:
                degree = degree_match.group(1)
                # Extract university if mentioned
                uni_match = re.search(r'(?:from|at|in)\s+([A-Z][a-zA-Z\s]+(?:University|College|Institute))', context, re.IGNORECASE)
                university = uni_match.group(1) if uni_match else None
                
                education.append({
                    'degree': degree,
                    'university': university,
                    'context': context.strip()
                })
    
    return education[:5]  # Return top 5

def extract_experience_structured(text: str) -> List[Dict]:
    """Extract structured experience information"""
    experience = []
    
    # Find experience section
    exp_keywords = ['experience', 'employment', 'work history', 'career', 'professional']
    lines = text.split('\n')
    in_exp_section = False
    exp_section = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in exp_keywords):
            in_exp_section = True
        
        if in_exp_section:
            exp_section.append(line)
            # Stop after 30 lines or when we hit another major section
            if len(exp_section) > 30 or (i < len(lines) - 1 and any(
                keyword in lines[i+1].lower() for keyword in ['education', 'skills', 'projects', 'certification']
            )):
                break
    
    exp_text = '\n'.join(exp_section)
    
    # Extract job titles and companies
    # Pattern: Job Title at Company or Company - Job Title
    patterns = [
        r'([A-Z][a-zA-Z\s]+(?:Engineer|Developer|Manager|Analyst|Architect|Lead|Specialist|Consultant))\s+(?:at|@|in)\s+([A-Z][a-zA-Z\s&]+)',
        r'([A-Z][a-zA-Z\s&]+)\s*[-–]\s*([A-Z][a-zA-Z\s]+(?:Engineer|Developer|Manager|Analyst|Architect|Lead|Specialist|Consultant))',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, exp_text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 2:
                title = match.group(1).strip()
                company = match.group(2).strip()
                
                # Extract duration if mentioned
                duration_match = re.search(r'(\d{4})\s*[-–]\s*(\d{4}|Present|Current)', exp_text[max(0, match.start()-50):match.end()+50])
                duration = duration_match.group(0) if duration_match else None
                
                experience.append({
                    'title': title,
                    'company': company,
                    'duration': duration
                })
    
    # If no structured matches, extract from bullet points
    if not experience:
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in ['developed', 'built', 'created', 'designed', 'implemented', 'managed', 'led']):
                # Check if previous line might be job title
                if i > 0 and len(lines[i-1].split()) <= 5:
                    experience.append({
                        'title': lines[i-1].strip(),
                        'description': line.strip()
                    })
    
    return experience[:10]  # Return top 10

def extract_skills_keybert(text: str, top_n: int = 20) -> List[str]:
    """Extract skills using KeyBERT"""
    # Lazy load model if needed
    model = _load_keybert_model()
    
    if model:
        try:
            # Combine known skills for better extraction
            candidate_keywords = PROGRAMMING_LANGUAGES + FRAMEWORKS_TECHNOLOGIES + SOFT_SKILLS
            keywords = model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words='english',
                top_n=top_n,
                candidates=candidate_keywords
            )
            return [kw[0] for kw in keywords]
        except Exception as e:
            print(f"[Resume NLP] KeyBERT extraction failed: {e}")
    
    # Fallback to regex-based extraction
    return extract_skills_regex(text)

def extract_skills_regex(text: str) -> List[str]:
    """Fallback: Extract skills using regex"""
    all_skills = PROGRAMMING_LANGUAGES + FRAMEWORKS_TECHNOLOGIES
    found_skills = []
    text_lower = text.lower()
    
    for skill in all_skills:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower, re.IGNORECASE):
            found_skills.append(skill)
    
    return found_skills[:20]

def calculate_similarity_sbert(text1: str, text2: str) -> float:
    """Calculate semantic similarity using Sentence-BERT"""
    # Lazy load model if needed
    model = _load_sentence_model()
    
    if model:
        try:
            embeddings = model.encode([text1, text2])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
        except Exception as e:
            print(f"[Resume NLP] Sentence-BERT similarity failed: {e}")
    
    # Fallback: Jaccard similarity
    return calculate_jaccard_similarity(text1, text2)

def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Fallback: Calculate Jaccard similarity"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union) if union else 0.0

def match_skills_semantic(resume_skills: List[str], jd_skills: List[str]) -> Dict:
    """Match skills using semantic similarity"""
    matching_skills = []
    missing_skills = []
    strong_skills = []
    
    if not resume_skills or not jd_skills:
        return {
            'matching_skills': [],
            'missing_skills': jd_skills[:] if jd_skills else [],
            'strong_skills': [],
            'match_percentage': 0.0
        }
    
    # Calculate semantic similarity for each JD skill
    skill_similarities = {}
    
    for jd_skill in jd_skills:
        best_match = None
        best_similarity = 0.0
        
        for resume_skill in resume_skills:
            # Use lazy-loaded model via calculate_similarity_sbert
            model = _load_sentence_model()
            if model:
                similarity = calculate_similarity_sbert(jd_skill, resume_skill)
            else:
                # Simple string matching
                similarity = 1.0 if jd_skill.lower() in resume_skill.lower() or resume_skill.lower() in jd_skill.lower() else 0.0
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = resume_skill
        
        skill_similarities[jd_skill] = {
            'best_match': best_match,
            'similarity': best_similarity
        }
        
        if best_similarity >= 0.7:  # High similarity threshold
            matching_skills.append({
                'jd_skill': jd_skill,
                'resume_skill': best_match,
                'similarity': best_similarity
            })
            if best_similarity >= 0.9:
                strong_skills.append(jd_skill)
        else:
            missing_skills.append(jd_skill)
    
    # Calculate match percentage
    match_percentage = (len(matching_skills) / len(jd_skills) * 100) if jd_skills else 0.0
    
    return {
        'matching_skills': matching_skills,
        'missing_skills': missing_skills,
        'strong_skills': strong_skills,
        'match_percentage': round(match_percentage, 2),
        'skill_similarities': skill_similarities
    }

def extract_jd_keywords_keybert(jd_text: str, top_n: int = 15) -> List[str]:
    """Extract keywords from JD using KeyBERT"""
    # Lazy load model if needed
    model = _load_keybert_model()
    
    if model:
        try:
            keywords = model.extract_keywords(
                jd_text,
                keyphrase_ngram_range=(1, 2),
                stop_words='english',
                top_n=top_n
            )
            return [kw[0] for kw in keywords]
        except Exception as e:
            print(f"[Resume NLP] KeyBERT JD extraction failed: {e}")
    
    return extract_jd_skills_regex(jd_text)

def extract_jd_skills_regex(jd_text: str) -> List[str]:
    """Fallback: Extract JD skills using regex"""
    all_skills = PROGRAMMING_LANGUAGES + FRAMEWORKS_TECHNOLOGIES
    found_skills = []
    jd_lower = jd_text.lower()
    
    for skill in all_skills:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, jd_lower, re.IGNORECASE):
            found_skills.append(skill)
    
    return found_skills

def suggest_focus_topics(resume_data: Dict, jd_data: Dict, match_data: Dict) -> List[str]:
    """Suggest focus topics for interview based on gaps and strengths"""
    topics = []
    
    # Focus on missing skills
    if match_data.get('missing_skills'):
        topics.extend([f"Deep dive into {skill}" for skill in match_data['missing_skills'][:3]])
    
    # Focus on strong skills (can ask advanced questions)
    if match_data.get('strong_skills'):
        topics.extend([f"Advanced {skill} concepts" for skill in match_data['strong_skills'][:2]])
    
    # Focus on projects related to JD
    if resume_data.get('projects') and jd_data.get('required_skills'):
        # Find projects that use JD skills
        for project in resume_data['projects'][:2]:
            project_text = project.get('description', '') + ' ' + project.get('name', '')
            for jd_skill in jd_data['required_skills'][:5]:
                if jd_skill.lower() in project_text.lower():
                    topics.append(f"Project: {project.get('name', 'Project')} using {jd_skill}")
                    break
    
    # Add general topics based on experience level
    experience_years = resume_data.get('experience_years', 0)
    if experience_years < 2:
        topics.append("Fundamentals and best practices")
    elif experience_years < 5:
        topics.append("System design and architecture")
    else:
        topics.append("Leadership and technical decision-making")
    
    return topics[:8]  # Return top 8 topics

def process_resume_advanced(resume_text: str) -> Dict:
    """
    Advanced resume processing with NLP
    Returns structured JSON with all extracted information
    """
    if not resume_text:
        return {}
    
    # Clean text
    cleaned_text = clean_text(resume_text)
    
    # Extract structured information
    name = extract_name_spacy(cleaned_text)
    education = extract_education(cleaned_text)
    experience = extract_experience_structured(cleaned_text)
    skills = extract_skills_keybert(cleaned_text)
    programming_languages = [skill for skill in skills if skill in PROGRAMMING_LANGUAGES]
    frameworks = [skill for skill in skills if skill in FRAMEWORKS_TECHNOLOGIES]
    
    # Extract projects and certificates (using existing logic)
    from utils.resume_processor import extract_projects, extract_certificates, extract_experience_years
    projects = extract_projects(cleaned_text)
    certificates = extract_certificates(cleaned_text)
    experience_years = extract_experience_years(cleaned_text)
    
    return {
        'name': name,
        'skills': skills,
        'programming_languages': programming_languages,
        'frameworks_technologies': frameworks,
        'education': education,
        'experience': experience,
        'experience_years': experience_years,
        'projects': projects,
        'certificates': certificates,
        'raw_text_length': len(cleaned_text),
        'processed_at': datetime.utcnow().isoformat()
    }

def process_job_description_advanced(jd_text: str, resume_data: Dict = None) -> Dict:
    """
    Advanced job description processing with NLP
    Returns structured JSON with matching analysis
    """
    if not jd_text:
        return {}
    
    # Clean text
    cleaned_text = clean_text(jd_text)
    
    # Extract required skills
    required_skills = extract_jd_keywords_keybert(cleaned_text)
    
    # Extract job title and experience requirement
    from utils.resume_processor import process_job_description
    jd_basic = process_job_description(cleaned_text)
    
    # Match with resume if provided
    match_data = {}
    if resume_data:
        resume_skills = resume_data.get('skills', []) + resume_data.get('programming_languages', []) + resume_data.get('frameworks_technologies', [])
        match_data = match_skills_semantic(resume_skills, required_skills)
    
    # Suggest focus topics
    focus_topics = []
    if resume_data:
        focus_topics = suggest_focus_topics(resume_data, {
            'required_skills': required_skills,
            'job_title': jd_basic.get('job_title'),
            'experience_required': jd_basic.get('experience_required')
        }, match_data)
    
    return {
        'required_skills': required_skills,
        'job_title': jd_basic.get('job_title'),
        'experience_required': jd_basic.get('experience_required'),
        'matching_skills': match_data.get('matching_skills', []),
        'missing_skills': match_data.get('missing_skills', []),
        'strong_skills': match_data.get('strong_skills', []),
        'skill_match_percentage': match_data.get('match_percentage', 0.0),
        'suggested_focus_topics': focus_topics,
        'skill_similarities': match_data.get('skill_similarities', {}),
        'processed_at': datetime.utcnow().isoformat()
    }

