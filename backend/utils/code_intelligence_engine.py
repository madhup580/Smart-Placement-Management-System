"""
Intelligent Coding Evaluation Engine
Multi-dimensional code analysis: complexity, quality, best practices, optimization
"""
import re
import ast
import json
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from utils.openai_client import get_openai_client, OpenAIError
from config import Config

class CodeParser:
    """
    Code Parser - AST Analysis
    Parses code into Abstract Syntax Tree to understand structure
    """
    
    @staticmethod
    def parse_python(code: str) -> Dict:
        """Parse Python code into AST structure"""
        try:
            tree = ast.parse(code)
            analyzer = PythonASTAnalyzer()
            analyzer.visit(tree)
            return analyzer.get_structure()
        except SyntaxError as e:
            return {'error': f'Syntax error: {str(e)}', 'valid': False}
        except Exception as e:
            return {'error': str(e), 'valid': False}
    
    @staticmethod
    def parse_code(code: str, language: str) -> Dict:
        """Parse code based on language"""
        if language == 'python':
            return CodeParser.parse_python(code)
        elif language in ['cpp', 'c', 'java']:
            return CodeParser._parse_imperative(code, language)
        else:
            return {'error': f'Unsupported language: {language}', 'valid': False}
    
    @staticmethod
    def _parse_imperative(code: str, language: str) -> Dict:
        """Basic parsing for C/C++/Java using regex patterns"""
        structure = {
            'valid': True,
            'functions': [],
            'loops': [],
            'conditionals': [],
            'recursion': False,
            'data_structures': [],
            'nesting_depth': 0,
            'complexity_indicators': []
        }
        
        # Detect functions
        func_pattern = r'(?:public|private|static)?\s*(?:int|void|string|bool|char|float|double)\s+(\w+)\s*\('
        functions = re.findall(func_pattern, code)
        structure['functions'] = [{'name': f, 'type': 'function'} for f in functions]
        
        # Detect loops
        loop_patterns = [
            (r'for\s*\([^)]+\)', 'for'),
            (r'while\s*\([^)]+\)', 'while'),
            (r'do\s*\{', 'do-while')
        ]
        for pattern, loop_type in loop_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                structure['loops'].append({
                    'type': loop_type,
                    'line': code[:match.start()].count('\n') + 1
                })
        
        # Detect conditionals
        if_pattern = r'if\s*\([^)]+\)'
        if_matches = re.findall(if_pattern, code)
        structure['conditionals'] = [{'type': 'if', 'count': len(if_matches)}]
        
        # Detect recursion (function calling itself)
        for func_name in functions:
            if re.search(rf'\b{func_name}\s*\(', code):
                structure['recursion'] = True
                break
        
        # Detect data structures
        ds_patterns = {
            'array': r'\[\]|array|vector|list',
            'map': r'map|dict|unordered_map|HashMap',
            'set': r'set|unordered_set|HashSet',
            'stack': r'stack|Stack',
            'queue': r'queue|Queue|deque'
        }
        for ds_type, pattern in ds_patterns.items():
            if re.search(pattern, code, re.IGNORECASE):
                structure['data_structures'].append(ds_type)
        
        # Calculate nesting depth (simplified)
        max_depth = 0
        current_depth = 0
        for char in code:
            if char == '{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == '}':
                current_depth -= 1
        structure['nesting_depth'] = max_depth
        
        # Complexity indicators
        if len(structure['loops']) > 1:
            structure['complexity_indicators'].append('nested_loops')
        if structure['recursion']:
            structure['complexity_indicators'].append('recursion')
        if 'sort' in code.lower() or 'sorted' in code.lower():
            structure['complexity_indicators'].append('sorting')
        if 'search' in code.lower() or 'find' in code.lower() or 'binary' in code.lower():
            structure['complexity_indicators'].append('searching')
        
        return structure


