"""
LeetCode-style Code Execution Engine
Uses Piston API (free, sandboxed) as primary execution engine
"""
import requests
import json
import subprocess
import tempfile
import os
import re
import sys
import time
import platform
from config import Config

# Language-specific time and memory limits (in seconds and MB)
LANGUAGE_LIMITS = {
    'python': {'time': 10, 'memory': 256},
    'cpp': {'time': 5, 'memory': 256},
    'c': {'time': 5, 'memory': 256},
    'java': {'time': 10, 'memory': 512}
}

# Piston API endpoint (free, open-source, sandboxed)
PISTON_API_URL = 'https://emkc.org/api/v2/piston/execute'

def execute_code(code, language, stdin='', time_limit=None, memory_limit=None):
    """
    Execute code using Piston API (sandboxed, LeetCode-style)
    Returns: (output, status, execution_time, memory_used)
    
    Status values:
    - 'accepted': Code executed successfully
    - 'compilation_error': Compilation failed
    - 'runtime_error': Runtime error occurred
    - 'time_limit_exceeded': Execution exceeded time limit
    - 'memory_limit_exceeded': Execution exceeded memory limit
    - 'error': Other errors
    """
    # Get language-specific limits
    limits = LANGUAGE_LIMITS.get(language, {'time': 10, 'memory': 256})
    time_limit = time_limit or limits['time']
    memory_limit = memory_limit or limits['memory']
    
    # Prefer local execution so coding practice works without depending on
    # external compiler API credentials or availability.
    if language == 'python':
        return _execute_python_subprocess(code, stdin, time_limit)
    if language == 'cpp':
        return _execute_cpp(code, stdin)
    if language == 'c':
        return _execute_c(code, stdin)
    if language == 'java':
        return _execute_java(code, stdin)

    return _execute_with_piston(code, language, stdin, time_limit, memory_limit)

def _execute_python_subprocess(code, stdin='', time_limit=10):
    """Execute Python code locally in a subprocess with a timeout."""
    temp_dir = tempfile.mkdtemp()
    try:
        code_file = os.path.join(temp_dir, 'main.py')
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)

        start_time = time.time()
        run_result = subprocess.run(
            [sys.executable, code_file],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=time_limit,
            cwd=temp_dir
        )
        execution_time = time.time() - start_time

        if run_result.returncode != 0:
            return run_result.stderr or run_result.stdout or 'Runtime error', 'runtime_error', execution_time, 0.0

        return run_result.stdout, 'accepted', execution_time, 0.0
    except subprocess.TimeoutExpired:
        return "Time Limit Exceeded", 'time_limit_exceeded', time_limit, 0.0
    except Exception as e:
        return str(e), 'runtime_error', 0.0, 0.0
    finally:
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def _execute_with_piston(code, language, stdin='', time_limit=10, memory_limit=256):
    """
    Execute code using Piston API (free, sandboxed execution engine)
    Piston provides secure sandboxed execution similar to LeetCode
    """
    try:
        # Map language names to Piston language identifiers
        lang_map = {
            'python': 'python3',
            'cpp': 'cpp',
            'c': 'c',
            'java': 'java'
        }
        
        piston_lang = lang_map.get(language, language)
        
        # Prepare payload for Piston API
        payload = {
            'language': piston_lang,
            'version': '*',  # Use latest version
            'files': [
                {
                    'content': code
                }
            ],
            'stdin': stdin,
            'compile_timeout': min(time_limit * 1000, 10000),  # Compilation timeout in ms
            'run_timeout': time_limit * 1000,  # Execution timeout in ms
            'memory_limit': memory_limit * 1024 * 1024  # Memory limit in bytes
        }
        
        # Make request to Piston API
        response = requests.post(PISTON_API_URL, json=payload, timeout=time_limit + 5)
        
        if response.status_code != 200:
            return f"API error: {response.status_code}", 'error', 0.0, 0.0
        
        data = response.json()
        
        # Check for compilation errors
        if 'compile' in data:
            compile_data = data['compile']
            if compile_data.get('stderr'):
                return compile_data['stderr'], 'compilation_error', 0.0, 0.0
        
        # Check for runtime execution
        if 'run' in data:
            run_data = data['run']
            stdout = run_data.get('stdout', '')
            stderr = run_data.get('stderr', '')
            
            # Check for timeout
            if run_data.get('signal') == 'SIGKILL' or 'timeout' in stderr.lower():
                return "Time Limit Exceeded", 'time_limit_exceeded', time_limit, 0.0
            
            # Check for memory issues
            if 'memory' in stderr.lower() or run_data.get('signal') == 'SIGSEGV':
                return "Memory Limit Exceeded", 'memory_limit_exceeded', 0.0, memory_limit
            
            # If there's stderr, it's a runtime error
            if stderr:
                return stderr, 'runtime_error', 0.0, 0.0
            
            # Calculate execution time
            execution_time = 0.0
            if 'time' in run_data:
                try:
                    # Piston returns time in seconds
                    execution_time = float(run_data['time'])
                except:
                    pass
            
            # Get memory usage if available
            memory_used = 0.0
            if 'memory' in run_data:
                try:
                    memory_used = float(run_data['memory']) / (1024 * 1024)  # Convert to MB
                except:
                    pass
            
            return stdout, 'accepted', execution_time, memory_used
        else:
            return "Unknown error from execution engine", 'error', 0.0, 0.0
            
    except requests.exceptions.Timeout:
        return "Time Limit Exceeded", 'time_limit_exceeded', time_limit, 0.0
    except requests.exceptions.RequestException as e:
        return f"Execution engine error: {str(e)}", 'error', 0.0, 0.0
    except Exception as e:
        return f"Error: {str(e)}", 'error', 0.0, 0.0

