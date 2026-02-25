from prompt.defects4j import *
from validator.junit import *
from validator.leetcode import *
from utils.patch_apply import *
import pandas as pd
from tqdm import tqdm
import time
import argparse
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
    test_config = config['test_config']

meta = {
    'defects4j': {
        'code': 'data/defects4j_code.csv',
        'artifact': 'data/defects4j_artifact.csv',
        'skip': ['Lang_18', 'Lang_25', 'Lang_48', 'JacksonDatabind_65', 'JacksonDatabind_89']
    },
    'debugbench': {
        'all': 'data/debugbench_all.json'
    }
}

def ppl_evaluate(ppl_path):
    evaluation = pd.read_csv(ppl_path, sep=',', encoding='utf-8')
    total_ppl = 0
    total_total_ppl = 0
    for i, row in evaluation.iterrows():
        if row['ppl'] != 'OOM':
            total_ppl += float(row['ppl'])
            total_total_ppl += float(row['total_ppl'])
    print(f"Average PPL: {total_ppl / len(evaluation)}")
    print(f"Average Total PPL: {total_total_ppl / len(evaluation)}")


def ppl_test(df_pred,df_ppl, df_data, pred_path, ppl_path):
    from utils.chat_local import LocalChat
    debugger = LocalChat("meta-llama/Llama-3.1-8B-Instruct")
    for i, row in df_pred.iterrows():
        sample = df_data[i]
        if 'agent' in pred_path or 'reverse' in pred_path:
            prompt = AGENT_PROMPT
            prompt = prompt.replace("{LANGUAGE}", sample['language'].strip())
            prompt = prompt.replace("{REQUIREMENT}", sample['question'].strip())
            prompt = prompt.replace("{CONSTRAINT}", sample['constraints'].strip())
            prompt = prompt.replace("{EXAMPLE}", '\n'.join(sample['examples']).strip())
            if 'agent' in pred_path: # different output
                prompt = prompt.replace("{BUGGY_CODE}", sample['buggy_code'].strip())
                prompt = prompt.strip() + "\nPlease follow your duty as an AI Debugger and generate a refined version of the buggy program."
                response = f"```{sample['language']}\n" + row['fix'].strip() + "\n```"
            else:
                prompt = prompt.replace("{BUGGY_CODE}", sample['located_code'].strip())
                prompt = prompt.strip() + "\nPlease follow your duty as an AI Debugger and generate the corrected code snippets for the buggy program."
                response = f"```{sample['language']}\n" + row['diff'].strip() + "\n```"
        elif 'located' in pred_path or 'hybrid' in pred_path:
            prompt = USER_PROMPT
            prompt = prompt.replace("{LANGUAGE}", sample['language'].strip())
            if 'located' in pred_path:
                prompt = prompt.replace("{BUGGY_CODE}", sample['located_code'].strip())
                prompt = prompt.strip() + "\nPlease follow your duty as an AI Debugger and generate code snippets to fill the chunks marked as `<Chunk_For_Modification>` in each provided buggy function."
                response = f"```{sample['language']}\n" + row['diff'].strip() + "\n```"
            else:
                prompt = prompt.replace("{BUGGY_CODE}", sample['buggy_code'].strip())
                prompt = prompt.strip() + "\nPlease follow your duty as an AI Debugger and generate a refined version of the buggy program."
                response = f"```{sample['language']}\n" + row['fix'].strip() + "\n```" 
        # print(prompt)
        # print(response)
        # break
        try:
            ppl, total_ppl = debugger.ppl(prompt, response)
        except Exception as e:
            ppl = "OOM"
            total_ppl = "OOM"
        df_ppl.loc[i] = {'ID': i, 'slug': sample['slug'], 'ppl': ppl, 'total_ppl': total_ppl}
        df_ppl.to_csv(ppl_path, sep=',', encoding='utf-8', index=False)


