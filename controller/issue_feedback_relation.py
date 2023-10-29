from transformers import DistilBertTokenizer, DistilBertModel
import torch
from flask import jsonify, Blueprint, request
from pymongo import MongoClient
from sklearn.metrics.pairwise import cosine_similarity
import spacy

nlp = spacy.load("en_core_web_sm")

issue_feedback_relation_bp = Blueprint('issue_feedback_relation', __name__)

client = MongoClient("mongodb://mongo:27017/")
dbIssues = client["jira_dashboard"]
collection_jira_issues = dbIssues["jira_issue"]
collection_imported_feedback = dbIssues["imported_feedback"]
collection_assigned_feedback = dbIssues["assigned_feedback"]
collection_assigned_feedback_with_tore = dbIssues["assigned_feedback_with_tore"]

tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
model = DistilBertModel.from_pretrained('distilbert-base-uncased')


@issue_feedback_relation_bp.route('/add_feedback_to_issue', methods=['POST'])
def add_feedback_to_issue():
    data = request.get_json()
    issue_key = data.get('issue_key')
    project_name = data.get('projectName')
    selected_feedback = data['selected_feedback']

    for feedback_obj in selected_feedback:
        feedback_id = feedback_obj.get('id')

        new_relation = {
            'project_name': project_name,
            'issue_key': issue_key,
            'feedback_id': feedback_id,
            'similarity': "Manually inserted"
        }

        collection_assigned_feedback.insert_one(new_relation)

    return jsonify(
        {"message": "Feedback relations added successfully"})


@issue_feedback_relation_bp.route('/add_tore_feedback_to_issue', methods=['POST'])
def add_tore_feedback_to_issue():
    data = request.get_json()
    issue_key = data.get('issue_key')
    project_name = data.get('projectName')
    selected_feedback = data['selected_feedback']

    for feedback_obj in selected_feedback:
        feedback_id = feedback_obj.get('id')

        new_relation = {
            'project_name': project_name,
            'issue_key': issue_key,
            'feedback_id': feedback_id,
            'similarity': "Manually inserted"
        }

        collection_assigned_feedback_with_tore.insert_one(new_relation)

    return jsonify(
        {"message": "Feedback relations added successfully"})


@issue_feedback_relation_bp.route('/add_issue_to_feedback', methods=['POST'])
def add_issue_to_feedback():
    data = request.get_json()
    feedback_id = data.get('feedback_id')
    selected_issues = data['selected_issues']

    for issue_obj in selected_issues:
        issue_key = issue_obj.get('key')
        project_name = issue_obj.get('projectName')

        new_relation = {
            'project_name': project_name,
            'issue_key': issue_key,
            'feedback_id': feedback_id,
            'similarity': "Manually inserted"
        }

        collection_assigned_feedback.insert_one(new_relation)

    return jsonify(
        {"message": "Feedback relations added successfully"})


@issue_feedback_relation_bp.route('/add_issue_to_tore_feedback', methods=['POST'])
def add_issue_to_tore_feedback():
    data = request.get_json()
    feedback_id = data.get('feedback_id')
    selected_issues = data['selected_issues']

    for issue_obj in selected_issues:
        issue_key = issue_obj.get('key')
        project_name = issue_obj.get('projectName')

        new_relation = {
            'project_name': project_name,
            'issue_key': issue_key,
            'feedback_id': feedback_id,
            'similarity': "Manually inserted"
        }

        collection_assigned_feedback_with_tore.insert_one(new_relation)

    return jsonify(
        {"message": "Feedback relations added successfully"})


@issue_feedback_relation_bp.route('/delete_feedback/<issue_key>/<feedback_id>', methods=['DELETE'])
def delete_feedback_from_issue(issue_key, feedback_id):
    collection_assigned_feedback.delete_one({'issue_key': issue_key, 'feedback_id': feedback_id})
    return jsonify({"message": "Feedback deleted successfully"})


@issue_feedback_relation_bp.route('/delete_tore_feedback/<issue_key>/<feedback_id>', methods=['DELETE'])
def delete_tore_feedback_from_issue(issue_key, feedback_id):
    collection_assigned_feedback_with_tore.delete_one({'issue_key': issue_key, 'feedback_id': feedback_id})
    return jsonify({"message": "Feedback deleted successfully"})


@issue_feedback_relation_bp.route('/delete_assigned_feedback_for_issue/<issue_key>', methods=['DELETE'])
def delete_assigned_feedback_for_issue(issue_key):
    collection_assigned_feedback.delete_many({'issue_key': issue_key})
    return jsonify({'error': 'Feedback deleted'})


