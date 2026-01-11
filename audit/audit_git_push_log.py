import datetime

import requests
from openpyxl import Workbook
from requests import HTTPError

# Configuration
# Replace with your GitLab instance URL
GITLAB_URL = ""
# all
ACCESS_TOKEN = ''

GITLAB_GROUPS_LABEL = '支付平台'
USERNAME = 'jstimmy'

# 设置请求头
headers = {
    'Private-Token': ACCESS_TOKEN
}

# 获取当前日期和前7天的日期
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=7)


# 获取用户的所有组
def get_groups():
    groups = []
    page = 1
    while True:
        url = f"{GITLAB_URL}/api/v4/groups?per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        groups.extend(data)
        page += 1
    return groups


# 获取组中的所有项目
def get_projects():
    projects = []
    page = 1
    while True:
        url = GITLAB_URL +'/api/v4/projects?merbership=true&per_page=100&simple=true&order_by=id&page='+str(page)
        payload = {}
        try:
            response = requests.request("GET", url, headers=headers, data=payload)
            response.raise_for_status()
            data = response.json()
            page += 1
            if response.status_code == 200 and data:
                print("project:"+str(data))
                projects.extend(data)
            else:
                break
        except HTTPError as http_err:
            print("群组处理异常："+str(http_err))
            page += 1
            continue
    return projects


# 获取项目中从特定日期范围内的merge requests
def get_merge_requests(project_id, start_date, end_date):
    merge_requests_url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests"
    params = {
        'created_after': start_date.isoformat(),
        'created_before': end_date.isoformat(),
        'state': 'merged'
    }
    response = requests.get(merge_requests_url, headers=headers, params=params)
    response.raise_for_status()
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        print("Error: Response is not in JSON format.")
        print(response.text)
        return []


def get_all_push(PROJECT_ID):
    one_week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    since_date = one_week_ago.isoformat()
    url = f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/repository/commits"
    # 参数设置，支持分页
    params = {
        "ref_name": "master",
        "per_page": 100,  # 每页最大记录数
        "since": since_date,
        "page": 1  # 初始页码
    }

    # 循环获取所有页面的提交记录
    all_commits = []
    while True:
        response = requests.get(url, headers=headers, params=params)

        # 检查请求是否成功
        if response.status_code != 200:
            print(f"Failed to fetch commits: {response.status_code}")
            break

        # 获取当前页的提交数据
        commits = response.json()
        all_commits.extend(commits)

        # 如果本页数据少于设定值，说明已到最后一页
        if len(commits) < params["per_page"]:
            break
        # 否则，继续获取下一页
        params["page"] += 1

    return all_commits


# 获取merge request的review comments
def get_merge_request_comments(project_id, mr_iid):
    notes_url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    response = requests.get(notes_url, headers=headers)
    response.raise_for_status()
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        print("Error: Response is not in JSON format.")
        print(response.text)
        return []


def scanMasterPushAndWirteInSheet(projects, sheet2):
    for project in projects:
        project_id = project['id']
        project_name = project['name']
        path_with_namespace = project['path_with_namespace']
        group_name = project['namespace']['name']
        if path_with_namespace.lower().startswith(group_name.lower()):
            commits = get_all_push(project_id)
            for commit in commits:
                # 检查每个提交是否与 Merge Request 关联
                commit_url = f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits/{commit['id']}/merge_requests"
                mr_response = requests.get(commit_url, headers=headers)

                # 如果没有关联的 Merge Request，说明是直接 push 的提交
                if mr_response.status_code == 200 and not mr_response.json():
                    title = commit['title']
                    id = commit['id']
                    author_name = commit['author_name']
                    authored_date = commit['authored_date']
                    committer_name = commit['committer_name']
                    committed_date = commit['committed_date']

                    result = [group_name, project_name, id, title, author_name, committer_name, authored_date,
                              committed_date]
                    print(result)
                    try:
                        sheet2.append(result)
                    except Exception as e:
                        print('error=' + e.__str__())


