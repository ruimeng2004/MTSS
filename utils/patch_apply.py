import re
import sys
import os
import subprocess

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

SOURCE = """
class Solution {
public:
    long long fact(int n)
    {
        if(n<=1)return 1;
        return (n*fact(n+1)%1000000007)%1000000007; 
    }
    int numPrimeArrangements(int n) {
        if(n==1)return 1;
        if(n<=3)return n-1;
        int t=0,flag;
        for(int i=2;i<=n;i++)
        {
            flag=0;
            for(int j=2;j<=sqrt(i);j++)
            {
                if(i%j==0)
                {
                    flag=1;
                    break;
                }
            }
            if(flag==0)
            {
                t++;
            }
        }
        return (fact(t)*fact(n-t))%1000000007;

    }
};
"""

PATCH = """```diff
diff --git a/Solution.cpp b/Solution.cpp
index 7c4b2a1..9d26670 100644
--- a/Solution.cpp
+++ b/Solution.cpp
@@ -3,7 +3,7 @@ class Solution {
     {
         if(n<=1)return 1;
-        return (n*fact(n+1)%1000000007)%1000000007; 
+        return (n*fact(n-1)%1000000007)%1000000007; 
     }
     int numPrimeArrangements(int n) {
```"""

FIX = """```cpp
class Solution {
public:
    long long fact(int n)
    {
        if(n<=1)return 1;
        return (n*fact(n-1)%1000000007)%1000000007; 
    }
    int numPrimeArrangements(int n) {
        if(n==1)return 1;
        if(n<=3)return n-1;
        int t=0,flag;
        for(int i=2;i<=n;i++)
        {
            flag=0;
            for(int j=2;j<=sqrt(i);j++)
            {
                if(i%j==0)
                {
                    flag=1;
                    break;
                }
            }
            if(flag==0)
            {
                t++;
            }
        }
        return (fact(t)*fact(n-t))%1000000007;

    }
};
```"""

MIX = """```diff
diff --git a/Solution.cpp b/Solution.cpp
index 7c4b2a1..9d26670 100644
--- a/Solution.cpp
+++ b/Solution.cpp
@@ -3,7 +3,7 @@ class Solution {
     {
         if(n<=1)return 1;
-        return (n*fact(n+1)%1000000007)%1000000007; 
+        return (n*fact(n-1)%1000000007)%1000000007; 
     }
     int numPrimeArrangements(int n) {
```
```cpp
class Solution {
public:
    long long fact(int n)
    {
        if(n<=1)return 1;
        return (n*fact(n-1)%1000000007)%1000000007; 
    }
    int numPrimeArrangements(int n) {
        if(n==1)return 1;
        if(n<=3)return n-1;
        int t=0,flag;
        for(int i=2;i<=n;i++)
        {
            flag=0;
            for(int j=2;j<=sqrt(i);j++)
            {
                if(i%j==0)
                {
                    flag=1;
                    break;
                }
            }
            if(flag==0)
            {
                t++;
            }
        }
        return (fact(t)*fact(n-t))%1000000007;

    }
};
```"""

def extract_code(s: str) -> str:
    pattern = r"```.*?\n(.*?)```"
    codeblocks = re.findall(pattern, s, flags=re.DOTALL)
    if len(codeblocks) == 0:
        return 'Match failed'
    return codeblocks


def find_hunk_range(code, chunk):
    A_raw = code.split("\n")
    B_raw = chunk.split("\n")
    len_A = len(A_raw)
    len_B = len(B_raw)
    A = A_raw.copy()
    B = B_raw.copy()

    for i in range(len_A):
        A[i] = A[i].strip()
    for i in range(len_B):
        B[i] = B[i].strip()

    if len_A < len_B:
        return -1, -1

    for i in range(len_A):
        if A[i].strip() == B[0].strip(): 
            if len_A - i < len_B: 
                return -1, -1
            match = True
            for j in range(len_B):
                if A[i+j].strip() != B[j].strip(): 
                    match = False
                    break
            if match:
                l = len('\n'.join(A_raw[:i])) + 1
                r = len('\n'.join(A_raw[:i+len_B]))
                return l, r
    return -1, -1
    

def apply_diff_to_program(code, diff):
    diff_lines = diff.split("\n")
    
    bug_chunks = []
    fix_chunks = []

    for diff_line in diff_lines:
        if diff_line.startswith(("diff", "index", "---", "+++")):
            continue
        elif diff_line.startswith("@@"):
            bug_chunks.append([])
            fix_chunks.append([])
            if len(bug_chunks) > 1:
                bug_chunks[-2] = "\n".join(bug_chunks[-2])
                fix_chunks[-2] = "\n".join(fix_chunks[-2])
                l, r = find_hunk_range(code, bug_chunks[-2])
                if l == -1 or r == -1:
                    raise Exception("Hunk not found")
                code = code[:l] + fix_chunks[-2] + code[r:]
        elif diff_line.strip() == "":
            bug_chunks[-1].append(diff_line)
            fix_chunks[-1].append(diff_line)
        elif diff_line.startswith("-"):
            line = diff_line[1:]
            bug_chunks[-1].append(line)
        elif diff_line.startswith("+"):
            line = diff_line[1:]
            fix_chunks[-1].append(line)
        else:
            bug_chunks[-1].append(diff_line[1:])
            fix_chunks[-1].append(diff_line[1:])

    bug_chunks[-1] = "\n".join(bug_chunks[-1])
    fix_chunks[-1] = "\n".join(fix_chunks[-1])
    l, r = find_hunk_range(code, bug_chunks[-1])
    if l == -1 or r == -1:
        raise Exception("Hunk not found")
    code = code[:l] + fix_chunks[-1] + code[r:]
    
    bug_chunks = ["\n".join(chunk) for chunk in bug_chunks]
    fix_chunks = ["\n".join(chunk) for chunk in fix_chunks]

    return code