class PythonASTAnalyzer(ast.NodeVisitor):
    """AST visitor for Python code analysis"""
    
    def __init__(self):
        self.functions = []
        self.loops = []
        self.conditionals = []
        self.recursion = False
        self.data_structures = []
        self.nesting_depth = 0
        self.complexity_indicators = []
        self.current_depth = 0
        self.function_names = set()
    
    def visit_FunctionDef(self, node):
        self.function_names.add(node.name)
        self.functions.append({
            'name': node.name,
            'line': node.lineno,
            'args': len(node.args.args)
        })
        self.generic_visit(node)
    
    def visit_For(self, node):
        self.loops.append({
            'type': 'for',
            'line': node.lineno,
            'depth': self.current_depth
        })
        self.current_depth += 1
        self.generic_visit(node)
        self.current_depth -= 1
    
    def visit_While(self, node):
        self.loops.append({
            'type': 'while',
            'line': node.lineno,
            'depth': self.current_depth
        })
        self.current_depth += 1
        self.generic_visit(node)
        self.current_depth -= 1
    
    def visit_If(self, node):
        self.conditionals.append({
            'type': 'if',
            'line': node.lineno,
            'depth': self.current_depth
        })
        self.current_depth += 1
        self.generic_visit(node)
        self.current_depth -= 1
    
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.function_names:
                self.recursion = True
            # Check for complexity indicators
            if node.func.id in ['sort', 'sorted', 'reverse']:
                self.complexity_indicators.append('sorting')
            if node.func.id in ['search', 'find', 'index']:
                self.complexity_indicators.append('searching')
        
        # Check for data structures
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ['append', 'extend', 'pop']:
                self.data_structures.append('list')
            elif node.func.attr in ['add', 'remove', 'discard']:
                self.data_structures.append('set')
            elif node.func.attr in ['get', 'keys', 'values']:
                self.data_structures.append('dict')
        
        self.generic_visit(node)
    
    def visit_List(self, node):
        self.data_structures.append('list')
        self.generic_visit(node)
    
    def visit_Dict(self, node):
        self.data_structures.append('dict')
        self.generic_visit(node)
    
    def visit_Set(self, node):
        self.data_structures.append('set')
        self.generic_visit(node)
    
    def get_structure(self) -> Dict:
        """Get parsed structure"""
        return {
            'valid': True,
            'functions': self.functions,
            'loops': self.loops,
            'conditionals': self.conditionals,
            'recursion': self.recursion,
            'data_structures': list(set(self.data_structures)),
            'nesting_depth': max([l.get('depth', 0) for l in self.loops + self.conditionals], default=0),
            'complexity_indicators': list(set(self.complexity_indicators))
        }


