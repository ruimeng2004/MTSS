import sys
import os

# NOTE: This file is a safe "fixed" variant of d4j_Rew_muliti.py.
# Main differences:
# - Uses a multiprocessing.Manager() lock (works with spawn start method)
# - Optional spawn start method to avoid fork-related deadlocks
# - Serializes the checkout/test section with a shared lock to avoid concurrent
#   edits/tests in the same Defects4J workspace.

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
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

log_dir = '/home/base/d4c/D4C/log'

checkout_path = '/home/data/Defects4j/checkout_new/buggy'
d4c_path = '/home/base/d4c/D4C/'
json_file_path = '/home/base/d4c/D4C/result/repair_level/repair_level_projects.json'


def get_repo_cases(json_file_path):
    """Reads a JSON file and extracts all cases under the 'repo' key into a list."""
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data.get('repo', [])


def read_slugs_from_file(file_path):
    """读取文件中的所有slug（每行一个），返回一个list。"""
    slugs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            slug = line.strip()
            if slug:
                slugs.append(slug)
    return slugs


def get_processed_slugs(csv_file_path):
    """Reads a CSV file and collects all processed slugs."""
    processed_slugs = set()
    with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
        reader = csv.reader(csv_file)
        next(reader)
        for row in reader:
            if len(row) > 1:
                processed_slugs.add(row[1])
    return processed_slugs


def _append_jsonl(path: str, record: dict, lock=None) -> None:
    if lock is None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return

    with lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def refresh_pathes(pathes, checkout_path):
    new_pathes = []
    for path in pathes:
        path = path.replace('/data/lith/APR/defects4j/defects4j/defects4j', checkout_path)
        new_pathes.append(path)
    return new_pathes


def test(bug_id, class_paths, class_replace_indexs, fixed_methods, checkout_path):
    class_paths = refresh_pathes(class_paths, checkout_path)
    if class_replace_indexs is None:
        return False, 'Locate failed'

    replace_files(class_paths, class_replace_indexs, fixed_methods)
    test_config_ins = dict()
    reward, submission_result = run_JUnit(bug_id, test_config_ins, checkout_path)
    restore_files(class_paths, bug_id, checkout_path)
    return reward, submission_result


def get_processed_slugs_2(file_path):
    processed_slugs = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                record = json.loads(line.strip())
                if "slug" in record:
                    processed_slugs.append(record["slug"])
    except Exception as e:
        print(f"Error reading file: {e}")
    return processed_slugs


