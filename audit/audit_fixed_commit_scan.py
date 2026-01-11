import datetime

import requests
from openpyxl import Workbook
from requests import HTTPError

# Configuration
# Replace with your GitLab instance URL
GITLAB_URL = ""

# all
ACCESS_TOKEN = ''

GITLAB_GROUPS_LABEL = ''

AUDIT_MESSAGE_LABEL = ""

FILTER_MESSAGE_LABEL= "Merge branch"

# 设置请求头
headers = {
    'Private-Token': ACCESS_TOKEN
}

# 获取当前日期和前7天的日期
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=365)

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
                projects.extend(data)
            else:
                break
        except HTTPError as http_err:
            print("群组处理异常："+str(http_err))
            page += 1
            continue
    return projects

# 获取项目所有提交记录
def get_all_commits(project_id):
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits"
    # 参数设置，支持分页
    params = {
        "ref_name": "master",
        "per_page": 100,  # 每页最大记录数
        "since": start_date,
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

# 审计提交扫描
def audit_commit_scan(projects, sheet):
    for project in projects:
        project_id = project['id']
        project_name = project['name']
        path_with_namespace = project['path_with_namespace']
        group_name = project['namespace']['name']
        if path_with_namespace.lower().startswith(group_name.lower()):
            commits = get_all_commits(project_id)
            for commit in commits:
                message = commit['message']
                if AUDIT_MESSAGE_LABEL in message and FILTER_MESSAGE_LABEL not in message:
                    result = [group_name, project_name, commit['id'], commit['title'], commit['author_name'], commit['committer_name'], commit['authored_date'], commit['committed_date']]
                    try:
                        sheet.append(result)
                    except Exception as e:
                        print('error=' + e.__str__())

# 导出所有审计信息
def export_all_audit():
    # 创建Excel工作簿
    wb = Workbook()

    # 获取所有相关项目列表
    projects = get_projects()
    sheet = wb.active
    sheet.title = '安全审计提交记录'
    sheet.append(["组名", "项目名称", "提交ID", "提交信息", "创作者", "提交者", '创建日期', '提交日期'])
    audit_commit_scan(projects, sheet)
    # 保存Excel文件
    output_filename = f'{str(start_date)[:10]}-{str(end_date)[:10]}{GITLAB_GROUPS_LABEL}安全审计提交commit记录.xlsx1'
    wb.save(output_filename)
    print(f"Data successfully exported to {output_filename}")

export_all_audit()
