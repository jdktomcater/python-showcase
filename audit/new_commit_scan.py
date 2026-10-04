import datetime

import requests
from openpyxl import Workbook


GITLAB_URL = ""
ACCESS_TOKEN = ""



USERNAME = ''
GITLAB_GROUPS_LABEL = 'TX' #

# 设置请求头
headers = {
    'Private-Token': ACCESS_TOKEN
}

API_BASE = GITLAB_URL.rstrip("/")

# 获取当前日期和前7天的日期
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=75)


def group_full_path(group):
    return group.get("full_path") or group.get("path") or group.get("name") or ""


def project_in_group(path_with_namespace, full_path):
    path = (path_with_namespace or "").strip().lower()
    prefix = (full_path or "").strip().lower()
    if not path or not prefix:
        return False
    return path == prefix or path.startswith(prefix + "/")


def is_default_target_branch(branch):
    name = (branch or "").lower()
    return "master" in name or "main" in name


def local_timezone():
    return datetime.datetime.now().astimezone().tzinfo


def parse_gitlab_time(value):
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_timezone())
    return dt.astimezone(local_timezone()).replace(tzinfo=None)


def in_export_window(value):
    dt = parse_gitlab_time(value)
    return dt is not None and start_date <= dt <= end_date


def get_groups():
    groups = []
    page = 1
    while True:
        url = f"{API_BASE}/api/v4/groups"
        response = requests.get(url, headers=headers, params={"per_page": 100, "page": page})
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        groups.extend(data)
        page += 1
    return groups


