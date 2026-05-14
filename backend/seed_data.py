"""
Seed demo learning content for coding practice, non-technical questions,
quizzes, assessments, and resource notes.
"""
import json
import os
from datetime import date, datetime, time, timedelta

from models import (
    Assessment,
    AssessmentQuestion,
    Batch,
    Company,
    Post,
    Question,
    Quiz,
    QuizQuestion,
    Resource,
    db,
)


def _json(value):
    return json.dumps(value, ensure_ascii=True)


def _upsert_batches(created_by):
    batches = [
        ("2021", "Student batch for the 2021 academic year."),
        ("2022", "Student batch for the 2022 academic year."),
        ("2023", "Student batch for the 2023 academic year."),
        ("2024", "Student batch for the 2024 academic year."),
    ]
    Batch.query.filter(Batch.name.in_(["Batch 1", "Batch 2"])).update(
        {Batch.is_active: False},
        synchronize_session=False,
    )
    for name, description in batches:
        batch = Batch.query.filter_by(name=name).first()
        if not batch:
            batch = Batch(name=name, created_by=created_by)
            db.session.add(batch)
        batch.description = description
        batch.created_by = created_by
        batch.is_active = True
    db.session.flush()


def _upsert_question(created_by, data):
    question = Question.query.filter_by(title=data["title"]).first()
    if not question:
        question = Question(title=data["title"], created_by=created_by)
        db.session.add(question)

    question.description = data["description"]
    question.type = data["type"]
    question.module_type = data["module_type"]
    question.difficulty = data.get("difficulty", "easy")
    question.tags = ",".join(data.get("tags", []))
    question.is_active = True
    question.marks = data.get("marks", 1)

    if data["type"] == "coding":
        question.test_cases = _json(data.get("test_cases", []))
        question.starter_code = data.get("starter_code", "")
        question.solution = data.get("solution", "")
        question.options = None
        question.correct_answer = None
        question.blanks = None
    elif data["type"] == "mcq":
        question.options = _json(data.get("options", []))
        question.correct_answer = data.get("correct_answer", "")
        question.test_cases = None
        question.starter_code = None
        question.solution = None
        question.blanks = None

    db.session.flush()
    return question


def _upsert_quiz(created_by, title, description, questions):
    quiz = Quiz.query.filter_by(title=title).first()
    if not quiz:
        quiz = Quiz(title=title, created_by=created_by)
        db.session.add(quiz)
        db.session.flush()

    quiz.description = description
    quiz.duration_minutes = 30
    quiz.total_marks = sum(question.marks or 1 for question in questions)
    quiz.deadline = datetime.utcnow() + timedelta(days=180)
    quiz.assignment_type = "entire_batch"
    quiz.lock_after_deadline = True
    quiz.is_active = True

    QuizQuestion.query.filter_by(quiz_id=quiz.id).delete()
    for order, question in enumerate(questions):
        db.session.add(QuizQuestion(
            quiz_id=quiz.id,
            question_id=question.id,
            marks=question.marks or 1,
            order=order,
        ))

    return quiz


def _upsert_assessment(created_by, title, description, questions):
    assessment = Assessment.query.filter_by(title=title).first()
    today = date.today()

    if not assessment:
        assessment = Assessment(
            title=title,
            created_by=created_by,
            assessment_mode="mixed",
            module_type="CodePractice",
            start_date=today,
            end_date=today + timedelta(days=180),
            start_time=time(0, 0),
            end_time=time(23, 59),
            difficulty="medium",
        )
        db.session.add(assessment)
        db.session.flush()

    assessment.description = description
    assessment.assessment_mode = "mixed"
    assessment.module_type = "CodePractice"
    assessment.start_date = today
    assessment.end_date = today + timedelta(days=180)
    assessment.start_time = time(0, 0)
    assessment.end_time = time(23, 59)
    assessment.difficulty = "medium"
    assessment.topic_tags = "Python,Java,SQL,DSA,Aptitude,DBMS"
    assessment.status = "published"
    assessment.published_at = assessment.published_at or datetime.utcnow()
    assessment.is_active = True
    assessment.assigned_batches = None
    assessment.total_marks = sum(10 if q.type == "coding" else q.marks or 1 for q in questions)

    AssessmentQuestion.query.filter_by(assessment_id=assessment.id).delete()
    for order, question in enumerate(questions):
        db.session.add(AssessmentQuestion(
            assessment_id=assessment.id,
            question_id=question.id,
            order=order,
            marks=10 if question.type == "coding" else question.marks or 1,
        ))

    return assessment


