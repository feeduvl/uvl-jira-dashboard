import os
import requests
from flask import Blueprint, request, jsonify
from pymongo import MongoClient
import re

jira_issue_bp = Blueprint('jira_issue', __name__)

client = MongoClient("mongodb://mongo:27017/")
dbIssues = client["jira_dashboard"]
collection_jira_issues = dbIssues["jira_issue"]
collection_assigned_feedback = dbIssues["assigned_feedback"]
collection_assigned_feedback_with_tore = dbIssues["assigned_feedback_with_tore"]


@jira_issue_bp.route('/get_unassigned_issues/<feedback_id>', methods=['GET'])
def get_unassigned_issues(feedback_id):
    assigned_issues = list(collection_assigned_feedback.find({'feedback_id': feedback_id}))

    issue_keys = set(feedback['issue_key'] for feedback in assigned_issues)

    missing_issues = []
    for jira_entry in collection_jira_issues.find({}):
        for issue in jira_entry.get('issues', []):
            if issue['key'] not in issue_keys:
                missing_issues.append(issue)

    page = int(request.args.get('page', default=1))
    size = int(request.args.get('size', default=-1))

    if size == -1:
        size = len(missing_issues)

    start_index = (page - 1) * size
    end_index = min(start_index + size, len(missing_issues))

    paginated_missing_issues = missing_issues[start_index:end_index]

    response = {
        "missing_issues": paginated_missing_issues,
        "currentPage": page,
        "totalItems": len(missing_issues),
        "totalPages": (len(missing_issues) + size - 1) // size
    }

    return jsonify(response)


@jira_issue_bp.route('/get_tore_unassigned_issues/<feedback_id>', methods=['GET'])
def get_tore_unassigned_issues(feedback_id):
    assigned_issues = list(collection_assigned_feedback_with_tore.find({'feedback_id': feedback_id}))

    issue_keys = set(feedback['issue_key'] for feedback in assigned_issues)

    missing_issues = []
    for jira_entry in collection_jira_issues.find({}):
        for issue in jira_entry.get('issues', []):
            if issue['key'] not in issue_keys:
                missing_issues.append(issue)

    page = int(request.args.get('page', default=1))
    size = int(request.args.get('size', default=-1))

    if size == -1:
        size = len(missing_issues)

    start_index = (page - 1) * size
    end_index = min(start_index + size, len(missing_issues))

    paginated_missing_issues = missing_issues[start_index:end_index]

    response = {
        "missing_issues": paginated_missing_issues,
        "currentPage": page,
        "totalItems": len(missing_issues),
        "totalPages": (len(missing_issues) + size - 1) // size
    }

    return jsonify(response)


@jira_issue_bp.route('/delete_project/<project_name>', methods=['DELETE'])
def delete_project(project_name):
    issue_keys = [issue['key'] for project in collection_jira_issues.find({'projectName': project_name})
                  for issue in project.get('issues', []) if 'key' in issue]
    collection_assigned_feedback.delete_many({'issue_key': {'$in': issue_keys}})
    collection_assigned_feedback_with_tore.delete_many({'issue_key': {'$in': issue_keys}})
    result = collection_jira_issues.delete_one({'projectName': project_name})
    if result.deleted_count > 0:
        return jsonify({'message': 'Project deleted successfully'})
    else:
        return jsonify({'message': 'Project not found or could not be deleted'})


@jira_issue_bp.route('/delete_issue/<project_name>/<key>', methods=['DELETE'])
def delete_issue(project_name, key):
    collection_assigned_feedback.delete_many({'issue_key': key})
    collection_assigned_feedback_with_tore.delete_many({'issue_key': key})

    projects = collection_jira_issues.find({'projectName': project_name})

    for project in projects:
        issues = project.get('issues', [])

        updated_issues = [issue for issue in issues if issue['key'] != key]

        if not updated_issues:
            collection_jira_issues.delete_one({'_id': project['_id']})
        else:
            collection_jira_issues.update_one({'_id': project['_id']}, {'$set': {'issues': updated_issues}})

    return jsonify({'message': 'Deleted element'})


