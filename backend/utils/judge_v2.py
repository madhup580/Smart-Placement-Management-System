"""
LeetCode-style Judge System v2
Strictly separates Run (practice) and Submit (judge) modes
"""
import re
import json
import ast
import subprocess
import tempfile
import os
import time
import platform
from utils.compiler import execute_code

# ============================================================================
# 1️⃣ SEPARATE EXECUTION MODES (MANDATORY)
# ============================================================================

class ExecutionMode:
    """Execution mode constants"""
    RUN = "run"      # Practice mode - allow main(), show stdout
    SUBMIT = "submit"  # Judge mode - function-based, no main()

# ============================================================================
# 2️⃣ RUN MODE - Practice Execution
# ============================================================================

def execute_run_mode(code, language, stdin='', sample_input=None):
    """
    Run mode: Execute code normally with main() support
    - Allow main() or equivalent
    - Use sample test cases only
    - Execute code normally
    - Capture and show stdout
    - Do not judge correctness strictly
    """
    # Always wrap code with main() if it doesn't have one
    # This ensures LeetCode-style code (without main) can still run in Run mode
    # The wrapper functions check if main() exists and only wrap if needed
    wrapped_code = wrap_code_for_run(code, language, sample_input)
    
    # Execute normally. If the editor does not provide custom stdin, run with
    # the visible sample input so practice runs work immediately.
    run_stdin = stdin if stdin else (sample_input or '')
    output, status, exec_time, memory = execute_code(wrapped_code, language, run_stdin)
    
    return {
        'output': output,
        'status': status,
        'execution_time': exec_time,
        'memory_used': memory,
        'mode': ExecutionMode.RUN
    }

# ============================================================================
# 3️⃣ SUBMIT MODE - Function-Based Judging
# ============================================================================

def execute_submit_mode(code, language, test_cases):
    """
    LeetCode-style Submit Mode: Judge code against multiple hidden test cases
    - Execute code in sandboxed environment (Piston API)
    - Run against ALL test cases (hidden from user)
    - Return proper verdicts: Accepted, Wrong Answer, Runtime Error, etc.
    - Do NOT expose test case details to students
    """
    from utils.compiler import execute_code, LANGUAGE_LIMITS
    
    # Get language-specific limits
    limits = LANGUAGE_LIMITS.get(language, {'time': 10, 'memory': 256})
    
    # Extract solution function (remove main if present)
    solution_code = extract_solution_function(code, language)
    
    if not solution_code:
        return {
            'passed': 0,
            'total': len(test_cases),
            'results': [],
            'status': 'compilation_error',
            'verdict': 'Compilation Error',
            'message': 'Could not extract solution function',
            'execution_time': 0.0,
            'mode': ExecutionMode.SUBMIT
        }
    
    # Run test cases - ALL test cases are hidden from user
    passed = 0
    total = len(test_cases)
    results = []
    first_error = None
    first_error_status = None
    max_execution_time = 0.0
    
    for i, test_case in enumerate(test_cases):
        input_str = test_case.get('input', '')
        expected_output_str = test_case.get('output', '').strip()
        
        # Build executable code with test case input
        executable_code = build_executable_code(solution_code, language, input_str)
        
        # Execute code with time and memory limits
        output, status, exec_time, memory = execute_code(
            executable_code, 
            language, 
            stdin='',
            time_limit=limits['time'],
            memory_limit=limits['memory']
        )
        
        max_execution_time = max(max_execution_time, exec_time)
        
        # Determine verdict for this test case
        verdict = _get_verdict(status, output, expected_output_str)
        
        # Check if test case passed
        if status == 'accepted':
            actual_output = output.strip()
            is_passed = _compare_outputs(actual_output, expected_output_str)
            
            if is_passed:
                passed += 1
                verdict = 'Accepted'
            else:
                verdict = 'Wrong Answer'
                if not first_error:
                    first_error = f"Expected: {expected_output_str[:100]}, Got: {actual_output[:100]}"
                    first_error_status = 'wrong_answer'
        else:
            # Compilation error, runtime error, timeout, etc.
            if not first_error:
                first_error = output[:200] if output else status
                first_error_status = status
            verdict = _get_verdict(status, output, expected_output_str)
        
        # Store result (but don't expose input/output details to user)
        results.append({
            'test_case': i + 1,
            'passed': verdict == 'Accepted',
            'status': status,
            'verdict': verdict,
            'execution_time': exec_time
        })
    
    # Determine overall verdict (LeetCode-style)
    if passed == total:
        overall_verdict = 'Accepted'
        overall_status = 'accepted'
        message = f'All {total} test cases passed!'
    elif first_error_status == 'compilation_error':
        overall_verdict = 'Compilation Error'
        overall_status = 'compilation_error'
        message = first_error or 'Compilation failed'
    elif first_error_status == 'time_limit_exceeded':
        overall_verdict = 'Time Limit Exceeded'
        overall_status = 'time_limit_exceeded'
        message = f'Execution exceeded time limit of {limits["time"]} seconds'
    elif first_error_status == 'memory_limit_exceeded':
        overall_verdict = 'Memory Limit Exceeded'
        overall_status = 'memory_limit_exceeded'
        message = f'Execution exceeded memory limit of {limits["memory"]} MB'
    elif first_error_status == 'runtime_error':
        overall_verdict = 'Runtime Error'
        overall_status = 'runtime_error'
        message = first_error or 'Runtime error occurred'
    else:
        overall_verdict = 'Wrong Answer'
        overall_status = 'wrong_answer'
        message = f'Passed {passed}/{total} test cases'
    
    return {
        'passed': passed,
        'total': total,
        'results': results,  # Results without exposing test case details
        'status': overall_status,
        'verdict': overall_verdict,
        'message': message,
        'execution_time': max_execution_time,
        'mode': ExecutionMode.SUBMIT
    }

