"""
Enhanced Resume and Job Description processing utilities
Extracts skills, projects, languages, certificates, and maps JD requirements
"""
import re
import json
from typing import Dict, List, Tuple

# Common programming languages
PROGRAMMING_LANGUAGES = [
    'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C', 'C#', 'PHP', 'Ruby', 'Go', 
    'Rust', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'Perl', 'Lua', 'Dart',
    'SQL', 'HTML', 'CSS', 'SCSS', 'SASS', 'Bash', 'Shell', 'PowerShell'
]

# Common frameworks and technologies
FRAMEWORKS_TECHNOLOGIES = [
    'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Django', 'Flask', 'Spring', 
    'Spring Boot', '.NET', 'ASP.NET', 'Laravel', 'Symfony', 'Ruby on Rails',
    'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn', 'Pandas', 'NumPy',
    'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Elasticsearch',
    'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'Jenkins', 'Git', 'GitHub',
    'Linux', 'Unix', 'Windows', 'MacOS', 'Apache', 'Nginx'
]

def extract_programming_languages(resume_text: str) -> List[str]:
    """
    Extract programming languages from resume text
    Returns list of found programming languages
    """
    if not resume_text:
        return []
    
    found_languages = []
    resume_lower = resume_text.lower()
    
    for lang in PROGRAMMING_LANGUAGES:
        # Check for exact word match (case-insensitive)
        pattern = r'\b' + re.escape(lang.lower()) + r'\b'
        if re.search(pattern, resume_lower, re.IGNORECASE):
            found_languages.append(lang)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_languages = []
    for lang in found_languages:
        if lang.lower() not in seen:
            seen.add(lang.lower())
            unique_languages.append(lang)
    
    return unique_languages[:10]  # Return top 10

def extract_skills(resume_text: str) -> List[str]:
    """
    Extract technical skills (frameworks, tools, technologies) from resume
    """
    if not resume_text:
        return []
    
    found_skills = []
    resume_lower = resume_text.lower()
    
    for skill in FRAMEWORKS_TECHNOLOGIES:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, resume_lower, re.IGNORECASE):
            found_skills.append(skill)
    
    # Also look for common skill patterns
    skill_patterns = [
        r'machine learning', r'deep learning', r'data science', r'artificial intelligence',
        r'web development', r'full stack', r'frontend', r'backend', r'devops',
        r'cloud computing', r'api development', r'microservices', r'rest api',
        r'agile', r'scrum', r'ci/cd', r'test driven development', r'tdd'
    ]
    
    for pattern in skill_patterns:
        if re.search(pattern, resume_lower, re.IGNORECASE):
            found_skills.append(pattern.replace('r\'', '').replace('\'', '').title())
    
    # Remove duplicates
    seen = set()
    unique_skills = []
    for skill in found_skills:
        if skill.lower() not in seen:
            seen.add(skill.lower())
            unique_skills.append(skill)
    
    return unique_skills[:15]  # Return top 15

def extract_projects(resume_text: str) -> List[Dict]:
    """
    Extract project information from resume
    Returns list of project dictionaries with name and description
    """
    if not resume_text:
        return []
    
    projects = []
    
    # Look for common project section headers
    project_keywords = ['project', 'projects', 'portfolio', 'work experience', 'experience']
    
    # Try to find project names (usually bold or in all caps or after "Project:")
    project_pattern = r'(?:project|projects)[\s:]+(.+?)(?:\n|$)'
    matches = re.finditer(project_pattern, resume_text, re.IGNORECASE | re.MULTILINE)
    
    for match in matches:
        project_text = match.group(1).strip()
        if len(project_text) > 10:  # Filter out very short matches
            # Try to extract project name (first line or first 50 chars)
            lines = project_text.split('\n')
            project_name = lines[0][:100] if lines else project_text[:100]
            projects.append({
                'name': project_name.strip(),
                'description': project_text[:500]  # Limit description
            })
    
    # If no structured projects found, look for bullet points with technical keywords
    if not projects:
        lines = resume_text.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower()
            # Check if line contains project indicators
            if any(keyword in line_lower for keyword in ['developed', 'built', 'created', 'designed', 'implemented']):
                # Check if next few lines might be related
                description = line
                for j in range(1, min(3, len(lines) - i)):
                    if lines[i + j].strip().startswith('-') or lines[i + j].strip().startswith('•'):
                        description += ' ' + lines[i + j].strip()
                
                projects.append({
                    'name': line[:100].strip(),
                    'description': description[:500]
                })
    
    return projects[:5]  # Return top 5 projects

