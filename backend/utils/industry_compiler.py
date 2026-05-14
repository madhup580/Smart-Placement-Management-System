"""
Industry-Standard Code Compiler & Evaluator
Complete pipeline: AST → Complexity → Memory → Test Cases → Quality → Best Practices → Report
"""

import ast
import re
import json
import subprocess
import tempfile
import os
import time
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from dataclasses import dataclass
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None
from utils.openai_client import get_openai_client

@dataclass
class ComplexityResult:
    """Time complexity analysis result"""
    complexity: str  # e.g., "O(n)", "O(n²)", "O(n log n)"
    explanation: str
    confidence: float  # 0.0-1.0
    indicators: List[str]  # What patterns led to this conclusion

@dataclass
class MemoryResult:
    """Memory usage analysis result"""
    complexity: str  # e.g., "O(n)", "O(n²)"
    explanation: str
    peak_usage_estimate: Optional[int]  # Bytes (if estimable)
    data_structures: List[Dict]  # List of data structures and their sizes

@dataclass
class TestCase:
    """Test case structure"""
    input_data: str
    expected_output: Optional[str]
    test_type: str  # "normal", "edge", "extreme", "invalid", "empty"
    description: str

@dataclass
class QualityScore:
    """Code quality metrics"""
    overall_score: int  # 0-100
    readability: int
    modularity: int
    naming: int
    structure: int
    comments: int
    error_handling: int

@dataclass
class BestPracticeViolation:
    """Best practice violation"""
    rule: str
    severity: str  # "high", "medium", "low"
    message: str
    line: Optional[int]
    suggestion: str

class ASTParser:
    """
    Advanced AST Parser for Python
    Extracts loops, recursion, data structures, nesting depth
    """
    
    def __init__(self):
        self.loops = []
        self.recursions = []
        self.data_structures = []
        self.functions = []
        self.nesting_depth = 0
        self.max_nesting = 0
        self.complexity_indicators = []
        
    def parse(self, code: str) -> Dict:
        """Parse Python code into structured AST"""
        try:
            tree = ast.parse(code)
            visitor = ASTVisitor(self)
            visitor.visit(tree)
            return self._get_structure()
        except SyntaxError as e:
            return {
                'valid': False,
                'error': f'Syntax error: {str(e)}',
                'line': e.lineno
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _get_structure(self) -> Dict:
        """Get parsed structure"""
        return {
            'valid': True,
            'loops': self.loops,
            'recursions': self.recursions,
            'data_structures': self.data_structures,
            'functions': self.functions,
            'nesting_depth': self.max_nesting,
            'complexity_indicators': self.complexity_indicators
        }

class ASTVisitor(ast.NodeVisitor):
    """AST visitor to extract code structure"""
    
    def __init__(self, parser: ASTParser):
        self.parser = parser
        self.current_depth = 0
        self.function_stack = []
        
    def visit_For(self, node):
        """Visit for loops"""
        self.current_depth += 1
        self.parser.max_nesting = max(self.parser.max_nesting, self.current_depth)
        
        # Detect nested loops
        is_nested = self.current_depth > 1
        
        loop_info = {
            'type': 'for',
            'line': node.lineno,
            'nested': is_nested,
            'iter': self._get_iter_type(node.iter)
        }
        self.parser.loops.append(loop_info)
        
        # Check for nested loops
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While)):
                self.parser.complexity_indicators.append('nested_loops')
        
        self.generic_visit(node)
        self.current_depth -= 1
    
    def visit_While(self, node):
        """Visit while loops"""
        self.current_depth += 1
        self.parser.max_nesting = max(self.parser.max_nesting, self.current_depth)
        
        loop_info = {
            'type': 'while',
            'line': node.lineno,
            'nested': self.current_depth > 1
        }
        self.parser.loops.append(loop_info)
        
        self.generic_visit(node)
        self.current_depth -= 1
    
    def visit_FunctionDef(self, node):
        """Visit function definitions"""
        func_info = {
            'name': node.name,
            'line': node.lineno,
            'args_count': len(node.args.args),
            'has_recursion': False
        }
        self.parser.functions.append(func_info)
        self.function_stack.append(node.name)
        
        # Check for recursion
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == node.name:
                    func_info['has_recursion'] = True
                    self.parser.recursions.append({
                        'function': node.name,
                        'line': node.lineno
                    })
                    self.parser.complexity_indicators.append('recursion')
        
        self.generic_visit(node)
        if self.function_stack:
            self.function_stack.pop()
    
    def visit_List(self, node):
        """Detect list comprehensions"""
        self.parser.data_structures.append({
            'type': 'list',
            'line': node.lineno if hasattr(node, 'lineno') else None
        })
        self.generic_visit(node)
    
    def visit_Dict(self, node):
        """Detect dictionaries"""
        self.parser.data_structures.append({
            'type': 'dict',
            'line': node.lineno if hasattr(node, 'lineno') else None
        })
        self.generic_visit(node)
    
    def visit_Set(self, node):
        """Detect sets"""
        self.parser.data_structures.append({
            'type': 'set',
            'line': node.lineno if hasattr(node, 'lineno') else None
        })
        self.generic_visit(node)
    
    def _get_iter_type(self, iter_node) -> str:
        """Get iteration type"""
        if isinstance(iter_node, ast.Call):
            if isinstance(iter_node.func, ast.Name):
                if iter_node.func.id == 'range':
                    return 'range'
                elif iter_node.func.id in ['enumerate', 'zip']:
                    return iter_node.func.id
        elif isinstance(iter_node, (ast.List, ast.Tuple)):
            return 'sequence'
        return 'unknown'