def _get_verdict(status, output, expected_output):
    """Get human-readable verdict from status"""
    verdict_map = {
        'accepted': 'Accepted',
        'compilation_error': 'Compilation Error',
        'runtime_error': 'Runtime Error',
        'time_limit_exceeded': 'Time Limit Exceeded',
        'memory_limit_exceeded': 'Memory Limit Exceeded',
        'error': 'Error'
    }
    return verdict_map.get(status, 'Error')

def _compare_outputs(actual, expected):
    """Compare actual and expected outputs (LeetCode-style)"""
    # Normalize whitespace
    actual = actual.strip().replace('\r\n', '\n').replace('\r', '\n')
    expected = expected.strip().replace('\r\n', '\n').replace('\r', '\n')

    if actual == expected:
        return True
    
    # Try JSON comparison for structured data
    try:
        import json
        actual_json = json.loads(actual)
        expected_json = json.loads(expected)
        
        # For exact structured matches, accept immediately. If JSON parses but
        # shapes differ (for example [-1] vs -1), continue to numeric parsing.
        if actual_json == expected_json:
            return True
    except:
        pass

    actual_numbers = _parse_numeric_output(actual)
    expected_numbers = _parse_numeric_output(expected)
    if actual_numbers is not None and expected_numbers is not None:
        return actual_numbers == expected_numbers
    
    # String comparison (normalized)
    return actual == expected

def _parse_numeric_output(value):
    """Parse numeric judge output in either '[0,1]' or '0 1' style."""
    cleaned = value.strip()
    if not cleaned:
        return None

    if not re.fullmatch(r'[\s,\[\]\(\)\{\}\-+\d.]+', cleaned):
        return None

    numbers = re.findall(r'[-+]?\d+(?:\.\d+)?', cleaned)
    if not numbers:
        return None

    parsed = []
    for number in numbers:
        parsed.append(float(number) if '.' in number else int(number))
    return parsed

def build_executable_code(solution_code, language, input_str):
    """Build executable code with test case input embedded"""
    # Parse input
    try:
        inputs = parse_test_case_input(input_str)
    except:
        inputs = input_str
    
    if language == 'python':
        return _build_python_executable(solution_code, inputs)
    elif language == 'cpp':
        return _build_cpp_executable(solution_code, inputs)
    elif language == 'c':
        return _build_c_executable(solution_code, inputs)
    elif language == 'java':
        return _build_java_executable(solution_code, inputs)
    return solution_code

def _build_python_executable(solution_code, inputs):
    """Build executable Python code"""
    # Try Solution class
    if 'class Solution' in solution_code:
        # Find method name
        import re
        method_match = re.search(r'def\s+(\w+)\s*\(', solution_code)
        if method_match:
            method_name = method_match.group(1)
            if isinstance(inputs, (list, tuple)) and len(inputs) >= 2:
                return f"""{solution_code}

if __name__ == "__main__":
    solution = Solution()
    result = solution.{method_name}({inputs[0]}, {inputs[1]})
    print(result)
"""
            elif isinstance(inputs, (list, tuple)):
                return f"""{solution_code}

if __name__ == "__main__":
    solution = Solution()
    result = solution.{method_name}({inputs[0]})
    print(result)
"""
    
    # Try standalone function
    import re
    func_match = re.search(r'def\s+(\w+)\s*\(', solution_code)
    if func_match:
        func_name = func_match.group(1)
        if isinstance(inputs, (list, tuple)):
            args = ', '.join(repr(inp) for inp in inputs)
            return f"""{solution_code}

if __name__ == "__main__":
    result = {func_name}({args})
    print(result)
"""
        else:
            return f"""{solution_code}

if __name__ == "__main__":
    result = {func_name}({inputs})
    print(result)
"""
    
    return solution_code

def _build_cpp_executable(solution_code, inputs):
    """Build executable C++ code"""
    import re
    # Find Solution class and method
    method_match = re.search(r'(\w+)\s*\([^)]*\)\s*\{', solution_code)
    method_name = method_match.group(1) if method_match else 'twoSum'
    
    # Parse inputs
    nums = []
    target = 0
    if isinstance(inputs, (list, tuple)) and len(inputs) >= 2:
        nums = list(inputs[0]) if isinstance(inputs[0], (list, tuple)) else [inputs[0]]
        target = inputs[1]
    elif isinstance(inputs, (list, tuple)):
        nums = list(inputs[0]) if isinstance(inputs[0], (list, tuple)) else [inputs[0]]
    
    nums_str = ', '.join(map(str, nums)) if nums else '0'
    
    return f"""#include <iostream>
#include <vector>
using namespace std;

{solution_code}

int main() {{
    Solution solution;
    vector<int> nums = {{{nums_str}}};
    int target = {target};
    vector<int> result = solution.{method_name}(nums, target);
    cout << "[";
    for (int i = 0; i < result.size(); i++) {{
        if (i > 0) cout << ",";
        cout << result[i];
    }}
    cout << "]";
    return 0;
}}
"""

