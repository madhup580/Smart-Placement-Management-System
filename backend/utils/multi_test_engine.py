"""
Multi-Test Engine - Comprehensive Test Case Execution
Runs multiple test case types: normal, edge, extreme, invalid, empty
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from utils.industry_compiler import TestCase, DockerSandbox
from utils.judge_v2 import execute_submit_mode
import json


@dataclass
class TestResult:
    """Test execution result"""
    test_type: str
    input_data: str
    expected_output: Optional[str]
    actual_output: str
    passed: bool
    execution_time: float
    memory_used: float
    status: str  # 'accepted', 'wrong_answer', 'runtime_error', 'timeout'
    error_message: Optional[str] = None
    description: str = ""


class MultiTestEngine:
    """
    Multi-Test Engine
    Executes code against multiple test case types for comprehensive evaluation
    """
    
    def __init__(self):
        self.sandbox = DockerSandbox()
    
    def run_all_tests(
        self,
        code: str,
        language: str,
        test_cases: List[TestCase],
        original_test_cases: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Run code against all test cases (normal, edge, extreme, invalid, empty)
        
        Args:
            code: User's code
            language: Programming language
            test_cases: Generated test cases (from TestCaseGenerator)
            original_test_cases: Original hidden test cases from question
        
        Returns:
            {
                'total_tests': int,
                'passed': int,
                'failed': int,
                'results': List[TestResult],
                'summary': {
                    'normal': {'passed': int, 'total': int},
                    'edge': {'passed': int, 'total': int},
                    'extreme': {'passed': int, 'total': int},
                    'invalid': {'passed': int, 'total': int},
                    'empty': {'passed': int, 'total': int}
                },
                'overall_status': str
            }
        """
        all_results = []
        
        # 1. Run original test cases (hidden from user)
        if original_test_cases:
            for test_case in original_test_cases:
                result = self._execute_test(
                    code, language,
                    test_case.get('input', ''),
                    test_case.get('expected_output', ''),
                    'original',
                    'Original test case'
                )
                all_results.append(result)
        
        # 2. Run generated test cases (normal, edge, extreme, invalid, empty)
        for test_case in test_cases:
            result = self._execute_test(
                code, language,
                test_case.input_data,
                test_case.expected_output,
                test_case.test_type,
                test_case.description
            )
            all_results.append(result)
        
        # 3. Calculate summary
        summary = self._calculate_summary(all_results)
        
        # 4. Determine overall status
        overall_status = self._determine_overall_status(all_results, summary)
        
        return {
            'total_tests': len(all_results),
            'passed': sum(1 for r in all_results if r.passed),
            'failed': sum(1 for r in all_results if not r.passed),
            'results': [
                {
                    'test_type': r.test_type,
                    'input': r.input_data,
                    'expected_output': r.expected_output,
                    'actual_output': r.actual_output,
                    'passed': r.passed,
                    'status': r.status,
                    'execution_time': r.execution_time,
                    'memory_used': r.memory_used,
                    'error_message': r.error_message,
                    'description': r.description
                }
                for r in all_results
            ],
            'summary': summary,
            'overall_status': overall_status
        }
    
    def _execute_test(
        self,
        code: str,
        language: str,
        input_data: str,
        expected_output: Optional[str],
        test_type: str,
        description: str
    ) -> TestResult:
        """Execute a single test case"""
        try:
            # Execute code with input
            result = self.sandbox.execute(
                code=code,
                language=language,
                stdin=input_data,
                timeout=5
            )
            
            actual_output = result.get('output', '').strip()
            status = result.get('status', 'runtime_error')
            execution_time = result.get('execution_time', 0.0)
            memory_used = result.get('memory_used', 0.0)
            
            # Determine if test passed
            passed = False
            error_message = None
            
            if status == 'accepted':
                if expected_output:
                    # Compare outputs
                    passed = self._compare_outputs(actual_output, expected_output)
                else:
                    # No expected output - just check if it ran without error
                    passed = True
            elif status == 'timeout':
                error_message = 'Execution timeout'
            elif status == 'runtime_error':
                error_message = actual_output or 'Runtime error'
            else:
                error_message = f'Status: {status}'
            
            return TestResult(
                test_type=test_type,
                input_data=input_data,
                expected_output=expected_output,
                actual_output=actual_output,
                passed=passed,
                execution_time=execution_time,
                memory_used=memory_used,
                status=status,
                error_message=error_message,
                description=description
            )
            
        except Exception as e:
            return TestResult(
                test_type=test_type,
                input_data=input_data,
                expected_output=expected_output,
                actual_output='',
                passed=False,
                execution_time=0.0,
                memory_used=0.0,
                status='error',
                error_message=str(e),
                description=description
            )
    
    def _compare_outputs(self, actual: str, expected: str) -> bool:
        """Compare actual and expected outputs"""
        # Normalize whitespace
        actual = actual.strip()
        expected = expected.strip()
        
        # Direct comparison
        if actual == expected:
            return True
        
        # Try numeric comparison (for floating point)
        try:
            actual_num = float(actual)
            expected_num = float(expected)
            return abs(actual_num - expected_num) < 1e-9
        except ValueError:
            pass
        
        # Try list/array comparison
        try:
            import ast
            actual_list = ast.literal_eval(actual)
            expected_list = ast.literal_eval(expected)
            return actual_list == expected_list
        except (ValueError, SyntaxError):
            pass
        
        return False
    
    def _calculate_summary(self, results: List[TestResult]) -> Dict:
        """Calculate summary by test type"""
        summary = {
            'normal': {'passed': 0, 'total': 0},
            'edge': {'passed': 0, 'total': 0},
            'extreme': {'passed': 0, 'total': 0},
            'invalid': {'passed': 0, 'total': 0},
            'empty': {'passed': 0, 'total': 0},
            'original': {'passed': 0, 'total': 0}
        }
        
        for result in results:
            test_type = result.test_type
            if test_type in summary:
                summary[test_type]['total'] += 1
                if result.passed:
                    summary[test_type]['passed'] += 1
        
        return summary
    
    def _determine_overall_status(self, results: List[TestResult], summary: Dict) -> str:
        """Determine overall test status"""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        
        if total == 0:
            return 'no_tests'
        
        if passed == total:
            return 'all_passed'
        elif passed == 0:
            return 'all_failed'
        elif passed >= total * 0.8:
            return 'mostly_passed'
        elif passed >= total * 0.5:
            return 'partially_passed'
        else:
            return 'mostly_failed'
