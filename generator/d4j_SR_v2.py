import sys
import os
sys.path.append(os.path.abspath('/home/base/d4c/D4C'))
os.chdir('/home/base/d4c/D4C')
from utils.chat_local import LocalChat
from utils.chat_remote import RemoteChat
from prompt.d4j import *
from validator.junit import *
from utils.patch_apply import *
import argparse
import pandas as pd
from tqdm import tqdm
import json
from generator_utils import *
import csv


log_dir = '/home/base/d4c/D4C/log'

checkout_path='/home/data/Defects4j/checkout/buggy'
d4c_path='/home/base/d4c/D4C/'
json_file_path = '/home/base/d4c/D4C/result/repair_level/repair_level_projects.json'

def get_repo_cases(json_file_path):
    """
    Reads a JSON file and extracts all cases under the 'repo' key into a list.

    :param json_file_path: Path to the JSON file.
    :return: List of cases under the 'repo' key.
    """
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Extract the 'repo' key and return its value as a list
    repo_cases = data.get('repo', [])
    return repo_cases

# Example usage

def read_slugs_from_file(file_path):
    """
    读取文件中的所有slug（每行一个），返回一个list。
    """
    slugs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            slug = line.strip()
            if slug:  # 跳过空行
                slugs.append(slug)
    return slugs


def get_processed_slugs(csv_file_path):
    """
    Reads a CSV file and collects all processed slugs.

    :param csv_file_path: Path to the CSV file.
    :return: A set of processed slugs.
    """
    processed_slugs = set()
    with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
        reader = csv.reader(csv_file)
        next(reader)  # Skip the header row
        for row in reader:
            if len(row) > 1:  # Ensure the row has enough columns
                slug = row[1]  # Assuming the second column contains the slug
                processed_slugs.add(slug)
    return processed_slugs


def debug(args):
    log_dir = args.log_path
    if not os.path.exists('result/defects4j'):
        os.makedirs('result/defects4j')
    data = pd.read_csv(args.data_path, sep=',', encoding='utf-8', engine='python') #code
    msg = pd.read_csv(args.msg_path, sep=',', encoding='utf-8', engine='python') #artifact
    id_count = data['slug'].value_counts()
    # total_unique = id_count[id_count == 1].sum()
    # print(f"total number of unique function bug: {total_unique}")
    # total_slugs = data['slug'].nunique()
    # print(f"Total number of slugs: {total_slugs}")
    # # extract all the unique 'slug" data
    # # 提取只出现一次的 slug 和所有出现过的 slug
    # unique_slugs = id_count[id_count == 1].index.tolist()  # 只出现一次的 slug
    all_slugs = id_count.index.tolist()  # 所有出现过的 slug
    # log_dir = "/home/lith/APR_formulation/granularity_agent/make_d4c_data/log"
    # json_file = os.path.join(log_dir, "slugs_d4c.json")
    # slugs_data = {
    #     "unique_slugs": unique_slugs,
    #     "all_slugs": all_slugs
    # }
    # with open(json_file, "w", encoding="utf-8") as f:
    #     json.dump(slugs_data, f, indent=4, ensure_ascii=False) 
    # print(f"Slugs data written to {json_file}")
    
    
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
        history = HISTORY_AGENT_D4J_SEARCH_REPLACE
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
    all_slugs = sorted(all_slugs, key=lambda slug: (slug.split('_')[0].lower(), int(slug.split('_')[1])))
    # repo_slugs = get_repo_cases(json_file_path)
    # tmp_slugs = read_slugs_from_file('/home/lith/APR_formulation/result/case_study/diff_cases_SR_1-2.txt')
    processed_slugs = set()
    if os.path.exists(args.eval_path):
        processed_slugs = get_processed_slugs(args.eval_path)
    for i, slug in tqdm(enumerate(all_slugs), total=len(all_slugs), desc="Processing Slugs", unit="slug"):
        # if slug not in tmp_slugs:
        #     continue
        # print(f"Processing slug: {slug}")
        if slug in processed_slugs:
            print(f"Slug {slug} has already been processed. Skipping...")
            continue
        buggy_info = extract_buggy_info_for_SR(data, msg,slug,log_dir)           
        if args.mode == 'agent':
            query = AGENT_PROMPT_SR
            query = query.replace("{BUGGY_COMMENT}", buggy_info['BUGGY_COMMENT'])
            query = query.replace("{ERROR_MESSAGE}", buggy_info['ERROR_MESSAGE'].strip())
            query = query.replace("{FAILED_TEST}", buggy_info['FAILED_TEST'].strip())
            query = query.replace("{BUGGY_CODE}",buggy_info['BUGGY_CODE'].strip())
        elif args.mode == 'pure':
            query = USER_PROMPT
            query = query.replace("{BUGGY_CODE}", buggy_info['BUGGY_CODE'].strip())
        else:
            raise ValueError("mode must be 'agent' or 'pure'")
        prompt = history.copy()                        
        prompt.append({
            "role": "user",
            "content": query
        })
        with open(os.path.join(log_dir, 'query.txt'), 'w') as f:
            f.write(query)
        for j in range(args.max_try):
            try:
                response = debugger.chat(prompt, i, temperature=args.temperature)[0]
                with open(os.path.join(log_dir, 'response.txt'), 'w') as f:
                    f.write(response)
                # with open(os.path.join(log_dir, 'response.txt'), 'r') as f:
                #     response = f.read() 
                SR_patches = extract_code(response)
                buggy_functions = extract_code(buggy_info['BUGGY_CODE'])
                function_signatures = buggy_info['METHOD_SIGNATURE']
                SR_func_pairs,is_problem = make_search_replace_pairs(buggy_functions, SR_patches, function_signatures)
                if len(SR_func_pairs) != len(buggy_functions):
                    print(f"The number of buggy functions and SR patches do not match.slug {slug}")
                    df_results.loc[i * args.max_try + j] = {'ID': i, 'lang': 'java', 'slug': buggy_info['SLUG'], 'bug': buggy_info['BUGGY_CODE'], 'diff': 'np.nan', 'fix': response}
                    df_results.to_csv(args.result_path, sep=',', encoding='utf-8', index=False)
                    df_eval.loc[i * args.max_try + j] = {'ID': i, 'slug': buggy_info['SLUG'], 'reward': False, 'submission_result': "SR patch number mismatch"}
                    df_eval.to_csv(args.eval_path, sep=',', encoding='utf-8', index=False)
                    continue

                # fixed_codes = apply_SR_patches(buggy_functions, SR_patches)
                fixed_codes = apply_SR_patches_v2(SR_func_pairs)
                reward, submission_result = test(buggy_info['SLUG'], buggy_info['PATHES'], buggy_info['RANGE_BLOCKS'], fixed_codes)
                df_results.loc[i * args.max_try + j] = {'ID': i, 'lang': 'java', 'slug': buggy_info['SLUG'], 'bug': buggy_info['BUGGY_CODE'], 'diff': 'np.nan', 'fix': response}
                df_results.to_csv(args.result_path, sep=',', encoding='utf-8', index=False)
                df_eval.loc[i * args.max_try + j] = {'ID': i, 'slug': buggy_info['SLUG'], 'reward': reward, 'submission_result': submission_result}
                df_eval.to_csv(args.eval_path, sep=',', encoding='utf-8', index=False)

                    # for item in prompt: # for observation
                    #     print(item['content'])
                    #     print('-'*80)
                    # print(fixed_code)
                    # exit()    

            except Exception as e:
                print(e)      