def _build_c_executable(solution_code, inputs):
    """Build executable C code"""
    import re
    func_match = re.search(r'(\w+)\s*\([^)]*\)\s*\{', solution_code)
    func_name = func_match.group(1) if func_match else 'twoSum'
    
    nums = []
    target = 0
    if isinstance(inputs, (list, tuple)) and len(inputs) >= 2:
        nums = list(inputs[0]) if isinstance(inputs[0], (list, tuple)) else [inputs[0]]
        target = inputs[1]
    
    nums_str = ', '.join(map(str, nums)) if nums else '0'
    
    return f"""#include <stdio.h>
#include <stdlib.h>

{solution_code}

int main() {{
    int nums[] = {{{nums_str}}};
    int numsSize = {len(nums)};
    int target = {target};
    int returnSize;
    int* result = {func_name}(nums, numsSize, target, &returnSize);
    if (result != NULL) {{
        printf("[");
        for (int i = 0; i < returnSize; i++) {{
            if (i > 0) printf(",");
            printf("%d", result[i]);
        }}
        printf("]");
        free(result);
    }}
    return 0;
}}
"""

def _build_java_executable(solution_code, inputs):
    """Build executable Java code"""
    import re
    method_match = re.search(r'public\s+(?:static\s+)?[\w<>\[\], ?]+\s+(\w+)\s*\([^)]*\)', solution_code)
    method_name = method_match.group(1) if method_match else 'twoSum'
    
    nums = []
    target = 0
    if isinstance(inputs, (list, tuple)) and len(inputs) >= 2:
        nums = list(inputs[0]) if isinstance(inputs[0], (list, tuple)) else [inputs[0]]
        target = inputs[1]
    
    nums_str = ', '.join(map(str, nums)) if nums else '0'
    
    return f"""import java.util.*;

{solution_code}

class Main {{
    public static void main(String[] args) {{
        Solution solution = new Solution();
        int[] nums = {{{nums_str}}};
        int target = {target};
        int[] result = solution.{method_name}(nums, target);
        System.out.print("[");
        for (int i = 0; i < result.length; i++) {{
            if (i > 0) System.out.print(",");
            System.out.print(result[i]);
        }}
        System.out.print("]");
    }}
}}
"""

# ============================================================================
# 4️⃣ INPUT HANDLING
# ============================================================================

def parse_test_case_input(input_str):
    """
    Parse test case input string into Python objects
    Platform supplies inputs - user code must not read input
    Handles formats like:
    - "[2,7,11,15], target = 9"
    - "[2,7,11,15]\n9"
    - "2 7 11 15\n9"
    """
    if not input_str or not input_str.strip():
        return None
    
    input_str = input_str.strip()
    
    # Handle format: "[2,7,11,15], target = 9"
    if ', target =' in input_str or ', target=' in input_str:
        parts = re.split(r',\s*target\s*=\s*', input_str, flags=re.IGNORECASE)
        if len(parts) == 2:
            try:
                # Parse array part
                array_str = parts[0].strip()
                if array_str.startswith('[') and array_str.endswith(']'):
                    nums = ast.literal_eval(array_str)
                else:
                    nums = json.loads(array_str)
                
                # Parse target
                target_str = parts[1].strip()
                target = int(target_str)
                
                return [nums, target]
            except:
                pass
    
    # Handle format: "[2,7,11,15]\n9" or multiple lines
    lines = input_str.split('\n')
    parsed = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            # Try to parse as JSON/Python literal
            parsed.append(ast.literal_eval(line))
        except:
            try:
                parsed.append(json.loads(line))
            except:
                # Try to parse as space-separated numbers
                try:
                    numbers = [int(x) for x in line.split()]
                    if len(numbers) == 1:
                        parsed.append(numbers[0])
                    else:
                        parsed.append(numbers)
                except:
                    parsed.append(line)
    
    # Common coding-practice format:
    # n
    # a1 a2 ... an
    # target
    if (
        len(parsed) >= 3
        and isinstance(parsed[0], int)
        and isinstance(parsed[1], list)
        and isinstance(parsed[2], int)
    ):
        return [parsed[1], parsed[2]]

    return parsed if len(parsed) > 1 else (parsed[0] if parsed else None)

# ============================================================================
# 5️⃣ FUNCTION-BASED JUDGING (Core)
# ============================================================================

def extract_solution_function(code, language):
    """
    Extract solution function from code
    Remove main() if present
    """
    if language == 'python':
        return extract_solution_python(code)
    elif language == 'cpp':
        return extract_solution_cpp(code)
    elif language == 'c':
        return extract_solution_c(code)
    elif language == 'java':
        return extract_solution_java(code)
    return code

def extract_solution_python(code):
    """Extract Python solution function, remove main if present"""
    # Remove main block
    code = re.sub(
        r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:.*?$',
        '',
        code,
        flags=re.DOTALL
    )
    return code.strip()

