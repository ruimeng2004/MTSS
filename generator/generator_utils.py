import pandas as pd
import os
import json

def extract_buggy_info(data, msg, slug,pass_log_dir):
    """
    Extract BUGGY_COMMENT, ERROR_MESSAGE, FAILED_TEST, and BUGGY_CODE for a specific slug.
    :param data: DataFrame containing buggy function information.
    :param msg: DataFrame containing error and test information.
    :param slug: The slug to filter data and msg.
    :return: A list of dictionaries containing the extracted information.
    """
    # 筛选出指定 slug 的所有 buggy functions
    datas = data[data['slug'] == slug]
    func_num= len(datas)

    # 筛选出指定 slug 的所有错误和测试信息
    msg_filtered = msg[msg['slug'] == slug]

    # 初始化结果列表
    buggy_codes=''
    buggy_comments=''
    pathes=[]
    range_blocks=[]
    locations=[]
    method_names=[]
    method_signatures=[]
    # 遍历每一行 buggy function 数据
    for _, row in datas.iterrows():
        # 获取 BUGGY_COMMENT 和 BUGGY_CODE
        buggy_comment = row['comment'].strip() if pd.notna(row['comment']) else "This function has no comment."
        buggy_code = row['buggy_code']
        path= row['path'].strip()
        range_line={'start': row['start_line'], 'end': row['end_line']}
        method_name = row['method_name'].strip()
        method_signature = row['method_sig'].strip()
        if method_name not in method_names:
            method_names.append(method_name)
        if method_signature not in method_signatures:
            method_signatures.append(method_signature)
        range_blocks.append(range_line)
        pathes.append(path)
        slug_prefix = f"{slug}_buggy"
        locations.append({
            "buggy_function": method_signature,
            "file_path": path.split(slug_prefix, 1)[-1],
            "start_line": row['start_line'],
            "end_line": row['end_line']
        })
        location_instruction=f'This function {method_name} start from line {str(row["start_line"])}'
        if buggy_comment != '':
            buggy_comments+='   '+buggy_comment+'\n'
        buggy_codes+= '```java\n'+buggy_code+'\n```\n'
        # 获取 ERROR_MESSAGE 和 FAILED_TEST
    error_message = '\n'.join(msg_filtered['exception_info'].dropna().tolist()) if not msg_filtered.empty else "This function has no exception info."
    failed_tests = '\n'.join(msg_filtered['test_method'].dropna().tolist()) if not msg_filtered.empty else "This function has no failed test."

        # 构造结果字典
    result = {
            'SLUG': slug,   
            'BUGGY_COMMENT': buggy_comments,
            'ERROR_MESSAGE': error_message,
            'FAILED_TEST': failed_tests,
            'BUGGY_CODE': buggy_codes,
            'PATHES': pathes,
            'RANGE_BLOCKS': range_blocks,
            'FUNC_NUM': func_num,
            'METHOD_NAME': method_names,
            'METHOD_SIGNATURE': method_signatures,
            'BUGGY_FUNCTIONS_LOCATION': locations
        }
    # 定义日志目录
    log_dir = pass_log_dir
    os.makedirs(log_dir, exist_ok=True)  # 确保目录存在

    # 将结果写入文件
    with open(os.path.join(log_dir, 'BUGGY_COMMENT.txt'), 'w') as f:
        f.write(result['BUGGY_COMMENT'])
    with open(os.path.join(log_dir, 'ERROR_MESSAGE.txt'), 'w') as f:
        f.write(result['ERROR_MESSAGE'])
    with open(os.path.join(log_dir, 'FAILED_TEST.txt'), 'w') as f:
        f.write(result['FAILED_TEST'])
    with open(os.path.join(log_dir, 'BUGGY_CODE.txt'), 'w') as f:
        f.write(result['BUGGY_CODE'])
    with open(os.path.join(log_dir, 'PATHES.txt'), 'w') as f:
        f.write(str(result['PATHES']))
    with open(os.path.join(log_dir, 'RANGE_BLOCKS.txt'), 'w') as f:
        f.write(str(result['RANGE_BLOCKS']))
    with open(os.path.join(log_dir, 'FUNC_NUM.txt'), 'w') as f:
        f.write(str(result['FUNC_NUM']))
    with open(os.path.join(log_dir, 'METHOD_NAME.txt'), 'w') as f:
        f.write(str(result['METHOD_NAME']))
    with open(os.path.join(log_dir, 'METHOD_SIGNATURE.txt'), 'w') as f:
        f.write(str(result['METHOD_SIGNATURE']))
    with open(os.path.join(log_dir, 'BUGGY_FUNCTIONS_LOCATION.json'), 'w', encoding='utf-8') as f:
        json.dump(locations, f, indent=4)  # 使用 indent=4 格式化输出
    return result


