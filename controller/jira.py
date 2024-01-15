import os
import requests
from flask import Blueprint, request, jsonify
import re
from mongo import mongo_db

collection_jira_issues = mongo_db.collection_jira_issues
collection_assigned_feedback = mongo_db.collection_assigned_feedback
collection_assigned_feedback_with_tore = mongo_db.collection_assigned_feedback_with_tore

jira_issue_bp = Blueprint('jira_issue', __name__)


@jira_issue_bp.route('/get_issues_without_assigned_elements', methods=['GET'])
def get_issues_without_assigned_elements():
    unassigned_issues = []
    # find all requirements
    for issue in collection_jira_issues.find({}):
        issues = issue.get('issues', [])
        # find the requirements that are related to a feedback (standard or using TORE)
        for individual_issue in issues:
            issue_key = individual_issue.get('key')

            assigned_issue = collection_assigned_feedback.find_one({'issue_key': issue_key})
            tore_issue = collection_assigned_feedback_with_tore.find_one({'issue_key': issue_key})
            # get all requirements that are not related
            if not assigned_issue and not tore_issue:
                unassigned_issues.append(individual_issue)

    page = int(request.args.get('page', default=1))
    size = int(request.args.get('size', default=-1))

    if size == -1:
        size = len(unassigned_issues)

    start_index = (page - 1) * size
    end_index = min(start_index + size, len(unassigned_issues))
    # get all unassigned with pagination
    paginated_unassigned_issues = unassigned_issues[start_index:end_index]

    return jsonify({
        "unassigned_issues": paginated_unassigned_issues,
        "currentPage": page,
        "totalItems": len(unassigned_issues),
        "totalPages": (len(unassigned_issues) + size - 1) // size
    })


@jira_issue_bp.route('/get_unassigned_issues/<feedback_id>', methods=['GET'])
def get_unassigned_issues(feedback_id):
    # find all reqiurements that are assigned to feedback
    assigned_issues = list(collection_assigned_feedback.find({'feedback_id': feedback_id}))
    issue_keys = set(feedback['issue_key'] for feedback in assigned_issues)
    # find all requirements that are not in assigned_issues and are unassigned
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
    # find all requirements that are assinged using TORE
    assigned_issues = list(collection_assigned_feedback_with_tore.find({'feedback_id': feedback_id}))
    issue_keys = set(feedback['issue_key'] for feedback in assigned_issues)
    # find all requirements that are not assigned using TORE
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
    # find all requirements of the chosen project
    issue_keys = [issue['key'] for project in collection_jira_issues.find({'projectName': project_name})
                  for issue in project.get('issues', []) if 'key' in issue]
    # delete all assignments of the requirements
    collection_assigned_feedback.delete_many({'issue_key': {'$in': issue_keys}})
    collection_assigned_feedback_with_tore.delete_many({'issue_key': {'$in': issue_keys}})
    # delete the project name
    result = collection_jira_issues.delete_one({'projectName': project_name})
    if result.deleted_count > 0:
        return jsonify({'message': 'Project deleted successfully'})
    else:
        return jsonify({'message': 'Project not found or could not be deleted'})


@jira_issue_bp.route('/delete_issue/<project_name>/<key>', methods=['DELETE'])
def delete_issue(project_name, key):
    # delete all assigned elements that are assigned to the chosen requirement
    collection_assigned_feedback.delete_many({'issue_key': key})
    collection_assigned_feedback_with_tore.delete_many({'issue_key': key})
    # find the requirement through the project name
    projects = collection_jira_issues.find({'projectName': project_name})
    for project in projects:
        issues = project.get('issues', [])
        # delete the requirement
        updated_issues = [issue for issue in issues if issue['key'] != key]
        if not updated_issues:
            collection_jira_issues.delete_one({'_id': project['_id']})
        else:
            collection_jira_issues.update_one({'_id': project['_id']}, {'$set': {'issues': updated_issues}})
    return jsonify({'message': 'Deleted element'})


@jira_issue_bp.route('/get_assigned_issues/<feedback_id>', methods=['GET'])
def get_assigned_issues(feedback_id):
    # find all requiements that are assigned to feedback and sort them
    assigned_issues = list(collection_assigned_feedback.find({'feedback_id': feedback_id}))
    assigned_issues = sorted(assigned_issues, key=lambda x: x.get('similarity', 0), reverse=True)
    issue_keys = [issue['issue_key'] for issue in assigned_issues]
    project_names = set(issue['project_name'] for issue in assigned_issues)
    related_issues = []
    # iterate through all requirements by project name
    for project_name in project_names:
        project = collection_jira_issues.find_one({'projectName': project_name})
        if project:
            issues_in_project = project.get('issues', [])

            for issue in issues_in_project:
                if issue['key'] in issue_keys:
                    # find the assigned requirements for the chosen feedback
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
    # sort the requirements for pagination
    sorted_issues = sorted(related_issues,
                           key=lambda x: float(x["similarity"]) if x["similarity"].replace('.', '',
                                                                                           1).isdigit() else float(
                               'inf'), reverse=True)

    page = int(request.args.get('page', default=1))
    size = int(request.args.get('size', default=-1))

    if size == -1:
        size = len(sorted_issues)

    start_index = (page - 1) * size
    end_index = min(start_index + size, len(sorted_issues))

    paginated_related_issues = sorted_issues[start_index:end_index]

    response = {
        "related_issues": paginated_related_issues,
        "currentPage": page,
        "totalItems": len(sorted_issues),
        "totalPages": (len(sorted_issues) + size - 1) // size
    }

    return jsonify(response)