def junit_test(pred_path, eval_path):
    df_pred = pd.read_csv(pred_path, sep=',', encoding='utf-8')
    df_data = pd.read_csv(meta['defects4j']['code'], sep=',', encoding='utf-8')
    if os.path.exists(eval_path):
        df_eval = pd.read_csv(eval_path, sep=',', encoding='utf-8')
    else:
        df_eval = pd.DataFrame(columns=['ID', 'slug', 'reward', 'submission_result'])

    for i, row in tqdm(df_pred.iterrows(), total=len(df_pred)):
        bug_slug = row['slug']
        sample = df_data[df_data['slug'] == bug_slug].iloc[0]
        if bug_slug in meta['defects4j']['skip']:
            reward, submission_result = False, 'Bug deprecated'
        elif row['fix'] == 'Match failed':
            reward, submission_result = False, 'Match failed'
        else:
            bug_id = row['slug']
            class_path = sample['class_path']
            fixed_method = row['fix']
            original_method = sample['buggy_code'].strip()
            original_method_len = len(original_method.split('\n'))
            fixed_method = fixed_method.replace('@Override', '').strip()
            function_head = fixed_method.split('{')[0].split(')')[0] + ')'
            function_head = function_head.strip()
            class_replace_index = extract_method_start_end_index(class_path, function_head, original_method_len)
            if class_replace_index is None:
                reward, submission_result = False, 'Locate failed'
            else:
                replace_file(class_path, class_replace_index, fixed_method)
                reward, submission_result = run_JUnit(bug_id, test_config)
                restore_file(class_path, bug_id)
        df_eval.loc[i] = {'ID': i, 'slug': sample['slug'], 'reward': reward, 'submission_result': submission_result}
        df_eval.to_csv(eval_path, sep=',', encoding='utf-8', index=False)


def junit_evaluate(eval_path):
    df_eval = pd.read_csv(eval_path, sep=',', encoding='utf-8')
    name_list = ['Chart', 'Lang', 'Math', 'Mockito', 'Time']
    total_list = []
    pass_list = []
    sp_list = []
    for i, row in df_eval.iterrows():
        total_list.append(row['slug'])
        if row['reward'] == True and row['slug'] not in pass_list:
            pass_list.append(row['slug'])
            if row['slug'] not in sp_list and row['slug'].split('_')[0] in name_list:
                sp_list.append(row['slug'])
            if row['slug'] not in sp_list and row['slug'].split('_')[0] == 'Closure' and int(row['slug'].split('_')[1]) <= 133:
                sp_list.append(row['slug'])
    print(f"Pass: {len(pass_list)}")
    print(f"Pass-1.2: {len(sp_list)}")
    # print(sp_list)


def leetcode_test(pred_path, eval_path):
    df_pred = pd.read_csv(pred_path, sep=',', encoding='utf-8')
    print(df_pred)
    row_num = 0
    if os.path.exists(eval_path):
        df_eval = pd.read_csv(eval_path, sep=',', encoding='utf-8')
        row_num = df_eval.shape[0]
    else:
        df_eval = pd.DataFrame(columns=['ID', 'slug', 'reward', 'submission_result'])
    print(f'start from {row_num}')

    tester = LeetcodeValidator(0) # single cookie

    last_correct_slug = ""
    last_correct_info = ""
    iter_test = 0
    last_run = datetime.now()
    for idx, row in tqdm(df_pred.iterrows()):

        if idx < row_num:
            continue
        if row['fix'] == 'Match failed':
            continue
        
        if row['slug'] == last_correct_slug:
            reward = True
            submission_result = last_correct_info
        else:

            ### loop cookies
            while (datetime.now() - last_run).total_seconds() < 10:
                time.sleep(0.1)
            tester = LeetcodeValidator(iter_test)
            last_run = datetime.now()

            reward, submission_result = tester.test(row['fix'], row['slug'], row['lang'])
            iter_test += 1
            if reward:
                last_correct_slug = row['slug']
                last_correct_info = submission_result
        df_eval.loc[idx] = {'ID': row['ID'], 'slug': row['slug'], 'reward': reward, 'submission_result': submission_result}
        df_eval.to_csv(eval_path, sep=',', encoding='utf-8', index=False)


def leetcode_evaluate_sample1(eval_path): # Pass@1
    evaluation = pd.read_csv(eval_path, sep=',', encoding='utf-8')
    total_list = []
    pass_list = []
    for i, row in evaluation.iterrows():
        if row['slug'] not in total_list:
            total_list.append(row['slug'])
            if row['reward'] == True:
                pass_list.append(row['slug'])
    print(f"Pass: {len(pass_list)}")