class TimeComplexityEstimator:
    """
    Estimates time complexity from AST analysis
    """
    
    @staticmethod
    def estimate(parsed_structure: Dict, code: str) -> ComplexityResult:
        """Estimate time complexity"""
        loops = parsed_structure.get('loops', [])
        recursions = parsed_structure.get('recursions', [])
        complexity_indicators = parsed_structure.get('complexity_indicators', [])
        
        # Count nested loops
        nested_count = sum(1 for loop in loops if loop.get('nested', False))
        total_loops = len(loops)
        
        # Determine complexity
        if 'nested_loops' in complexity_indicators:
            # Count nesting levels
            max_nesting = parsed_structure.get('nesting_depth', 0)
            if max_nesting >= 3:
                complexity = "O(n³)"
                explanation = f"Triple nested loops detected (depth: {max_nesting})"
            elif max_nesting == 2:
                complexity = "O(n²)"
                explanation = "Nested loops detected (2 levels)"
            else:
                complexity = "O(n²)"
                explanation = "Nested loops detected"
        elif total_loops > 1 and not nested_count:
            # Multiple sequential loops
            complexity = "O(n)"
            explanation = f"Multiple sequential loops ({total_loops} loops)"
        elif recursions:
            # Check recursion pattern
            if any('binary' in str(r).lower() or 'divide' in str(r).lower() for r in recursions):
                complexity = "O(log n)"
                explanation = "Recursive binary search or divide-and-conquer pattern"
            else:
                complexity = "O(n)"
                explanation = "Linear recursion detected"
        elif total_loops == 1:
            complexity = "O(n)"
            explanation = "Single loop detected"
        elif 'sort' in code.lower() or 'sorted' in code:
            complexity = "O(n log n)"
            explanation = "Sorting operation detected"
        else:
            complexity = "O(1)"
            explanation = "No loops detected, constant time"
        
        # Check for exponential patterns
        if '2**' in code or 'pow(2' in code or 'math.pow(2' in code:
            complexity = "O(2^n)"
            explanation = "Exponential pattern detected (2^n)"
        
        indicators = []
        if nested_count > 0:
            indicators.append(f"{nested_count} nested loop(s)")
        if recursions:
            indicators.append(f"{len(recursions)} recursive function(s)")
        if 'sort' in code.lower():
            indicators.append("sorting operation")
        
        confidence = 0.9 if (nested_count > 0 or recursions) else 0.7
        
        return ComplexityResult(
            complexity=complexity,
            explanation=explanation,
            confidence=confidence,
            indicators=indicators
        )