@jira_issue_bp.route('/get_tore_assigned_issues/<feedback_id>', methods=['GET'])
def get_tore_assigned_issues(feedback_id):
    # find all requiements that are assigned to feedback through TORE and sort them
    assigned_issues = list(collection_assigned_feedback_with_tore.find({'feedback_id': feedback_id}))
    assigned_issues = sorted(assigned_issues, key=lambda x: x.get('similarity', 0), reverse=True)
    issue_keys = [issue['issue_key'] for issue in assigned_issues]
    project_names = set(issue['project_name'] for issue in assigned_issues)
    related_issues = []
    # iterate through all requirements by project name
    for project_name in project_names:
        project = collection_jira_issues.find_one({'projectName': project_name})
        if project:
            issues_in_project = project.get('issues', [])

            for issue in issues_in_project:
                if issue['key'] in issue_keys:
                    # find the assigned requirements for the chosen feedback
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
    sorted_issues = sorted(related_issues,
                           key=lambda x: float(x["similarity"]) if x["similarity"].replace('.', '',
                                                                                           1).isdigit() else float(
                               'inf'), reverse=True)
    page = int(request.args.get('page', default=1))
    size = int(request.args.get('size', default=-1))

    if size == -1:
        size = len(sorted_issues)

    start_index = (page - 1) * size
    end_index = min(start_index + size, len(sorted_issues))

    paginated_related_issues = sorted_issues[start_index:end_index]

    response = {
        "related_issues": paginated_related_issues,
        "currentPage": page,
        "totalItems": len(sorted_issues),
        "totalPages": (len(sorted_issues) + size - 1) // size
    }

    return jsonify(response)


@jira_issue_bp.route("/remove_all_issues", methods=["DELETE"])
def remove_all_issues():
    # delete all requirements and the assignments
    collection_assigned_feedback.delete_many({})
    collection_assigned_feedback_with_tore.delete_many({})
    collection_jira_issues.delete_many({})
    return jsonify({"message": "removed successfully"})


@jira_issue_bp.route("/add", methods=["POST"])
def add_jira_issues():
    data = request.json
    new_issues = data.get("jsonObject", [])
    # iterate through all requirements
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
        # check if the requirement is already in list
        already_used = any(jira_issue["key"] == key for jira_issue in existing_issues)
        # if requirement is in list, then do not add it
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
        # find all requirements to show in table
        all_issues = []
        for issues_array in collection:
            # if the requirements of a project are not selected, then do not show them
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

        return jsonify(res)
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500


@jira_issue_bp.route("/issues_to_assign", methods=["POST"])
def activate_projects():
    data = request.get_json()
    selected_projects = data.get('selectedProjects')
    # set all requirement projects to false
    collection_jira_issues.update_many(
        {},
        {"$set": {"selectedToAssign": False}}
    )
    # set all projects to true, that are selected
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
    # get all added project names
    jira_projects = list(collection_jira_issues.find({}))
    for element in jira_projects:
        element["_id"] = str(element["_id"])
    return jira_projects


@jira_issue_bp.route("/load/issueTypes/<project_name>", methods=["GET"])
def load_issue_types_from_jira_issues(project_name):
    issue_types = []
    try:
        # get the requirement types from jira for the chosen project
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
            # get list of all types
            issue_type = response_json["issues"][i]["fields"]["issuetype"]["name"]
            if issue_type not in issue_types:
                issue_types.append(issue_type)
    except Exception as e:
        return e
    return issue_types


@jira_issue_bp.route("/load/issues/<project_name>", methods=["POST"])
def load_issues_from_project(project_name):
    data = request.json
    list = []
    issue_types = [item["item"] for item in data["jsonObject"]]
    # get all requirements from jira by project name and requirement types
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
            extracted_text = re.sub(r'\r\n|\r|\n', ' ', extracted_text)
            issue_type = response_json["issues"][i]["fields"]["issuetype"]["name"]
            project_name = response_json["issues"][i]["fields"]["project"]["name"]
            summary = response_json["issues"][i]["fields"]["summary"]
            summary = re.sub(r'^[^:]+:', '', summary)
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
        # get all project names from jira
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
        return e

    return project_names
