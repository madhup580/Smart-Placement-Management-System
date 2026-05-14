"""
Coding routes for live coding practice
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Question, CodeSubmission, db
from utils.auth import role_required
from utils.compiler import execute_code, run_test_cases
from utils.judge_v2 import (
    ExecutionMode,
    execute_run_mode,
    execute_submit_mode
)
from utils.code_intelligence_engine import analyze_code_intelligence
from utils.industry_compiler import (
    analyze_code_comprehensive,
    DockerSandbox,
    TestCaseGenerator
)
from utils.multi_test_engine import MultiTestEngine
from utils.leaderboard import update_leaderboard
import json
from typing import Dict, List

coding_bp = Blueprint('coding', __name__)

@coding_bp.route('/questions', methods=['GET'])
@jwt_required()
def list_questions():
    """List active coding questions for practice pages."""
    try:
        difficulty = request.args.get('difficulty')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        query = Question.query.filter_by(
            type='coding',
            module_type='CodePractice',
            is_active=True
        )

        if difficulty:
            query = query.filter_by(difficulty=difficulty)

        questions = query.order_by(Question.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'questions': [q.to_dict(hide_test_cases=False) for q in questions.items],
            'total': questions.total,
            'page': page,
            'per_page': per_page,
            'pages': questions.pages
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_comprehensive_feedback(
    execution_result: Dict, 
    comprehensive_analysis: Dict,
    generated_test_results: List[Dict]
) -> Dict:
    """
    Generate comprehensive interview-style feedback from industry-standard analysis
    """
    passed = execution_result.get('passed', 0)
    total = execution_result.get('total', 0)
    status = execution_result.get('status', 'wrong_answer')
    
    # Extract metrics from comprehensive analysis
    time_complexity = comprehensive_analysis.get('time_complexity', {}).get('complexity', 'Unknown')
    memory_usage = comprehensive_analysis.get('memory_usage', {}).get('complexity', 'Unknown')
    quality_score = comprehensive_analysis.get('quality_score', {}).get('overall', 0)
    best_practices = comprehensive_analysis.get('best_practices', {})
    violations = best_practices.get('violations', [])
    
    feedback_parts = []
    
    # Correctness feedback
    if status == 'accepted' and passed == total:
        feedback_parts.append("✅ Your solution is correct and passes all test cases.")
    elif status == 'accepted' and passed < total:
        feedback_parts.append(f"⚠️ Your solution passes {passed}/{total} test cases. Consider edge cases.")
    elif status == 'wrong_answer':
        feedback_parts.append("❌ Your solution produces incorrect output. Review your logic.")
    elif status == 'time_limit_exceeded':
        feedback_parts.append("⏱️ Your solution exceeds the time limit. Consider optimizing the algorithm.")
    elif status == 'runtime_error':
        feedback_parts.append("💥 Runtime error detected. Check for null pointers, array bounds, and edge cases.")
    else:
        feedback_parts.append(f"Status: {status}")
    
    # Time complexity feedback
    if time_complexity and time_complexity != 'Unknown':
        if 'O(n²)' in time_complexity or 'O(2^n)' in time_complexity:
            feedback_parts.append(f"⚠️ Time complexity is {time_complexity}. This may not scale well for large inputs.")
        elif 'O(n log n)' in time_complexity:
            feedback_parts.append(f"✓ Time complexity is {time_complexity}, which is efficient for most cases.")
        else:
            feedback_parts.append(f"Time complexity: {time_complexity}")
    
    # Memory usage feedback
    if memory_usage and memory_usage != 'Unknown':
        if 'O(n²)' in memory_usage:
            feedback_parts.append(f"⚠️ Memory usage is {memory_usage}. Consider optimizing for large inputs.")
        else:
            feedback_parts.append(f"Memory usage: {memory_usage}")
    
    # Quality feedback
    if quality_score >= 80:
        feedback_parts.append("✓ Code quality is excellent - well-structured and readable.")
    elif quality_score >= 60:
        feedback_parts.append("Code quality is good, but there's room for improvement.")
    else:
        feedback_parts.append("⚠️ Code quality needs improvement. Focus on readability and modularity.")
    
    # Best practices feedback
    if violations:
        high_severity = [v for v in violations if v.get('severity') == 'high']
        if high_severity:
            feedback_parts.append(f"⚠️ Critical issues: {high_severity[0].get('message', '')}")
    
    # Generated test case results
    edge_case_passed = sum(1 for r in generated_test_results if r.get('status') == 'accepted' and r.get('test_type') == 'edge')
    edge_case_total = sum(1 for r in generated_test_results if r.get('test_type') == 'edge')
    if edge_case_total > 0:
        if edge_case_passed == edge_case_total:
            feedback_parts.append("✓ All edge cases passed.")
        else:
            feedback_parts.append(f"⚠️ Edge cases: {edge_case_passed}/{edge_case_total} passed.")
    
    # Interview perspective
    if status == 'accepted' and passed == total:
        if 'O(n²)' in time_complexity:
            feedback_parts.append("💼 Interview perspective: While your solution works, in production it may fail for large inputs due to O(n²) complexity. Can you optimize it?")
        elif quality_score < 70:
            feedback_parts.append("💼 Interview perspective: The solution works, but consider improving code structure and error handling for production readiness.")
        else:
            feedback_parts.append("💼 Interview perspective: Solid solution! Well done.")
    
    return {
        'feedback': ' '.join(feedback_parts),
        'overall_assessment': 'Excellent' if (status == 'accepted' and passed == total and quality_score >= 80) else 'Good' if (status == 'accepted' and passed == total) else 'Needs Improvement',
        'suggestions': best_practices.get('suggestions', [])[:5]
    }

def generate_interview_feedback(execution_result: Dict, code_intelligence: Dict) -> Dict:
    """
    Generate interview-style feedback like a real interviewer
    """
    passed = execution_result.get('passed', 0)
    total = execution_result.get('total', 0)
    status = execution_result.get('status', 'wrong_answer')
    
    intelligence = code_intelligence.get('summary', {})
    quality_score = code_intelligence.get('code_quality', {}).get('quality_score', 0)
    time_complexity = code_intelligence.get('time_complexity', {}).get('complexity', 'Unknown')
    best_practices = code_intelligence.get('best_practices', {})
    optimizations = code_intelligence.get('optimizations', {})
    
    feedback_parts = []
    
    # Correctness feedback
    if status == 'accepted' and passed == total:
        feedback_parts.append("✅ Your solution is correct and passes all test cases.")
    elif status == 'accepted' and passed < total:
        feedback_parts.append(f"⚠️ Your solution passes {passed}/{total} test cases. Consider edge cases.")
    elif status == 'wrong_answer':
        feedback_parts.append("❌ Your solution produces incorrect output. Review your logic.")
    elif status == 'time_limit_exceeded':
        feedback_parts.append("⏱️ Your solution exceeds the time limit. Consider optimizing the algorithm.")
    elif status == 'runtime_error':
        feedback_parts.append("💥 Runtime error detected. Check for null pointers, array bounds, and edge cases.")
    else:
        feedback_parts.append(f"Status: {status}")
    
    # Complexity feedback
    if time_complexity and time_complexity != 'Unknown':
        if 'O(n²)' in time_complexity or 'O(2^n)' in time_complexity:
            feedback_parts.append(f"⚠️ Time complexity is {time_complexity}. This may not scale well for large inputs.")
        elif 'O(n log n)' in time_complexity:
            feedback_parts.append(f"✓ Time complexity is {time_complexity}, which is efficient for most cases.")
        else:
            feedback_parts.append(f"Time complexity: {time_complexity}")
    
    # Quality feedback
    if quality_score >= 80:
        feedback_parts.append("✓ Code quality is excellent - well-structured and readable.")
    elif quality_score >= 60:
        feedback_parts.append("Code quality is good, but there's room for improvement.")
    else:
        feedback_parts.append("⚠️ Code quality needs improvement. Focus on readability and modularity.")
    
    # Best practices feedback
    violations = best_practices.get('violations', [])
    if violations:
        high_severity = [v for v in violations if v.get('severity') == 'high']
        if high_severity:
            feedback_parts.append(f"⚠️ Critical issues: {high_severity[0].get('message', '')}")
    
    # Optimization suggestions
    opt_suggestions = optimizations.get('optimizations', [])
    if opt_suggestions:
        high_priority = [o for o in opt_suggestions if o.get('priority') == 'high']
        if high_priority:
            feedback_parts.append(f"💡 Optimization: {high_priority[0].get('suggestion', '')}")
    
    # Interview perspective
    if status == 'accepted' and passed == total:
        if 'O(n²)' in time_complexity:
            feedback_parts.append("💼 Interview perspective: While your solution works, in production it may fail for large inputs due to O(n²) complexity. Can you optimize it?")
        elif quality_score < 70:
            feedback_parts.append("💼 Interview perspective: The solution works, but consider improving code structure and error handling for production readiness.")
        else:
            feedback_parts.append("💼 Interview perspective: Solid solution! Well done.")
    
    return {
        'feedback': ' '.join(feedback_parts),
        'overall_assessment': 'Excellent' if (status == 'accepted' and passed == total and quality_score >= 80) else 'Good' if (status == 'accepted' and passed == total) else 'Needs Improvement',
        'suggestions': best_practices.get('suggestions', []) + [o.get('suggestion', '') for o in opt_suggestions[:2]]
    }

@coding_bp.route('/questions/<int:question_id>', methods=['GET'])
@jwt_required()
def get_question(question_id):
    """
    Get coding question details
    Show full test cases to every authenticated role for practice/demo use.
    """
    try:
        question = Question.query.get_or_404(question_id)
        
        if question.type != 'coding':
            return jsonify({'error': 'Not a coding question'}), 400
        
        return jsonify({
            'question': question.to_dict(hide_test_cases=False)
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@coding_bp.route('/execute', methods=['POST'])
@jwt_required()
def execute():
    """
    RUN MODE: Practice execution
    - Allow main() or equivalent
    - Execute code normally
    - Capture and show stdout
    - Do not judge correctness strictly
    """
    try:
        data = request.get_json()
        code = data.get('code')
        language = data.get('language')
        stdin = data.get('stdin', '')
        question_id = data.get('question_id')
        
        if not code or not language:
            return jsonify({'error': 'Code and language required'}), 400
        
        if language not in ['c', 'cpp', 'python', 'java']:
            return jsonify({'error': 'Unsupported language'}), 400
        
        # Get sample input from first test case if question_id provided
        sample_input = None
        if question_id:
            question = Question.query.get(question_id)
            if question and question.test_cases:
                test_cases = json.loads(question.test_cases) if isinstance(question.test_cases, str) else question.test_cases
                if test_cases:
                    sample_input = test_cases[0].get('input')
        
        # Execute in RUN mode - just execute code, show output
        # Run mode = user program controls input/output (like normal compiler)
        result = execute_run_mode(code, language, stdin, sample_input)
        
        # ===== AST + STATIC ANALYSIS + QUALITY SCORING =====
        # Get question description for context
        question_description = None
        if question_id:
            question = Question.query.get(question_id)
            if question:
                question_description = question.description or question.title or ""
        
        # Full industry-standard analysis (AST + Static Analysis + Quality)
        comprehensive_analysis = analyze_code_comprehensive(
            code=code,
            language=language,
            question_description=question_description
        )
        
        # Include comprehensive analysis in result
        result['ast_analysis'] = comprehensive_analysis.get('ast_analysis', {})
        result['static_analysis'] = {
            'loops': comprehensive_analysis.get('ast_analysis', {}).get('loops', []),
            'recursions': comprehensive_analysis.get('ast_analysis', {}).get('recursions', []),
            'data_structures': comprehensive_analysis.get('ast_analysis', {}).get('data_structures', []),
            'functions': comprehensive_analysis.get('ast_analysis', {}).get('functions', []),
            'nesting_depth': comprehensive_analysis.get('ast_analysis', {}).get('nesting_depth', 0)
        }
        result['time_complexity'] = comprehensive_analysis.get('time_complexity', {})
        result['memory_usage'] = comprehensive_analysis.get('memory_usage', {})
        result['quality_score'] = comprehensive_analysis.get('quality_score', {})
        result['best_practices'] = comprehensive_analysis.get('best_practices', {})
        
        # Backward compatibility
        code_intelligence = analyze_code_intelligence(code, language)
        result['code_intelligence'] = code_intelligence
        # ===== END AST + STATIC ANALYSIS + QUALITY SCORING =====
        
        # Format output - if empty, show "(no output)"
        if not result.get('output') or result.get('output').strip() == '':
            result['output'] = '(no output)'
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@coding_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit():
    """
    LeetCode-style SUBMIT MODE: Judge code against hidden test cases
    - Execute code in sandboxed environment (Piston API)
    - Run against ALL hidden test cases
    - Return proper verdicts: Accepted, Wrong Answer, Runtime Error, etc.
    - Do NOT expose test case details to students
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        question_id = data.get('question_id')
        code = data.get('code')
        language = data.get('language')
        
        if not question_id or not code or not language:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if language not in ['c', 'cpp', 'python', 'java']:
            return jsonify({'error': 'Unsupported language'}), 400
        
        question = Question.query.get_or_404(question_id)
        
        if question.type != 'coding':
            return jsonify({'error': 'Not a coding question'}), 400
        
        # Get test cases (hidden from user)
        test_cases = json.loads(question.test_cases) if isinstance(question.test_cases, str) else (question.test_cases or [])
        
        if not test_cases:
            return jsonify({'error': 'No test cases available'}), 400
        
        # ===== CORE JUDGING =====
        question_description = question.description or question.title or ""
        
        # Judge against the question's stored test cases first. This is the
        # source of truth for accept/wrong-answer and must not depend on any
        # optional analysis pipeline.
        execution_result = execute_submit_mode(code, language, test_cases)

        # ===== OPTIONAL ANALYSIS =====
        # These enrich the report but should never make a valid submission fail
        # with API error 500 during a demo.
        comprehensive_analysis = {}
        generated_test_results = []
        multi_test_results = {'results': [], 'summary': {}, 'overall_status': execution_result.get('status')}
        code_intelligence = {}
        interview_feedback = {}

        try:
            comprehensive_analysis = analyze_code_comprehensive(
                code=code,
                language=language,
                question_description=question_description
            )
        except Exception as analysis_error:
            current_app.logger.warning(f'Optional code analysis failed: {analysis_error}', exc_info=True)

        try:
            generated_test_cases = TestCaseGenerator.generate(question_description, language)
            multi_test_engine = MultiTestEngine()
            multi_test_results = multi_test_engine.run_all_tests(
                code=code,
                language=language,
                test_cases=generated_test_cases,
                original_test_cases=[]
            )
            generated_test_results = [
                r for r in multi_test_results.get('results', [])
                if r.get('test_type') != 'original'
            ]
        except Exception as test_error:
            current_app.logger.warning(f'Optional generated test execution failed: {test_error}', exc_info=True)

        try:
            code_intelligence = analyze_code_intelligence(code, language)
        except Exception as intelligence_error:
            current_app.logger.warning(f'Optional code intelligence failed: {intelligence_error}', exc_info=True)

        try:
            interview_feedback = generate_comprehensive_feedback(
                execution_result,
                comprehensive_analysis,
                generated_test_results
            )
        except Exception as feedback_error:
            current_app.logger.warning(f'Optional feedback generation failed: {feedback_error}', exc_info=True)
        
        # ===== END INDUSTRY-STANDARD ANALYSIS =====
        
        # Create submission record
        submission = CodeSubmission(
            user_id=user_id,
            question_id=question_id,
            language=language,
            code=code,
            output=json.dumps(execution_result.get('results', [])),
            status=execution_result.get('status', 'wrong_answer'),
            execution_time=execution_result.get('execution_time', 0.0),
            test_cases_passed=execution_result.get('passed', 0),
            total_test_cases=execution_result.get('total', 0)
        )
        
        # Store comprehensive analysis in output field (JSON)
        analysis_data = {
            'comprehensive_analysis': comprehensive_analysis,
            'interview_feedback': interview_feedback,
            'multi_test_results': multi_test_results
        }
        submission.output = json.dumps({
            'test_results': execution_result.get('results', []),
            'analysis': analysis_data
        })
        
        db.session.add(submission)
        db.session.commit()
        
        # Update leaderboard
        update_leaderboard(user_id)
        
        # ===== COMPREHENSIVE FINAL REPORT =====
        final_report = comprehensive_analysis.get('final_report', {})
        
        # Return comprehensive industry-standard report
        return jsonify({
            'submission': submission.to_dict(),
            'verdict': execution_result.get('verdict', 'Wrong Answer'),
            'message': execution_result.get('message', ''),
            'passed': execution_result.get('passed', 0),
            'total': execution_result.get('total', 0),
            'execution_time': execution_result.get('execution_time', 0.0),
            'status': execution_result.get('status', 'wrong_answer'),
            'test_cases_passed': execution_result.get('passed', 0),
            'total_test_cases': execution_result.get('total', 0),
            'test_results': execution_result.get('results', []),
            
            # Industry-standard analysis (AST + Static Analysis + Quality Scoring)
            'comprehensive_analysis': {
                'ast_analysis': comprehensive_analysis.get('ast_analysis', {}),
                'static_analysis': {
                    'loops': comprehensive_analysis.get('ast_analysis', {}).get('loops', []),
                    'recursions': comprehensive_analysis.get('ast_analysis', {}).get('recursions', []),
                    'data_structures': comprehensive_analysis.get('ast_analysis', {}).get('data_structures', []),
                    'functions': comprehensive_analysis.get('ast_analysis', {}).get('functions', []),
                    'nesting_depth': comprehensive_analysis.get('ast_analysis', {}).get('nesting_depth', 0)
                },
                'time_complexity': comprehensive_analysis.get('time_complexity', {}),
                'memory_usage': comprehensive_analysis.get('memory_usage', {}),
                'quality_score': comprehensive_analysis.get('quality_score', {}),
                'best_practices': comprehensive_analysis.get('best_practices', {}),
                'test_cases': comprehensive_analysis.get('test_cases', []),
                'multi_test_results': multi_test_results,  # Full multi-test engine results
                'generated_test_results': generated_test_results
            },
            
            # Final report (industry format with quality scoring)
            'final_report': {
                'output_status': final_report.get('output_status', 'Unknown'),
                'time_complexity': comprehensive_analysis.get('time_complexity', {}).get('complexity', 'Unknown'),
                'memory_usage': comprehensive_analysis.get('memory_usage', {}).get('complexity', 'Unknown'),
                'code_quality': f"{comprehensive_analysis.get('quality_score', {}).get('overall_score', 0)}/100",
                'quality_breakdown': {
                    'readability': comprehensive_analysis.get('quality_score', {}).get('readability', 0),
                    'modularity': comprehensive_analysis.get('quality_score', {}).get('modularity', 0),
                    'naming': comprehensive_analysis.get('quality_score', {}).get('naming', 0),
                    'structure': comprehensive_analysis.get('quality_score', {}).get('structure', 0),
                    'comments': comprehensive_analysis.get('quality_score', {}).get('comments', 0),
                    'error_handling': comprehensive_analysis.get('quality_score', {}).get('error_handling', 0)
                },
                'test_summary': multi_test_results.get('summary', {}),
                'edge_case_status': f"{multi_test_results.get('summary', {}).get('edge', {}).get('passed', 0)}/{multi_test_results.get('summary', {}).get('edge', {}).get('total', 0)}",
                'suggestions': comprehensive_analysis.get('best_practices', {}).get('suggestions', [])
            },
            
            # Backward compatibility
            'code_intelligence': code_intelligence,
            'interview_feedback': interview_feedback,
            
            # Test results (hidden test cases - minimal info)
            'results': [
                {
                    'test_case': r.get('test_case'),
                    'passed': r.get('passed'),
                    'verdict': r.get('verdict', 'Accepted' if r.get('passed') else 'Wrong Answer')
                }
                for r in execution_result.get('results', [])
            ]
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@coding_bp.route('/submissions', methods=['GET'])
@jwt_required()
def get_submissions():
    """Get user's code submissions"""
    try:
        user_id = get_jwt_identity()
        question_id = request.args.get('question_id')
        
        query = CodeSubmission.query.filter_by(user_id=user_id)
        
        if question_id:
            query = query.filter_by(question_id=question_id)
        
        submissions = query.order_by(CodeSubmission.submitted_at.desc()).all()
        
        return jsonify({
            'submissions': [s.to_dict() for s in submissions]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@coding_bp.route('/submissions/last', methods=['GET'])
@jwt_required()
def get_last_submission():
    """
    Get the last submitted code for a question
    LeetCode-style: Retrieve last submitted code into editor
    """
    try:
        user_id = get_jwt_identity()
        question_id = request.args.get('question_id')
        language = request.args.get('language')  # Optional: filter by language
        
        if not question_id:
            return jsonify({'error': 'question_id required'}), 400
        
        query = CodeSubmission.query.filter_by(
            user_id=user_id,
            question_id=question_id
        )
        
        if language:
            query = query.filter_by(language=language)
        
        # Get the most recent submission
        last_submission = query.order_by(CodeSubmission.submitted_at.desc()).first()
        
        if not last_submission:
            return jsonify({
                'submission': None,
                'message': 'No previous submission found'
            }), 200
        
        return jsonify({
            'submission': last_submission.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