def debug(args, i, slug, write_lock=None, checkout_lock=None):
    log_dir = args.log_path
    if not os.path.exists('result/defects4j'):
        os.makedirs('result/defects4j')

    data = pd.read_csv(args.data_path, sep=',', encoding='utf-8', engine='python')
    msg = pd.read_csv(args.msg_path, sep=',', encoding='utf-8', engine='python')

    if args.mode == 'agent':
        history = HISTORY_AGENT_D4J_MUTI
    elif args.mode == 'no_comment':
        history = HISTORY_AGENT_D4J_MUTI_NO_COMMENT
    elif args.mode == 'no_test':
        history = HISTORY_AGENT_D4J_MUTI_NO_TEST
    elif args.mode == 'no_test_message':
        history = HISTORY_AGENT_D4J_MUTI_NO_MESSAGE
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

    buggy_info = extract_buggy_info(data, msg, slug, log_dir)

    if args.mode == 'agent':
        query = AGENT_PROMPT_MUTI
        query = query.replace("{BUGGY_COMMENT}", buggy_info['BUGGY_COMMENT'])
        query = query.replace("{ERROR_MESSAGE}", buggy_info['ERROR_MESSAGE'].strip())
        query = query.replace("{FAILED_TEST}", buggy_info['FAILED_TEST'].strip())
        query = query.replace("{BUGGY_CODE}", buggy_info['BUGGY_CODE'].strip())
    elif args.mode == 'no_comment':
        query = AGENT_PROMPT_MUTI_NO_COMMENT
        query = query.replace("{ERROR_MESSAGE}", buggy_info['ERROR_MESSAGE'].strip())
        query = query.replace("{FAILED_TEST}", buggy_info['FAILED_TEST'].strip())
        query = query.replace("{BUGGY_CODE}", buggy_info['BUGGY_CODE'].strip())
    elif args.mode == 'no_test':
        query = AGENT_PROMPT_MUTI_NO_TEST
        query = query.replace("{BUGGY_COMMENT}", buggy_info['BUGGY_COMMENT'])
        query = query.replace("{ERROR_MESSAGE}", buggy_info['ERROR_MESSAGE'].strip())
        query = query.replace("{BUGGY_CODE}", buggy_info['BUGGY_CODE'].strip())
    elif args.mode == 'no_test_message':
        query = AGENT_PROMPT_MUTI_NO_MESSAGE
        query = query.replace("{BUGGY_COMMENT}", buggy_info['BUGGY_COMMENT'])
        query = query.replace("{FAILED_TEST}", buggy_info['FAILED_TEST'].strip())
        query = query.replace("{BUGGY_CODE}", buggy_info['BUGGY_CODE'].strip())
    elif args.mode == 'pure':
        query = USER_PROMPT
        query = query.replace("{BUGGY_CODE}", buggy_info['BUGGY_CODE'].strip())
    else:
        raise ValueError("mode must be 'agent' or 'pure'")

    prompt = history.copy()
    prompt.append({"role": "user", "content": query})

    # Avoid multiple workers clobbering the same log files.
    with open(os.path.join(log_dir, f'query_{slug}.txt'), 'w', encoding='utf-8') as f:
        f.write(query)

    for j in range(args.max_try):
        response = None
        try:
            response = debugger.chat(prompt, i, temperature=args.temperature)[0]
            with open(os.path.join(log_dir, f'response_{slug}.txt'), 'w', encoding='utf-8') as f:
                f.write(response)

            fixed_codes = extract_code(response)

            # Critical section: patch+test touches Defects4J checkout.
            # Serializing this avoids rare deadlocks / workspace corruption.
            if checkout_lock is None:
                reward, submission_result = test(
                    buggy_info['SLUG'],
                    buggy_info['PATHES'],
                    buggy_info['RANGE_BLOCKS'],
                    fixed_codes,
                    checkout_path,
                )
            else:
                with checkout_lock:
                    reward, submission_result = test(
                        buggy_info['SLUG'],
                        buggy_info['PATHES'],
                        buggy_info['RANGE_BLOCKS'],
                        fixed_codes,
                        checkout_path,
                    )

            if not isinstance(submission_result, str):
                submission_result = "error"

            _append_jsonl(
                args.result_path.replace(".csv", ".jsonl"),
                {
                    "slug": slug,
                    "reward": reward,
                    "submission_result": submission_result,
                    "buggy_code": buggy_info['BUGGY_CODE'],
                    "fixed_code": response,
                },
                lock=write_lock,
            )

            if reward:
                break

        except Exception as e:
            print(e)
            _append_jsonl(
                args.result_path.replace(".csv", ".jsonl"),
                {
                    "slug": slug,
                    "reward": False,
                    "submission_result": "error",
                    "buggy_code": buggy_info.get('BUGGY_CODE'),
                    "fixed_code": response,
                    "exception": str(e),
                },
                lock=write_lock,
            )