class MemoryUsageEstimator:
    """
    Estimates memory usage from code analysis
    """
    
    @staticmethod
    def estimate(parsed_structure: Dict, code: str) -> MemoryResult:
        """Estimate memory usage"""
        data_structures = parsed_structure.get('data_structures', [])
        loops = parsed_structure.get('loops', [])
        
        # Detect large allocations
        large_arrays = []
        memory_patterns = []
        
        # Check for array/list allocations
        array_patterns = [
            r'\[0\]\s*\*\s*(\w+)',  # [0] * n
            r'list\(\)\s*\*\s*(\w+)',  # list() * n
            r'\[\s*\]\s*\*\s*(\w+)',  # [] * n
            r'\[0\]\s*\*\s*(\d+)',  # [0] * 1000000
        ]
        
        for pattern in array_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                var = match.group(1)
                if var.isdigit():
                    size = int(var)
                    if size > 10000:
                        large_arrays.append({
                            'type': 'array',
                            'size': size,
                            'line': code[:match.start()].count('\n') + 1
                        })
                        memory_patterns.append(f"Large array allocation: {size} elements")
        
        # Check for 2D arrays
        matrix_patterns = [
            r'\[\s*\[0\]\s*\*\s*\w+\s*\]\s*\*\s*(\w+)',  # [[0] * n] * m
        ]
        
        for pattern in matrix_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                var = match.group(1)
                memory_patterns.append(f"2D matrix allocation: {var} x {var}")
        
        # Count data structures
        ds_count = len(data_structures)
        ds_types = defaultdict(int)
        for ds in data_structures:
            ds_type = ds.get('type', 'unknown')
            ds_types[ds_type] += 1
        
        # Determine memory complexity
        if large_arrays:
            max_size = max(arr['size'] for arr in large_arrays)
            if any('matrix' in p.lower() or '2d' in p.lower() for p in memory_patterns):
                complexity = "O(n²)"
                explanation = f"2D matrix detected with size up to {max_size}"
            else:
                complexity = "O(n)"
                explanation = f"Large array(s) detected with size up to {max_size}"
        elif ds_count > 10:
            complexity = "O(n)"
            explanation = f"Multiple data structures ({ds_count} total)"
        elif loops:
            # If loops create data structures
            complexity = "O(n)"
            explanation = "Data structures created in loops"
        else:
            complexity = "O(1)"
            explanation = "Constant memory usage"
        
        # Estimate peak usage (rough)
        peak_estimate = None
        if large_arrays:
            max_size = max(arr['size'] for arr in large_arrays)
            # Rough estimate: 8 bytes per element (for integers)
            peak_estimate = max_size * 8
        
        return MemoryResult(
            complexity=complexity,
            explanation=explanation,
            peak_usage_estimate=peak_estimate,
            data_structures=[
                {
                    'type': ds_type,
                    'count': count
                }
                for ds_type, count in ds_types.items()
            ]
        )