def leetcode_evaluate_sample3(eval_path): # Pass@3
    evaluation = pd.read_csv(eval_path, sep=',', encoding='utf-8')
    total_list = []
    pass_list = []
    for i, row in evaluation.iterrows():
        if total_list.count(row['slug']) < 3:
            total_list.append(row['slug'])
            if row['reward'] == True and row['slug'] not in pass_list:
                pass_list.append(row['slug'])
    print(f"Pass: {len(pass_list)}")


def leetcode_evaluate_sample1_pl3(eval_path): # Pass@1 for each language
    evaluation = pd.read_csv(eval_path, sep=',', encoding='utf-8')
    total_list_cpp = []
    total_list_java = []
    total_list_python = []
    pass_list_cpp = []
    pass_list_java = []
    pass_list_python = [] 
    for i, row in evaluation.iterrows():
        if "'lang': 'cpp'" in row['submission_result']:
            if row['slug'] not in total_list_cpp:
                total_list_cpp.append(row['slug'])
                if row['reward'] == True:
                    pass_list_cpp.append(row['slug'])
        if "'lang': 'java'" in row['submission_result']:
            if row['slug'] not in total_list_java:
                total_list_java.append(row['slug'])
                if row['reward'] == True:
                    pass_list_java.append(row['slug'])
        if "'lang': 'python3'" in row['submission_result']:
            if row['slug'] not in total_list_python:
                total_list_python.append(row['slug'])
                if row['reward'] == True:
                    pass_list_python.append(row['slug'])
    print(f"Pass cpp: {len(pass_list_cpp)}")
    print(f"Pass java: {len(pass_list_java)}")
    print(f"Pass python: {len(pass_list_python)}")

def leetcode_evaluate_sample3_pl3(eval_path): # Pass@3 for each language
    evaluation = pd.read_csv(eval_path, sep=',', encoding='utf-8')
    total_list_cpp = []
    total_list_java = []
    total_list_python = []
    pass_list_cpp = []
    pass_list_java = []
    pass_list_python = []
    for i, row in evaluation.iterrows():
        if "'lang': 'cpp'" in row['submission_result']:
            if total_list_cpp.count(row['slug']) < 3:
                total_list_cpp.append(row['slug'])
                if row['reward'] == True and row['slug'] not in pass_list_cpp:
                    pass_list_cpp.append(row['slug'])
        if "'lang': 'java'" in row['submission_result']:
            if total_list_java.count(row['slug']) < 3:
                total_list_java.append(row['slug'])
                if row['reward'] == True and row['slug'] not in pass_list_java:
                    pass_list_java.append(row['slug'])
        if "'lang': 'python3'" in row['submission_result']:
            if total_list_python.count(row['slug']) < 3:
                total_list_python.append(row['slug'])
                if row['reward'] == True and row['slug'] not in pass_list_python:
                    pass_list_python.append(row['slug'])
    print(f"Pass cpp: {len(pass_list_cpp)}")
    print(f"Pass java: {len(pass_list_java)}")
    print(f"Pass python: {len(pass_list_python)}")


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--test', default=True, type=bool) # re-test the results
    parser.add_argument('--data', default="defects4j", type=str) # defects4j or debugbench
    parser.add_argument('--pred', default="archive/defects4j/pred_d4c_gpt_archived.csv", type=str) # use the archived data as an example
    parser.add_argument('--eval', default="result/defects4j/eval_d4c_gpt_archived.csv", type=str) # use the archived data as an example
    args = parser.parse_args()

    print("re-test?: ", args.test)
    print("dataset: ", args.data)

    if args.data == 'defects4j':
        path = 'result/defects4j/'
        if not os.path.exists(path):
            os.makedirs(path)
        if args.test:
            junit_test(args.pred, args.eval)
        junit_evaluate(args.eval)
    elif args.data == 'debugbench':
        path = 'result/debugbench/'
        if not os.path.exists(path):
            os.makedirs(path)
        if args.test:
            leetcode_test(args.pred, args.eval)
        leetcode_evaluate_sample3_pl3(args.eval)
        # leetcode_evaluate_sample1_pl3(args.eval)
        # leetcode_evaluate_sample1(args.eval)
        # leetcode_evaluate_sample3(args.eval)
    else:
        raise ValueError("dataset must be 'defects4j' or 'debugbench'")
