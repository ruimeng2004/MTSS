import argparse
import csv
import json
import os
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# 优雅地设置项目根目录 (必须在导入项目模块之前)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'generator'))

from generator_utils import extract_buggy_info_for_SR  # type: ignore  # noqa: E402
from prompt.d4j import (  # noqa: E402
    AGENT_PROMPT_SR,
    HISTORY_AGENT_D4J_SEARCH_REPLACE,
    HISTORY_PURE_D4J,
    USER_PROMPT,
)
from utils.chat_local import LocalChat  # noqa: E402
from utils.chat_remote import RemoteChat  # noqa: E402
from validator.junit import replace_files, restore_files, run_JUnit  # noqa: E402


log_dir = '/home/base/d4c/D4C/log'

checkout_path='/home/data/Defects4j/checkout_new/buggy'
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
    all_slugs = id_count.index.tolist()  # 所有出现过的 slug
    # Check if result and eval paths exist
    if not os.path.exists(args.result_path):
        pass  # result file doesn't exist
    if not os.path.exists(args.eval_path):
        pass  # eval data doesn't exist
    # for plausible check
    if args.ablation == 'full' and args.check:
        plausible_df = pd.read_csv('result/defects4j/evaluation_agent_1shot_gpt-4_10try_temp=1.0.csv', sep=',', encoding='utf-8', engine='python')
        # Filter for reward cases
        plausible_df[plausible_df['reward']]

    if args.mode == 'agent':
        history = HISTORY_AGENT_D4J_SEARCH_REPLACE
    elif args.mode == 'pure':
        history = HISTORY_PURE_D4J
    else:
        raise ValueError("mode must be 'agent' or 'pure'")

    if args.chat_mode == 'remote':
        RemoteChat(args.api_key, args.remote_model, args.remote_proxy)
    elif args.chat_mode == 'local':
        LocalChat(args.cp_path, args.local_model, args.local_proxy)
    else:
        raise ValueError("chat_mode must be 'remote' or 'local'")
    all_slugs = sorted(all_slugs, key=lambda slug: (slug.split('_')[0].lower(), int(slug.split('_')[1])))
    # 创建 prompt_list 目录
    prompt_list_dir = os.path.join(os.path.dirname(__file__), '..', 'prompt_list')
    os.makedirs(prompt_list_dir, exist_ok=True)
    
    for i, slug in tqdm(enumerate(all_slugs), total=len(all_slugs), desc="Processing Slugs", unit="slug"):
        
        buggy_info = extract_buggy_info_for_SR(data, msg,slug,log_dir)
        
        # 为每个 slug 创建子文件夹
        slug_dir = os.path.join(prompt_list_dir, slug)
        os.makedirs(slug_dir, exist_ok=True)
        
        # 保存 BUGGY_COMMENT
        with open(os.path.join(slug_dir, 'BUGGY_COMMENT.txt'), 'w', encoding='utf-8') as f:
            f.write(buggy_info['BUGGY_COMMENT'])
        
        # 保存 ERROR_MESSAGE
        with open(os.path.join(slug_dir, 'ERROR_MESSAGE.txt'), 'w', encoding='utf-8') as f:
            f.write(buggy_info['ERROR_MESSAGE'].strip())
        
        # 保存 FAILED_TEST
        with open(os.path.join(slug_dir, 'FAILED_TEST.txt'), 'w', encoding='utf-8') as f:
            f.write(buggy_info['FAILED_TEST'].strip())
        
        # 保存 BUGGY_CODE
        with open(os.path.join(slug_dir, 'BUGGY_CODE.txt'), 'w', encoding='utf-8') as f:
            f.write(buggy_info['BUGGY_CODE'].strip())
        
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
        
        # 保存 query
        with open(os.path.join(slug_dir, 'query.txt'), 'w', encoding='utf-8') as f:
            f.write(query)
        
        prompt = history.copy()                        
        prompt.append({
            "role": "user",
            "content": query
        })
        
        print(f"Saved prompt files for {slug} in {slug_dir}")
       

def refresh_pathes(pathes, checkout_path):
    new_pathes = []
    for path in pathes:
        path=path.replace('/data/lith/APR/defects4j/defects4j/defects4j', checkout_path)
        new_pathes.append(path)
    return new_pathes

def test(bug_id, class_paths, class_replace_indexs, fixed_methods, checkout_path):
    
    class_paths = refresh_pathes(class_paths, checkout_path)
    # class_replace_index = extract_method_start_end_index(class_path, function_head, original_method_len)
    if class_replace_indexs is None:
        return False, 'Locate failed'
    replace_files(class_paths, class_replace_indexs, fixed_methods)
    test_config_ins=dict()
    reward, submission_result = run_JUnit(bug_id, test_config_ins,checkout_path)
    restore_files(class_paths, bug_id, checkout_path)
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
    parser.add_argument('--max_try', default=8, type=int)
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

    
            
        




