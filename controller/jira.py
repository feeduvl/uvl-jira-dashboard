import os
# from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
# import torch
import requests
from flask import Blueprint, request, jsonify
from pymongo import MongoClient

jira_issue_bp = Blueprint('jira_issue', __name__)

client = MongoClient("mongodb://mongo:27017/")
dbIssues = client["jira-issues"]
collectionJiraProjects = dbIssues["jiraProject"]
collectionJiraIssues = dbIssues["jiraIssue"]


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
            issue_type = response_json["issues"][i]["fields"]["issuetype"]["name"]
            project_name = response_json["issues"][i]["fields"]["project"]["name"]
            summary = response_json["issues"][i]["fields"]["summary"]
            issue = {"key": issue_key, "issueType": issue_type, "projectName": project_name, "summary": summary}
            list.append(issue)

    return jsonify(list)


@jira_issue_bp.route("/import", methods=["POST"])
def import_jira_issues():
    data = request.json
    collectionJiraIssues.delete_many({})
    saved_issues = []

    for item in data["jsonObject"]:
        key = item["key"]
        project_name = item["projectName"]
        issue_type = item["issueType"]
        summary = item["summary"]
        jira_issue = {
            "key": key,
            "issueType": issue_type,
            "projectName": project_name,
            "summary": summary
        }
        saved_issue = collectionJiraIssues.insert_one(jira_issue)
        saved_issue_info = {
            "inserted_id": str(saved_issue.inserted_id),
            "key": key,
            "issueType": issue_type,
            "projectName": project_name,
            "summary": summary
        }
        saved_issues.append(saved_issue_info)

    return jsonify(saved_issues)


@jira_issue_bp.route("/add", methods=["POST"])
def add_jira_issues():
    data = request.json
    saved_issues = list(collectionJiraIssues.find({}))

    for item in data["jsonObject"]:
        key = item["key"]
        project_name = item["projectName"]
        issue_type = item["issueType"]
        summary = item["summary"]
        jira_issue = {
            "key": key,
            "issueType": issue_type,
            "projectName": project_name,
            "summary": summary
        }
        already_used = any(jira_issue["key"] == key for jira_issue in saved_issues)
        if not already_used:
            collectionJiraIssues.insert_one(jira_issue)

    updated_issues = list(collectionJiraIssues.find({}))
    for element in updated_issues:
        element["_id"] = str(element["_id"])

    return jsonify(updated_issues)


@jira_issue_bp.route("/all", methods=["GET"])
def get_all_jira_issues_from_db():
    try:
        page = int(request.args.get("page", default=1))
        size = int(request.args.get("size", default=-1))

        if size == -1:
            size = collectionJiraIssues.count_documents({})

        skip = (page - 1) * size
        cursor = collectionJiraIssues.find().skip(skip).limit(size)

        issues = list(cursor)
        for issue in issues:
            issue["_id"] = str(issue["_id"])
        if issues:
            total_items = collectionJiraIssues.count_documents({})
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


@jira_issue_bp.route("/projectNames", methods=["GET"])
def get_all_project_names():
    project_names = list(collectionJiraProjects.find({}))
    for element in project_names:
        element["_id"] = str(element["_id"])
    return project_names


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
        set_new_project_names(response_json["issues"][0]["fields"]["project"]["name"])
        total_issues = int(response_json.get("total", 0))

        print("ist drin")
        for i in range(total_issues):
            issue_type = response_json["issues"][i]["fields"]["issuetype"]["name"]
            if issue_type not in issue_types:
                issue_types.append(issue_type)
    except Exception as e:
        pass

    return issue_types


def set_new_project_names(project_name):
    filter_query = {"name": project_name}
    # matching_elements = list(collectionJiraProjects.find(filter_query))

    if list(collectionJiraProjects.find(filter_query)):
        return jsonify({"message": "Einträge mit dem Namen 'test' gefunden."})
    else:
        collectionJiraProjects.insert_one(filter_query)