def extract_certificates(resume_text: str) -> List[str]:
    """
    Extract certificates and certifications from resume
    """
    if not resume_text:
        return []
    
    certificates = []
    resume_lower = resume_text.lower()
    
    # Look for certificate section
    cert_keywords = ['certificate', 'certification', 'certified', 'cert']
    cert_pattern = r'(?:certificate|certification|certified|cert)[\s:]+(.+?)(?:\n|$)'
    matches = re.finditer(cert_pattern, resume_text, re.IGNORECASE | re.MULTILINE)
    
    for match in matches:
        cert_text = match.group(1).strip()
        if len(cert_text) > 5:
            # Extract certificate name (first line)
            cert_name = cert_text.split('\n')[0].strip()
            certificates.append(cert_name[:200])
    
    # Also look for common certifications
    common_certs = [
        'AWS', 'Azure', 'GCP', 'Oracle', 'Microsoft', 'Google', 'IBM',
        'Cisco', 'CompTIA', 'PMP', 'Scrum', 'Agile', 'ITIL'
    ]
    
    for cert in common_certs:
        pattern = r'\b' + re.escape(cert.lower()) + r'\b'
        if re.search(pattern, resume_lower, re.IGNORECASE) and cert not in certificates:
            certificates.append(cert)
    
    return certificates[:10]  # Return top 10

def extract_experience_years(resume_text: str) -> int:
    """
    Extract years of experience from resume
    """
    if not resume_text:
        return 0
    
    # Look for patterns like "X years", "X+ years", "X yr", etc.
    patterns = [
        r'(\d+)[\+]?\s*years?\s*(?:of\s*)?(?:experience|exp)',
        r'experience[:\s]+(\d+)[\+]?\s*years?',
        r'(\d+)[\+]?\s*yr[s]?\s*(?:of\s*)?(?:experience|exp)'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, resume_text, re.IGNORECASE)
        for match in matches:
            try:
                years = int(match.group(1))
                return years
            except ValueError:
                continue
    
    # Fallback: count job entries or estimate based on keywords
    # This is a simple heuristic
    experience_keywords = ['senior', 'lead', 'manager', 'architect', 'principal']
    resume_lower = resume_text.lower()
    if any(keyword in resume_lower for keyword in experience_keywords):
        return 5  # Default estimate for experienced candidates
    
    return 0

def extract_jd_skills(jd_text: str) -> List[str]:
    """
    Extract required skills from job description
    """
    if not jd_text:
        return []
    
    all_skills = PROGRAMMING_LANGUAGES + FRAMEWORKS_TECHNOLOGIES
    found_skills = []
    jd_lower = jd_text.lower()
    
    for skill in all_skills:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, jd_lower, re.IGNORECASE):
            found_skills.append(skill)
    
    # Look for skill-related keywords
    skill_keywords = [
        r'required[:\s]+(.+?)(?:\n|\.)',
        r'skills[:\s]+(.+?)(?:\n|\.)',
        r'technologies[:\s]+(.+?)(?:\n|\.)',
        r'experience with[:\s]+(.+?)(?:\n|\.)'
    ]
    
    for pattern in skill_keywords:
        matches = re.finditer(pattern, jd_text, re.IGNORECASE)
        for match in matches:
            skill_text = match.group(1)
            # Check if any known skills are mentioned in this section
            for skill in all_skills:
                if skill.lower() in skill_text.lower() and skill not in found_skills:
                    found_skills.append(skill)
    
    # Remove duplicates
    seen = set()
    unique_skills = []
    for skill in found_skills:
        if skill.lower() not in seen:
            seen.add(skill.lower())
            unique_skills.append(skill)
    
    return unique_skills[:20]  # Return top 20