def test(bug_id, class_paths, class_replace_indexs, fixed_methods):
    func_num=len(fixed_methods)
    # class_replace_index = extract_method_start_end_index(class_path, function_head, original_method_len)
    if class_replace_indexs is None:
        return False, 'Locate failed'
    replace_files(class_paths, class_replace_indexs, fixed_methods)
    test_config_ins=dict()
    reward, submission_result = run_JUnit(bug_id, test_config_ins)
    restore_files(class_paths, bug_id)
    return reward, submission_result
        
        




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api_key', default="sk-4aba884b61424f59b1fab0f60d188103", type=str)
    parser.add_argument('--cp_path', default="~/.cache/huggingface/hub", type=str)
    parser.add_argument('--chat_mode', default="remote", type=str) # remote or local
    parser.add_argument('--remote_model', default="deepseek-chat", type=str) # Choose model: gpt-3.5-turbo, gpt-4, claude-2, palm-2-chat-bison, gemini-pro
    parser.add_argument('--local_model', default='models--mistralai--Mixtral-8x7B-Instruct-v0.1', type=str)
    parser.add_argument('--data_path', default=d4c_path+"data/defects4j_code.csv", type=str) 
    parser.add_argument('--msg_path', default=d4c_path+"data/defects4j_artifact.csv", type=str)
    parser.add_argument('--result_path', default=d4c_path+"result/defects4j/pred", type=str)
    parser.add_argument('--eval_path', default=d4c_path+"result/defects4j/eval", type=str)
    parser.add_argument('--remote_proxy', default='DeepSeek', type=str)
    parser.add_argument('--local_proxy', default='batch', type=str)
    parser.add_argument('--mode', default='agent', type=str)
    parser.add_argument('--shot', default=1, type=int)
    parser.add_argument('--max_try', default=10, type=int)
    parser.add_argument('--temperature', default=1.0, type=float)
    parser.add_argument('--ablation', default='full', type=str)
    parser.add_argument('--check', default=False, type=bool)
    parser.add_argument('--early_stop', default=False, type=bool)
    parser.add_argument('--log_path', default=d4c_path+"/log", type=str)
    args = parser.parse_args()
    # if not os.path.exists(args.eval_path):
    #     os.makedirs(args.eval_path)
    # if not os.path.exists(args.result_path):
    #     os.makedirs(args.result_path)
    result_elements = [args.result_path, args.ablation, str(args.shot)]
    eval_elements = [args.eval_path, args.ablation, str(args.shot)]

    remote_mode_alias = args.remote_model.split('/')[-1]
    local_mode_alias = args.local_model.split('/')[-1]

    if args.chat_mode == 'remote':
        args.result_path = '_'.join(elem for elem in result_elements if elem != '') + f'shot_{remote_mode_alias}_{args.max_try}try_temp={args.temperature}.csv'
        args.eval_path = '_'.join(elem for elem in eval_elements if elem != '') + f'shot_{remote_mode_alias}_{args.max_try}try_temp={args.temperature}.csv'
        # print(args.result_path)
        # print(args.eval_path)
    elif args.chat_mode == 'local':
        args.result_path = '_'.join(elem for elem in result_elements if elem != '') + f'shot_{local_mode_alias}_{args.max_try}try_temp={args.temperature}.csv'
        args.eval_path = '_'.join(elem for elem in eval_elements if elem != '') + f'shot_{local_mode_alias}_{args.max_try}try_temp={args.temperature}.csv'
    else:
        raise ValueError("chat_mode must be 'remote' or 'local'")

    debug(args)

    
            
        