def annotate_function_with_line_numbers(function_code: str, start_line: int) -> str:
    """
    Annotates each line of the given function code with its corresponding line number.

    :param function_code: The function code as a string.
    :param start_line: The starting line number of the function.
    :return: The annotated function code with line numbers as comments.
    """
    # 将函数代码按行分割
    lines = function_code.splitlines()
    
    # 初始化结果列表
    annotated_lines = []
    
    # 遍历每一行，添加行号注释
    for i, line in enumerate(lines):
        line_number = start_line + i
        annotated_line = f"{line}  // Line {line_number}"
        annotated_lines.append(annotated_line)
    
    # 将注释后的行重新拼接为字符串
    return "\n".join(annotated_lines)

def extract_buggy_info_for_patch(data, msg, slug):
    """
    Extract BUGGY_COMMENT, ERROR_MESSAGE, FAILED_TEST, and BUGGY_CODE for a specific slug.
    :param data: DataFrame containing buggy function information.
    :param msg: DataFrame containing error and test information.
    :param slug: The slug to filter data and msg.
    :return: A list of dictionaries containing the extracted information.
    """
    # 筛选出指定 slug 的所有 buggy functions
    datas = data[data['slug'] == slug]
    func_num= len(datas)

    # 筛选出指定 slug 的所有错误和测试信息
    msg_filtered = msg[msg['slug'] == slug]

    # 初始化结果列表
    buggy_codes=''
    buggy_comments=''
    pathes=[]
    range_blocks=[]
    locations=[]
    method_names=[]
    method_signatures=[]
    # 遍历每一行 buggy function 数据
    for _, row in datas.iterrows():
        # 获取 BUGGY_COMMENT 和 BUGGY_CODE
        buggy_comment = row['comment'].strip() if pd.notna(row['comment']) else "This function has no comment."
        buggy_code = row['buggy_code']
        path= row['path'].strip()
        range_line={'start': row['start_line'], 'end': row['end_line']}
        method_name = row['method_name'].strip()
        method_signature = row['method_sig'].strip()
        if method_name not in method_names:
            method_names.append(method_name)
        if method_signature not in method_signatures:
            method_signatures.append(method_signature)
        range_blocks.append(range_line)
        pathes.append(path)
        slug_prefix = f"{slug}_buggy"
        a_path=path.split(slug_prefix, 1)[-1]
        locations.append({
            "buggy_function": method_signature,
            "file_path": path.split(slug_prefix, 1)[-1],
            "start_line": row['start_line'],
            "end_line": row['end_line']
        })
        location_instruction=f'This function {method_name} start from line {str(row["start_line"])}'
        if buggy_comment != '':
            buggy_comments+='   '+buggy_comment+'\n'
        buggy_codes+= a_path+'\n```java\n'+annotate_function_with_line_numbers(buggy_code, row['start_line'])+'\n```\n'
        # 获取 ERROR_MESSAGE 和 FAILED_TEST
    error_message = '\n'.join(msg_filtered['exception_info'].dropna().tolist()) if not msg_filtered.empty else "This function has no exception info."
    failed_tests = '\n'.join(msg_filtered['test_method'].dropna().tolist()) if not msg_filtered.empty else "This function has no failed test."

        # 构造结果字典
    result = {
            'SLUG': slug,   
            'BUGGY_COMMENT': buggy_comments,
            'ERROR_MESSAGE': error_message,
            'FAILED_TEST': failed_tests,
            'BUGGY_CODE': buggy_codes,
            'PATHES': pathes,
            'RANGE_BLOCKS': range_blocks,
            'FUNC_NUM': func_num,
            'METHOD_NAME': method_names,
            'METHOD_SIGNATURE': method_signatures,
            'BUGGY_FUNCTIONS_LOCATION': locations
        }
    # 定义日志目录
    log_dir = '/home/lith/APR_formulation/D4C/D4C/log/patch'
    os.makedirs(log_dir, exist_ok=True)  # 确保目录存在

    # 将结果写入文件
    with open(os.path.join(log_dir, 'BUGGY_COMMENT.txt'), 'w') as f:
        f.write(result['BUGGY_COMMENT'])
    with open(os.path.join(log_dir, 'ERROR_MESSAGE.txt'), 'w') as f:
        f.write(result['ERROR_MESSAGE'])
    with open(os.path.join(log_dir, 'FAILED_TEST.txt'), 'w') as f:
        f.write(result['FAILED_TEST'])
    with open(os.path.join(log_dir, 'BUGGY_CODE.txt'), 'w') as f:
        f.write(result['BUGGY_CODE'])
    with open(os.path.join(log_dir, 'PATHES.txt'), 'w') as f:
        f.write(str(result['PATHES']))
    with open(os.path.join(log_dir, 'RANGE_BLOCKS.txt'), 'w') as f:
        f.write(str(result['RANGE_BLOCKS']))
    with open(os.path.join(log_dir, 'FUNC_NUM.txt'), 'w') as f:
        f.write(str(result['FUNC_NUM']))
    with open(os.path.join(log_dir, 'METHOD_NAME.txt'), 'w') as f:
        f.write(str(result['METHOD_NAME']))
    with open(os.path.join(log_dir, 'METHOD_SIGNATURE.txt'), 'w') as f:
        f.write(str(result['METHOD_SIGNATURE']))
    with open(os.path.join(log_dir, 'BUGGY_FUNCTIONS_LOCATION.json'), 'w', encoding='utf-8') as f:
        json.dump(locations, f, indent=4)  # 使用 indent=4 格式化输出
    return result