def extract_solution_cpp(code):
    """Extract C++ solution, remove main if present"""
    # Remove main function (handle multi-line)
    lines = code.split('\n')
    result_lines = []
    in_main = False
    brace_count = 0
    
    for line in lines:
        if re.search(r'int\s+main\s*\(', line):
            in_main = True
            brace_count = line.count('{') - line.count('}')
            continue
        if in_main:
            brace_count += line.count('{') - line.count('}')
            if brace_count <= 0:
                in_main = False
            continue
        result_lines.append(line)
    
    return '\n'.join(result_lines).strip()

def extract_solution_c(code):
    """Extract C solution, remove main if present"""
    # Same as C++
    return extract_solution_cpp(code)

def extract_solution_java(code):
    """Extract Java solution, remove main if present"""
    lines = code.split('\n')
    result_lines = []
    in_main = False
    brace_count = 0
    
    for line in lines:
        if re.search(r'public\s+static\s+void\s+main\s*\(', line):
            in_main = True
            brace_count = line.count('{') - line.count('}')
            continue
        if in_main:
            brace_count += line.count('{') - line.count('}')
            if brace_count <= 0:
                in_main = False
            continue
        result_lines.append(line)
    
    return '\n'.join(result_lines).strip()

def call_solution_function(solution_code, language, inputs):
    """
    Call solution function programmatically
    Platform provides main() internally
    """
    if language == 'python':
        return call_python_function(solution_code, inputs)
    elif language == 'cpp':
        return call_cpp_function(solution_code, inputs)
    elif language == 'c':
        return call_c_function(solution_code, inputs)
    elif language == 'java':
        return call_java_function(solution_code, inputs)
    return None, 'error'

def call_python_function(solution_code, inputs):
    """Call Python function directly"""
    namespace = {}
    try:
        exec(solution_code, namespace)
        
        # Parse inputs - ensure proper format
        parsed_inputs = inputs
        if isinstance(inputs, (list, tuple)) and len(inputs) >= 2:
            # Ensure first input is a list
            nums_input = inputs[0]
            if not isinstance(nums_input, (list, tuple)):
                nums_input = [nums_input]
            parsed_inputs = [nums_input, inputs[1]]
        elif isinstance(inputs, (list, tuple)) and len(inputs) == 1:
            if isinstance(inputs[0], (list, tuple)):
                parsed_inputs = inputs[0]
            else:
                parsed_inputs = [inputs[0]]
        
        # Try Solution class
        if 'Solution' in namespace:
            solution = namespace['Solution']()
            for attr_name in dir(solution):
                if not attr_name.startswith('_') and callable(getattr(solution, attr_name)):
                    attr = getattr(solution, attr_name)
                    if attr.__name__ != '__init__':
                        method = getattr(solution, attr_name)
                        if isinstance(parsed_inputs, (list, tuple)) and len(parsed_inputs) >= 2:
                            result = method(parsed_inputs[0], parsed_inputs[1])
                        elif isinstance(parsed_inputs, (list, tuple)):
                            result = method(*parsed_inputs)
                        else:
                            result = method(parsed_inputs)
                        return result, 'accepted'
        
        # Try standalone function
        common_names = ['twoSum', 'solution', 'solve', 'answer']
        for name in common_names:
            if name in namespace and callable(namespace[name]):
                func = namespace[name]
                if isinstance(parsed_inputs, (list, tuple)) and len(parsed_inputs) >= 2:
                    result = func(parsed_inputs[0], parsed_inputs[1])
                elif isinstance(parsed_inputs, (list, tuple)):
                    result = func(*parsed_inputs)
                else:
                    result = func(parsed_inputs)
                return result, 'accepted'
        
        return None, 'error'
    except Exception as e:
        return str(e), 'runtime_error'

def call_cpp_function(solution_code, inputs):
    """Call C++ function - platform provides main() internally"""
    # Detect function name
    method_match = re.search(r'(\w+)\s*\([^)]*\)\s*\{', solution_code)
    method_name = method_match.group(1) if method_match else 'twoSum'
    
    # Parse inputs - ensure proper format
    nums = []
    target = 0
    
    if isinstance(inputs, (list, tuple)):
        if len(inputs) >= 2:
            # First input should be the array, second should be target
            nums_input = inputs[0]
            if isinstance(nums_input, (list, tuple)):
                nums = [int(n) for n in nums_input]
            else:
                nums = [int(nums_input)]
            target = int(inputs[1])
        elif len(inputs) == 1:
            # Single input - could be array or single value
            if isinstance(inputs[0], (list, tuple)):
                nums = [int(n) for n in inputs[0]]
            else:
                nums = [int(inputs[0])]
    else:
        # Single value input
        try:
            nums = [int(inputs)] if isinstance(inputs, (int, float)) else []
        except:
            nums = []
    
    # Ensure nums is a list of integers
    if not isinstance(nums, list):
        nums = [int(nums)] if nums else []
    else:
        nums = [int(n) for n in nums] if nums else []
    
    target = int(target) if target else 0
    
    # Generate proper C++ vector initialization
    nums_str = ', '.join(map(str, nums)) if nums else '0'
    
    # Platform provides main() internally
    judge_code = f"""
#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <unordered_map>
using namespace std;

{solution_code}

int main() {{
    Solution solution;
    vector<int> nums = {{{nums_str}}};
    int target = {target};
    vector<int> result = solution.{method_name}(nums, target);
    cout << "[";
    for (int i = 0; i < result.size(); i++) {{
        if (i > 0) cout << ",";
        cout << result[i];
    }}
    cout << "]";
    return 0;
}}
"""
    
    output, status, exec_time, memory = execute_code_with_limits(judge_code, 'cpp', '')
    
    if status == 'accepted':
        try:
            result_str = output.strip()
            match = re.search(r'\[([^\]]+)\]', result_str)
            if match:
                result = json.loads('[' + match.group(1) + ']')
                return result, 'accepted'
            return output, 'accepted'
        except:
            return output, status
    else:
        return output, status

