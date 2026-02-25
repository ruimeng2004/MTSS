from utils.chat_local import LocalChat
from utils.chat_remote import RemoteChat
from prompt.debugbench import *
from utils.patch_apply import *
import argparse
import pandas as pd
import json
from tqdm import tqdm
import os


def debug(args):
    if not os.path.exists('result/debugbench'):
        os.makedirs('result/debugbench')
    json_file = open(args.data_path, 'r')
    data = json.load(json_file)
    json_file.close()
    row_num = 0
    if os.path.exists(args.result_path):
        df_results = pd.read_csv(args.result_path, sep=',', encoding='utf-8', engine='python')
        row_num = df_results['ID'].iloc[-1]
    else:
        df_results = pd.DataFrame(columns=['ID', 'lang', 'slug', 'bug', 'diff', 'fix'])
    print(f'start from {row_num}')


    if args.mode == 'agent':
        history_list = HISTORY_AGENT_LIST
    elif args.mode == 'located':
        history_list = HISTORY_LOCATED_LIST
    elif args.mode == 'hybrid':
        history_list = HISTORY_HYBRID_LIST
    elif args.mode == 'reverse':
        history_list = HISTORY_REVERSE_LIST
    elif args.mode == 'pure':
        history_list = HISTORY_PURE_LIST


    if args.chat_mode == 'remote':
        debugger = RemoteChat(args.api_key, args.remote_model, args.remote_proxy)
    elif args.chat_mode == 'local':
        debugger = LocalChat(args.cp_path, args.local_model, args.local_proxy)
    else:
        raise ValueError("chat_mode must be 'remote' or 'local'")
    
    for i in tqdm(range(len(data))):
        sample = data[i]

        if i < row_num:
            continue

        if sample['category'] != "logic error":
            continue

        prompt = history_list[sample['language']] # select languange specific history
        prompt = prompt.copy()


        # different input
        if args.mode == 'agent' or args.mode == 'reverse':
            query = AGENT_PROMPT
            query = query.replace("{LANGUAGE}", sample['language'].strip())
            query = query.replace("{REQUIREMENT}", sample['question'].strip())
            query = query.replace("{CONSTRAINT}", sample['constraints'].strip())
            query = query.replace("{EXAMPLE}", '\n'.join(sample['examples']).strip())
            if args.mode == 'agent': # different output
                query = query.replace("{BUGGY_CODE}", sample['buggy_code'].strip())
                query = query.strip() + "\nPlease follow your duty as an AI Debugger and generate a refined version of the buggy program."
            else:
                query = query.replace("{BUGGY_CODE}", sample['located_code'].strip())
                query = query.strip() + "\nPlease follow your duty as an AI Debugger and generate the corrected code snippets for the buggy program."
        elif args.mode == 'located' or args.mode == 'hybrid':
            query = USER_PROMPT
            query = query.replace("{LANGUAGE}", sample['language'].strip())
            if args.mode == 'located':
                query = query.replace("{BUGGY_CODE}", sample['located_code'].strip())
                query = query.strip() + "\nPlease follow your duty as an AI Debugger and generate code snippets to fill the chunks marked as `<Chunk_For_Modification>` in each provided buggy function."
            else:
                query = query.replace("{BUGGY_CODE}", sample['buggy_code'].strip())
                query = query.strip() + "\nPlease follow your duty as an AI Debugger and generate a refined version of the buggy program."
        elif args.mode == 'pure':
            query = USER_PROMPT
            query = query.replace("{LANGUAGE}", sample['language'].strip())
            query = query.replace("{BUGGY_CODE}", sample['buggy_code'].strip())
            query = query.strip() + "\nPlease follow your duty as an AI Debugger and generate a refined version of the buggy program."
        else:
            raise ValueError("mode must be 'located' or 'hybrid' or 'reverse' or 'agent'")

        prompt.append({
            "role": "user",
            "content": query
        })


        if args.ablation != 'full':
            if args.ablation == 'comment':
                pattern = r'### Program requirements:\n```[\s\S]*?```\n\n'
            elif args.ablation == 'example':
                pattern = r'### Test examples:\n```[\s\S]*?```\n\n'
            elif args.ablation == 'message':
                pattern = r'### Input constraints:\n```[\s\S]*?```\n\n'
            else:
                raise ValueError("ablation must be 'full' or 'comment' or 'case' or 'message'")
            prompt[1]['content'] = re.sub(pattern, '', prompt[1]['content'])
            prompt[3]['content'] = re.sub(pattern, '', prompt[3]['content'])


        for j in range(args.max_try):
            try:
                if args.mode in {'agent', 'hybrid', 'pure'}:
                    response = debugger.chat(prompt, i, temperature=args.temperature)
                    fixed_code = extract_code(response)[0]
                    df_results.loc[i * args.max_try + j] = {'ID': i, 'lang': sample['language'], 'slug': sample['slug'], 'bug': sample['buggy_code'], 'diff': 'None', 'fix': fixed_code}
                    df_results.to_csv(args.result_path, sep=',', encoding='utf-8', index=False)
                    
                elif args.mode in {'located', 'reverse'}:
                    response = debugger.chat(prompt, i, temperature=args.temperature)
                    codeblock = extract_code(response)
                    if len(codeblock) == sample['located_code'].count('<Chunk_For_Modification>'):
                        fixed_code = sample['located_code']
                        patch = '\n'.join(codeblock)
                        for hunk in codeblock:
                            fixed_code = fixed_code.replace('<Chunk_For_Modification>', hunk, 1)
                        df_results.loc[i * args.max_try + j] = {'ID': i, 'lang': sample['language'], 'slug': sample['slug'], 'bug': sample['located_code'], 'diff': patch, 'fix': fixed_code}
                        df_results.to_csv(args.result_path, sep=',', encoding='utf-8', index=False)
                    elif args.mode == 'reverse':
                        patch = '\n'.join(codeblock)
                        df_results.loc[i * args.max_try + j] = {'ID': i, 'lang': sample['language'], 'slug': sample['slug'], 'bug': sample['located_code'], 'diff': patch, 'fix': 'To Be Applied'}
                        df_results.to_csv(args.result_path, sep=',', encoding='utf-8', index=False)
                    else:
                        df_results.loc[i * args.max_try + j] = {'ID': i, 'lang': sample['language'], 'slug': sample['slug'], 'bug': sample['located_code'], 'diff': 'None', 'fix': 'Match failed'}
                        df_results.to_csv(args.result_path, sep=',', encoding='utf-8', index=False)

                # for item in prompt: # for observation
                #     print(item['content'])
                #     print('-'*80)
                # print(fixed_code)
                # exit()
                        
            except Exception as e:
                print(e)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api_key', default="sh-xxxx", type=str)
    parser.add_argument('--cp_path', default="~/.cache/huggingface/hub", type=str)
    parser.add_argument('--chat_mode', default="remote", type=str) # remote or local
    parser.add_argument('--remote_model', default="gpt-4-0613", type=str) # Choose model: gpt-3.5-turbo, gpt-4, claude-2, palm-2-chat-bison, gemini-pro
    parser.add_argument('--local_model', default='models--mistralai--Mixtral-8x7B-Instruct-v0.1', type=str)
    parser.add_argument('--data_path', default="data/debugbench_all.json", type=str) 
    parser.add_argument('--result_path', default="result/debugbench/pred", type=str)
    parser.add_argument('--eval_path', default="result/debugbench/eval", type=str)
    parser.add_argument('--remote_proxy', default='OpenAI', type=str)
    parser.add_argument('--local_proxy', default='batch', type=str)
    parser.add_argument('--mode', default='agent', type=str)
    parser.add_argument('--shot', default=1, type=int)
    parser.add_argument('--max_try', default=3, type=int)
    parser.add_argument('--temperature', default=1.0, type=float)
    parser.add_argument('--ablation', default='full', type=str)
    args = parser.parse_args()

    result_elements = [args.result_path, args.mode, args.ablation, str(args.shot)]
    eval_elements = [args.eval_path, args.mode, args.ablation, str(args.shot)]

    remote_model_alias = args.remote_model.split('/')[-1]
    local_model_alias = args.local_model.split('/')[-1]

    if args.chat_mode == 'remote':
        args.result_path = '_'.join(elem for elem in result_elements if elem != '') + f'shot_{remote_model_alias}_{args.max_try}try_temp={args.temperature}.csv'
        args.eval_path = '_'.join(elem for elem in eval_elements if elem != '') + f'shot_{remote_model_alias}_{args.max_try}try_temp={args.temperature}.csv'
    elif args.chat_mode == 'local':
        args.result_path = '_'.join(elem for elem in result_elements if elem != '') + f'shot_{local_model_alias}_{args.max_try}try_temp={args.temperature}.csv'
        args.eval_path = '_'.join(elem for elem in eval_elements if elem != '') + f'shot_{local_model_alias}_{args.max_try}try_temp={args.temperature}.csv'
    else:
        raise ValueError("chat_mode must be 'remote' or 'local'")

    debug(args)

    
            
        




