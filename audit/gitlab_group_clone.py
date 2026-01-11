import os
import subprocess
import requests

# ======= 配置 =======
GITLAB_URL = ""  # 你的 GitLab 地址
GROUP_ID = ""  # 可以是组名或组 ID
PRIVATE_TOKEN = ""  # GitLab 个人访问令牌
USE_SSH = False  # True 用 SSH URL, False 用 HTTPS URL
CLONE_DIR = "E:/workspace/cursor"  # 克隆到本地的目录


# ======= 获取所有群组 =======
def get_all_group():
    groups = []
    page = 1
    per_page = 10
    while True:
        url = f"{GITLAB_URL}/api/v4/groups"
        params = {
            "page": page,
            "per_page": per_page,
            "all_available": "true",
            "order_by": "id",
            "sort": "asc"
        }
        headers = {"PRIVATE-TOKEN": PRIVATE_TOKEN}
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        groups.extend(data)
        page += 1
    return groups


# ======= 获取所有项目 =======
def get_all_projects():
    page = 1
    per_page = 100
    projects = []
    while True:
        url = f"{GITLAB_URL}/api/v4/groups/{GROUP_ID}/projects"
        params = {
            "page": page,
            "per_page": per_page,
            "include_subgroups": "true",
            "order_by": "id",
            "sort": "asc",
            "simple": "true"
        }
        headers = {"PRIVATE-TOKEN": PRIVATE_TOKEN}
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        projects.extend(data)
        page += 1
    return projects


# ======= 获取所有项目 =======
def get_group_projects(group):
    page = 1
    per_page = 100
    group_projects = []
    group_id = group["id"]
    group_name = group["name"]
    os.makedirs(CLONE_DIR+"/"+group_name, exist_ok=True)
    while True:
        url = f"{GITLAB_URL}/api/v4/groups/{group_id}/projects"
        params = {
            "page": page,
            "per_page": per_page,
            "include_subgroups": "true",
            "order_by": "id",
            "sort": "asc",
            "simple": "true"
        }
        headers = {"PRIVATE-TOKEN": PRIVATE_TOKEN}
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        group_projects.extend(data)
        page += 1
    return group_projects


# ======= 克隆项目 =======
def clone_projects(projects):
    for proj in projects:
        repo_url = proj["ssh_url_to_repo"] if USE_SSH else proj["http_url_to_repo"]
        dest_path = os.path.join(CLONE_DIR, proj["path"])
        if os.path.exists(dest_path):
            print(f"[跳过] {proj['name']} 已存在")
            continue

        print(f"[克隆] {proj['name']} -> {repo_url}")
        subprocess.run(["git", "clone", repo_url, dest_path], check=True)


# ======= 克隆项目 =======
def clone_group_projects(group, projects):
    group_name = group["name"]
    for proj in projects:
        repo_url = proj["ssh_url_to_repo"] if USE_SSH else proj["http_url_to_repo"]
        dest_path = os.path.join(CLONE_DIR+"/"+group_name, proj["path"])
        if os.path.exists(dest_path):
            print(f"[跳过] {proj['name']} 已存在")
            continue

        print(f"[克隆] {proj['name']} -> {repo_url}")
        subprocess.run(["git", "clone", repo_url, dest_path], check=True)

if __name__ == "__main__":
    groups = get_all_group()
    for group in groups:
        projects = get_group_projects(group)
        print(f"共获取到 {len(projects)} 个项目")
        clone_group_projects(group,projects)