def extract_buggy_info_for_AIDER(data, msg, slug):
    """
    Extract BUGGY_COMMENT, ERROR_MESSAGE, FAILED_TEST, and BUGGY_CODE for a specific slug.
    :param data: DataFrame containing buggy function information.
    :param msg: DataFrame containing error and test information.
    :param slug: The slug to filter data and msg.
    :return: A list of dictionaries containing the extracted information.
    """
    # 筛选出指定 slug 的所有 buggy functions
    datas = data[data['slug'] == slug]
    func_num= len(datas)

    # 筛选出指定 slug 的所有错误和测试信息
    msg_filtered = msg[msg['slug'] == slug]

    # 初始化结果列表
    buggy_codes=''
    buggy_comments=''
    pathes=[]
    range_blocks=[]
    locations=[]
    method_names=[]
    method_signatures=[]
    buggy_locations=[]
    # 遍历每一行 buggy function 数据
    for _, row in datas.iterrows():
        # 获取 BUGGY_COMMENT 和 BUGGY_CODE
        buggy_comment = row['comment'].strip() if pd.notna(row['comment']) else "This function has no comment."
        buggy_code = row['buggy_code']
        path= row['path'].strip()
        range_line={'start': row['start_line'], 'end': row['end_line']}
        method_name = row['method_name'].strip()
        method_signature = row['method_sig'].strip()
        if method_name not in method_names:
            method_names.append(method_name)
        if method_signature not in method_signatures:
            method_signatures.append(method_signature)
        range_blocks.append(range_line)
        pathes.append(path)
        slug_prefix = f"{slug}_buggy"
        a_path=path.split(slug_prefix, 1)[-1]
        locations.append({
            "buggy_function": method_signature,
            "file_path": path.split(slug_prefix, 1)[-1],
            "start_line": row['start_line'],
            "end_line": row['end_line']
        })
        buggy_locations=buggy_locations+f'buggy_function: {method_signature}\nfile_path: {a_path}\n'
        location_instruction=f'This function {method_name} start from line {str(row["start_line"])}'
        if buggy_comment != '':
            buggy_comments+='   '+buggy_comment+'\n'
        buggy_codes+= a_path+'\n```java\n'+annotate_function_with_line_numbers(buggy_code, row['start_line'])+'\n```\n'
        # 获取 ERROR_MESSAGE 和 FAILED_TEST
    error_message = '\n'.join(msg_filtered['exception_info'].dropna().tolist()) if not msg_filtered.empty else "This function has no exception info."
    failed_tests = '\n'.join(msg_filtered['test_method'].dropna().tolist()) if not msg_filtered.empty else "This function has no failed test."

        # 构造结果字典
    result = {
            'SLUG': slug,   
            'BUGGY_COMMENT': buggy_comments,
            'ERROR_MESSAGE': error_message,
            'FAILED_TEST': failed_tests,
            'BUGGY_CODE': buggy_codes,
            'PATHES': pathes,
            'RANGE_BLOCKS': range_blocks,
            'FUNC_NUM': func_num,
            'METHOD_NAME': method_names,
            'METHOD_SIGNATURE': method_signatures,
            'BUGGY_FUNCTIONS_LOCATION': locations,
            'BUGGY_LOCATION':buggy_locations
        }
    # 定义日志目录
    log_dir = '/home/lith/APR_formulation/D4C/D4C/log/AIDER'
    os.makedirs(log_dir, exist_ok=True)  # 确保目录存在

    # 将结果写入文件
    with open(os.path.join(log_dir, 'BUGGY_COMMENT.txt'), 'w') as f:
        f.write(result['BUGGY_COMMENT'])
    with open(os.path.join(log_dir, 'ERROR_MESSAGE.txt'), 'w') as f:
        f.write(result['ERROR_MESSAGE'])
    with open(os.path.join(log_dir, 'FAILED_TEST.txt'), 'w') as f:
        f.write(result['FAILED_TEST'])
    with open(os.path.join(log_dir, 'BUGGY_CODE.txt'), 'w') as f:
        f.write(result['BUGGY_CODE'])
    with open(os.path.join(log_dir, 'PATHES.txt'), 'w') as f:
        f.write(str(result['PATHES']))
    with open(os.path.join(log_dir, 'RANGE_BLOCKS.txt'), 'w') as f:
        f.write(str(result['RANGE_BLOCKS']))
    with open(os.path.join(log_dir, 'FUNC_NUM.txt'), 'w') as f:
        f.write(str(result['FUNC_NUM']))
    with open(os.path.join(log_dir, 'METHOD_NAME.txt'), 'w') as f:
        f.write(str(result['METHOD_NAME']))
    with open(os.path.join(log_dir, 'METHOD_SIGNATURE.txt'), 'w') as f:
        f.write(str(result['METHOD_SIGNATURE']))
    with open(os.path.join(log_dir, 'BUGGY_FUNCTIONS_LOCATION.json'), 'w', encoding='utf-8') as f:
        json.dump(locations, f, indent=4)  # 使用 indent=4 格式化输出
    return result