class TestCaseGenerator:
    """
    Generates comprehensive test cases: normal, edge, extreme, invalid, empty
    """
    
    @staticmethod
    def generate(question_description: str, language: str = 'python') -> List[TestCase]:
        """Generate test cases based on problem description"""
        test_cases = []
        
        # Extract problem type from description
        problem_type = TestCaseGenerator._detect_problem_type(question_description)
        
        if 'array' in problem_type or 'list' in problem_type:
            # Array/list problems
            test_cases.extend([
                TestCase(
                    input_data="[1, 2, 3, 4, 5]",
                    expected_output=None,
                    test_type="normal",
                    description="Normal case with positive numbers"
                ),
                TestCase(
                    input_data="[]",
                    expected_output=None,
                    test_type="empty",
                    description="Empty array"
                ),
                TestCase(
                    input_data="[-1, -2, -3]",
                    expected_output=None,
                    test_type="edge",
                    description="Negative numbers"
                ),
                TestCase(
                    input_data="[0]",
                    expected_output=None,
                    test_type="edge",
                    description="Single element"
                ),
                TestCase(
                    input_data="[" + ", ".join([str(i) for i in range(1000)]) + "]",
                    expected_output=None,
                    test_type="extreme",
                    description="Large input (1000 elements)"
                )
            ])
        elif 'string' in problem_type:
            # String problems
            test_cases.extend([
                TestCase(
                    input_data='"hello world"',
                    expected_output=None,
                    test_type="normal",
                    description="Normal string"
                ),
                TestCase(
                    input_data='""',
                    expected_output=None,
                    test_type="empty",
                    description="Empty string"
                ),
                TestCase(
                    input_data='"a"',
                    expected_output=None,
                    test_type="edge",
                    description="Single character"
                ),
                TestCase(
                    input_data='"a" * 10000',
                    expected_output=None,
                    test_type="extreme",
                    description="Very long string"
                )
            ])
        else:
            # Generic test cases
            test_cases.extend([
                TestCase(
                    input_data="5",
                    expected_output=None,
                    test_type="normal",
                    description="Normal input"
                ),
                TestCase(
                    input_data="0",
                    expected_output=None,
                    test_type="edge",
                    description="Zero input"
                ),
                TestCase(
                    input_data="1",
                    expected_output=None,
                    test_type="edge",
                    description="Minimum value"
                ),
                TestCase(
                    input_data="1000000",
                    expected_output=None,
                    test_type="extreme",
                    description="Large input"
                )
            ])
        
        return test_cases
    
    @staticmethod
    def _detect_problem_type(description: str) -> str:
        """Detect problem type from description"""
        description_lower = description.lower()
        
        if any(word in description_lower for word in ['array', 'list', 'vector']):
            return 'array'
        elif any(word in description_lower for word in ['string', 'char']):
            return 'string'
        elif any(word in description_lower for word in ['tree', 'node', 'binary']):
            return 'tree'
        elif any(word in description_lower for word in ['graph', 'edge', 'vertex']):
            return 'graph'
        else:
            return 'generic'

class CodeQualityScorer:
    """
    Scores code quality: readability, modularity, naming, structure, comments
    """
    
    @staticmethod
    def score(code: str, language: str = 'python') -> QualityScore:
        """Score code quality"""
        scores = {
            'readability': CodeQualityScorer._score_readability(code),
            'modularity': CodeQualityScorer._score_modularity(code),
            'naming': CodeQualityScorer._score_naming(code),
            'structure': CodeQualityScorer._score_structure(code),
            'comments': CodeQualityScorer._score_comments(code),
            'error_handling': CodeQualityScorer._score_error_handling(code)
        }
        
        overall = sum(scores.values()) // len(scores)
        
        return QualityScore(
            overall_score=overall,
            readability=scores['readability'],
            modularity=scores['modularity'],
            naming=scores['naming'],
            structure=scores['structure'],
            comments=scores['comments'],
            error_handling=scores['error_handling']
        )
    
    @staticmethod
    def _score_readability(code: str) -> int:
        """Score readability (0-100)"""
        score = 100
        
        # Penalize long lines (> 100 chars)
        lines = code.split('\n')
        long_lines = sum(1 for line in lines if len(line) > 100)
        if long_lines > 0:
            score -= min(20, long_lines * 2)
        
        # Penalize deep nesting (> 4 levels)
        nesting = code.count('    ') // 4  # Rough estimate
        if nesting > 4:
            score -= 15
        
        # Penalize magic numbers
        magic_numbers = re.findall(r'\b\d{3,}\b', code)
        if len(magic_numbers) > 3:
            score -= 10
        
        return max(0, score)
    
    @staticmethod
    def _score_modularity(code: str) -> int:
        """Score modularity (0-100)"""
        score = 50  # Base score
        
        # Check for functions
        func_count = len(re.findall(r'def\s+\w+', code))
        if func_count > 0:
            score += 30
        if func_count > 2:
            score += 20
        
        # Check for classes
        class_count = len(re.findall(r'class\s+\w+', code))
        if class_count > 0:
            score += 10
        
        # Penalize very long functions (> 50 lines)
        lines = code.split('\n')
        if len(lines) > 50 and func_count == 0:
            score -= 30
        
        return min(100, max(0, score))
    
    @staticmethod
    def _score_naming(code: str) -> int:
        """Score variable/function naming (0-100)"""
        score = 100
        
        # Check for single-letter variables (except loop counters)
        bad_vars = re.findall(r'\b[a-z]\s*=', code)
        # Exclude common loop counters
        bad_vars = [v for v in bad_vars if not re.search(r'for\s+' + v[0], code)]
        if len(bad_vars) > 3:
            score -= 20
        
        # Check for abbreviations
        abbrevs = re.findall(r'\b[a-z]{1,2}\s*=', code)
        if len(abbrevs) > 5:
            score -= 15
        
        # Check for descriptive names
        good_names = re.findall(r'\b[a-z_]{4,}\s*=', code)
        if len(good_names) > len(bad_vars):
            score += 10
        
        return max(0, min(100, score))
    
    @staticmethod
    def _score_structure(code: str) -> int:
        """Score code structure (0-100)"""
        score = 100
        
        # Check indentation consistency
        lines = [line for line in code.split('\n') if line.strip()]
        if not lines:
            return 0
        
        # Check for proper spacing
        no_spacing = sum(1 for i, line in enumerate(lines[1:], 1) 
                        if line.strip() and lines[i-1].strip() and 
                        not line.startswith((' ', '\t')) and 
                        not lines[i-1].endswith((':', '{', '[')))
        if no_spacing > 5:
            score -= 15
        
        return max(0, score)
    
    @staticmethod
    def _score_comments(code: str) -> int:
        """Score comments (0-100)"""
        lines = code.split('\n')
        total_lines = len([l for l in lines if l.strip()])
        comment_lines = len([l for l in lines if l.strip().startswith('#')])
        
        if total_lines == 0:
            return 0
        
        comment_ratio = comment_lines / total_lines
        
        if comment_ratio > 0.2:
            return 100
        elif comment_ratio > 0.1:
            return 70
        elif comment_ratio > 0.05:
            return 50
        else:
            return 30
    
    @staticmethod
    def _score_error_handling(code: str) -> int:
        """Score error handling (0-100)"""
        score = 50  # Base
        
        # Check for try-except
        if 'try' in code and 'except' in code:
            score += 30
        
        # Check for input validation
        if any(keyword in code for keyword in ['if', 'assert', 'isinstance', 'len(']):
            score += 20
        
        return min(100, score)