class TimeComplexityPredictor:
    """
    Time Complexity Predictor
    Estimates time complexity using loop nesting, recursive patterns, sorting/searching
    """
    
    @staticmethod
    def predict_complexity(code_structure: Dict, code: str) -> Dict:
        """
        Predict time complexity
        
        Returns:
        {
            "complexity": "O(n log n)",
            "confidence": 0.85,
            "reasoning": "Nested loop with sorting operation",
            "breakdown": {
                "base_complexity": "O(n)",
                "operations": ["sorting: O(n log n)"]
            }
        }
        """
        if not code_structure.get('valid', False):
            return {
                'complexity': 'Unknown',
                'confidence': 0.0,
                'reasoning': 'Invalid code structure'
            }
        
        loops = code_structure.get('loops', [])
        recursion = code_structure.get('recursion', False)
        indicators = code_structure.get('complexity_indicators', [])
        nesting_depth = code_structure.get('nesting_depth', 0)
        
        # Analyze loop patterns
        loop_depths = [l.get('depth', 0) for l in loops]
        max_loop_depth = max(loop_depths) if loop_depths else 0
        
        # Base complexity from loops
        if max_loop_depth == 0:
            base_complexity = "O(1)"
            confidence = 0.9
        elif max_loop_depth == 1:
            base_complexity = "O(n)"
            confidence = 0.8
        elif max_loop_depth == 2:
            base_complexity = "O(n²)"
            confidence = 0.75
        elif max_loop_depth >= 3:
            base_complexity = "O(n³)"
            confidence = 0.7
        else:
            base_complexity = "O(n)"
            confidence = 0.6
        
        # Adjust for operations
        operations = []
        final_complexity = base_complexity
        
        if 'sorting' in indicators:
            if base_complexity == "O(1)":
                final_complexity = "O(n log n)"
            elif base_complexity == "O(n)":
                final_complexity = "O(n log n)"
            else:
                # Nested loop + sorting
                final_complexity = f"{base_complexity} + O(n log n)"
            operations.append("sorting: O(n log n)")
            confidence = min(confidence + 0.1, 0.95)
        
        if 'searching' in indicators:
            if 'binary' in code.lower():
                operations.append("binary search: O(log n)")
                if base_complexity == "O(n)":
                    final_complexity = "O(n log n)"
            else:
                operations.append("linear search: O(n)")
        
        if recursion:
            # Try to detect recursion pattern
            if 'memo' in code.lower() or 'cache' in code.lower() or 'dp' in code.lower():
                operations.append("memoized recursion: O(n)")
                if base_complexity.startswith("O(n"):
                    final_complexity = "O(n)"
            else:
                operations.append("recursion: exponential possible")
                if base_complexity == "O(1)":
                    final_complexity = "O(2^n)"  # Worst case
                confidence = max(confidence - 0.2, 0.5)
        
        # Use AI for more accurate prediction if available
        if Config.OPENAI_API_KEY:
            ai_prediction = TimeComplexityPredictor._ai_predict_complexity(code, code_structure)
            if ai_prediction:
                final_complexity = ai_prediction.get('complexity', final_complexity)
                confidence = max(confidence, ai_prediction.get('confidence', confidence))
        
        return {
            'complexity': final_complexity,
            'confidence': round(confidence, 2),
            'reasoning': f"Based on {max_loop_depth} nested loop(s)" + 
                        (f", {', '.join(operations)}" if operations else ""),
            'breakdown': {
                'base_complexity': base_complexity,
                'operations': operations,
                'loop_depth': max_loop_depth,
                'recursion': recursion
            }
        }
    
    @staticmethod
    def _ai_predict_complexity(code: str, structure: Dict) -> Optional[Dict]:
        """Use AI for more accurate complexity prediction"""
        try:
            client = get_openai_client()
            
            prompt = f"""Analyze this code and predict its time complexity.

Code:
{code[:2000]}

Structure:
- Loops: {len(structure.get('loops', []))}
- Nesting depth: {structure.get('nesting_depth', 0)}
- Recursion: {structure.get('recursion', False)}
- Operations: {', '.join(structure.get('complexity_indicators', []))}

Predict the time complexity in Big O notation (e.g., O(1), O(n), O(n log n), O(n²), O(2^n)).
Also provide confidence (0-1) and brief reasoning.

Return ONLY a JSON object:
{{
    "complexity": "O(n log n)",
    "confidence": 0.85,
    "reasoning": "Single loop with sorting operation"
}}

Return ONLY the JSON object, no other text."""

            response = client.chat_completion(
                model=Config.OPENAI_MODEL or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert algorithm analyst. Predict time complexity accurately. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )
            
            content = response.get('content', '').strip()
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"[Code Intelligence] AI complexity prediction failed: {e}")
            return None


class MemoryUsageEstimator:
    """
    Memory Usage Estimator
    Analyzes data structures, object creation, recursion depth
    """
    
    @staticmethod
    def estimate_memory(code_structure: Dict, code: str) -> Dict:
        """
        Estimate memory/space complexity
        
        Returns:
        {
            "space_complexity": "O(n)",
            "confidence": 0.8,
            "reasoning": "Array of size n created",
            "breakdown": {
                "data_structures": ["array: O(n)"],
                "recursion_stack": "O(n)",
                "auxiliary_space": "O(1)"
            }
        }
        """
        if not code_structure.get('valid', False):
            return {
                'space_complexity': 'Unknown',
                'confidence': 0.0,
                'reasoning': 'Invalid code structure'
            }
        
        data_structures = code_structure.get('data_structures', [])
        recursion = code_structure.get('recursion', False)
        
        space_components = []
        max_space = "O(1)"
        
        # Analyze data structures
        ds_space = {}
        for ds in data_structures:
            if ds in ['list', 'array', 'vector']:
                ds_space[ds] = "O(n)"
                space_components.append(f"{ds}: O(n)")
            elif ds in ['dict', 'map', 'set']:
                ds_space[ds] = "O(n)"
                space_components.append(f"{ds}: O(n)")
            elif ds in ['stack', 'queue']:
                ds_space[ds] = "O(n)"
                space_components.append(f"{ds}: O(n)")
        
        if ds_space:
            max_space = "O(n)"
        
        # Recursion stack
        recursion_stack = "O(1)"
        if recursion:
            recursion_stack = "O(n)"  # Worst case
            space_components.append(f"recursion stack: {recursion_stack}")
            if max_space == "O(1)":
                max_space = "O(n)"
        
        # Check for auxiliary space (in-place operations)
        auxiliary = "O(1)"
        if 'in-place' in code.lower() or 'swap' in code.lower():
            auxiliary = "O(1)"
        else:
            # Check if new arrays/structures are created
            if re.search(r'new\s+\w+\[|\[\]\s*=|list\(\)|dict\(\)|set\(\)', code):
                auxiliary = "O(n)"
        
        # Final space complexity
        if max_space == "O(1)" and auxiliary == "O(n)":
            max_space = "O(n)"
        elif max_space == "O(n)" and auxiliary == "O(n)":
            max_space = "O(n)"  # Still O(n)
        
        confidence = 0.7
        if len(space_components) > 0:
            confidence = 0.8
        
        return {
            'space_complexity': max_space,
            'confidence': confidence,
            'reasoning': f"Data structures: {', '.join(space_components) if space_components else 'minimal'}",
            'breakdown': {
                'data_structures': space_components,
                'recursion_stack': recursion_stack,
                'auxiliary_space': auxiliary
            }
        }