def run_aider_with_edit(buggy_functions, search_replace_edits, api_key):
    """
    Write the buggy function to a temporary file, then start the aider command-line tool
    and prepare the Search/Replace edit for manual input.

    :param buggy_functions: List of buggy functions as strings.
    :param search_replace_edits: List of Search/Replace edits as strings.
    :param api_key: API key for the aider tool.
    """
    log_path = '/home/lith/APR_formulation/aider_wk/log/history'
    fw = open(log_path, 'w')
    temp_file_path = "/home/lith/APR_formulation/aider_wk/tmp/temp.java"
    fix_codes=[]
    for i, buggy_function in enumerate(buggy_functions):
        with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
            temp_file.write(buggy_function)
        search_replace_edit = search_replace_edits[i] 
        search_replace_edit=f"please help me apply the *SEARCH/REPLACE* edit.Don't repair the function.Just apply the *SEARCH/REPLACE* edit for me:\n {search_replace_edit}" 
        try:
            os.chdir("/home/lith/APR_formulation")
            env_cmd = 'source /home/lith/APR_formulation/aider_env/bin/activate'
            cmd = f'aider {temp_file_path} --model deepseek --api-key deepseek={api_key}'
            print(f"Running command: {cmd}")
            # Activate the virtual environment
            subprocess.run(env_cmd, shell=True, check=True, executable='/bin/bash')

            # Run the aider command and pass the search_replace_edit via stdin
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=search_replace_edit)
            if stderr:
                print("\nAider errors:\n")
                print(stderr)
            if os.path.exists(temp_file_path):
                with open(temp_file_path, 'r', encoding='utf-8') as temp_file:
                    updated_content = temp_file.read()
                    fix_codes.append(updated_content)  # 将内容添加到 fix_code 列表
        except Exception as e:
            print(f"aider error: {e}\n")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    return fix_codes



if __name__ == '__main__':

    PATCH = extract_code(PATCH)[0]
    print(PATCH)
    MERGE = apply_diff_to_program(SOURCE.strip(), PATCH.strip()).strip()
    print(MERGE)
    FIX = extract_code(FIX)[0].strip()
    print(FIX)
    print(MERGE == FIX)
    MIX_DIFF, MIX_FIX = extract_code(MIX)
    print(MIX_DIFF)
    print(MIX_FIX)

def make_search_replace_pairs(buggy_functions,SR_patches,function_signatures):
    """
    Create pairs of buggy functions and their corresponding Search/Replace patches.

    :param buggy_functions: List of buggy functions as strings.
    :param SR_patches: List of Search/Replace patches as strings.
    :return: List of tuples containing pairs of buggy functions and their corresponding patches.
    """
    def parse_edit_func(SR_patch):
        """
        从SR补丁中提取被修改的函数签名（如 'protected void drawVerticalItem(...)'）。
        """
        # 匹配以###开头，后面是函数签名
        match = re.match(r"^###([^\n]+)", SR_patch)
        if match:
            return match.group(1).strip()
        return None
    
    def normalize_signature(sig):
        # 去除所有空白字符（包括空格、制表符等）
        return ''.join(sig.split())
    is_problem = False
    result = []
    assigned_patches = set()
    for i in range(len(buggy_functions)):
        buggy_function = buggy_functions[i]
        function_signature = function_signatures[i] if function_signatures else None
        tmp_dict = {}
        tmp_dict['BUGGY_FUNCTION'] = buggy_function
        tmp_dict['SIGNATURE'] = function_signature
        sr_patch_set = set()
        for SR_patch in SR_patches:
            patch_sig = parse_edit_func(SR_patch)
            if patch_sig is None or function_signature is None:
                continue
            if (normalize_signature(patch_sig) == normalize_signature(function_signature) or
                normalize_signature(function_signature) in normalize_signature(patch_sig)):
                if SR_patch not in sr_patch_set:
                    sr_patch_set.add(SR_patch)
                    assigned_patches.add(SR_patch)
        tmp_dict['SR_PATCH'] = list(sr_patch_set)
        result.append(tmp_dict)
    for SR_patch in SR_patches:
        if SR_patch not in assigned_patches:
            is_problem = True           
    return result,is_problem