class BestPracticeAnalyzer:
    """
    Analyzes code for best practice violations
    """
    
    @staticmethod
    def analyze(code: str, language: str = 'python') -> List[BestPracticeViolation]:
        """Analyze code for best practice violations"""
        violations = []
        
        # Check for global variables
        if re.search(r'^global\s+\w+', code, re.MULTILINE):
            violations.append(BestPracticeViolation(
                rule="Avoid global variables",
                severity="medium",
                message="Global variables detected",
                line=None,
                suggestion="Use function parameters or class attributes instead"
            ))
        
        # Check for hardcoded values
        magic_numbers = re.findall(r'\b\d{3,}\b', code)
        if len(magic_numbers) > 3:
            violations.append(BestPracticeViolation(
                rule="Avoid magic numbers",
                severity="low",
                message=f"{len(magic_numbers)} magic numbers detected",
                line=None,
                suggestion="Use named constants instead of hardcoded values"
            ))
        
        # Check for range(len()) pattern
        if re.search(r'range\s*\(\s*len\s*\(', code):
            violations.append(BestPracticeViolation(
                rule="Use enumerate instead of range(len())",
                severity="low",
                message="range(len()) pattern detected",
                line=None,
                suggestion="Use enumerate() for better readability"
            ))
        
        # Check for poor variable names
        single_letter_vars = re.findall(r'\b([a-z])\s*=', code)
        if len(single_letter_vars) > 5:
            violations.append(BestPracticeViolation(
                rule="Use descriptive variable names",
                severity="medium",
                message="Multiple single-letter variables detected",
                line=None,
                suggestion="Use descriptive names that explain the variable's purpose"
            ))
        
        # Check for missing edge case handling
        if 'if' not in code and 'assert' not in code:
            violations.append(BestPracticeViolation(
                rule="Handle edge cases",
                severity="high",
                message="No edge case handling detected",
                line=None,
                suggestion="Add checks for empty inputs, null values, and boundary conditions"
            ))
        
        # Check for input validation
        if 'input(' in code and 'try' not in code:
            violations.append(BestPracticeViolation(
                rule="Validate user input",
                severity="high",
                message="Input validation missing",
                line=None,
                suggestion="Add try-except blocks and input validation"
            ))
        
        return violations