class CodeQualityScorer:
    """
    Code Quality Scorer
    Scores based on readability, modularity, naming, comments, reusability, error handling
    """
    
    @staticmethod
    def score_quality(code: str, language: str, code_structure: Dict) -> Dict:
        """
        Score code quality (0-100)
        
        Returns:
        {
            "quality_score": 78,
            "breakdown": {
                "readability": 80,
                "modularity": 75,
                "naming": 70,
                "comments": 60,
                "reusability": 85,
                "error_handling": 70
            },
            "issues": ["Missing input validation", "No error handling"],
            "strengths": ["Well-structured functions", "Clear variable names"]
        }
        """
        scores = {}
        issues = []
        strengths = []
        
        # 1. Readability (30 points)
        readability_score = CodeQualityScorer._score_readability(code, code_structure)
        scores['readability'] = readability_score
        
        # 2. Modularity (20 points)
        modularity_score = CodeQualityScorer._score_modularity(code_structure)
        scores['modularity'] = modularity_score
        
        # 3. Naming Conventions (15 points)
        naming_score = CodeQualityScorer._score_naming(code, language)
        scores['naming'] = naming_score
        
        # 4. Comments (10 points)
        comments_score = CodeQualityScorer._score_comments(code)
        scores['comments'] = comments_score
        
        # 5. Reusability (15 points)
        reusability_score = CodeQualityScorer._score_reusability(code_structure)
        scores['reusability'] = reusability_score
        
        # 6. Error Handling (10 points)
        error_handling_score = CodeQualityScorer._score_error_handling(code, language)
        scores['error_handling'] = error_handling_score
        
        # Calculate weighted total
        weights = {
            'readability': 0.30,
            'modularity': 0.20,
            'naming': 0.15,
            'comments': 0.10,
            'reusability': 0.15,
            'error_handling': 0.10
        }
        
        total_score = sum(scores[key] * weights[key] for key in scores)
        
        # Identify issues and strengths
        if readability_score < 60:
            issues.append("Low readability - consider simplifying logic")
        if modularity_score < 60:
            issues.append("Low modularity - break into smaller functions")
        if naming_score < 60:
            issues.append("Poor naming conventions")
        if comments_score < 50:
            issues.append("Missing or insufficient comments")
        if error_handling_score < 50:
            issues.append("Missing error handling")
        
        if readability_score >= 80:
            strengths.append("Clear and readable code")
        if modularity_score >= 80:
            strengths.append("Well-modularized functions")
        if naming_score >= 80:
            strengths.append("Good naming conventions")
        
        return {
            'quality_score': round(total_score),
            'breakdown': scores,
            'issues': issues,
            'strengths': strengths
        }
    
    @staticmethod
    def _score_readability(code: str, structure: Dict) -> float:
        """Score readability (0-100)"""
        score = 70  # Base score
        
        # Penalize high nesting
        nesting = structure.get('nesting_depth', 0)
        if nesting > 3:
            score -= 20
        elif nesting > 2:
            score -= 10
        
        # Penalize long functions
        functions = structure.get('functions', [])
        if functions:
            # Estimate function length (simplified)
            avg_func_length = len(code) / max(len(functions), 1)
            if avg_func_length > 100:
                score -= 15
            elif avg_func_length > 50:
                score -= 5
        
        # Reward clear structure
        if len(functions) > 0:
            score += 10
        
        return max(0, min(100, score))
    
    @staticmethod
    def _score_modularity(structure: Dict) -> float:
        """Score modularity (0-100)"""
        functions = structure.get('functions', [])
        
        if len(functions) == 0:
            return 40  # No functions = low modularity
        elif len(functions) == 1:
            return 60  # Single function
        elif len(functions) >= 3:
            return 85  # Good modularity
        else:
            return 70  # Moderate
    
    @staticmethod
    def _score_naming(code: str, language: str) -> float:
        """Score naming conventions (0-100)"""
        score = 70  # Base
        
        # Check for single-letter variables (bad)
        single_letter_vars = re.findall(r'\b[a-z]\s*=', code)
        if len(single_letter_vars) > 3:
            score -= 20
        
        # Check for descriptive names
        descriptive_patterns = [
            r'\b(count|index|length|size|result|temp|data)\b',
            r'\b(is|has|can|should)\w+',  # Boolean naming
            r'\b(get|set|find|calculate|process)\w+'  # Verb-based naming
        ]
        descriptive_count = sum(1 for pattern in descriptive_patterns if re.search(pattern, code, re.IGNORECASE))
        if descriptive_count > 5:
            score += 15
        
        # Check for magic numbers
        magic_numbers = re.findall(r'\b\d{2,}\b', code)  # Numbers >= 10
        if len(magic_numbers) > 5:
            score -= 10
        
        return max(0, min(100, score))
    
    @staticmethod
    def _score_comments(code: str) -> float:
        """Score comments (0-100)"""
        comment_patterns = {
            'python': r'#.*|""".*?"""|\'\'\'.*?\'\'\'',
            'cpp': r'//.*|/\*.*?\*/',
            'c': r'//.*|/\*.*?\*/',
            'java': r'//.*|/\*.*?\*/'
        }
        
        pattern = comment_patterns.get('python', r'//.*|/\*.*?\*/')
        comments = re.findall(pattern, code, re.DOTALL)
        
        code_lines = len([l for l in code.split('\n') if l.strip()])
        comment_lines = len(comments)
        
        if code_lines == 0:
            return 0
        
        comment_ratio = comment_lines / code_lines
        
        if comment_ratio > 0.2:
            return 90
        elif comment_ratio > 0.1:
            return 70
        elif comment_ratio > 0.05:
            return 50
        else:
            return 30
    
    @staticmethod
    def _score_reusability(structure: Dict) -> float:
        """Score reusability (0-100)"""
        functions = structure.get('functions', [])
        
        if len(functions) >= 2:
            return 85  # Good reusability
        elif len(functions) == 1:
            return 60  # Moderate
        else:
            return 40  # Low (no functions)
    
    @staticmethod
    def _score_error_handling(code: str, language: str) -> float:
        """Score error handling (0-100)"""
        error_patterns = {
            'python': [r'try:', r'except', r'raise', r'assert'],
            'cpp': [r'try', r'catch', r'throw', r'assert'],
            'java': [r'try', r'catch', r'throw', r'assert'],
            'c': [r'assert', r'if\s*\(.*==\s*NULL', r'if\s*\(.*==\s*nullptr']
        }
        
        patterns = error_patterns.get(language, [])
        error_handling_count = sum(1 for pattern in patterns if re.search(pattern, code, re.IGNORECASE))
        
        if error_handling_count >= 2:
            return 85
        elif error_handling_count == 1:
            return 60
        else:
            return 30