@jira_issue_bp.route('/get_assigned_issues/<feedback_id>', methods=['GET'])
def get_assigned_issues(feedback_id):
    assigned_issues = list(collection_assigned_feedback.find({'feedback_id': feedback_id}))
    issue_keys = [issue['issue_key'] for issue in assigned_issues]
    project_names = set(issue['project_name'] for issue in assigned_issues)
    related_issues = []
    for project_name in project_names:
        project = collection_jira_issues.find_one({'projectName': project_name})
        if project:
            issues_in_project = project.get('issues', [])

            for issue in issues_in_project:
                if issue['key'] in issue_keys:
                    matching_assigned_feedback = next((af for af in assigned_issues if af['issue_key'] == issue['key']),
                                                      None)

                    if matching_assigned_feedback:
                        similarity = matching_assigned_feedback.get('similarity')
                    else:
                        similarity = None

                    related_issue = {
                        'key': issue['key'],
                        'summary': issue['summary'],
                        'description': issue['description'],
                        'similarity': similarity
                    }

                    related_issues.append(related_issue)

    page = int(request.args.get('page', default=1))
    size = int(request.args.get('size', default=-1))

    if size == -1:
        size = len(related_issues)

    start_index = (page - 1) * size
    end_index = min(start_index + size, len(related_issues))

    paginated_related_issues = related_issues[start_index:end_index]

    response = {
        "related_issues": paginated_related_issues,
        "currentPage": page,
        "totalItems": len(related_issues),
        "totalPages": (len(related_issues) + size - 1) // size
    }

    return jsonify(response)


@jira_issue_bp.route('/get_tore_assigned_issues/<feedback_id>', methods=['GET'])
def get_tore_assigned_issues(feedback_id):
    assigned_issues = list(collection_assigned_feedback_with_tore.find({'feedback_id': feedback_id}))
    issue_keys = [issue['issue_key'] for issue in assigned_issues]
    project_names = set(issue['project_name'] for issue in assigned_issues)
    related_issues = []
    for project_name in project_names:
        project = collection_jira_issues.find_one({'projectName': project_name})
        if project:
            issues_in_project = project.get('issues', [])

            for issue in issues_in_project:
                if issue['key'] in issue_keys:
                    matching_assigned_feedback = next((af for af in assigned_issues if af['issue_key'] == issue['key']),
                                                      None)

                    if matching_assigned_feedback:
                        similarity = matching_assigned_feedback.get('similarity')
                    else:
                        similarity = None

                    related_issue = {
                        'key': issue['key'],
                        'summary': issue['summary'],
                        'description': issue['description'],
                        'similarity': similarity
                    }

                    related_issues.append(related_issue)

    page = int(request.args.get('page', default=1))
    size = int(request.args.get('size', default=-1))

    if size == -1:
        size = len(related_issues)

    start_index = (page - 1) * size
    end_index = min(start_index + size, len(related_issues))

    paginated_related_issues = related_issues[start_index:end_index]

    response = {
        "related_issues": paginated_related_issues,
        "currentPage": page,
        "totalItems": len(related_issues),
        "totalPages": (len(related_issues) + size - 1) // size
    }

    return jsonify(response)


@jira_issue_bp.route("/remove_all_issues", methods=["DELETE"])
def remove_all_issues():
    collection_assigned_feedback.delete_many({})
    collection_assigned_feedback_with_tore.delete_many({})
    collection_jira_issues.delete_many({})
    return jsonify({"message": "removed successfully"})


@jira_issue_bp.route("/add", methods=["POST"])
def add_jira_issues():
    data = request.json
    new_issues = data.get("jsonObject", [])

    for item in new_issues:
        project_name = item.get("projectName")
        existing_issues_element = collection_jira_issues.find_one({"projectName": project_name})

        if existing_issues_element:
            existing_issues = existing_issues_element.get("issues", [])
        else:
            existing_issues = []

        key = item.get("key")
        issue_type = item.get("issueType")
        summary = item.get("summary")
        description = item.get("description")

        already_used = any(jira_issue["key"] == key for jira_issue in existing_issues)

        if not already_used:
            new_issue = {
                "key": key,
                "issueType": issue_type,
                "projectName": project_name,
                "summary": summary,
                "description": description
            }
            existing_issues.append(new_issue)

        collection_jira_issues.update_one(
            {"projectName": project_name},
            {"$set": {"issues": existing_issues, "selectedToAssign": True}},
            upsert=True
        )
    return jsonify({"message": "updated successfully"})


