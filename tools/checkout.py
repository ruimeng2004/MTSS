"""
DATA PROCESS SCRIPTS
FOR DEFECTS4J V2.0
"""
import os

def parse_id_ranges(id_ranges):
    id_list = []
    ranges = id_ranges.split(',')
    ids = []
    for r in ranges:
            if '-' in r:
                start, end = map(int, r.split('-'))
                ids.extend(range(start, end + 1))
            else:
                ids.append(int(r))
    id_list.append(ids)
    return id_list



def get_repos(root_dir, proj_list, id_list):
    repos_dir = root_dir + 'defects4j/'
    for i in range(len(proj_list)):
        project = proj_list[i]
        for j in id_list[i]:
            for k in j:
                unique_id = project + '_' + str(k)
                dir_name=repos_dir + unique_id + '_buggy'
                path='/data/lith/APR/defects4j/defects4j/defects4j/'+unique_id + '_buggy'
                if os.path.exists(path):
                    print("already exists: " + project + '_' + str(k))
                    continue
                try:
                    print("in processing: " + project + '_' + str(k))
                    cmd = 'defects4j checkout -p '+ project + ' -v '+ str(k) + 'b -w ' + dir_name
                    os.system(cmd)
                    print(cmd)
                except (RuntimeError, TypeError, NameError,FileNotFoundError) as e:
                    print(e)


def get_repos_fixed(root_dir, proj_list, id_list):
    repos_dir = root_dir + 'defects4j/'
    for i in range(len(proj_list)):
        project = proj_list[i]
        for j in id_list[i]:
            for k in j:
                unique_id = project + '_' + str(k)
                dir_name=repos_dir + unique_id + '_fixed'
                path=repos_dir+unique_id + '_fixed'
                if os.path.exists(path):
                    print("already exists: " + project + '_' + str(k))
                    continue
                try:
                    print("in processing: " + project + '_' + str(k))
                    cmd = 'defects4j checkout -p '+ project + ' -v '+ str(k) + 'f -w ' + dir_name
                    os.system(cmd)
                    print(cmd)
                except (RuntimeError, TypeError, NameError,FileNotFoundError) as e:
                    print(e)


def get_repos_buggy(root_dir, proj_list, id_list):
    repos_dir = root_dir + 'buggy/'
    for i in range(len(proj_list)):
        project = proj_list[i]
        for j in id_list[i]:
            for k in j:
                unique_id = project + '_' + str(k)
                dir_name=repos_dir + unique_id + '_buggy'
                path=repos_dir+unique_id + '_buggy'
                if os.path.exists(path):
                    print("already exists: " + project + '_' + str(k))
                    continue
                try:
                    print("in processing: " + project + '_' + str(k))
                    cmd = 'defects4j checkout -p '+ project + ' -v '+ str(k) + 'b -w ' + dir_name
                    os.system(cmd)
                    print(cmd)
                except (RuntimeError, TypeError, NameError,FileNotFoundError) as e:
                    print(e)

root_dir = '/home/data/Defects4j/checkout' + '/'
proj_list = [
            'Chart',
            'Cli',
            'Closure',
            'Codec',
            'Collections',
            'Compress',
            'Csv',
            'Gson',
            'JacksonCore',
            'JacksonDatabind',
            'JacksonXml',
            'Jsoup',
            'JxPath',
            'Lang',
            'Math',
            'Mockito',
            'Time'
            ]   
id_range = [
            '1-26',
            '1-5,7-40',
            '1-62,64-92,94-176',
            '1-18',
            '1-28',
            '1-47',
            '1-16',
            '1-18',
            '1-26',
            '1-64,66-88,90-112',
            '1-6',
            '1-93',
            '1-22',
            '1,3-17,19-24,26-47,49-65',
            '1-106',
            '1-38',
            '1-20,22-27',
            ]
id_list = []

for i in range(len(id_range)):
    range_id=parse_id_ranges(id_range[i])
    id_list.append(range_id)
    
# get_repos_fixed(root_dir, proj_list, id_list)
get_repos_buggy(root_dir, proj_list, id_list)