def get_projects(group_id):
    projects = []
    page = 1
    while True:
        url = f"{API_BASE}/api/v4/groups/{group_id}/projects"
        response = requests.get(
            url,
            headers=headers,
            params={
                "per_page": 100,
                "page": page,
                "include_subgroups": True,
            },
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        projects.extend(data)
        page += 1
    return projects


def get_merge_requests(project_id, start_date, end_date):
    merge_requests_url = f"{API_BASE}/api/v4/projects/{project_id}/merge_requests"
    params = {
        "updated_after": start_date.isoformat(),
        "state": "merged",
        "per_page": 100,
        "page": 1,
    }
    merge_requests = []
    while True:
        response = requests.get(merge_requests_url, headers=headers, params=params)
        response.raise_for_status()
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            print("Error: Response is not in JSON format.")
            print(response.text)
            break
        if not data:
            break
        merge_requests.extend(data)
        if len(data) < params["per_page"]:
            break
        params["page"] += 1
    return [mr for mr in merge_requests if in_export_window(mr.get("merged_at"))]


def get_merge_request_comments(project_id, mr_iid):
    notes_url = f"{API_BASE}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    response = requests.get(notes_url, headers=headers)
    response.raise_for_status()
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        print("Error: Response is not in JSON format.")
        print(response.text)
        return []


def since_param():
    return start_date.replace(tzinfo=local_timezone()).isoformat()


def is_master_branch(branch):
    return (branch or "").strip().lower() in {"master", "main"}


def is_merge_commit(commit):
    if len(commit.get("parent_ids") or []) > 1:
        return True
    title = (commit.get("title") or "").strip()
    return title.startswith("Merge branch") or title.startswith("Merge remote-tracking")


def get_master_commits(project_id):
    url = f"{API_BASE}/api/v4/projects/{project_id}/repository/commits"
    for ref in ("master", "main"):
        params = {
            "ref_name": ref,
            "first_parent": "true",
            "per_page": 100,
            "since": since_param(),
            "page": 1,
        }
        commits = []
        while True:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 404:
                break
            if response.status_code != 200:
                print(f"Failed to fetch commits project={project_id} ref={ref}: {response.status_code}")
                return []
            page_commits = response.json()
            commits.extend(page_commits)
            if len(page_commits) < params["per_page"]:
                return commits
            params["page"] += 1
    return []


def merged_to_master_by_mr(project_id, commit_id):
    url = f"{API_BASE}/api/v4/projects/{project_id}/repository/commits/{commit_id}/merge_requests"
    page = 1
    while True:
        response = requests.get(url, headers=headers, params={"per_page": 100, "page": page})
        if response.status_code != 200:
            print(f"Failed to fetch commit merge requests project={project_id} commit={commit_id}: {response.status_code}")
            return False
        merge_requests = response.json()
        for mr in merge_requests:
            if mr.get("state") == "merged" and is_master_branch(mr.get("target_branch")):
                return True
        if len(merge_requests) < 100:
            return False
        page += 1


def user_key(user):
    if not user:
        return ""
    return (user.get("username") or user.get("name") or "").strip().lower()


def mr_problems(mr, review_comments):
    reviewers = mr.get("reviewers") or []
    reviewer_keys = {user_key(reviewer) for reviewer in reviewers}
    reviewer_keys.discard("")
    problems = []
    if not reviewer_keys:
        problems.append("MR缺少Reviewer ")
    author_key = user_key(mr.get("author"))
    if author_key and author_key in reviewer_keys:
        problems.append("MR Reviewer与创建人为同一人 ")
    if not (review_comments or "").strip():
        problems.append("MR Review Comments没有处理意见")
    return problems


def scanMasterPushAndWirteInSheet(projects, group_name, group_path, sheet2):
    for project in projects:
        project_id = project["id"]
        project_name = project["name"]
        path_with_namespace = project["path_with_namespace"]
        if not project_in_group(path_with_namespace, group_path):
            continue
        namespace = project.get("namespace") or {}
        row_group = namespace.get("name") or group_name
        commits = get_master_commits(project_id)
        for commit in commits:
            if is_merge_commit(commit):
                continue
            if not in_export_window(commit.get("committed_date") or commit.get("authored_date")):
                continue
            if merged_to_master_by_mr(project_id, commit["id"]):
                continue
            result = [
                row_group, project_name, commit["id"], commit["title"],
                commit["author_name"], commit["committer_name"],
                commit["authored_date"], commit["committed_date"],
                "直接PUSH master",
            ]
            print(result)
            try:
                sheet2.append(result)
            except Exception as e:
                print("error=" + e.__str__())


def scanProjectsMrAndWirteInSheet(projects, group_name, group_path, sheet):
    for project in projects:
        project_id = project["id"]
        project_name = project["name"]
        if not project_in_group(project.get("path_with_namespace"), group_path):
            continue
        merge_requests = get_merge_requests(project_id, start_date, end_date)
        for mr in merge_requests:
            if not is_default_target_branch(mr.get("target_branch")):
                continue
            created_by = mr["author"]["name"] if mr.get("author") else "N/A"
            merged_user = mr.get("merged_by") or mr.get("merge_user")
            merged_by = merged_user["name"] if merged_user else "N/A"
            reviewers_text = " ".join([reviewer["name"] for reviewer in mr.get("reviewers") or []])
            comments = get_merge_request_comments(project_id, mr["iid"])
            review_comments = ""
            for comment in comments:
                if comment.get("system"):
                    continue
                try:
                    content = str(comment["body"]).strip()
                except Exception:
                    content = ""
                try:
                    resolved = str(comment["resolved"]).strip()
                except Exception:
                    resolved = ""
                if content:
                    origin_comment = f"{review_comments}；" if review_comments else ""
                    review_comments = f"{origin_comment}{content}(resolved: {resolved})"
            problems = mr_problems(mr, review_comments)
            if not problems:
                continue
            result = [
                group_name, project_name, mr["title"], merged_by, created_by, mr["merged_at"],
                mr["source_branch"], mr["target_branch"], reviewers_text, review_comments,
                "；".join(problems),
            ]
            print(result)
            sheet.append(result)


def export_all_merge_request():
    wb = Workbook()
    sheet = wb.active
    sheet.title = "Master Branch Merge Requests"
    sheet.append([
        "Group Name", "Project Name", "MR Title", "Merged By", "Created By", "merged_at",
        "source_branch", "target_branch", "Reviewers", "Review Comments", "问题",
    ])
    sheet2 = wb.create_sheet("Master Push Requests")
    sheet2.append([
        "Group Name", "Project Name", "Id", "Title", "author", "commiter",
        "authored_date", "committed_date", "问题",
    ])
    groups = get_groups()
    print(f"loaded groups={len(groups)} window={str(start_date)[:10]}~{str(end_date)[:10]}")
    seen_project_ids = set()
    for group in groups:
        group_name = group["name"]
        group_path = group_full_path(group)
        raw_projects = get_projects(group["id"])
        projects = []
        for project in raw_projects:
            project_id = project["id"]
            if project_id in seen_project_ids:
                continue
            if not project_in_group(project.get("path_with_namespace"), group_path):
                continue
            seen_project_ids.add(project_id)
            projects.append(project)
        print(f"group={group_path} name={group_name} projects={len(projects)}")
        scanProjectsMrAndWirteInSheet(projects, group_name, group_path, sheet)
        scanMasterPushAndWirteInSheet(projects, group_name, group_path, sheet2)
    label = globals().get("GITLAB_GROUPS_LABEL", "")
    output_filename = f"{str(start_date)[:10]}-{str(end_date)[:10]}{label}问题数据.xlsx"
    wb.save(output_filename)
    print(f"Data successfully exported to {output_filename}")


if __name__ == "__main__":
    export_all_merge_request()