def repair(args):
    log_dir = args.log_path
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    result_dir = os.path.dirname(args.result_path)
    eval_dir = os.path.dirname(args.eval_path)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    if not os.path.exists(eval_dir):
        os.makedirs(eval_dir)

    try:
        data = pd.read_csv(args.data_path, sep=',', encoding='utf-8', engine='python')
    except Exception as e:
        print(f"Error reading data file: {e}")
        return

    processed_slugs = set()
    jsonl_path = args.result_path.replace(".csv", ".jsonl")
    if os.path.exists(jsonl_path):
        processed_slugs = set(get_processed_slugs_2(jsonl_path))

    id_count = data['slug'].value_counts()
    all_slugs = id_count.index.tolist()
    all_slugs = sorted(all_slugs, key=lambda s: (s.split('_')[0].lower(), int(s.split('_')[1])))

    # Single-process mode
    if args.num_threads == 1:
        for i, slug in tqdm(enumerate(all_slugs), total=len(all_slugs), desc="Processing Slugs", unit="slug"):
            if slug in processed_slugs:
                continue
            try:
                debug(args, i, slug)
            except Exception as e:
                print(f"Error processing slug {slug}: {e}")
        return

    # Multi-process mode
    # Use spawn by default to reduce fork-related deadlocks with network/ML libs.
    mp_context = mp.get_context(args.mp_start_method)

    # Use a Manager lock so it is shareable across spawn'ed processes.
    with mp_context.Manager() as manager:
        write_lock = manager.Lock()
        checkout_lock = manager.Lock()

        with ProcessPoolExecutor(max_workers=args.num_threads, mp_context=mp_context) as executor:
            futures = {}
            for i, slug in enumerate(all_slugs):
                if slug in processed_slugs:
                    continue
                futures[executor.submit(debug, args, i, slug, write_lock, checkout_lock)] = slug

            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), colour="MAGENTA"):
                slug = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing slug {slug}: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api_key', default="sk-4aba884b61424f59b1fab0f60d188103", type=str)
    parser.add_argument('--cp_path', default="~/.cache/huggingface/hub", type=str)
    parser.add_argument('--chat_mode', default="remote", type=str)
    parser.add_argument('--remote_model', default="deepseek-v3-0324", type=str)
    parser.add_argument('--local_model', default='models--mistralai--Mixtral-8x7B-Instruct-v0.1', type=str)
    parser.add_argument('--data_path', default=d4c_path + "data/defects4j_code.csv", type=str)
    parser.add_argument('--msg_path', default=d4c_path + "data/defects4j_artifact.csv", type=str)
    parser.add_argument('--result_path', default=d4c_path + "result/defects4j/pred", type=str)
    parser.add_argument('--eval_path', default=d4c_path + "result/defects4j/eval", type=str)
    parser.add_argument('--remote_proxy', default='OpenAI', type=str)
    parser.add_argument('--local_proxy', default='batch', type=str)
    parser.add_argument('--mode', default='agent', type=str)
    parser.add_argument('--shot', default=1, type=int)
    parser.add_argument('--max_try', default=5, type=int)
    parser.add_argument('--temperature', default=1.0, type=float)
    parser.add_argument('--ablation', default='full', type=str)
    parser.add_argument('--check', default=False, type=bool)
    parser.add_argument('--early_stop', default=False, type=bool)
    parser.add_argument('--log_path', default=d4c_path + "/log", type=str)
    parser.add_argument('--num_threads', default=5, type=int, help='Number of processes for parallel processing')
    parser.add_argument(
        '--mp_start_method',
        default='spawn',
        choices=['spawn', 'fork', 'forkserver'],
        type=str,
        help='Multiprocessing start method. spawn is safer for many libs; fork is faster on Linux.',
    )

    args = parser.parse_args()

    result_elements = [args.result_path, args.ablation, str(args.shot)]
    eval_elements = [args.eval_path, args.ablation, str(args.shot)]

    remote_mode_alias = args.remote_model.split('/')[-1]
    local_mode_alias = args.local_model.split('/')[-1]

    if args.chat_mode == 'remote':
        args.result_path = '_'.join(elem for elem in result_elements if elem != '') + f'_shot_{remote_mode_alias}_{args.max_try}try_temp={args.temperature}.csv'
        args.eval_path = '_'.join(elem for elem in eval_elements if elem != '') + f'_shot_{remote_mode_alias}_{args.max_try}try_temp={args.temperature}.csv'
    elif args.chat_mode == 'local':
        args.result_path = '_'.join(elem for elem in result_elements if elem != '') + f'_shot_{local_mode_alias}_{args.max_try}try_temp={args.temperature}.jsonl'
        args.eval_path = '_'.join(elem for elem in eval_elements if elem != '') + f'_shot_{local_mode_alias}_{args.max_try}try_temp={args.temperature}.jsonl'
    else:
        raise ValueError("chat_mode must be 'remote' or 'local'")

    args.result_path = args.result_path.replace("pred", "pred_REW")
    args.eval_path = args.eval_path.replace("pred", "pred_REW")

    repair(args)