def call_c_function(solution_code, inputs):
    """Call C function - platform provides main() internally"""
    # Detect function name
    func_match = re.search(r'(\w+)\s*\([^)]*\)\s*\{', solution_code)
    func_name = func_match.group(1) if func_match else 'twoSum'
    
    # Parse inputs - ensure proper format
    nums = []
    target = 0
    
    if isinstance(inputs, (list, tuple)):
        if len(inputs) >= 2:
            # First input should be the array, second should be target
            nums = list(inputs[0]) if isinstance(inputs[0], (list, tuple)) else [inputs[0]]
            target = inputs[1] if len(inputs) > 1 else 0
        elif len(inputs) == 1:
            # Single input - could be array or single value
            if isinstance(inputs[0], (list, tuple)):
                nums = list(inputs[0])
            else:
                nums = [inputs[0]]
    else:
        # Single value input
        nums = [inputs] if isinstance(inputs, (int, float)) else []
    
    # Ensure nums is a list of numbers
    if not isinstance(nums, list):
        nums = [nums] if nums else []
    
    # Convert all to integers
    try:
        nums = [int(n) for n in nums]
        target = int(target)
    except (ValueError, TypeError):
        nums = []
        target = 0
    
    # Platform provides main() internally
    has_stdio = '#include <stdio.h>' in solution_code or '#include<stdio.h>' in solution_code
    has_stdlib = '#include <stdlib.h>' in solution_code or '#include<stdlib.h>' in solution_code
    
    headers = ''
    if not has_stdio:
        headers += '#include <stdio.h>\n'
    if not has_stdlib:
        headers += '#include <stdlib.h>\n'
    
    # Generate proper C array initialization
    nums_str = ', '.join(map(str, nums)) if nums else '0'
    
    judge_code = f"""
{headers}
{solution_code}

int main() {{
    int nums[] = {{{nums_str}}};
    int numsSize = {len(nums)};
    int target = {target};
    int returnSize;
    int* result = {func_name}(nums, numsSize, target, &returnSize);
    if (result != NULL) {{
        printf("[");
        for (int i = 0; i < returnSize; i++) {{
            if (i > 0) printf(",");
            printf("%d", result[i]);
        }}
        printf("]");
        free(result);
    }}
    return 0;
}}
"""
    
    output, status, exec_time, memory = execute_code_with_limits(judge_code, 'c', '')
    
    if status == 'accepted':
        try:
            result_str = output.strip()
            match = re.search(r'\[([^\]]+)\]', result_str)
            if match:
                result = json.loads('[' + match.group(1) + ']')
                return result, 'accepted'
            return output, 'accepted'
        except:
            return output, status
    else:
        return output, status

def call_java_function(solution_code, inputs):
    """Call Java function - platform provides Main class internally"""
    # Detect method name
    method_match = re.search(r'public\s+(?:static\s+)?[\w<>\[\], ?]+\s+(\w+)\s*\([^)]*\)', solution_code)
    method_name = method_match.group(1) if method_match else 'twoSum'
    
    # Parse inputs - ensure proper format
    nums = []
    target = 0
    
    if isinstance(inputs, (list, tuple)):
        if len(inputs) >= 2:
            # First input should be the array, second should be target
            nums_input = inputs[0]
            if isinstance(nums_input, (list, tuple)):
                nums = [int(n) for n in nums_input]
            else:
                nums = [int(nums_input)]
            target = int(inputs[1])
        elif len(inputs) == 1:
            # Single input - could be array or single value
            if isinstance(inputs[0], (list, tuple)):
                nums = [int(n) for n in inputs[0]]
            else:
                nums = [int(inputs[0])]
    else:
        # Single value input
        try:
            nums = [int(inputs)] if isinstance(inputs, (int, float)) else []
        except:
            nums = []
    
    # Ensure nums is a list of integers
    if not isinstance(nums, list):
        nums = [int(nums)] if nums else []
    else:
        nums = [int(n) for n in nums] if nums else []
    
    target = int(target) if target else 0
    
    # Generate proper Java array initialization
    nums_str = ', '.join(map(str, nums)) if nums else '0'
    
    # Platform provides Main class internally
    judge_code = f"""
import java.util.*;

{solution_code}

class Main {{
    public static void main(String[] args) {{
        Solution solution = new Solution();
        int[] nums = {{{nums_str}}};
        int target = {target};
        int[] result = solution.{method_name}(nums, target);
        System.out.print("[");
        for (int i = 0; i < result.length; i++) {{
            if (i > 0) System.out.print(",");
            System.out.print(result[i]);
        }}
        System.out.print("]");
    }}
}}
"""
    
    output, status, exec_time, memory = execute_code_with_limits(judge_code, 'java', '')
    
    if status == 'accepted':
        try:
            result_str = output.strip()
            match = re.search(r'\[([^\]]+)\]', result_str)
            if match:
                result = json.loads('[' + match.group(1) + ']')
                return result, 'accepted'
            return output, 'accepted'
        except:
            return output, status
    else:
        return output, status