def _execute_python(code, stdin=''):
    """Execute Python code locally"""
    import io
    import sys
    
    # Capture stdout
    old_stdout = sys.stdout
    old_stdin = sys.stdin
    sys.stdout = buffer = io.StringIO()
    sys.stdin = io.StringIO(stdin)
    
    try:
        start_time = time.time()
        exec(code)
        execution_time = time.time() - start_time
        
        # Get output
        output = buffer.getvalue()
        sys.stdout = old_stdout
        sys.stdin = old_stdin
        
        return output, 'accepted', execution_time, 10.0
    except Exception as e:
        sys.stdout = old_stdout
        sys.stdin = old_stdin
        return str(e), 'runtime_error', 0.0, 0.0

def _execute_cpp(code, stdin=''):
    """Execute C++ code locally using g++ or fallback to online API"""
    temp_dir = tempfile.mkdtemp()
    try:
        # Write code to file
        code_file = os.path.join(temp_dir, 'main.cpp')
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Determine executable name based on OS
        is_windows = platform.system() == 'Windows'
        exe_name = 'main.exe' if is_windows else 'main'
        exe_path = os.path.join(temp_dir, exe_name)
        
        # Compile - try g++ first, then cl on Windows
        compile_cmd = None
        if _check_command('g++'):
            compile_cmd = ['g++', '-o', exe_path, code_file, '-std=c++17']
        elif is_windows and _check_command('cl'):
            # Try cl.exe (MSVC) on Windows
            compile_cmd = ['cl', '/EHsc', f'/Fe:{exe_path}', code_file]
        
        if not compile_cmd:
            # Fallback to free online compiler API
            return _execute_cpp_online(code, stdin)
        
        compile_result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=temp_dir
        )
        
        if compile_result.returncode != 0:
            return compile_result.stderr, 'compilation_error', 0.0, 0.0
        
        # Execute
        start_time = time.time()
        run_result = subprocess.run(
            [exe_path] if not is_windows else [exe_path],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=temp_dir
        )
        execution_time = time.time() - start_time
        
        if run_result.returncode != 0:
            return run_result.stderr or "Runtime error", 'runtime_error', execution_time, 0.0
        
        return run_result.stdout, 'accepted', execution_time, 0.0
        
    except subprocess.TimeoutExpired:
        return "Execution timeout", 'timeout', 0.0, 0.0
    except Exception as e:
        return str(e), 'runtime_error', 0.0, 0.0
    finally:
        # Cleanup
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def _execute_c(code, stdin=''):
    """Execute C code locally using gcc"""
    temp_dir = tempfile.mkdtemp()
    try:
        # Write code to file
        code_file = os.path.join(temp_dir, 'main.c')
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Determine executable name based on OS
        is_windows = platform.system() == 'Windows'
        exe_name = 'main.exe' if is_windows else 'main'
        exe_path = os.path.join(temp_dir, exe_name)
        
        # Compile
        compile_cmd = ['gcc', '-o', exe_path, code_file]
        if not _check_command('gcc'):
            # Fallback to online compiler API
            return _execute_c_online(code, stdin)
        
        compile_result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=temp_dir
        )
        
        if compile_result.returncode != 0:
            return compile_result.stderr, 'compilation_error', 0.0, 0.0
        
        # Execute
        start_time = time.time()
        run_result = subprocess.run(
            [exe_path] if not is_windows else [exe_path],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=temp_dir
        )
        execution_time = time.time() - start_time
        
        if run_result.returncode != 0:
            return run_result.stderr or "Runtime error", 'runtime_error', execution_time, 0.0
        
        return run_result.stdout, 'accepted', execution_time, 0.0
        
    except subprocess.TimeoutExpired:
        return "Execution timeout", 'timeout', 0.0, 0.0
    except Exception as e:
        return str(e), 'runtime_error', 0.0, 0.0
    finally:
        # Cleanup
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def _execute_java(code, stdin=''):
    """Execute Java code locally"""
    temp_dir = tempfile.mkdtemp()
    try:
        # Java needs the source filename to match the public class, while the
        # judge wrapper may still need to run its generated Main class.
        file_class_name = 'Main'
        run_class_name = 'Main'
        if 'public class' in code:
            file_class_name = code.split('public class')[1].split()[0].split('{')[0].strip()
            run_class_name = file_class_name
        if re.search(r'\bclass\s+Main\b', code) and re.search(r'public\s+static\s+void\s+main\s*\(', code):
            run_class_name = 'Main'
        
        # Write code to file
        code_file = os.path.join(temp_dir, f'{file_class_name}.java')
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Compile
        if not _check_command('javac'):
            # Fallback to online compiler API
            return _execute_java_online(code, stdin)
        
        compile_result = subprocess.run(
            ['javac', code_file],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=temp_dir
        )
        
        if compile_result.returncode != 0:
            return compile_result.stderr, 'compilation_error', 0.0, 0.0
        
        # Execute
        if not _check_command('java'):
            return "Java runtime (java) not found. Please install JDK.", 'error', 0.0, 0.0
        
        start_time = time.time()
        run_result = subprocess.run(
            ['java', '-cp', temp_dir, run_class_name],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=temp_dir
        )
        execution_time = time.time() - start_time
        
        if run_result.returncode != 0:
            return run_result.stderr or "Runtime error", 'runtime_error', execution_time, 0.0
        
        return run_result.stdout, 'accepted', execution_time, 0.0
        
    except subprocess.TimeoutExpired:
        return "Execution timeout", 'timeout', 0.0, 0.0
    except Exception as e:
        return str(e), 'runtime_error', 0.0, 0.0
    finally:
        # Cleanup
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def _execute_online(code, language, stdin=''):
    """Execute code using free online compiler API (Piston API)"""
    try:
        # Use Piston API (free, no authentication required)
        piston_url = 'https://emkc.org/api/v2/piston/execute'
        
        # Map language names
        lang_map = {
            'cpp': 'cpp',
            'c': 'c',
            'java': 'java',
            'python': 'python3'
        }
        
        piston_lang = lang_map.get(language, language)
        
        payload = {
            'language': piston_lang,
            'version': '*',
            'files': [
                {
                    'content': code
                }
            ],
            'stdin': stdin
        }
        
        response = requests.post(piston_url, json=payload, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'run' in data:
                run_data = data['run']
                output = run_data.get('stdout', '')
                stderr = run_data.get('stderr', '')
                
                if stderr:
                    # If there's stderr, it might be a compilation or runtime error
                    if 'compile' in data and data['compile'].get('stderr'):
                        return data['compile']['stderr'], 'compilation_error', 0.0, 0.0
                    return stderr, 'runtime_error', 0.0, 0.0
                
                # Calculate execution time if available
                execution_time = 0.0
                if 'time' in run_data:
                    try:
                        execution_time = float(run_data['time'])
                    except:
                        pass
                
                return output, 'accepted', execution_time, 0.0
            else:
                return "Unknown error from compiler API", 'error', 0.0, 0.0
        else:
            return f"Compiler API error: {response.status_code}", 'error', 0.0, 0.0
            
    except requests.exceptions.Timeout:
        return "Compiler API timeout. Please try again.", 'timeout', 0.0, 0.0
    except requests.exceptions.RequestException as e:
        return f"Compiler API error: {str(e)}", 'error', 0.0, 0.0
    except Exception as e:
        return f"Error: {str(e)}", 'error', 0.0, 0.0

def _execute_cpp_online(code, stdin=''):
    """Execute C++ code using free online compiler API"""
    return _execute_online(code, 'cpp', stdin)

def _execute_c_online(code, stdin=''):
    """Execute C code using free online compiler API"""
    return _execute_online(code, 'c', stdin)

def _execute_java_online(code, stdin=''):
    """Execute Java code using free online compiler API"""
    return _execute_online(code, 'java', stdin)

def _check_command(cmd):
    """Check if a command is available in the system"""
    try:
        subprocess.run(
            [cmd, '--version'] if cmd not in ['cl'] else [cmd],
            capture_output=True,
            timeout=2
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False

def run_test_cases(code, language, test_cases):
    """
    Run code against test cases
    Returns: (passed_count, total_count, results)
    """
    passed = 0
    total = len(test_cases)
    results = []
    
    for i, test_case in enumerate(test_cases):
        stdin = test_case.get('input', '')
        expected_output = test_case.get('output', '').strip()
        
        output, status, exec_time, memory = execute_code(code, language, stdin)
        actual_output = output.strip()
        
        is_passed = actual_output == expected_output and status == 'accepted'
        if is_passed:
            passed += 1
        
        results.append({
            'test_case': i + 1,
            'input': stdin,
            'expected_output': expected_output,
            'actual_output': actual_output,
            'passed': is_passed,
            'status': status,
            'execution_time': exec_time
        })
    
    return passed, total, results

