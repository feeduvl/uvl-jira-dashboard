import os
# from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
# import torch
import requests
from flask import Flask, request, jsonify, Blueprint
from pymongo import MongoClient

feedback_bp = Blueprint('feedback', __name__)

client = MongoClient("mongodb://mongo:27017/")
dbIssues = client["jira-issues"]
dbFeedback = client["concepts_data"]
collectionJiraIssues = dbIssues["jiraIssue"]
collectionFeedback = dbFeedback["dataset"]
collectionAnnotations = dbFeedback["annotation"]
collectionFeedbackWithToreCategories = dbIssues["feedback_with_tore"]


@feedback_bp.route('/assign_feedback_to_issues', methods=['POST'])
def assign_feedback_to_issues():
    print("test")
    print(os.environ.get('PASSWORD'))
    return "HALLO " + os.environ.get('USERNAME')


@feedback_bp.route('/assign_feedback_to_issues_by_tore', methods=['POST'])
def assign_feedback_to_issues_by_tore():
    feedback_collection = list(collectionFeedbackWithToreCategories.find({}))
    jira_issues = collectionJiraIssues.find({})
    assigned_feedback = []
    for issue in jira_issues:
        issue_type = issue.get('issueType')
        for feedback in feedback_collection:
            assigned_tore = feedback.get('tore', [])
            for tore in assigned_tore:
                if issue_type == tore:
                    id_and_text = {
                        'id': feedback.get('id'),
                        'text': feedback.get('text')
                    }
                    assigned_feedback.append(id_and_text)
        if assigned_feedback:
            issue_id = issue.get('_id')
            update_criteria = {"_id": issue_id}
            update_operation = {"$set": {"feedback": assigned_feedback}}
            collectionJiraIssues.update_one(update_criteria, update_operation)
            assigned_feedback = []
    issues_new = list(collectionJiraIssues.find({}))
    for element in issues_new:
        element["_id"] = str(element["_id"])
    return issues_new


@feedback_bp.route('/assign_tore_to_feedback/<annotation_name>', methods=['GET'])
def set_tore_categories(annotation_name):
    try:
        feedback_collection = collectionFeedbackWithToreCategories.find({})
        annotations = collectionAnnotations.find({})
        docs = collectionAnnotations.distinct('docs')
        codes = collectionAnnotations.distinct('codes')
        tore_list = []
        for annotation in annotations:
            annotation_name1 = annotation.get('name')
            if annotation_name1 == annotation_name:
                for feedback in feedback_collection:
                    document_id = feedback.get('id')
                    for doc in docs:
                        doc_name = doc.get('name')
                        if document_id == doc_name:
                            begin_index = doc.get('begin_index')
                            end_index = doc.get('end_index')
                            for code in codes:
                                tokens = code.get('tokens', [])
                                for token in tokens:
                                    if begin_index <= token <= end_index:
                                        tore = code.get('tore')
                                        if tore not in tore_list:
                                            tore_list.append(tore)

                            if tore_list:
                                feedback_id = feedback.get('_id')
                                update_criteria = {"_id": feedback_id}
                                update_operation = {"$set": {"tore": set_issue_type_by_tore_category(tore_list)}}
                                collectionFeedbackWithToreCategories.update_one(update_criteria, update_operation)
                                tore_list.clear()
        feedback_new = list(collectionFeedbackWithToreCategories.find({}))
        for element in feedback_new:
            element["_id"] = str(element["_id"])
        return feedback_new
    except Exception as e:
        return jsonify({"message": str(e)})


def set_issue_type_by_tore_category(tore_list):
    issue_types = []
    for category in tore_list:
        if category == "Task":
            issue_types.append("User Task")
        elif category == "Activity":
            issue_types.append("User Subtask")  # ?
            issue_types.append("User Story")
        elif category == "Domain Data":
            issue_types.append("Domain Data Diagram")  # Diagram?
            issue_types.append("User Task")
            issue_types.append("User Subtask")  # User Sub-Task?
        elif category == "Stakeholder":
            issue_types.append("Persona")
            issue_types.append("User Role")
            issue_types.append("User Story")
        elif category == "Interaction":
            issue_types.append("System Function")
            issue_types.append("UI-Structure Diagram")  # ?
        elif category == "Interaction Data":
            issue_types.append("System Function")
            issue_types.append("Workspace")
        elif category == "Workspace":
            issue_types.append("Workspace")
            issue_types.append("UI-Structure Diagram")  # ?
        elif category == "System Function":
            issue_types.append("System Function")
    types_set = set(issue_types)
    types_list = list(types_set)
    return types_list


@feedback_bp.route("/load/<feedback_name>", methods=["GET"])
def load_feedback(feedback_name):
    try:
        if collectionFeedbackWithToreCategories.count_documents({}) > 0:
            collectionFeedbackWithToreCategories.delete_many({})

        feedback_collection = collectionFeedback.find({})

        for feedback in feedback_collection:
            feedback_name1 = feedback.get('name')
            if feedback_name1 == feedback_name:
                documents = feedback.get('documents', [])

                for doc in documents:
                    doc_id = doc.get('id')
                    doc_text = doc.get('text')

                    id_and_text = {
                        'id': doc_id,
                        'text': doc_text
                    }
                    collectionFeedbackWithToreCategories.insert_one(id_and_text)
        feedback_new = list(collectionFeedbackWithToreCategories.find({}))
        for element in feedback_new:
            element["_id"] = str(element["_id"])
        return jsonify(feedback_new)
    except Exception as e:
        return jsonify({"message": str(e)})


@feedback_bp.route('/get_feedback', methods=['GET'])
def get_feedback():
    issues = list(collectionFeedbackWithToreCategories.find({}))
    for element in issues:
        element["_id"] = str(element["_id"])
    return issues


@feedback_bp.route('/get_feedback_names', methods=['GET'])
def get_feedback_names():
    feedback = collectionFeedback.find({})
    names_list = [doc["name"] for doc in feedback]
    return names_list


@feedback_bp.route('/get_annotations_names', methods=['GET'])
def get_annotations_names():
    annotations = collectionAnnotations.find({})
    names_list = [doc["name"] for doc in annotations]
    return names_list
