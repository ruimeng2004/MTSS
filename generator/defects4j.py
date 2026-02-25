import sys
import os
sys.path.append(os.path.abspath('/home/lith/APR_formulation/D4C/D4C'))
os.chdir('/home/lith/APR_formulation/D4C/D4C')
from utils.chat_local import LocalChat
from utils.chat_remote import RemoteChat
from prompt.defects4j import *
from validator.junit import *
from utils.patch_apply import *
import argparse
import pandas as pd
from tqdm import tqdm
import json

checkout_path='/data/lith/APR/defects4j/defects4j/defects4j'
d4c_path='/home/lith/APR_formulation/D4C/D4C/'
def debug(args):
    if not os.path.exists('result/defects4j'):
        os.makedirs('result/defects4j')
    data = pd.read_csv(args.data_path, sep=',', encoding='utf-8', engine='python') #code
    msg = pd.read_csv(args.msg_path, sep=',', encoding='utf-8', engine='python') #artifact
    id_count = data['slug'].value_counts()
    total_unique = id_count[id_count == 1].sum()
    print(f"total number of unique function bug: {total_unique}")
    # extract all the unique 'slug" data
    data = data.groupby('slug').filter(lambda x: len(x) == 1)
    row_num = 0
    if os.path.exists(args.result_path):
        df_results = pd.read_csv(args.result_path, sep=',', encoding='utf-8', engine='python')
        row_num = df_results['ID'].iloc[-1]
    else:
        df_results = pd.DataFrame(columns=['ID', 'lang', 'slug', 'bug', 'diff', 'fix'])
    if os.path.exists(args.eval_path):
        df_eval = pd.read_csv(args.eval_path, sep=',', encoding='utf-8', engine='python')
    else:
        df_eval = pd.DataFrame(columns=['ID', 'slug', 'reward', 'submission_result'])

    # for plausible check
    if args.ablation == 'full' and args.check:
        plausible_df = pd.read_csv('result/defects4j/evaluation_agent_1shot_gpt-4_10try_temp=1.0.csv', sep=',', encoding='utf-8', engine='python')
        reward_true_df = plausible_df[plausible_df['reward'] == True]
        slugs = set(reward_true_df['slug'])

    if args.mode == 'agent':
        history = HISTORY_AGENT_D4J
    elif args.mode == 'pure':
        history = HISTORY_PURE_D4J
    else:
        raise ValueError("mode must be 'agent' or 'pure'")

    if args.chat_mode == 'remote':
        debugger = RemoteChat(args.api_key, args.remote_model, args.remote_proxy)
    elif args.chat_mode == 'local':
        debugger = LocalChat(args.cp_path, args.local_model, args.local_proxy)
    else:
        raise ValueError("chat_mode must be 'remote' or 'local'")

    for i, row in tqdm(data.iterrows(), total=len(data)):
        sample = row

        if i < row_num:
            continue

        if args.ablation == 'full' and args.check and sample['slug'] not in slugs:
            print(f"skip fault patch slugs: {sample['slug']}")
            continue

        prompt = history.copy()
        if args.mode == 'agent':
            query = AGENT_PROMPT
            query = query.replace("{BUGGY_COMMENT}", sample['comment'].strip() if str(sample['comment']) not in {'', 'nan'} else "This function has no comment.")
            query = query.replace("{ERROR_MESSAGE}", msg[msg['slug'] == sample['slug']]['exception_info'].values[0] if len(msg[msg['slug'] == sample['slug']]['exception_info'].values) > 0 else "This function has no exception info.")
            query = query.replace("{FAILED_TEST}", msg[msg['slug'] == sample['slug']]['test_method'].values[0] if len(msg[msg['slug'] == sample['slug']]['test_method'].values) > 0 else "This function has no failed test.")
            query = query.replace("{BUGGY_CODE}", sample['buggy_code'].strip())
        elif args.mode == 'pure':
            query = USER_PROMPT
            query = query.replace("{BUGGY_CODE}", sample['buggy_code'].strip())
        else:
            raise ValueError("mode must be 'agent' or 'pure'")
                                
        prompt.append({
            "role": "user",
            "content": query
        })

        if args.ablation != 'full':
            if args.ablation == 'comment':
                pattern = r'### Buggy function comment:\n[\s\S]*?(?=\n###)'
            elif args.ablation == 'example':
                pattern = r'### Failed JUnit test:\n[\s\S]*?(?=\n###)'
            elif args.ablation == 'message':
                pattern = r'### Error message from JUnit test:\n[\s\S]*?(?=\n###)'
            else:
                raise ValueError("ablation must be 'full' or 'comment' or 'case' or 'message'")
            prompt[1]['content'] = re.sub(pattern, '', prompt[1]['content'])
            prompt[3]['content'] = re.sub(pattern, '', prompt[3]['content'])

        for j in range(args.max_try):
            try:
                response = debugger.chat(prompt, i, temperature=args.temperature)
                response_file_path = f"/home/lith/APR_formulation/result/response"
                with open(response_file_path, 'w', encoding='utf-8') as response_file:
                    response_file.write(response)
                prompt_file_path = f"/home/lith/APR_formulation/result/prompt"
                with open(prompt_file_path, 'w', encoding='utf-8') as prompt_file:
                    prompt_file.write(json.dumps(prompt))
                fixed_code = extract_code(response)[0]
                reward, submission_result = test(sample['slug'], sample['class_path'], sample['buggy_code'], fixed_code)
                df_results.loc[i * args.max_try + j] = {'ID': i, 'lang': 'java', 'slug': sample['slug'], 'bug': sample['buggy_code'], 'diff': 'np.nan', 'fix': fixed_code}
                df_results.to_csv(args.result_path, sep=',', encoding='utf-8', index=False)
                df_eval.loc[i * args.max_try + j] = {'ID': i, 'slug': sample['slug'], 'reward': reward, 'submission_result': submission_result}
                df_eval.to_csv(args.eval_path, sep=',', encoding='utf-8', index=False)

                if args.early_stop and reward: # early stop
                    break

                # for item in prompt: # for observation
                #     print(item['content'])
                #     print('-'*80)
                # print(fixed_code)
                # exit()    

            except Exception as e:
                print(e)  