def map_resume_jd_skills(resume_skills: List[str], jd_skills: List[str]) -> Tuple[List[str], List[str]]:
    """
    Map resume skills to JD skills
    Returns: (matching_skills, missing_skills)
    """
    if not resume_skills or not jd_skills:
        return [], jd_skills[:] if jd_skills else []
    
    resume_skills_lower = [s.lower() for s in resume_skills]
    matching_skills = []
    missing_skills = []
    
    for jd_skill in jd_skills:
        jd_skill_lower = jd_skill.lower()
        # Check for exact match or partial match
        matched = False
        for resume_skill in resume_skills_lower:
            if jd_skill_lower in resume_skill or resume_skill in jd_skill_lower:
                matching_skills.append(jd_skill)
                matched = True
                break
        
        if not matched:
            missing_skills.append(jd_skill)
    
    return matching_skills, missing_skills

def process_resume(resume_text: str) -> Dict:
    """
    Process resume and extract all relevant information
    Returns dictionary with extracted data
    """
    return {
        'skills': extract_skills(resume_text),
        'programming_languages': extract_programming_languages(resume_text),
        'projects': extract_projects(resume_text),
        'certificates': extract_certificates(resume_text),
        'experience_years': extract_experience_years(resume_text)
    }

def process_job_description(jd_text: str, resume_skills: List[str] = None) -> Dict:
    """
    Process job description and extract required skills
    Also maps against resume skills if provided
    Returns dictionary with JD data
    """
    jd_skills = extract_jd_skills(jd_text)
    
    matching_skills = []
    missing_skills = jd_skills[:]
    
    if resume_skills:
        matching_skills, missing_skills = map_resume_jd_skills(resume_skills, jd_skills)
    
    # Extract job title - look for actual job titles, not descriptions
    job_title = None
    
    # First, try to find job title at the beginning (usually first line or first 200 chars)
    first_lines = jd_text[:300].split('\n')
    for line in first_lines[:5]:  # Check first 5 lines
        line = line.strip()
        # Skip lines that are clearly descriptions
        if any(keyword in line.lower() for keyword in ['description', 'responsibilities', 'requirements', 'qualifications']):
            continue
        # Look for job title patterns (usually 2-6 words, title case)
        if 2 <= len(line.split()) <= 6 and line[0].isupper():
            # Check if it looks like a job title (contains common job title words)
            job_keywords = ['engineer', 'developer', 'manager', 'analyst', 'specialist', 'consultant', 
                          'architect', 'lead', 'director', 'coordinator', 'assistant', 'agent', 
                          'representative', 'executive', 'officer', 'administrator']
            if any(keyword in line.lower() for keyword in job_keywords):
                job_title = line
                break
    
    # Fallback: Use regex patterns but limit length
    if not job_title:
        title_patterns = [
            r'^(?:job\s+)?title[:\s]+(.+?)(?:\n|$)',
            r'^(?:position|role)[:\s]+(.+?)(?:\n|$)',
            r'^([A-Z][a-zA-Z\s]+(?:Engineer|Developer|Manager|Analyst|Architect|Lead|Specialist|Consultant|Agent|Representative))',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, jd_text[:500], re.IGNORECASE | re.MULTILINE)
            if match:
                job_title = match.group(1).strip()
                # Limit to first line or 100 chars
                job_title = job_title.split('\n')[0].strip()
                if len(job_title) > 100:
                    job_title = job_title[:100]
                break
    
    # Clean and truncate to 200 characters (database limit)
    if job_title:
        # Remove common prefixes/suffixes that might have been captured
        job_title = re.sub(r'^(description|role|position|job)[:\s]+', '', job_title, flags=re.IGNORECASE)
        job_title = job_title.strip()
        # Split by common separators and take first part (usually the actual title)
        if ':' in job_title:
            job_title = job_title.split(':')[0].strip()
        if ' - ' in job_title:
            job_title = job_title.split(' - ')[0].strip()
        # Limit to 200 characters
        job_title = job_title[:200].strip()
    
    # Extract experience requirement
    exp_patterns = [
        r'(\d+)[\+]?\s*years?\s*(?:of\s*)?(?:experience|exp)',
        r'experience[:\s]+(\d+)[\+]?\s*years?'
    ]
    
    experience_required = None
    for pattern in exp_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            experience_required = match.group(0)
            break
    
    return {
        'required_skills': jd_skills,
        'matching_skills': matching_skills,
        'missing_skills': missing_skills,
        'job_title': job_title,
        'experience_required': experience_required
    }