def _upsert_note(user_id, title, description, tags, content):
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "seed_notes"))
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{title.lower().replace(' ', '_').replace('/', '_')}.txt"
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "w", encoding="utf-8") as note_file:
        note_file.write(content.strip() + "\n")

    resource = Resource.query.filter_by(title=title).first()
    if not resource:
        resource = Resource(title=title, user_id=user_id)
        db.session.add(resource)

    resource.description = description
    resource.type = "notes"
    resource.file_path = file_path
    resource.content = content.strip()
    resource.tags = ",".join(tags)
    resource.is_public = True
    return resource


def _upsert_company(name, description, logo_url=None):
    company = Company.query.filter_by(name=name).first()
    if not company:
        company = Company(name=name)
        db.session.add(company)

    company.description = description
    company.logo_url = logo_url
    db.session.flush()
    return company


def _upsert_company_interview_post(company, question, options, correct_answer, content, tags):
    title = f"{company.name} - Interview Question"
    post = Post.query.filter_by(title=title, company_id=company.id).first()
    if not post:
        post = Post(
            title=title,
            company_id=company.id,
            user_id=None,
            post_type="question",
        )
        db.session.add(post)

    post.content = content.strip()
    post.file_path = None
    post.file_type = None
    post.tags = ",".join(tags)
    post.mcq_questions = _json([{
        "question": question,
        "options": options,
        "correct_answer": correct_answer,
    }])
    post.coding_questions = None
    post.is_active = True
    return post


