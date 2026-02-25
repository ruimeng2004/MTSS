import os
import re
import subprocess
import signal

def signal_handler(signum, frame):
    raise TimeoutError("Time out")

def set_timeout(seconds):
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)

def reset_timeout():
    signal.alarm(0)

def run_JUnit(bug_id, test_config,checkout_path):
    test_config['time_out'] = 1000
    java_root_path=checkout_path
    try:
        os.chdir(java_root_path+'/' + bug_id + '_buggy')
        set_timeout(test_config['time_out'])
        # set_d4j_cmd = 'export PATH=$PATH:/home/data/Defects4j/defects4j/framework/bin'
        # os.system(set_d4j_cmd)
        cmd = 'defects4j test'
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        os.chdir('../../')
        output, _ = process.communicate()
        process.kill()
        output = output.decode('utf-8')
        # with open('/home/lith/APR_formulation/result/output', 'w', encoding='utf-8') as file:
        #     file.write(output)
        reset_timeout()
        # if output != 'Failing tests: 0':
        if 'Running ant (compile.tests)................................................ FAIL' in output:
            return False, 'Compile failed' 
        else:
            match = re.search(r'Failing tests:\s*\d+', output)
            if match:
                failing_test_result = match.group(0)
            else:
                failing_test_result = 'Failing tests count not found'
            return True if failing_test_result == 'Failing tests: 0' else False, failing_test_result
    except (RuntimeError, TypeError, NameError, FileNotFoundError, TimeoutError) as e:
        print(e)
        process.kill()
        return False, e

def class_read(java_file_path):
    try:
        with open(java_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        with open(java_file_path, 'r', encoding='iso-8859-1') as file:  # otherwise, try 'iso-8859-1' or 'cp1252'
            content = file.read()
    return content

def class_write(java_file_path, content):
    with open(java_file_path, 'w', encoding='utf-8', errors='ignore') as outfile:
        outfile.write(content)
    outfile.close()
    
def extract_method_start_end_index(java_file_path, function_head, method_length):
    java_root_path='/home/lith/APR_formulation/dataset/defects4j/defects4j/'
    java_file_path=java_root_path+java_file_path    
    content = class_read(java_file_path)
    lines = content.split('\n')
    pattern_lines = function_head.split('\n')

    start_char_idx = content.find(function_head)
    if start_char_idx != -1:
        start_line_idx = content[:start_char_idx].count('\n')
        return [start_line_idx, start_line_idx + method_length]

    for i in range(len(lines)):
        if lines[i].split(')')[0].strip() == pattern_lines[0].strip():
            if len(pattern_lines) == 1:
                return [i, i + method_length]
            for j in range(len(pattern_lines))[1:]:
                if lines[i + j].split(')')[0].strip() != pattern_lines[j].strip():
                    break
            return [i, i + method_length]   
        
    return None

def restore_file(file_path, bug_id, checkout_path):
        java_root_path=checkout_path
        try:
            # Using git restore command to revert the file to the last commit state
            os.chdir(java_root_path+'/' + bug_id + '_buggy')
            cmd = 'git checkout --  .' 
            os.system(cmd)
            os.chdir('../../')
        except (RuntimeError, TypeError, NameError,FileNotFoundError) as e:
            print(f"An error occurred while restoring changes to the file: {e}")

def replace_file(java_file_path, replace_index, fixed_method):
        java_file_path=java_file_path 
        java_root_path='/home/lith/APR_formulation/dataset/defects4j/defects4j/'
        content = class_read(java_file_path)
        class_lines = content.split('\n')
        fixed_method_lines = fixed_method.split('\n')
        fixed_method_lines[-1] = fixed_method_lines[-1].split('@Override')[0] # remove redundant '@Override' at the end of the method
        class_lines[replace_index[0]:replace_index[1]] = fixed_method_lines
        code = '\n'.join(class_lines)
        class_write(java_file_path, code)

def replace_files(java_file_pathes, replace_indexes, fixed_methods):
    func_num=len(fixed_methods)
    
    for i in range(func_num):
        replace_index = [replace_indexes[i]['start']-1,replace_indexes[i]['end']]
        fixed_method = fixed_methods[i]
        java_file_path = java_file_pathes[i]
        replace_file(java_file_path, replace_index, fixed_method)


def apply_patch(patch, bug_id):
    java_root_path = '/data/lith/APR/defects4j/defects4j/defects4j'
    buggy_project_path = os.path.join(java_root_path, bug_id + '_buggy')
    try:
        os.chdir(buggy_project_path)
        patch_file_path = os.path.join(buggy_project_path, 'temp_patch.diff')
        with open(patch_file_path, 'w', encoding='utf-8') as patch_file:
            patch_file.write(patch)
        cmd = f'git apply {patch_file_path}'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"Failed to apply patch: {result.stderr.decode('utf-8')}")
        else:
            print("Patch applied successfully.")
        os.remove(patch_file_path)
    except (RuntimeError, TypeError, NameError, FileNotFoundError, OSError) as e:
        print(f"An error occurred while applying the patch: {e}")

def restore_files(file_path, bug_id, checkout_path):
    file_num=len(file_path)
    for i in range(file_num):
        restore_file(file_path[i], bug_id, checkout_path)


def apply_search_replace_edit(function_body: str, search_replace_edit: str) -> str:
    """
    Applies a *SEARCH/REPLACE* edit to a given function body.

    :param function_body: The original function body as a string.
    :param search_replace_edit: The *SEARCH/REPLACE* edit as a string.
    :return: The updated function body with the edit applied.
    """
    # Extract the SEARCH and REPLACE hunks using regex
    search_match = re.search(r'<<<<<<< SEARCH\n(.*?)=======', search_replace_edit, re.DOTALL)
    replace_match = re.search(r'=======\n(.*?)>>>>>>> REPLACE', search_replace_edit, re.DOTALL)

    if not search_match or not replace_match:
        return "error"

    # Get the SEARCH and REPLACE hunks
    search_hunk = search_match.group(1).strip()
    replace_hunk = replace_match.group(1).strip()

    # Replace the SEARCH hunk with the REPLACE hunk in the function body
    if search_hunk not in function_body:
       return "error"

    updated_function_body = function_body.replace(search_hunk, replace_hunk)
    return updated_function_body

def apply_SR_patches(buggy_codes, SR_patches):
    fixed_codes =[]
    for i in range(len(buggy_codes)):
        buggy_code = buggy_codes[i]
        SR_patch = SR_patches[i]
        updated_function_body = apply_search_replace_edit(buggy_code, SR_patch)
        if updated_function_body == "error":
            print("error in applying search/replace edit")
            return []
        fixed_codes.append(updated_function_body)
    return fixed_codes

def apply_SR_patches_v2(SR_func_pairs):
    fixed_codes =[]
    for i in range(len(SR_func_pairs)):
        buggy_code = SR_func_pairs[i]['BUGGY_FUNCTION']     
        SR_patchs = SR_func_pairs[i]['SR_PATCH']
        updated_function_body = buggy_code
        for SR_patch in SR_patchs:
            updated_function_body = apply_search_replace_edit(updated_function_body, SR_patch)
        fixed_codes.append(updated_function_body)
    return fixed_codes