class BestPracticeAnalyzer:
    """
    Best Practice Analyzer
    Detects hardcoded values, poor naming, missing edge cases, no input validation
    """
    
    @staticmethod
    def analyze_best_practices(code: str, language: str, code_structure: Dict) -> Dict:
        """
        Analyze best practices
        
        Returns:
        {
            "violations": [
                {
                    "type": "hardcoded_value",
                    "severity": "medium",
                    "message": "Consider using constants instead of magic numbers",
                    "line": 5
                }
            ],
            "suggestions": [
                "Consider separating logic into smaller functions",
                "Add input validation for edge cases"
            ],
            "score": 75  // 0-100
        }
        """
        violations = []
        suggestions = []
        
        # 1. Check for hardcoded values
        magic_numbers = re.findall(r'\b\d{2,}\b', code)
        if len(magic_numbers) > 3:
            violations.append({
                'type': 'hardcoded_value',
                'severity': 'medium',
                'message': f'Found {len(magic_numbers)} magic numbers. Consider using named constants.',
                'line': None
            })
            suggestions.append("Replace magic numbers with named constants for better maintainability")
        
        # 2. Check for input validation
        if not re.search(r'if\s*\(.*input|if\s*\(.*stdin|if\s*\(.*arg', code, re.IGNORECASE):
            violations.append({
                'type': 'missing_validation',
                'severity': 'high',
                'message': 'No input validation detected. Add checks for edge cases.',
                'line': None
            })
            suggestions.append("Add input validation for edge cases (empty input, negative numbers, etc.)")
        
        # 3. Check for poor naming
        single_letter = re.findall(r'\b[a-z]\s*=', code)
        if len(single_letter) > 5:
            violations.append({
                'type': 'poor_naming',
                'severity': 'low',
                'message': 'Too many single-letter variables. Use descriptive names.',
                'line': None
            })
            suggestions.append("Use descriptive variable names instead of single letters")
        
        # 4. Check for missing edge cases
        if not re.search(r'if\s*\(.*==\s*0|if\s*\(.*==\s*null|if\s*\(.*empty', code, re.IGNORECASE):
            suggestions.append("Consider handling edge cases: empty input, zero, null values")
        
        # 5. Check for modularity
        functions = code_structure.get('functions', [])
        if len(functions) == 0 and len(code) > 100:
            violations.append({
                'type': 'low_modularity',
                'severity': 'medium',
                'message': 'Code is not modular. Consider breaking into functions.',
                'line': None
            })
            suggestions.append("Break code into smaller, reusable functions")
        
        # 6. Check for error handling
        if language == 'python' and not re.search(r'try:|except', code):
            violations.append({
                'type': 'no_error_handling',
                'severity': 'high',
                'message': 'No error handling detected. Add try-except blocks.',
                'line': None
            })
            suggestions.append("Add error handling (try-except blocks) for robustness")
        
        # Calculate score
        base_score = 100
        for violation in violations:
            severity_penalty = {'high': 15, 'medium': 10, 'low': 5}.get(violation['severity'], 5)
            base_score -= severity_penalty
        
        score = max(0, base_score)
        
        return {
            'violations': violations,
            'suggestions': suggestions,
            'score': score
        }