def seed_initial_data():
    """Seed content once, then keep it updated on later app starts."""
    system_user_id = None
    _upsert_batches(system_user_id)

    coding_questions = [
        _upsert_question(system_user_id, {
            "title": "Two Sum Indices",
            "description": "Given n integers and a target value, print the 0-based indices of two numbers whose sum equals the target. If no pair exists, print -1.",
            "type": "coding",
            "module_type": "CodePractice",
            "difficulty": "easy",
            "tags": ["arrays", "hashmap", "python", "java"],
            "test_cases": [
                {"input": "4\n2 7 11 15\n9\n", "output": "0 1"},
                {"input": "5\n3 2 4 8 10\n6\n", "output": "1 2"},
                {"input": "3\n1 2 3\n10\n", "output": "-1"},
            ],
            "starter_code": "n = int(input())\narr = list(map(int, input().split()))\ntarget = int(input())\n# print the answer\n",
            "solution": "n = int(input())\narr = list(map(int, input().split()))\ntarget = int(input())\nseen = {}\nfor i, value in enumerate(arr):\n    need = target - value\n    if need in seen:\n        print(seen[need], i)\n        break\n    seen[value] = i\nelse:\n    print(-1)\n",
        }),
        _upsert_question(system_user_id, {
            "title": "Count Vowels in a String",
            "description": "Read a string and print the number of vowels in it. Count both uppercase and lowercase vowels.",
            "type": "coding",
            "module_type": "CodePractice",
            "difficulty": "easy",
            "tags": ["strings", "basics", "python", "java"],
            "test_cases": [
                {"input": "Audisankara\n", "output": "5"},
                {"input": "JAVA programming\n", "output": "5"},
                {"input": "rhythm\n", "output": "0"},
            ],
            "starter_code": "s = input()\n# count vowels and print the count\n",
            "solution": "s = input()\nprint(sum(1 for ch in s if ch.lower() in 'aeiou'))\n",
        }),
        _upsert_question(system_user_id, {
            "title": "Second Largest Number",
            "description": "Given n integers, print the second largest distinct number. If it does not exist, print -1.",
            "type": "coding",
            "module_type": "CodePractice",
            "difficulty": "medium",
            "tags": ["arrays", "sorting", "edge-cases"],
            "test_cases": [
                {"input": "5\n10 20 4 45 99\n", "output": "45"},
                {"input": "4\n7 7 7 7\n", "output": "-1"},
                {"input": "6\n-1 -5 -2 -2 -9 -3\n", "output": "-2"},
            ],
            "starter_code": "n = int(input())\narr = list(map(int, input().split()))\n# print the second largest distinct number\n",
            "solution": "n = int(input())\narr = sorted(set(map(int, input().split())))\nprint(arr[-2] if len(arr) >= 2 else -1)\n",
        }),
    ]

    non_technical_questions = [
        _upsert_question(system_user_id, {
            "title": "OOP Encapsulation",
            "description": "Which OOP concept binds data and methods together and restricts direct access to internal state?",
            "type": "mcq",
            "module_type": "Non-Technical",
            "difficulty": "easy",
            "tags": ["oops", "java"],
            "options": ["Inheritance", "Encapsulation", "Polymorphism", "Abstraction"],
            "correct_answer": "B",
            "marks": 2,
        }),
        _upsert_question(system_user_id, {
            "title": "SQL Primary Key",
            "description": "What is the main purpose of a primary key in a relational database table?",
            "type": "mcq",
            "module_type": "Non-Technical",
            "difficulty": "easy",
            "tags": ["sql", "dbms"],
            "options": ["To allow duplicate rows", "To uniquely identify each row", "To encrypt the table", "To store only text values"],
            "correct_answer": "B",
            "marks": 2,
        }),
        _upsert_question(system_user_id, {
            "title": "Python List Mutability",
            "description": "Which statement about Python lists is correct?",
            "type": "mcq",
            "module_type": "Non-Technical",
            "difficulty": "easy",
            "tags": ["python", "data-structures"],
            "options": ["Lists are immutable", "Lists can store only integers", "Lists are ordered and mutable", "Lists cannot contain duplicates"],
            "correct_answer": "C",
            "marks": 2,
        }),
        _upsert_question(system_user_id, {
            "title": "HR Interview Strength",
            "description": "In an HR interview, what is the best way to answer 'Tell me about your strength'?",
            "type": "mcq",
            "module_type": "Non-Technical",
            "difficulty": "medium",
            "tags": ["hr", "communication"],
            "options": ["Give a generic one-word answer", "Share a strength with a brief real example", "Say you have no strengths", "Only discuss salary expectations"],
            "correct_answer": "B",
            "marks": 2,
        }),
        _upsert_question(system_user_id, {
            "title": "Aptitude Percentage Increase",
            "description": "A number is increased from 80 to 100. What is the percentage increase?",
            "type": "mcq",
            "module_type": "Non-Technical",
            "difficulty": "easy",
            "tags": ["aptitude", "percentages"],
            "options": ["20%", "25%", "30%", "40%"],
            "correct_answer": "B",
            "marks": 2,
        }),
        _upsert_question(system_user_id, {
            "title": "Professional Email Closing",
            "description": "Which closing is most appropriate for a professional email to a recruiter?",
            "type": "mcq",
            "module_type": "Non-Technical",
            "difficulty": "easy",
            "tags": ["communication", "hr"],
            "options": ["Bye", "Regards", "See ya", "Whatever"],
            "correct_answer": "B",
            "marks": 2,
        }),
    ]

    quiz = _upsert_quiz(
        system_user_id,
        "Python Java SQL Basics Quiz",
        "A quick placement-prep quiz covering Python fundamentals, Java OOP, SQL keys, and HR communication.",
        non_technical_questions[:4],
    )

    assessment = _upsert_assessment(
        system_user_id,
        "Placement Readiness Mixed Assessment",
        "Practice assessment with coding and non-technical questions for Python, Java, SQL, and aptitude preparation.",
        coding_questions[:2] + non_technical_questions[:3],
    )

    _upsert_note(system_user_id, "Python Notes", "Core Python revision notes for placement preparation.", ["python", "notes", "placement"], """
Python Notes

1. Variables are dynamically typed. Use clear names and avoid shadowing built-ins.
2. Lists are ordered and mutable. Tuples are ordered and immutable.
3. Dictionaries provide average O(1) lookup and are useful for frequency maps.
4. Use functions to separate input parsing, logic, and output.
5. Common interview patterns: two pointers, hashing, sorting, stack, queue, recursion.
6. Handle edge cases: empty input, duplicates, negative values, and single-element arrays.
7. Prefer for item in collection when the index is not needed.
8. Use set for uniqueness and membership checks.
9. Exceptions should be specific where possible.
10. Practice writing clean code with simple variable names and comments only when helpful.
""")

    _upsert_note(system_user_id, "Java Notes", "Java OOP and core language notes for interviews and coding rounds.", ["java", "oops", "notes"], """
Java Notes

1. Java is statically typed and object-oriented.
2. Encapsulation keeps fields private and exposes controlled access through methods.
3. Inheritance reuses behavior from a parent class; use it only for true is-a relationships.
4. Polymorphism lets the same method call behave differently based on the object.
5. Interfaces define contracts; classes can implement multiple interfaces.
6. ArrayList is good for dynamic arrays; HashMap is good for key-value lookup.
7. String is immutable; use StringBuilder for repeated modifications.
8. Understand equals vs ==: equals compares content when implemented, == compares references for objects.
9. Checked exceptions must be handled or declared.
10. For coding rounds, write a public class Main and parse input using Scanner or BufferedReader.
""")

    _upsert_note(system_user_id, "Database SQL Notes", "SQL and DBMS notes covering keys, joins, normalization, and query basics.", ["sql", "database", "dbms", "notes"], """
Database SQL Notes

1. A primary key uniquely identifies each row and cannot be null.
2. A foreign key links a row to a primary key in another table.
3. Use SELECT with WHERE to filter rows.
4. INNER JOIN returns matching rows from both tables.
5. LEFT JOIN returns all rows from the left table and matching rows from the right table.
6. GROUP BY groups rows for aggregate functions such as COUNT, SUM, AVG, MIN, and MAX.
7. HAVING filters grouped results; WHERE filters rows before grouping.
8. Normalization reduces redundancy and update anomalies.
9. Indexes speed up reads but can slow down writes.
10. Transactions use ACID properties: Atomicity, Consistency, Isolation, Durability.
""")

    company_posts = []
    company_seed_data = [
        {
            "name": "TCS",
            "description": "Tata Consultancy Services is a major IT services and consulting company. Prepare for aptitude, programming basics, SQL, project discussion, and HR communication.",
            "question": "In a TCS technical interview, which topic is most important to revise for a fresher software role?",
            "options": ["Only company history", "Programming basics, SQL, OOP, and project explanation", "Only salary negotiation", "Only UI design tools"],
            "correct_answer": "B",
            "content": "Common focus: aptitude, coding basics, OOP, DBMS, SDLC, final-year project, communication, and willingness to learn.\nPractice answer tip: explain your project with problem statement, tech stack, your contribution, and result.",
            "tags": ["tcs", "service-company", "aptitude", "oops", "sql"],
        },
        {
            "name": "Infosys",
            "description": "Infosys is a global IT services and consulting company. Campus preparation usually benefits from logical reasoning, pseudocode, DBMS, Java/Python basics, and HR readiness.",
            "question": "Which answer best fits an Infosys-style project discussion?",
            "options": ["I do not remember my project", "Explain the problem, modules, database, role, and learning clearly", "Only name the project title", "Talk only about marks"],
            "correct_answer": "B",
            "content": "Common focus: logical ability, problem solving, programming fundamentals, DBMS, software engineering basics, and project confidence.\nPractice answer tip: prepare a 60-second project summary before the interview.",
            "tags": ["infosys", "project", "dbms", "pseudocode"],
        },
        {
            "name": "Wipro",
            "description": "Wipro is an IT services, consulting, and business process company. Prepare for aptitude, coding basics, verbal ability, OOP, SQL, and scenario-based HR questions.",
            "question": "For Wipro placement interviews, what is the best way to answer a strengths question?",
            "options": ["Give a strength with a real academic or project example", "Say every strength possible", "Avoid answering", "Discuss only hobbies"],
            "correct_answer": "A",
            "content": "Common focus: aptitude, verbal communication, programming fundamentals, DBMS, project explanation, and HR attitude.\nPractice answer tip: use STAR format for HR answers: Situation, Task, Action, Result.",
            "tags": ["wipro", "hr", "communication", "aptitude"],
        },
        {
            "name": "Accenture",
            "description": "Accenture is a global professional services company with technology, consulting, cloud, and operations roles. Prepare for communication, problem solving, coding basics, and business awareness.",
            "question": "What should a candidate highlight for an Accenture technology role?",
            "options": ["Only personal details", "Adaptability, communication, technical basics, and project ownership", "Only preferred location", "Only memorized definitions"],
            "correct_answer": "B",
            "content": "Common focus: communication, business mindset, scenario questions, programming basics, cloud awareness, and teamwork examples.\nPractice answer tip: connect your technical skills to practical problem solving.",
            "tags": ["accenture", "communication", "technology", "cloud"],
        },
        {
            "name": "Capgemini",
            "description": "Capgemini is a consulting, technology services, and digital transformation company. Prepare for pseudocode, English communication, game-based aptitude, OOP, SQL, and project questions.",
            "question": "Which preparation area is most useful for Capgemini technical screening?",
            "options": ["Pseudocode, OOP, SQL, and project explanation", "Only sports news", "Only typing speed", "Only resume font style"],
            "correct_answer": "A",
            "content": "Common focus: pseudocode, aptitude, communication, Java/Python basics, SQL joins, and final-year project clarity.\nPractice answer tip: revise flowcharts, loops, conditionals, and basic data structures.",
            "tags": ["capgemini", "pseudocode", "oops", "sql"],
        },
        {
            "name": "Cognizant",
            "description": "Cognizant is an IT services and consulting company. Prepare for coding fundamentals, database concepts, testing basics, communication, and real project examples.",
            "question": "Which response is strongest when asked about a bug in your project?",
            "options": ["Blame another teammate", "Explain the issue, debugging steps, fix, and learning", "Say no bug ever occurred", "Change the topic"],
            "correct_answer": "B",
            "content": "Common focus: programming basics, SQL, testing mindset, project contribution, teamwork, and HR confidence.\nPractice answer tip: prepare one real challenge from your project and how you solved it.",
            "tags": ["cognizant", "debugging", "testing", "project"],
        },
        {
            "name": "Amazon",
            "description": "Amazon hires for software, support, operations, and cloud-related roles. For technical roles, prepare data structures, algorithms, problem solving, and behavioral examples.",
            "question": "For an Amazon SDE-style interview, which topic should be prioritized?",
            "options": ["Data structures, algorithms, complexity, and behavioral examples", "Only resume color", "Only company logo", "Only memorized HR answers"],
            "correct_answer": "A",
            "content": "Common focus: arrays, strings, hash maps, trees, recursion, time complexity, edge cases, and leadership-principle style behavioral answers.\nPractice answer tip: always explain brute force first, then optimize.",
            "tags": ["amazon", "dsa", "algorithms", "behavioral"],
        },
        {
            "name": "Microsoft",
            "description": "Microsoft is a global software, cloud, and productivity technology company. Prepare for problem solving, clean code, system thinking, debugging, and collaboration examples.",
            "question": "What makes a coding answer stronger in a Microsoft-style interview?",
            "options": ["Silent coding only", "Clear approach, edge cases, complexity, and readable code", "Ignoring constraints", "Only using the longest code"],
            "correct_answer": "B",
            "content": "Common focus: DSA, clean code, debugging, design thinking, communication, and learning mindset.\nPractice answer tip: speak your approach, confirm constraints, then code step by step.",
            "tags": ["microsoft", "dsa", "clean-code", "debugging"],
        },
        {
            "name": "Google",
            "description": "Google is a technology company known for search, cloud, Android, AI, and large-scale systems. Prepare for algorithms, data structures, reasoning, and precise communication.",
            "question": "Which habit is most important in a Google-style problem-solving interview?",
            "options": ["Jump directly to code without explanation", "Clarify constraints, discuss approach, analyze complexity, then implement", "Avoid testing", "Memorize only one solution"],
            "correct_answer": "B",
            "content": "Common focus: algorithms, data structures, complexity analysis, edge cases, and clear reasoning.\nPractice answer tip: after solving, test with a normal case, edge case, and failure case.",
            "tags": ["google", "algorithms", "complexity", "problem-solving"],
        },
        {
            "name": "Deloitte",
            "description": "Deloitte provides consulting, technology, audit, risk, and advisory services. Prepare for communication, case-style thinking, technical basics, SQL, and business scenarios.",
            "question": "For a Deloitte technology consulting interview, which answer style is best?",
            "options": ["Technical point plus business impact and clear communication", "Only one-word answers", "Only coding syntax", "Avoid examples"],
            "correct_answer": "A",
            "content": "Common focus: communication, business understanding, SQL, analytics basics, teamwork, client scenarios, and role clarity.\nPractice answer tip: connect your technical solution to user or business value.",
            "tags": ["deloitte", "consulting", "business", "sql"],
        },
    ]

    for item in company_seed_data:
        company = _upsert_company(item["name"], item["description"])
        company_posts.append(_upsert_company_interview_post(
            company=company,
            question=item["question"],
            options=item["options"],
            correct_answer=item["correct_answer"],
            content=item["content"],
            tags=item["tags"],
        ))

    db.session.commit()
    print(
        "[Seed] Added/updated demo content: "
        f"{len(coding_questions)} coding questions, "
        f"{len(non_technical_questions)} non-technical questions, "
        f"quiz #{quiz.id}, assessment #{assessment.id}, 3 notes resources, "
        f"and {len(company_posts)} company interview questions."
    )