# ============================================================================
# 6️⃣ LANGUAGE-SPECIFIC RULES
# ============================================================================

def wrap_code_for_run(code, language, sample_input=None):
    """
    Wrap code with main() for Run mode
    Language-specific handling
    """
    if language == 'python':
        return wrap_python_for_run(code, sample_input)
    elif language == 'cpp':
        return wrap_cpp_for_run(code, sample_input)
    elif language == 'c':
        return wrap_c_for_run(code, sample_input)
    elif language == 'java':
        return wrap_java_for_run(code, sample_input)
    return code

def wrap_python_for_run(code, sample_input=None):
    """Wrap Python code with main() for Run mode"""
    # If main() already exists, return as-is
    if re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]', code):
        return code
    
    # Try to find Solution class with method
    method_match = re.search(r'class\s+Solution.*?def\s+(\w+)\s*\(', code, re.DOTALL)
    if method_match:
        func_name = method_match.group(1)
        if sample_input:
            try:
                inputs = parse_test_case_input(sample_input)
                if isinstance(inputs, (list, tuple)) and len(inputs) >= 2:
                    return f"""
{code}

if __name__ == "__main__":
    solution = Solution()
    result = solution.{func_name}({inputs[0]}, {inputs[1]})
    print(result)
"""
            except:
                pass
        # Even without sample_input, wrap with main() so code can execute
        return f"""
{code}

if __name__ == "__main__":
    solution = Solution()
    # Add your test input here
    # Example: result = solution.{func_name}([2,7,11,15], 9)
    # print(result)
    pass
"""
    
    # Try to find standalone function
    func_match = re.search(r'def\s+(\w+)\s*\(', code)
    if func_match:
        func_name = func_match.group(1)
        if sample_input:
            try:
                inputs = parse_test_case_input(sample_input)
                if isinstance(inputs, (list, tuple)) and len(inputs) >= 1:
                    return f"""
{code}

if __name__ == "__main__":
    result = {func_name}({', '.join(repr(inp) for inp in inputs)})
    print(result)
"""
            except:
                pass
        return f"""
{code}

if __name__ == "__main__":
    # Add your test input here
    # Example: result = {func_name}([2,7,11,15], 9)
    # print(result)
    pass
"""
    
    # If no function found, return as-is (might be a script)
    return code