class DockerSandbox:
    """
    Docker-based code execution sandbox with resource limits
    """
    
    def __init__(self):
        if not DOCKER_AVAILABLE:
            self.client = None
            return
        
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
            print("[DockerSandbox] Docker connected successfully")
        except Exception as e:
            print(f"[DockerSandbox] Docker not available: {e}")
            self.client = None
    
    def execute(self, code: str, language: str, stdin: str = '', 
                timeout: int = 5, memory_limit: str = '128m') -> Dict:
        """
        Execute code in Docker sandbox
        
        Returns:
        {
            'output': str,
            'status': 'accepted' | 'timeout' | 'memory_limit' | 'runtime_error',
            'execution_time': float,
            'memory_used': int (bytes)
        }
        """
        if not self.client:
            # Fallback to local execution
            return self._execute_local(code, language, stdin, timeout)
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{self._get_extension(language)}', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Determine image and command
            image, command = self._get_docker_config(language)
            
            # Run in Docker container with limits
            container = self.client.containers.run(
                image,
                command=command,
                volumes={os.path.dirname(temp_file): {'bind': '/code', 'mode': 'ro'}},
                working_dir='/code',
                stdin_open=True,
                mem_limit=memory_limit,
                cpu_period=100000,
                cpu_quota=50000,  # 50% CPU
                network_disabled=True,
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
                timeout=timeout
            )
            
            # Get output
            output = container.decode('utf-8') if isinstance(container, bytes) else str(container)
            
            return {
                'output': output,
                'status': 'accepted',
                'execution_time': timeout,  # Approximate
                'memory_used': 0  # Would need monitoring
            }
            
        except docker.errors.ContainerError as e:
            return {
                'output': str(e),
                'status': 'runtime_error',
                'execution_time': 0.0,
                'memory_used': 0
            }
        except subprocess.TimeoutExpired:
            return {
                'output': 'Execution timeout',
                'status': 'timeout',
                'execution_time': timeout,
                'memory_used': 0
            }
        except Exception as e:
            return {
                'output': str(e),
                'status': 'runtime_error',
                'execution_time': 0.0,
                'memory_used': 0
            }
        finally:
            # Cleanup
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
    
    def _execute_local(self, code: str, language: str, stdin: str, timeout: int) -> Dict:
        """Fallback to local execution"""
        # Use existing compiler.py logic
        from utils.compiler import execute_code
        output, status, exec_time, _ = execute_code(code, language, stdin)
        return {
            'output': output,
            'status': status,
            'execution_time': exec_time,
            'memory_used': 0
        }
    
    def _get_extension(self, language: str) -> str:
        """Get file extension for language"""
        extensions = {
            'python': 'py',
            'cpp': 'cpp',
            'c': 'c',
            'java': 'java'
        }
        return extensions.get(language, 'txt')
    
    def _get_docker_config(self, language: str) -> Tuple[str, str]:
        """Get Docker image and command for language"""
        configs = {
            'python': ('python:3.9-slim', 'python /code/main.py'),
            'cpp': ('gcc:latest', 'g++ /code/main.cpp -o /tmp/main && /tmp/main'),
            'c': ('gcc:latest', 'gcc /code/main.c -o /tmp/main && /tmp/main'),
            'java': ('openjdk:11', 'javac /code/Main.java && java -cp /code Main')
        }
        return configs.get(language, ('python:3.9-slim', 'python /code/main.py'))