def scanProjectsMrAndWirteInSheet(projects, sheet):
    for project in projects:
        project_id = project['id']
        project_name = project['name']
        group_name = project['namespace']['name']
        print("处理中， group_name:"+group_name+" project_name:"+project_name)
        if project['path_with_namespace'].startswith(group_name):
            # 获取merge requests
            merge_requests = get_merge_requests(project_id, start_date, end_date)
            for mr in merge_requests:
                target_branch = mr['target_branch']
                if target_branch.__contains__("master"):
                    mr_title = mr['title']
                    created_by = mr['author']['name'] if 'author' in mr and mr['author'] else 'N/A'
                    merged_by = mr['merged_by']['name'] if 'merged_by' in mr and mr['merged_by'] else 'N/A'
                    merged_at = mr['merged_at']

                    source_branch = mr['source_branch']
                    reviewers_text = ' '.join(
                        [reviewer['name'] for reviewer in mr['reviewers']])
                    # 获取每个merge request的comments
                    comments = get_merge_request_comments(project_id, mr['iid'])
                    review_comments = ""
                    for comment in comments:
                        resolved = ""
                        content = ""
                        if not comment['system']:
                            try:
                                content = str(comment['body']).strip()
                            except:
                                pass
                            try:
                                resolved = str(comment['resolved']).strip()
                            except:
                                pass
                        if len(content) > 0:
                            origin_comment = f'{review_comments}；' if len(review_comments)>0 else ''
                            review_comments =  f'{origin_comment}{content}(resolved: {resolved})'
                    result = [group_name, project_name, mr_title, merged_by, created_by, merged_at, source_branch,
                              target_branch,
                              reviewers_text, review_comments]
                    print(result)
                    sheet.append(result)


def export_all_merge_request():
    # 创建Excel工作簿
    wb = Workbook()
    sheet = wb.active
    sheet.title = 'Master Branch Merge Requests'
    sheet.append(["Group Name", "Project Name", "MR Title", "Merged By", "Created By", 'merged_at', 'source_branch',
                  'target_branch', "Reviewers", "Review Comments"])

    sheet2 = wb.create_sheet("Master Push Requests")
    sheet2.append(
        ["Group Name", "Project Name", "Id", "Title", "author", "commiter", 'authored_date', 'committed_date'])
    # 获取所有相关项目列表
    projects = get_projects()
    scanProjectsMrAndWirteInSheet(projects, sheet)
    scanMasterPushAndWirteInSheet(projects, sheet2)

    # 保存Excel文件
    output_filename = f'{str(start_date)[:10]}-{str(end_date)[:10]}{GITLAB_GROUPS_LABEL}代码commit记录.xlsx'
    wb.save(output_filename)
    print(f"Data successfully exported to {output_filename}")


def test():
    groups = get_groups()
    group_id = groups[0]['id']
    group_name = groups[0]['name']
    print("group_id：" + str(group_id) + "--group_name:" + str(group_name))
    projects = get_projects(group_id)
    # scanMasterPushAndWirteInSheet(projects, group_name)
    for project in projects:
        project_id = project['id']
        project_name = project['name']
        print("project_id：" + str(project_id) + "--project_name:" + str(project_name))
        # 获取merge requests
        merge_requests = get_merge_requests(project_id, start_date, end_date)
        for mr in merge_requests:
            print(mr)
            # mr_title = mr['title']
            # merged_by = mr['merged_by']['name'] if 'merged_by' in mr and mr['merged_by'] else 'N/A'
            #
            # # 获取每个merge request的comments
            comments = get_merge_request_comments(project_id, mr['iid'])
            print(comments)
            # review_comments = '\n'.join(
            #     [note['body'] for note in comments])
            # print(review_comments)


export_all_merge_request()
#print(start_date)