def wrap_cpp_for_run(code, sample_input=None):
    """Wrap C++ code with main() for Run mode"""
    # If main() already exists, return as-is
    if re.search(r'int\s+main\s*\(', code):
        return code
    
    # Check what headers are already included
    has_iostream = '#include <iostream>' in code or '#include<iostream>' in code
    has_vector = '#include <vector>' in code or '#include<vector>' in code
    has_unordered_map = '#include <unordered_map>' in code or '#include<unordered_map>' in code
    has_map = '#include <map>' in code or '#include<map>' in code
    has_string = '#include <string>' in code or '#include<string>' in code
    
    # Build headers string
    headers = []
    if not has_iostream:
        headers.append('#include <iostream>')
    if not has_vector:
        headers.append('#include <vector>')
    if not has_unordered_map and ('unordered_map' in code or 'unordered_set' in code):
        headers.append('#include <unordered_map>')
    if not has_map and ('map<' in code or 'set<' in code):
        headers.append('#include <map>')
    if not has_string and ('std::string' in code or 'string ' in code):
        headers.append('#include <string>')
    
    # Determine if code uses std:: prefix or using namespace std
    uses_std_prefix = 'std::' in code
    has_using_namespace = 'using namespace std' in code or 'using std::' in code
    
    # Build headers string
    if headers:
        headers_str = '\n'.join(headers)
        if not uses_std_prefix and not has_using_namespace:
            headers_str += '\nusing namespace std;'
    else:
        if not uses_std_prefix and not has_using_namespace:
            headers_str = 'using namespace std;'
        else:
            headers_str = ''
    
    # Determine namespace prefix to use in main()
    if uses_std_prefix:
        ns_prefix = 'std::'
    else:
        ns_prefix = ''
    
    # Try to find Solution class method
    method_name = None
    
    # Find Solution class and extract method name
    solution_match = re.search(r'class\s+Solution\s*\{', code, re.DOTALL)
    if solution_match:
        # Extract class body by finding matching braces
        start_pos = solution_match.end()
        brace_count = 1
        end_pos = start_pos
        for i in range(start_pos, len(code)):
            if code[i] == '{':
                brace_count += 1
            elif code[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break
        class_body = code[start_pos:end_pos]
        
        # Find all methods in class body - look for method declarations
        # Pattern: return_type method_name(params) {
        method_pattern = r'(?:std::)?(?:vector|int|void|string|bool|double|float|char|long|short|unsigned)\s*[<>\w\s&*]*?\s+(\w+)\s*\([^)]*\)\s*\{'
        method_matches = re.finditer(method_pattern, class_body)
        
        # Filter out constructors, destructors, and common non-solution methods
        excluded = {'Solution', '~Solution', 'operator', 'get', 'set', '__init__', 'begin', 'end', 'size', 'empty', 'clear', 'push_back', 'pop_back'}
        for match in method_matches:
            name = match.group(1)
            if name not in excluded:
                method_name = name
                break
        
        # Fallback: if no method found with return type, look for any method
        if not method_name:
            all_methods = re.findall(r'(\w+)\s*\([^)]*\)\s*\{', class_body)
            for name in all_methods:
                if name not in excluded:
                    method_name = name
                    break
    
    if method_name:
        if sample_input:
            try:
                inputs = parse_test_case_input(sample_input)
                if isinstance(inputs, (list, tuple)) and len(inputs) >= 2:
                    # Ensure nums is a list of integers
                    nums_input = inputs[0]
                    if isinstance(nums_input, (list, tuple)):
                        nums = [int(n) for n in nums_input]
                    else:
                        nums = [int(nums_input)]
                    target = int(inputs[1])
                    
                    nums_str = ', '.join(map(str, nums))
                    return f"""
{headers_str}

{code}

int main() {{
    {ns_prefix}vector<int> nums = {{{nums_str}}};
    int target = {target};
    Solution solution;
    {ns_prefix}vector<int> result = solution.{method_name}(nums, target);
    {ns_prefix}cout << "[";
    for (int i = 0; i < result.size(); i++) {{
        if (i > 0) {ns_prefix}cout << ",";
        {ns_prefix}cout << result[i];
    }}
    {ns_prefix}cout << "]\\n";
    return 0;
}}
"""
            except Exception as e:
                pass
        
        # Even without sample_input, wrap with main() using first test case example
        # Make sure headers_str is properly formatted
        if headers_str and not headers_str.endswith('\n'):
            headers_str += '\n'
        
        return f"""{headers_str}
{code}

int main() {{
    // Example test case
    {ns_prefix}vector<int> nums = {{2, 7, 11, 15}};
    int target = 9;
    Solution solution;
    {ns_prefix}vector<int> result = solution.{method_name}(nums, target);
    {ns_prefix}cout << "[";
    for (int i = 0; i < result.size(); i++) {{
        if (i > 0) {ns_prefix}cout << ",";
        {ns_prefix}cout << result[i];
    }}
    {ns_prefix}cout << "]\\n";
    return 0;
}}
"""
    
    # Try to find standalone function
    func_match = re.search(r'(\w+)\s*\([^)]*\)\s*\{', code)
    if func_match:
        func_name = func_match.group(1)
        if sample_input:
            try:
                inputs = parse_test_case_input(sample_input)
                if isinstance(inputs, (list, tuple)) and len(inputs) >= 2:
                    # Ensure nums is a list of integers
                    nums_input = inputs[0]
                    if isinstance(nums_input, (list, tuple)):
                        nums = [int(n) for n in nums_input]
                    else:
                        nums = [int(nums_input)]
                    target = int(inputs[1])
                    
                    nums_str = ', '.join(map(str, nums))
                    return f"""
{headers_str}

{code}

int main() {{
    {ns_prefix}vector<int> nums = {{{nums_str}}};
    int target = {target};
    {ns_prefix}vector<int> result = {func_name}(nums, target);
    {ns_prefix}cout << "[";
    for (int i = 0; i < result.size(); i++) {{
        if (i > 0) {ns_prefix}cout << ",";
        {ns_prefix}cout << result[i];
    }}
    {ns_prefix}cout << "]\\n";
    return 0;
}}
"""
            except:
                pass
        return f"""
{headers_str}

{code}

int main() {{
    // Add your test input here
    return 0;
}}
"""
    
    # If no function found, still wrap with basic main() so it compiles
    return f"""
{headers_str}

{code}

int main() {{
    // Add your test input here
    return 0;
}}
"""

def wrap_c_for_run(code, sample_input=None):
    """Wrap C code with main() for Run mode - user program controls input/output"""
    # If main() already exists, return as-is (user controls everything)
    if re.search(r'int\s+main\s*\(', code):
        return code
    
    # Find function name
    func_match = re.search(r'(\w+)\s*\([^)]*\)\s*\{', code)
    if not func_match:
        return code
    
    func_name = func_match.group(1)
    
    # Check headers
    has_stdio = '#include <stdio.h>' in code or '#include<stdio.h>' in code
    has_stdlib = '#include <stdlib.h>' in code or '#include<stdlib.h>' in code
    
    headers = ''
    if not has_stdio:
        headers += '#include <stdio.h>\n'
    if not has_stdlib:
        headers += '#include <stdlib.h>\n'
    
    # Determine test input to use - ensure proper parsing
    nums = [2, 7, 11, 15]
    target = 9
    
    if sample_input:
        try:
            inputs = parse_test_case_input(sample_input)
            if isinstance(inputs, (list, tuple)) and len(inputs) >= 2:
                # Ensure nums is a list
                nums_input = inputs[0]
                if isinstance(nums_input, (list, tuple)):
                    nums = [int(n) for n in nums_input]
                else:
                    nums = [int(nums_input)]
                target = int(inputs[1])
            elif isinstance(inputs, (list, tuple)) and len(inputs) == 1:
                # Single input - could be array
                if isinstance(inputs[0], (list, tuple)):
                    nums = [int(n) for n in inputs[0]]
        except (ValueError, TypeError, AttributeError) as e:
            # If parsing fails, use defaults
            pass
    
    # Ensure nums is a list of integers
    if not isinstance(nums, list):
        nums = [nums] if nums else [2, 7, 11, 15]
    nums = [int(n) for n in nums] if nums else [2, 7, 11, 15]
    target = int(target) if target else 9
    
    # Generate proper C array initialization
    nums_str = ', '.join(map(str, nums))
    
    # Always wrap with main() that calls function and prints result
    # This allows Run mode to show output like a normal compiler
    return f"""
{headers}
{code}

int main() {{
    int nums[] = {{{nums_str}}};
    int numsSize = {len(nums)};
    int target = {target};
    int returnSize;
    int* result = {func_name}(nums, numsSize, target, &returnSize);
    if (result != NULL) {{
        printf("[");
        for (int i = 0; i < returnSize; i++) {{
            if (i > 0) printf(",");
            printf("%d", result[i]);
        }}
        printf("]\\n");
        free(result);
    }} else {{
        printf("No solution found\\n");
    }}
    return 0;
}}
"""

def wrap_java_for_run(code, sample_input=None):
    """Wrap Java code with main() for Run mode"""
    if re.search(r'public\s+static\s+void\s+main\s*\(', code):
        return code
    
    method_match = re.search(r'public\s+(?:static\s+)?[\w<>\[\], ?]+\s+(\w+)\s*\([^)]*\)', code)
    if not method_match:
        return code
    
    method_name = method_match.group(1)
    
    if sample_input:
        try:
            inputs = parse_test_case_input(sample_input)
            if isinstance(inputs, (list, tuple)) and len(inputs) >= 2:
                # Ensure nums is a list of integers
                nums_input = inputs[0]
                if isinstance(nums_input, (list, tuple)):
                    nums = [int(n) for n in nums_input]
                else:
                    nums = [int(nums_input)]
                target = int(inputs[1])
                
                nums_str = ', '.join(map(str, nums))
                return f"""
{code}

class Main {{
    public static void main(String[] args) {{
        Solution solution = new Solution();
        int[] nums = {{{nums_str}}};
        int target = {target};
        int[] result = solution.{method_name}(nums, target);
        System.out.print("[");
        for (int i = 0; i < result.length; i++) {{
            if (i > 0) System.out.print(",");
            System.out.print(result[i]);
        }}
        System.out.println("]");
    }}
}}
"""
        except:
            pass
    
    return f"""
{code}

class Main {{
    public static void main(String[] args) {{
        // Add your test input here
    }}
}}
"""

# ============================================================================
# 7️⃣ COMPILATION RULES
# ============================================================================

def execute_code_with_limits(code, language, stdin='', time_limit=5, memory_limit=256):
    """
    Execute code with security limits
    - Time limits (enforced by compiler.py timeout)
    - Memory limits (enforced by compiler.py)
    - Disable system calls & file access (should be in compiler.py)
    """
    # Delegate to compiler.py which should handle limits
    # The compiler already has timeout=5 in subprocess calls
    return execute_code(code, language, stdin)

# ============================================================================
# 8️⃣ OUTPUT COMPARISON RULES
# ============================================================================

def format_output(value):
    """Format output for comparison"""
    if isinstance(value, (list, tuple)):
        return json.dumps(value).replace(' ', '')
    elif isinstance(value, dict):
        return json.dumps(value, sort_keys=True).replace(' ', '')
    elif isinstance(value, (int, float, bool)):
        return str(value)
    else:
        return str(value)

def normalize_and_compare(actual, expected):
    """
    Normalize outputs and compare
    - Normalize order, spacing, types
    - Compare values, not text
    """
    # Remove all whitespace
    actual = actual.replace(' ', '').replace('\n', '').replace('\t', '')
    expected = expected.replace(' ', '').replace('\n', '').replace('\t', '')
    
    # Try JSON comparison for structured data
    try:
        actual_json = json.loads(actual)
        expected_json = json.loads(expected)
        
        # For lists, sort if order doesn't matter (depends on problem)
        # For now, compare as-is
        return actual_json == expected_json
    except:
        pass
    
    # String comparison
    return actual == expected

# ============================================================================
# 9️⃣ ERROR HANDLING RULES
# ============================================================================

def handle_compilation_error(error_msg):
    """Handle compilation errors"""
    return {
        'status': 'compilation_error',
        'error': error_msg
    }

def handle_runtime_error(error_msg):
    """Handle runtime errors"""
    return {
        'status': 'runtime_error',
        'error': error_msg
    }

def handle_timeout():
    """Handle timeout"""
    return {
        'status': 'timeout',
        'error': 'Time Limit Exceeded'
    }

# ============================================================================
# 🔟 SECURITY RULES (CRITICAL)
# ============================================================================

# Security limits should be enforced in compiler.py
# Time limits, memory limits, system call restrictions