@jira_issue_bp.route("/all", methods=["GET"])
def get_all_jira_issues_from_db():
    try:
        page = int(request.args.get("page", default=1))
        size = int(request.args.get("size", default=-1))
        collection = collection_jira_issues.find({})

        all_issues = []
        for issues_array in collection:
            is_selected = issues_array.get("selectedToAssign")
            if is_selected:
                issues = issues_array.get("issues", [])
                for issue in issues:
                    all_issues.append(issue)

        if size == -1:
            size = len(all_issues)

        skip = (page - 1) * size
        cursor = all_issues[skip:skip + size]
        issues = list(cursor)
        if issues:
            total_items = len(all_issues)
            total_pages = (total_items + size - 1) // size
            res = {
                "issues": issues,
                "currentPage": page,
                "totalItems": total_items,
                "totalPages": total_pages
            }
        else:
            res = {
                "issues": issues,
                "currentPage": page,
                "totalItems": 0,
                "totalPages": 0
            }

        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500


@jira_issue_bp.route("/issues_to_assign", methods=["POST"])
def activate_projects():
    data = request.get_json()
    selected_projects = data.get('selectedProjects')
    collection_jira_issues.update_many(
        {},
        {"$set": {"selectedToAssign": False}}
    )
    matching_issues = collection_jira_issues.find({'projectName': {'$in': selected_projects}})
    for issue_element in matching_issues:
        if not issue_element.get("selectedToAssign", False):
            collection_jira_issues.update_one(
                {"_id": issue_element["_id"]},
                {"$set": {"selectedToAssign": True}}
            )

    return jsonify({"message": "activated project"})


@jira_issue_bp.route("/projectNames", methods=["GET"])
def get_all_project_names():
    jira_projects = list(collection_jira_issues.find({}))
    for element in jira_projects:
        element["_id"] = str(element["_id"])
    return jira_projects


@jira_issue_bp.route("/load/issueTypes/<project_name>", methods=["GET"])
def load_issue_types_from_jira_issues(project_name):
    issue_types = []

    try:
        base_url = "https://jira-se.ifi.uni-heidelberg.de"
        uri = f"{base_url}/rest/api/2/search?jql=project={project_name}&maxResults=10000"

        response = requests.get(
            uri,
            auth=(os.environ.get('USERNAME'), os.environ.get('PASSWORD')),
            headers={"Accept": "application/json"}
        )
        response_json = response.json()
        total_issues = int(response_json.get("total", 0))
        for i in range(total_issues):
            issue_type = response_json["issues"][i]["fields"]["issuetype"]["name"]
            if issue_type not in issue_types:
                issue_types.append(issue_type)
    except Exception as e:
        pass

    return issue_types


@jira_issue_bp.route("/load/issues/<project_name>", methods=["POST"])
def load_issues_from_project(project_name):
    data = request.json
    list = []

    issue_types = [item["item"] for item in data["jsonObject"]]

    for issue_type in issue_types:
        uri = f"https://jira-se.ifi.uni-heidelberg.de/rest/api/2/search?jql=project={project_name} AND issuetype='{issue_type}'&maxResults=520"
        response = requests.get(
            uri,
            auth=(os.environ.get('USERNAME'), os.environ.get('PASSWORD')),
            headers={"Accept": "application/json"}
        )

        response_json = response.json()
        total_issues = int(response_json.get("total", 0))

        for i in range(total_issues):
            issue_key = response_json["issues"][i]["key"]
            description = response_json["issues"][i]["fields"]["description"]
            if not isinstance(description, str):
                description = str(description)
            extracted_text = re.sub(r'\{[^}]*}', '', description)
            extracted_text = re.sub(r'\*|\|', '', extracted_text)
            extracted_text = re.sub(r'\r\n|\r|\n', ' ', extracted_text)
            issue_type = response_json["issues"][i]["fields"]["issuetype"]["name"]
            project_name = response_json["issues"][i]["fields"]["project"]["name"]
            summary = response_json["issues"][i]["fields"]["summary"]
            issue = {
                "key": issue_key,
                "description": extracted_text,
                "issueType": issue_type,
                "projectName": project_name,
                "summary": summary}
            list.append(issue)

    return jsonify(list)


@jira_issue_bp.route("/get_all_jira_projects", methods=["GET"])
def get_all_jira_projects():
    project_names = []
    try:
        uri = "https://jira-se.ifi.uni-heidelberg.de/rest/api/2/project"
        response = requests.get(
            uri,
            auth=(os.environ.get('USERNAME'), os.environ.get('PASSWORD')),
            headers={"Accept": "application/json"}
        )

        response_json = response.json()

        for project in response_json:
            project_name = project["key"]
            project_names.append(project_name)

    except Exception as e:
        pass

    return project_names