class OptimizationAdvisor:
    """
    Optimization Advisor
    Suggests better algorithms, data structure replacement, loop reduction, memoization
    """
    
    @staticmethod
    def suggest_optimizations(code: str, language: str, code_structure: Dict, 
                             complexity: Dict, quality: Dict) -> Dict:
        """
        Suggest optimizations
        
        Returns:
        {
            "optimizations": [
                {
                    "type": "algorithm",
                    "priority": "high",
                    "current": "O(n²) nested loop",
                    "suggestion": "Use hash map for O(n) lookup",
                    "impact": "Reduces time complexity from O(n²) to O(n)"
                }
            ],
            "estimated_improvement": {
                "time_complexity": "O(n²) → O(n)",
                "space_complexity": "O(1) → O(n)",
                "quality_score": "+15 points"
            }
        }
        """
        optimizations = []
        
        # Analyze complexity
        time_complexity = complexity.get('complexity', '')
        space_complexity = complexity.get('space_complexity', '')
        
        # 1. Time complexity optimizations
        if 'O(n²)' in time_complexity or 'O(n^2)' in time_complexity:
            loops = code_structure.get('loops', [])
            if len(loops) >= 2:
                optimizations.append({
                    'type': 'algorithm',
                    'priority': 'high',
                    'current': 'O(n²) nested loop',
                    'suggestion': 'Consider using hash map/dictionary for O(n) lookup instead of nested loops',
                    'impact': 'Reduces time complexity from O(n²) to O(n)'
                })
        
        if 'O(2^n)' in time_complexity or 'exponential' in complexity.get('reasoning', '').lower():
            if code_structure.get('recursion', False):
                optimizations.append({
                    'type': 'memoization',
                    'priority': 'high',
                    'current': 'Exponential recursion',
                    'suggestion': 'Add memoization/caching to avoid recalculating subproblems',
                    'impact': 'Reduces time complexity from O(2^n) to O(n)'
                })
        
        # 2. Data structure optimizations
        data_structures = code_structure.get('data_structures', [])
        if 'list' in data_structures and 'search' in code.lower():
            optimizations.append({
                'type': 'data_structure',
                'priority': 'medium',
                'current': 'Linear search in list',
                'suggestion': 'Use set or hash map for O(1) lookup instead of O(n) list search',
                'impact': 'Faster lookups for membership testing'
            })
        
        # 3. Space optimizations
        if space_complexity == 'O(n)' and 'array' in str(data_structures):
            optimizations.append({
                'type': 'space',
                'priority': 'low',
                'current': 'O(n) auxiliary space',
                'suggestion': 'Consider in-place operations to reduce space to O(1)',
                'impact': 'Reduces space complexity'
            })
        
        # 4. Code quality optimizations
        if quality.get('quality_score', 0) < 70:
            if quality.get('breakdown', {}).get('modularity', 0) < 60:
                optimizations.append({
                    'type': 'modularity',
                    'priority': 'medium',
                    'current': 'Low modularity',
                    'suggestion': 'Break code into smaller functions for better maintainability',
                    'impact': 'Improves code quality and reusability'
                })
        
        # Estimate improvement
        estimated_improvement = {}
        if optimizations:
            time_opt = [o for o in optimizations if o['type'] == 'algorithm' or o['type'] == 'memoization']
            if time_opt:
                estimated_improvement['time_complexity'] = f"{time_complexity} → Improved"
            
            space_opt = [o for o in optimizations if o['type'] == 'space']
            if space_opt:
                estimated_improvement['space_complexity'] = f"{space_complexity} → Improved"
            
            if quality.get('quality_score', 0) < 80:
                estimated_improvement['quality_score'] = f"+{min(20, (80 - quality.get('quality_score', 0)))} points"
        
        return {
            'optimizations': optimizations,
            'estimated_improvement': estimated_improvement
        }


