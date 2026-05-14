"""
Career Intelligence Engine
Multi-dimensional resume reasoning system that analyzes experience depth,
project complexity, skill strength, role fit, and career progression
"""
import re
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from utils.openai_client import get_openai_client, OpenAIError
from config import Config

class SemanticResumeParser:
    """
    Semantic Resume Parser
    Extracts roles, duration, responsibilities, technologies, outcomes, and impact
    """
    
    @staticmethod
    def parse_experience_sections(resume_text: str) -> List[Dict]:
        """
        Parse experience sections with semantic understanding
        
        Returns:
        [
            {
                "role": "Backend Developer",
                "company": "Tech Corp",
                "duration": "2 years",
                "start_date": "2022-01",
                "end_date": "2024-01",
                "responsibilities": ["Developed APIs", "Optimized performance"],
                "technologies": ["Python", "Flask", "MySQL"],
                "outcomes": ["Improved API performance by 40%"],
                "impact": "High",
                "achievements": ["Led team of 3", "Reduced latency by 50%"]
            }
        ]
        """
        if not Config.OPENAI_API_KEY:
            return SemanticResumeParser._basic_parse(resume_text)
        
        try:
            client = get_openai_client()
            
            prompt = f"""Parse this resume and extract experience sections with semantic understanding.

Resume Text:
{resume_text[:3000]}

Extract each work experience/role with:
- Role/Job Title
- Company Name
- Duration (years/months)
- Start and end dates (if available)
- Responsibilities (list of key responsibilities)
- Technologies used (specific tech stack)
- Outcomes/Achievements (quantifiable results)
- Impact level (High/Medium/Low based on outcomes)
- Leadership indicators (team size, decision-making, ownership)

Return ONLY a valid JSON array of experience objects:
[
    {{
        "role": "Backend Developer",
        "company": "Tech Corp",
        "duration": "2 years",
        "start_date": "2022-01",
        "end_date": "2024-01",
        "responsibilities": ["Developed REST APIs", "Optimized database queries"],
        "technologies": ["Python", "Flask", "MySQL", "Docker"],
        "outcomes": ["Improved API performance by 40%", "Reduced query time by 50%"],
        "impact": "High",
        "achievements": ["Led team of 3 developers"],
        "leadership_indicators": ["Team leadership", "System design"]
    }}
]

If no experience found, return empty array [].

Return ONLY the JSON array, no other text."""

            response = client.chat_completion(
                model=Config.OPENAI_MODEL or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert resume parser. Extract structured experience data. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            content = response.get('content', '').strip()
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            experiences = json.loads(content)
            return experiences if isinstance(experiences, list) else []
            
        except (OpenAIError, json.JSONDecodeError, Exception) as e:
            print(f"[Career Intelligence] Error parsing experience: {e}")
            return SemanticResumeParser._basic_parse(resume_text)
    
    @staticmethod
    def _basic_parse(resume_text: str) -> List[Dict]:
        """Fallback basic parsing using regex"""
        experiences = []
        
        # Look for experience section
        experience_patterns = [
            r'experience[:\s]+(.*?)(?=\n\n|\n[A-Z]|$)',
            r'work history[:\s]+(.*?)(?=\n\n|\n[A-Z]|$)',
            r'employment[:\s]+(.*?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in experience_patterns:
            match = re.search(pattern, resume_text, re.IGNORECASE | re.DOTALL)
            if match:
                exp_text = match.group(1)
                # Simple extraction
                experiences.append({
                    "role": "Developer",  # Placeholder
                    "company": "Company",
                    "duration": "Unknown",
                    "responsibilities": [],
                    "technologies": [],
                    "outcomes": [],
                    "impact": "Medium"
                })
                break
        
        return experiences


class SkillStrengthScorer:
    """
    Skill Strength Scorer
    Scores each skill based on usage frequency, project complexity, years, impact, role relevance
    """
    
    @staticmethod
    def score_skills(experiences: List[Dict], projects: List[Dict] = None) -> Dict[str, float]:
        """
        Score skills based on multiple factors
        
        Returns:
        {
            "Python": 0.82,
            "Flask": 0.75,
            "MySQL": 0.68
        }
        """
        skill_scores = {}
        skill_usage_count = {}
        skill_years = {}
        skill_impact = {}
        skill_complexity = {}
        
        # Analyze experiences
        for exp in experiences:
            technologies = exp.get('technologies', [])
            duration_str = exp.get('duration', '')
            impact = exp.get('impact', 'Medium')
            outcomes = exp.get('outcomes', [])
            
            # Extract years from duration
            years = SkillStrengthScorer._extract_years(duration_str)
            
            # Impact score (High=1.0, Medium=0.6, Low=0.3)
            impact_score = {'High': 1.0, 'Medium': 0.6, 'Low': 0.3}.get(impact, 0.6)
            
            for tech in technologies:
                tech = tech.strip()
                if not tech:
                    continue
                
                # Usage frequency
                skill_usage_count[tech] = skill_usage_count.get(tech, 0) + 1
                
                # Years of usage (accumulate)
                skill_years[tech] = skill_years.get(tech, 0) + years
                
                # Impact (take maximum)
                if tech not in skill_impact or impact_score > skill_impact[tech]:
                    skill_impact[tech] = impact_score
                
                # Complexity (based on outcomes - more outcomes = higher complexity)
                complexity_score = min(1.0, len(outcomes) / 3.0)  # Max 1.0 for 3+ outcomes
                if tech not in skill_complexity or complexity_score > skill_complexity[tech]:
                    skill_complexity[tech] = complexity_score
        
        # Analyze projects
        if projects:
            for project in projects:
                project_tech = project.get('technologies', [])
                project_desc = project.get('description', '').lower()
                
                # Project complexity indicators
                complexity_indicators = [
                    'production', 'enterprise', 'scalable', 'microservices',
                    'distributed', 'cloud', 'ml', 'ai', 'real-time', 'high-performance'
                ]
                project_complexity = sum(1 for indicator in complexity_indicators if indicator in project_desc)
                project_complexity_score = min(1.0, project_complexity / 3.0)
                
                for tech in project_tech:
                    tech = tech.strip()
                    if not tech:
                        continue
                    
                    skill_usage_count[tech] = skill_usage_count.get(tech, 0) + 1
                    if tech not in skill_complexity or project_complexity_score > skill_complexity[tech]:
                        skill_complexity[tech] = project_complexity_score
        
        # Calculate final scores (weighted combination)
        for skill in skill_usage_count:
            # Normalize factors
            usage_score = min(1.0, skill_usage_count[skill] / 5.0)  # Max at 5+ uses
            years_score = min(1.0, skill_years[skill] / 5.0)  # Max at 5+ years
            impact_score = skill_impact.get(skill, 0.5)
            complexity_score = skill_complexity.get(skill, 0.5)
            
            # Weighted combination
            # Usage frequency: 30%, Years: 20%, Impact: 25%, Complexity: 25%
            final_score = (
                usage_score * 0.30 +
                years_score * 0.20 +
                impact_score * 0.25 +
                complexity_score * 0.25
            )
            
            skill_scores[skill] = round(final_score, 2)
        
        return skill_scores
    
    @staticmethod
    def _extract_years(duration_str: str) -> float:
        """Extract years from duration string"""
        if not duration_str:
            return 0.0
        
        # Look for year patterns
        year_match = re.search(r'(\d+\.?\d*)\s*(?:years?|yrs?|y)', duration_str, re.IGNORECASE)
        if year_match:
            return float(year_match.group(1))
        
        # Look for month patterns (convert to years)
        month_match = re.search(r'(\d+)\s*(?:months?|mos?|m)', duration_str, re.IGNORECASE)
        if month_match:
            return float(month_match.group(1)) / 12.0
        
        return 0.0


class ProjectComplexityAnalyzer:
    """
    Project Complexity Analyzer
    Classifies and scores projects based on architecture, scale, security, deployment, performance
    """
    
    @staticmethod
    def analyze_projects(projects: List[Dict]) -> List[Dict]:
        """
        Analyze and classify projects
        
        Returns projects with complexity scores and classifications
        """
        if not Config.OPENAI_API_KEY:
            return ProjectComplexityAnalyzer._basic_analysis(projects)
        
        analyzed_projects = []
        
        for project in projects:
            project_name = project.get('name', '')
            project_desc = project.get('description', '')
            
            try:
                client = get_openai_client()
                
                prompt = f"""Analyze this project and classify its complexity.

Project Name: {project_name}
Description: {project_desc[:500]}

Classify the project type:
- Academic (student project, coursework)
- Internship (learning project during internship)
- Production System (real-world deployed application)
- Enterprise Scale (large-scale, multi-team, enterprise-grade)

Score the project (0-1) on:
- Architecture Depth (system design, patterns, scalability)
- Scale (users, data, transactions)
- Security (authentication, encryption, security practices)
- Deployment (CI/CD, cloud, DevOps)
- Performance (optimization, efficiency)

Return ONLY a JSON object:
{{
    "classification": "Production System",
    "architecture_depth": 0.7,
    "scale": 0.6,
    "security": 0.5,
    "deployment": 0.8,
    "performance": 0.6,
    "overall_complexity": 0.64
}}

Return ONLY the JSON object, no other text."""

                response = client.chat_completion(
                    model=Config.OPENAI_MODEL or "gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert project analyst. Classify and score projects. Return only valid JSON."},
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
                
                analysis = json.loads(content)
                
                # Merge with original project
                project['complexity_analysis'] = analysis
                analyzed_projects.append(project)
                
            except Exception as e:
                print(f"[Career Intelligence] Error analyzing project: {e}")
                # Fallback analysis
                project['complexity_analysis'] = ProjectComplexityAnalyzer._basic_project_analysis(project)
                analyzed_projects.append(project)
        
        return analyzed_projects
    
    @staticmethod
    def _basic_analysis(projects: List[Dict]) -> List[Dict]:
        """Fallback basic analysis"""
        for project in projects:
            project['complexity_analysis'] = ProjectComplexityAnalyzer._basic_project_analysis(project)
        return projects
    
    @staticmethod
    def _basic_project_analysis(project: Dict) -> Dict:
        """Basic heuristic-based project analysis"""
        desc = project.get('description', '').lower()
        
        # Classification
        if any(word in desc for word in ['academic', 'coursework', 'university', 'college', 'student']):
            classification = "Academic"
        elif any(word in desc for word in ['internship', 'intern', 'learning']):
            classification = "Internship"
        elif any(word in desc for word in ['enterprise', 'large-scale', 'multi-team', 'organization']):
            classification = "Enterprise Scale"
        else:
            classification = "Production System"
        
        # Complexity scores (heuristic)
        complexity_indicators = [
            'microservices', 'distributed', 'scalable', 'cloud', 'docker', 'kubernetes',
            'ml', 'ai', 'real-time', 'high-performance', 'security', 'authentication'
        ]
        indicator_count = sum(1 for indicator in complexity_indicators if indicator in desc)
        overall_complexity = min(1.0, indicator_count / 5.0)
        
        return {
            "classification": classification,
            "architecture_depth": overall_complexity * 0.8,
            "scale": overall_complexity * 0.7,
            "security": overall_complexity * 0.6,
            "deployment": overall_complexity * 0.7,
            "performance": overall_complexity * 0.8,
            "overall_complexity": overall_complexity
        }


class ExperienceDepthAnalyzer:
    """
    Experience Depth Analyzer
    Detects leadership, ownership, decision-making, system design exposure
    """
    
    @staticmethod
    def analyze_experience_depth(experiences: List[Dict]) -> Dict:
        """
        Analyze experience depth across all roles
        
        Returns:
        {
            "leadership_score": 0.75,
            "ownership_score": 0.68,
            "decision_making_score": 0.70,
            "system_design_score": 0.65,
            "overall_depth": 0.70,
            "leadership_indicators": ["Led team of 5", "Mentored juniors"],
            "ownership_indicators": ["Owned API architecture", "Responsible for performance"],
            "career_level": "Senior Developer"
        }
        """
        if not Config.OPENAI_API_KEY:
            return ExperienceDepthAnalyzer._basic_analysis(experiences)
        
        try:
            client = get_openai_client()
            
            # Build experience summary
            exp_summary = ""
            for i, exp in enumerate(experiences[:5], 1):  # Last 5 experiences
                exp_summary += f"\n{i}. {exp.get('role', '')} at {exp.get('company', '')} ({exp.get('duration', '')})\n"
                exp_summary += f"   Responsibilities: {', '.join(exp.get('responsibilities', [])[:3])}\n"
                exp_summary += f"   Achievements: {', '.join(exp.get('achievements', [])[:3])}\n"
                exp_summary += f"   Leadership: {', '.join(exp.get('leadership_indicators', []))}\n"
            
            prompt = f"""Analyze the career depth and progression from these work experiences.

Experiences:
{exp_summary}

Score (0-1) on:
- Leadership (team leadership, mentoring, people management)
- Ownership (system ownership, responsibility, accountability)
- Decision-making (architectural decisions, technology choices, strategic decisions)
- System Design (architecture, scalability, design patterns, system thinking)

Infer career level:
- Intern/Junior (0-1 years, learning phase)
- Developer (1-3 years, execution focus)
- Senior Developer (3-5 years, ownership, mentoring)
- Lead/Architect (5+ years, system design, leadership)

Return ONLY a JSON object:
{{
    "leadership_score": 0.75,
    "ownership_score": 0.68,
    "decision_making_score": 0.70,
    "system_design_score": 0.65,
    "overall_depth": 0.70,
    "leadership_indicators": ["Led team of 5", "Mentored 3 juniors"],
    "ownership_indicators": ["Owned API architecture", "Responsible for performance"],
    "career_level": "Senior Developer",
    "career_trajectory": "Growing" // "Growing", "Stable", "Stagnant"
}}

Return ONLY the JSON object, no other text."""

            response = client.chat_completion(
                model=Config.OPENAI_MODEL or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert career analyst. Analyze experience depth and career progression. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.get('content', '').strip()
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            analysis = json.loads(content)
            return analysis
            
        except Exception as e:
            print(f"[Career Intelligence] Error analyzing experience depth: {e}")
            return ExperienceDepthAnalyzer._basic_analysis(experiences)
    
    @staticmethod
    def _basic_analysis(experiences: List[Dict]) -> Dict:
        """Fallback basic analysis"""
        total_years = sum(SkillStrengthScorer._extract_years(exp.get('duration', '')) for exp in experiences)
        
        # Infer career level from years
        if total_years < 1:
            career_level = "Intern/Junior"
        elif total_years < 3:
            career_level = "Developer"
        elif total_years < 5:
            career_level = "Senior Developer"
        else:
            career_level = "Lead/Architect"
        
        # Basic scores based on years
        depth_score = min(1.0, total_years / 5.0)
        
        return {
            "leadership_score": depth_score * 0.7,
            "ownership_score": depth_score * 0.8,
            "decision_making_score": depth_score * 0.75,
            "system_design_score": depth_score * 0.7,
            "overall_depth": depth_score,
            "leadership_indicators": [],
            "ownership_indicators": [],
            "career_level": career_level,
            "career_trajectory": "Growing" if total_years > 0 else "Stable"
        }


class RoleSuitabilityEngine:
    """
    Role Suitability Engine
    Multi-dimensional comparison: skill match + experience depth + project complexity + domain relevance + career level
    """
    
    @staticmethod
    def calculate_role_fit(resume_intelligence: Dict, jd_data: Dict) -> Dict:
        """
        Calculate role suitability score with explainable reasoning
        
        Returns:
        {
            "role_fit_score": 0.86,
            "skill_match_score": 0.80,
            "experience_depth_score": 0.75,
            "project_complexity_score": 0.70,
            "domain_relevance_score": 0.85,
            "career_level_match": 0.90,
            "explanation": "Candidate is suitable for Backend role due to strong Python usage in production APIs...",
            "strengths": ["Strong Python skills", "Production experience"],
            "gaps": ["Missing Kubernetes", "No microservices experience"],
            "recommendations": ["Focus on system design questions", "Explore cloud experience"]
        }
        """
        if not Config.OPENAI_API_KEY:
            return RoleSuitabilityEngine._basic_calculation(resume_intelligence, jd_data)
        
        try:
            client = get_openai_client()
            
            # Build resume summary
            resume_summary = f"""
Resume Intelligence:
- Skills with Strength: {json.dumps(resume_intelligence.get('skill_strengths', {}), indent=2)}
- Experience Depth: {resume_intelligence.get('experience_depth', {})}
- Project Complexity: {len([p for p in resume_intelligence.get('projects', []) if p.get('complexity_analysis', {}).get('classification') == 'Production System'])} production projects
- Career Level: {resume_intelligence.get('experience_depth', {}).get('career_level', 'Unknown')}
- Total Experience: {resume_intelligence.get('total_experience_years', 0)} years
"""
            
            # Build JD summary
            jd_summary = f"""
Job Description:
- Required Skills: {', '.join(jd_data.get('required_skills', [])[:10])}
- Job Title: {jd_data.get('job_title', 'Unknown')}
- Experience Required: {jd_data.get('experience_required', 'Not specified')}
"""
            
            prompt = f"""Analyze role suitability between candidate resume and job description.

{resume_summary}

{jd_summary}

Calculate suitability scores (0-1) on:
1. Skill Match: How well do candidate skills match required skills?
2. Experience Depth: Does candidate have sufficient depth for the role?
3. Project Complexity: Are candidate's projects relevant to role complexity?
4. Domain Relevance: Does candidate's domain experience match role domain?
5. Career Level Match: Is candidate's career level appropriate for role?

Generate:
- Overall Role Fit Score (weighted average)
- Detailed explanation of why this score
- Strengths (what makes candidate suitable)
- Gaps (what's missing)
- Recommendations (what to explore in interview)

Return ONLY a JSON object:
{{
    "role_fit_score": 0.86,
    "skill_match_score": 0.80,
    "experience_depth_score": 0.75,
    "project_complexity_score": 0.70,
    "domain_relevance_score": 0.85,
    "career_level_match": 0.90,
    "explanation": "Candidate is suitable for Backend Developer role due to strong Python skills (0.82 strength) used in production APIs, 3 years of experience with system design exposure, and relevant project complexity. Career level (Senior Developer) matches role requirements.",
    "strengths": ["Strong Python skills", "Production API experience", "System design knowledge"],
    "gaps": ["Missing Kubernetes", "No microservices experience"],
    "recommendations": ["Focus on system design questions", "Explore cloud deployment experience", "Ask about scalability challenges"]
}}

Return ONLY the JSON object, no other text."""

            response = client.chat_completion(
                model=Config.OPENAI_MODEL or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert recruiter. Analyze role suitability with explainable reasoning. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.get('content', '').strip()
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            suitability = json.loads(content)
            return suitability
            
        except Exception as e:
            print(f"[Career Intelligence] Error calculating role fit: {e}")
            return RoleSuitabilityEngine._basic_calculation(resume_intelligence, jd_data)
    
    @staticmethod
    def _basic_calculation(resume_intelligence: Dict, jd_data: Dict) -> Dict:
        """Fallback basic calculation"""
        # Simple skill matching
        resume_skills = list(resume_intelligence.get('skill_strengths', {}).keys())
        jd_skills = jd_data.get('required_skills', [])
        
        matching_skills = [s for s in resume_skills if s.lower() in [js.lower() for js in jd_skills]]
        skill_match_score = len(matching_skills) / len(jd_skills) if jd_skills else 0.5
        
        return {
            "role_fit_score": skill_match_score,
            "skill_match_score": skill_match_score,
            "experience_depth_score": 0.6,
            "project_complexity_score": 0.6,
            "domain_relevance_score": 0.6,
            "career_level_match": 0.7,
            "explanation": f"Basic skill match: {len(matching_skills)}/{len(jd_skills)} required skills found.",
            "strengths": matching_skills[:3],
            "gaps": [s for s in jd_skills[:5] if s not in matching_skills],
            "recommendations": ["Explore technical depth", "Ask about project experience"]
        }


class CareerPathInferencer:
    """
    Career Path Inferencer
    Infers career trajectory: Intern → Developer → Senior → Architect
    Detects stagnation or growth
    """
    
    @staticmethod
    def infer_career_path(experiences: List[Dict]) -> Dict:
        """
        Infer career progression trajectory
        
        Returns:
        {
            "trajectory": ["Intern", "Developer", "Senior Developer"],
            "progression_rate": 0.85,  // 0-1, higher = faster growth
            "stagnation_detected": false,
            "growth_indicators": ["Increasing responsibility", "Team leadership"],
            "current_level": "Senior Developer",
            "next_expected_level": "Lead Developer",
            "years_to_next_level": 1.5
        }
        """
        if not experiences:
            return {
                "trajectory": [],
                "progression_rate": 0.0,
                "stagnation_detected": False,
                "growth_indicators": [],
                "current_level": "Unknown",
                "next_expected_level": "Unknown",
                "years_to_next_level": 0
            }
        
        # Sort experiences by date (most recent first)
        sorted_experiences = sorted(experiences, key=lambda x: x.get('start_date', ''), reverse=True)
        
        # Extract career levels from roles
        trajectory = []
        for exp in sorted_experiences:
            role = exp.get('role', '').lower()
            if any(word in role for word in ['intern', 'internship', 'trainee']):
                trajectory.append("Intern")
            elif any(word in role for word in ['junior', 'entry', 'associate']):
                trajectory.append("Junior Developer")
            elif any(word in role for word in ['senior', 'sr', 'lead', 'principal']):
                trajectory.append("Senior Developer")
            elif any(word in role for word in ['architect', 'tech lead', 'engineering manager']):
                trajectory.append("Architect/Lead")
            else:
                trajectory.append("Developer")
        
        # Calculate progression
        unique_levels = []
        for level in trajectory:
            if level not in unique_levels:
                unique_levels.append(level)
        
        # Detect stagnation (same level for multiple roles)
        stagnation_detected = len(unique_levels) < 2 and len(trajectory) > 2
        
        # Progression rate (based on level diversity and advancement)
        progression_rate = len(unique_levels) / max(4, len(trajectory))  # Max 4 levels
        
        # Growth indicators
        growth_indicators = []
        if any(exp.get('leadership_indicators') for exp in sorted_experiences[:2]):
            growth_indicators.append("Increasing leadership responsibility")
        if any(exp.get('impact') == 'High' for exp in sorted_experiences[:2]):
            growth_indicators.append("High impact achievements")
        
        current_level = trajectory[0] if trajectory else "Unknown"
        
        # Predict next level
        level_hierarchy = ["Intern", "Junior Developer", "Developer", "Senior Developer", "Architect/Lead"]
        try:
            current_index = level_hierarchy.index(current_level)
            if current_index < len(level_hierarchy) - 1:
                next_expected_level = level_hierarchy[current_index + 1]
            else:
                next_expected_level = current_level
        except:
            next_expected_level = "Senior Developer"
        
        # Estimate years to next level (heuristic)
        total_years = sum(SkillStrengthScorer._extract_years(exp.get('duration', '')) for exp in experiences)
        years_to_next_level = max(0, 3 - (total_years % 3))  # Rough estimate
        
        return {
            "trajectory": unique_levels,
            "progression_rate": round(progression_rate, 2),
            "stagnation_detected": stagnation_detected,
            "growth_indicators": growth_indicators,
            "current_level": current_level,
            "next_expected_level": next_expected_level,
            "years_to_next_level": years_to_next_level
        }


def analyze_resume_intelligence(resume_text: str, jd_data: Dict = None) -> Dict:
    """
    Main function: Comprehensive resume intelligence analysis
    
    Returns complete career intelligence report
    """
    # Step 1: Semantic parsing
    experiences = SemanticResumeParser.parse_experience_sections(resume_text)
    
    # Step 2: Extract projects (using existing function)
    from utils.resume_processor import extract_projects
    projects = extract_projects(resume_text)
    
    # Step 3: Skill strength scoring
    skill_strengths = SkillStrengthScorer.score_skills(experiences, projects)
    
    # Step 4: Project complexity analysis
    analyzed_projects = ProjectComplexityAnalyzer.analyze_projects(projects)
    
    # Step 5: Experience depth analysis
    experience_depth = ExperienceDepthAnalyzer.analyze_experience_depth(experiences)
    
    # Step 6: Career path inference
    career_path = CareerPathInferencer.infer_career_path(experiences)
    
    # Step 7: Role suitability (if JD provided)
    role_suitability = None
    if jd_data:
        resume_intelligence = {
            'skill_strengths': skill_strengths,
            'experience_depth': experience_depth,
            'projects': analyzed_projects,
            'total_experience_years': sum(SkillStrengthScorer._extract_years(exp.get('duration', '')) for exp in experiences)
        }
        role_suitability = RoleSuitabilityEngine.calculate_role_fit(resume_intelligence, jd_data)
    
    # Build comprehensive intelligence report
    intelligence_report = {
        'experiences': experiences,
        'skill_strengths': skill_strengths,
        'projects': analyzed_projects,
        'experience_depth': experience_depth,
        'career_path': career_path,
        'role_suitability': role_suitability,
        'summary': {
            'total_experience_years': sum(SkillStrengthScorer._extract_years(exp.get('duration', '')) for exp in experiences),
            'top_skills': sorted(skill_strengths.items(), key=lambda x: x[1], reverse=True)[:5],
            'career_level': experience_depth.get('career_level', 'Unknown'),
            'production_projects': len([p for p in analyzed_projects if p.get('complexity_analysis', {}).get('classification') == 'Production System']),
            'role_fit_score': role_suitability.get('role_fit_score', 0.0) if role_suitability else None
        }
    }
    
    return intelligence_report