@issue_feedback_relation_bp.route('/delete_tore_assigned_feedback_for_issue/<issue_key>', methods=['DELETE'])
def delete_tore_assigned_feedback_for_issue(issue_key):
    collection_assigned_feedback_with_tore.delete_many({'issue_key': issue_key})
    return jsonify({'error': 'Feedback deleted'})


@issue_feedback_relation_bp.route('/delete_assigned_issues_for_feedback/<feedback_id>', methods=['DELETE'])
def delete_assigned_issues_for_feedback(feedback_id):
    collection_assigned_feedback.delete_many({'feedback_id': feedback_id})
    return jsonify({'error': 'Feedback deleted'})


@issue_feedback_relation_bp.route('/delete_tore_assigned_issues_for_feedback/<feedback_id>', methods=['DELETE'])
def delete_tore_assigned_issues_for_feedback(feedback_id):
    collection_assigned_feedback_with_tore.delete_many({'feedback_id': feedback_id})
    return jsonify({'error': 'Feedback deleted'})


def get_embeddings(text):
    doc = nlp(text)
    nouns_and_verbs = [token.text for token in doc if token.pos_ in ("NOUN", "VERB")]

    tokens = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**tokens)
    embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

    embeddings = []

    if nouns_and_verbs:
        for word in nouns_and_verbs:
            # tokenize word
            word_tokens = tokenizer.tokenize(word)

            # convert token-sequenz to String
            tokenized_text = tokenizer.convert_ids_to_tokens(tokens["input_ids"][0])

            # search for word in tokenized String
            for i in range(len(tokenized_text) - len(word_tokens) + 1):
                if tokenized_text[i:i + len(word_tokens)] == word_tokens:
                    word_embedding = outputs.last_hidden_state[0, i:i + len(word_tokens), :].mean(dim=0).numpy()
                    embeddings.append(word_embedding)
    # Creating an overall embedding for the set by averaging the embeddings
    if embeddings:
        summary_embedding = sum(embeddings) / len(embeddings)
        return summary_embedding
    else:
        return embedding


@issue_feedback_relation_bp.route('/assign_feedback_to_issues', methods=['POST'])
def assign_feedback_to_issues():
    collection_assigned_feedback.delete_many({})
    feedback_collection = list(collection_imported_feedback.find({}))
    jira_collection = collection_jira_issues.find({})
    for project in jira_collection:
        is_selected = project.get("selectedToAssign")
        if is_selected:
            project_issues = project.get("issues", [])
            for issue in project_issues:
                summary = issue.get("summary")
                description = issue.get("description")
                issue_text = summary
                if description is not None:
                    issue_text = summary + " " + description
                summary_embedding = get_embeddings(issue_text)
                for feedback in feedback_collection:
                    feedback_text = feedback.get("text")
                    text_embedding = get_embeddings(feedback_text)

                    similarity = cosine_similarity([summary_embedding], [text_embedding])[0][0]

                    # if similarity > 0.7:
                    assigned_feedback = {
                            'feedback_id': feedback.get('id'),
                            "issue_key": issue["key"],
                            "project_name": issue["projectName"],
                            "similarity": float(similarity),
                    }
                    collection_assigned_feedback.insert_one(assigned_feedback)

    return jsonify({'message': 'Feedbacks erfolgreich Issues zugewiesen'})


@issue_feedback_relation_bp.route('/assign_feedback_to_issues_by_tore', methods=['POST'])
def assign_feedback_to_issues_by_tore():
    collection_assigned_feedback_with_tore.delete_many({})
    feedback_collection = list(collection_imported_feedback.find({}))
    jira_collection = list(collection_jira_issues.find({}))
    for project in jira_collection:
        is_selected = project.get("selectedToAssign")
        if is_selected:
            project_issues = project.get("issues", [])
            for issue in project_issues:
                issue_type = issue.get('issueType')
                summary = issue.get("summary")
                description = issue.get("description")
                issue_text = summary
                if description is not None:
                    issue_text = summary + " " + description
                summary_embedding = get_embeddings(issue_text)
                for feedback in feedback_collection:
                    assigned_tore = feedback.get('tore', [])
                    feedback_text = feedback.get("text")
                    for tore in assigned_tore:
                        if issue_type == tore:
                            text_embedding = get_embeddings(feedback_text)

                            similarity = cosine_similarity([summary_embedding], [text_embedding])[0][0]

                            # if similarity > 0.7:
                            assigned_feedback_with_tore = {
                                'feedback_id': feedback.get('id'),
                                "issue_key": issue["key"],
                                "project_name": issue["projectName"],
                                "similarity": float(similarity),
                            }
                            collection_assigned_feedback_with_tore.insert_one(assigned_feedback_with_tore)

    return jsonify({'message': 'the assignment was successful'})