def analyze_code_intelligence(code: str, language: str) -> Dict:
    """
    Main function: Comprehensive code intelligence analysis
    
    Returns complete evaluation report
    """
    # Step 1: Parse code
    code_structure = CodeParser.parse_code(code, language)
    
    # Step 2: Predict time complexity
    time_complexity = TimeComplexityPredictor.predict_complexity(code_structure, code)
    
    # Step 3: Estimate memory usage
    memory_usage = MemoryUsageEstimator.estimate_memory(code_structure, code)
    
    # Step 4: Score code quality
    code_quality = CodeQualityScorer.score_quality(code, language, code_structure)
    
    # Step 5: Analyze best practices
    best_practices = BestPracticeAnalyzer.analyze_best_practices(code, language, code_structure)
    
    # Step 6: Suggest optimizations
    optimizations = OptimizationAdvisor.suggest_optimizations(
        code, language, code_structure, time_complexity, code_quality
    )
    
    # Build comprehensive report
    intelligence_report = {
        'code_structure': code_structure,
        'time_complexity': time_complexity,
        'memory_usage': memory_usage,
        'code_quality': code_quality,
        'best_practices': best_practices,
        'optimizations': optimizations,
        'summary': {
            'overall_score': round((code_quality.get('quality_score', 0) + best_practices.get('score', 0)) / 2),
            'complexity_rating': 'High' if 'O(n²)' in time_complexity.get('complexity', '') or 'O(2^n)' in time_complexity.get('complexity', '') else 'Moderate',
            'quality_rating': 'Excellent' if code_quality.get('quality_score', 0) >= 80 else 'Good' if code_quality.get('quality_score', 0) >= 60 else 'Needs Improvement'
        }
    }
    
    return intelligence_report