def test(bug_id, class_path, original_method, fixed_method):
    if fixed_method == 'Match failed':
        return False, 'Match failed'
    bug_id = bug_id
    original_method = original_method.strip()
    original_method_len = len(original_method.split('\n'))
    fixed_method = fixed_method.replace('@Override', '').strip()
    function_head = fixed_method.split('{')[0].split(')')[0] + ')'
    function_head = function_head.strip()

    class_replace_index = extract_method_start_end_index(class_path, function_head, original_method_len)
    if class_replace_index is None:
        return False, 'Locate failed'
    replace_file(class_path, class_replace_index, fixed_method)
    test_config_ins=dict()
    reward, submission_result = run_JUnit(bug_id, test_config_ins)
    restore_file(class_path, bug_id)
    return reward, submission_result
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api_key', default="sh-xxxx", type=str)
    parser.add_argument('--cp_path', default="~/.cache/huggingface/hub", type=str)
    parser.add_argument('--chat_mode', default="remote", type=str) # remote or local
    parser.add_argument('--remote_model', default="deepseek-reasoner", type=str) # Choose model: gpt-3.5-turbo, gpt-4, claude-2, palm-2-chat-bison, gemini-pro
    parser.add_argument('--local_model', default='models--mistralai--Mixtral-8x7B-Instruct-v0.1', type=str)
    parser.add_argument('--data_path', default=d4c_path+"data/defects4j_code.csv", type=str) 
    parser.add_argument('--msg_path', default=d4c_path+"data/defects4j_artifact.csv", type=str)
    parser.add_argument('--result_path', default=d4c_path+"result/defects4j/pred", type=str)
    parser.add_argument('--eval_path', default=d4c_path+"result/defects4j/eval", type=str)
    parser.add_argument('--remote_proxy', default='DeepSeek', type=str)
    parser.add_argument('--local_proxy', default='batch', type=str)
    parser.add_argument('--mode', default='agent', type=str)
    parser.add_argument('--shot', default=1, type=int)
    parser.add_argument('--max_try', default=2, type=int)
    parser.add_argument('--temperature', default=1.0, type=float)
    parser.add_argument('--ablation', default='full', type=str)
    parser.add_argument('--check', default=False, type=bool)
    parser.add_argument('--early_stop', default=False, type=bool)
    args = parser.parse_args()
    if not os.path.exists(args.eval_path):
        os.makedirs(args.eval_path)
    if not os.path.exists(args.result_path):
        os.makedirs(args.result_path)
    result_elements = [args.result_path, args.ablation, str(args.shot)]
    eval_elements = [args.eval_path, args.ablation, str(args.shot)]

    remote_mode_alias = args.remote_model.split('/')[-1]
    local_mode_alias = args.local_model.split('/')[-1]

    if args.chat_mode == 'remote':
        args.result_path = '_'.join(elem for elem in result_elements if elem != '') + f'shot_{remote_mode_alias}_{args.max_try}try_temp={args.temperature}.csv'
        args.eval_path = '_'.join(elem for elem in eval_elements if elem != '') + f'shot_{remote_mode_alias}_{args.max_try}try_temp={args.temperature}.csv'
    elif args.chat_mode == 'local':
        args.result_path = '_'.join(elem for elem in result_elements if elem != '') + f'shot_{local_mode_alias}_{args.max_try}try_temp={args.temperature}.csv'
        args.eval_path = '_'.join(elem for elem in eval_elements if elem != '') + f'shot_{local_mode_alias}_{args.max_try}try_temp={args.temperature}.csv'
    else:
        raise ValueError("chat_mode must be 'remote' or 'local'")

    debug(args)

    
            
        