def analyze_code_comprehensive(
    code: str,
    language: str,
    question_description: Optional[str] = None
) -> Dict:
    """
    Complete industry-standard code analysis pipeline
    
    Returns comprehensive report:
    {
        'ast_analysis': {...},
        'time_complexity': {...},
        'memory_usage': {...},
        'test_cases': [...],
        'quality_score': {...},
        'best_practices': {...},
        'execution_results': {...},
        'final_report': {...}
    }
    """
    # 1. AST Parsing
    parser = ASTParser()
    ast_result = parser.parse(code)
    
    if not ast_result.get('valid', False):
        return {
            'error': ast_result.get('error', 'Invalid code'),
            'ast_analysis': ast_result
        }
    
    # 2. Time Complexity Estimation
    time_complexity = TimeComplexityEstimator.estimate(ast_result, code)
    
    # 3. Memory Usage Estimation
    memory_usage = MemoryUsageEstimator.estimate(ast_result, code)
    
    # 4. Test Case Generation
    test_cases = []
    if question_description:
        test_cases = TestCaseGenerator.generate(question_description, language)
    
    # 5. Code Quality Scoring
    quality_score = CodeQualityScorer.score(code, language)
    
    # 6. Best Practice Analysis
    best_practices = BestPracticeAnalyzer.analyze(code, language)
    
    # 7. Execute ALL test cases (multi-test engine)
    execution_results = []
    sandbox = DockerSandbox()
    for test_case in test_cases:  # Run ALL test cases, not just 5
        result = sandbox.execute(code, language, test_case.input_data, timeout=5)
        execution_results.append({
            'test_case': test_case.test_type,
            'input': test_case.input_data,
            'output': result['output'],
            'status': result['status'],
            'execution_time': result['execution_time'],
            'description': test_case.description
        })
    
    # 8. Generate Final Report
    final_report = _generate_final_report(
        time_complexity,
        memory_usage,
        quality_score,
        best_practices,
        execution_results
    )
    
    return {
        'ast_analysis': ast_result,
        'time_complexity': {
            'complexity': time_complexity.complexity,
            'explanation': time_complexity.explanation,
            'confidence': time_complexity.confidence,
            'indicators': time_complexity.indicators
        },
        'memory_usage': {
            'complexity': memory_usage.complexity,
            'explanation': memory_usage.explanation,
            'peak_estimate': memory_usage.peak_usage_estimate,
            'data_structures': memory_usage.data_structures
        },
        'test_cases': [
            {
                'type': tc.test_type,
                'input': tc.input_data,
                'description': tc.description
            }
            for tc in test_cases
        ],
        'quality_score': {
            'overall': quality_score.overall_score,
            'readability': quality_score.readability,
            'modularity': quality_score.modularity,
            'naming': quality_score.naming,
            'structure': quality_score.structure,
            'comments': quality_score.comments,
            'error_handling': quality_score.error_handling
        },
        'best_practices': {
            'violations': [
                {
                    'rule': v.rule,
                    'severity': v.severity,
                    'message': v.message,
                    'suggestion': v.suggestion
                }
                for v in best_practices
            ],
            'total_violations': len(best_practices),
            'high_severity': len([v for v in best_practices if v.severity == 'high'])
        },
        'execution_results': execution_results,
        'final_report': final_report
    }

def _generate_final_report(
    time_complexity: ComplexityResult,
    memory_usage: MemoryResult,
    quality_score: QualityScore,
    best_practices: List[BestPracticeViolation],
    execution_results: List[Dict]
) -> Dict:
    """Generate final comprehensive report"""
    
    # Count test case results
    passed = sum(1 for r in execution_results if r['status'] == 'accepted')
    total = len(execution_results)
    
    suggestions = []
    
    # Time complexity suggestions
    if 'O(n²)' in time_complexity.complexity or 'O(2^n)' in time_complexity.complexity:
        suggestions.append("Reduce nested loops to improve time complexity")
    
    # Memory suggestions
    if memory_usage.peak_usage_estimate and memory_usage.peak_usage_estimate > 1000000:
        suggestions.append("Optimize memory usage for large inputs")
    
    # Quality suggestions
    if quality_score.overall_score < 70:
        suggestions.append("Improve code structure and readability")
    
    # Best practice suggestions
    high_severity = [v for v in best_practices if v.severity == 'high']
    for violation in high_severity[:3]:
        suggestions.append(violation.suggestion)
    
    return {
        'output_status': 'Correct' if passed == total else f'Passed {passed}/{total}',
        'time_complexity': time_complexity.complexity,
        'memory_usage': memory_usage.complexity,
        'code_quality': f"{quality_score.overall_score}/100",
        'edge_case_status': f"Passed {passed}/{total}",
        'suggestions': suggestions[:5]  # Top 5 suggestions
    }