def extract_buggy_info_for_SR(data, msg, slug,pass_log_dir):
    """
    Extract BUGGY_COMMENT, ERROR_MESSAGE, FAILED_TEST, and BUGGY_CODE for a specific slug.
    :param data: DataFrame containing buggy function information.
    :param msg: DataFrame containing error and test information.
    :param slug: The slug to filter data and msg.
    :return: A list of dictionaries containing the extracted information.
    """
    # 筛选出指定 slug 的所有 buggy functions
    datas = data[data['slug'] == slug]
    func_num= len(datas)

    # 筛选出指定 slug 的所有错误和测试信息
    msg_filtered = msg[msg['slug'] == slug]

    # 初始化结果列表
    buggy_codes=''
    buggy_comments=''
    pathes=[]
    range_blocks=[]
    locations=[]
    method_names=[]
    method_signatures=[]
    # 遍历每一行 buggy function 数据
    for _, row in datas.iterrows():
        # 获取 BUGGY_COMMENT 和 BUGGY_CODE
        buggy_comment = row['comment'].strip() if pd.notna(row['comment']) else "This function has no comment."
        buggy_code = row['buggy_code']
        path= row['path'].strip()
        range_line={'start': row['start_line'], 'end': row['end_line']}
        method_name = row['method_name'].strip()
        method_signature = row['method_sig'].strip()
        if method_name not in method_names:
            method_names.append(method_name)
        if method_signature not in method_signatures:
            method_signatures.append(method_signature)
        range_blocks.append(range_line)
        pathes.append(path)
        slug_prefix = f"{slug}_buggy"
        locations.append({
            "buggy_function": method_signature,
            "file_path": path.split(slug_prefix, 1)[-1],
            "start_line": row['start_line'],
            "end_line": row['end_line']
        })
        location_instruction=f'This function {method_name} start from line {str(row["start_line"])}'
        if buggy_comment != '':
            buggy_comments+='   '+buggy_comment+'\n'
        buggy_codes+= '```java\n'+buggy_code+'\n```\n'
        # 获取 ERROR_MESSAGE 和 FAILED_TEST
    error_message = '\n'.join(msg_filtered['exception_info'].dropna().tolist()) if not msg_filtered.empty else "This function has no exception info."
    failed_tests = '\n'.join(msg_filtered['test_method'].dropna().tolist()) if not msg_filtered.empty else "This function has no failed test."

        # 构造结果字典
    result = {
            'SLUG': slug,   
            'BUGGY_COMMENT': buggy_comments,
            'ERROR_MESSAGE': error_message,
            'FAILED_TEST': failed_tests,
            'BUGGY_CODE': buggy_codes,
            'PATHES': pathes,
            'RANGE_BLOCKS': range_blocks,
            'FUNC_NUM': func_num,
            'METHOD_NAME': method_names,
            'METHOD_SIGNATURE': method_signatures,
            'BUGGY_FUNCTIONS_LOCATION': locations
        }
    # 定义日志目录
    log_dir = pass_log_dir
    os.makedirs(log_dir, exist_ok=True)  # 确保目录存在

    # 将结果写入文件
    with open(os.path.join(log_dir, 'BUGGY_COMMENT.txt'), 'w') as f:
        f.write(result['BUGGY_COMMENT'])
    with open(os.path.join(log_dir, 'ERROR_MESSAGE.txt'), 'w') as f:
        f.write(result['ERROR_MESSAGE'])
    with open(os.path.join(log_dir, 'FAILED_TEST.txt'), 'w') as f:
        f.write(result['FAILED_TEST'])
    with open(os.path.join(log_dir, 'BUGGY_CODE.txt'), 'w') as f:
        f.write(result['BUGGY_CODE'])
    with open(os.path.join(log_dir, 'PATHES.txt'), 'w') as f:
        f.write(str(result['PATHES']))
    with open(os.path.join(log_dir, 'RANGE_BLOCKS.txt'), 'w') as f:
        f.write(str(result['RANGE_BLOCKS']))
    with open(os.path.join(log_dir, 'FUNC_NUM.txt'), 'w') as f:
        f.write(str(result['FUNC_NUM']))
    with open(os.path.join(log_dir, 'METHOD_NAME.txt'), 'w') as f:
        f.write(str(result['METHOD_NAME']))
    with open(os.path.join(log_dir, 'METHOD_SIGNATURE.txt'), 'w') as f:
        f.write(str(result['METHOD_SIGNATURE']))
    with open(os.path.join(log_dir, 'BUGGY_FUNCTIONS_LOCATION.json'), 'w', encoding='utf-8') as f:
        json.dump(locations, f, indent=4)  # 使用 indent=4 格式化输出
    return result