from operator import itemgetter

from transformers import DistilBertTokenizer, DistilBertModel
import torch
from flask import jsonify, Blueprint, request
from sklearn.metrics.pairwise import cosine_similarity
import spacy
import re
import numpy as np
from mongo import mongo_db
import logging

collection_jira_issues = mongo_db.collection_jira_issues
collection_assigned_feedback = mongo_db.collection_assigned_feedback
collection_imported_feedback = mongo_db.collection_imported_feedback
collection_feedback = mongo_db.collection_feedback
collection_saved_data = mongo_db.collection_saved_data
# load spacy library
nlp = spacy.load("en_core_web_sm")

issue_feedback_relation_bp = Blueprint('issue_feedback_relation', __name__)

# load tokenizer and distilbert model
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
model = DistilBertModel.from_pretrained('distilbert-base-uncased')

@issue_feedback_relation_bp.route('/create_dashboard/<name>/<type>', methods=['POST'])
def create_dashboard(name, type):
    if collection_saved_data.find_one({'name': name}):
        return jsonify({'error': 'Name already exists!'}), 400

    combined_data = {
        'name': name,
        'imported_feedback': [],
        'jira_issues': [],
        'assigned_feedback': [],
        'datasets': [],
        'type': type,
        'threshold': "",
        'annotation': [],
        'classifier':""
    }
    collection_imported_feedback.delete_many({})
    collection_jira_issues.delete_many({})
    collection_assigned_feedback.delete_many({})
    # TODO: Clear annotation table
    collection_saved_data.insert_one(combined_data)

    return jsonify({'message': 'Saved successfully'})

@issue_feedback_relation_bp.route('/delete_data/<name>', methods=['DELETE'])
def delete_data(name):
    if collection_saved_data.find_one({'name': name}):
        collection_saved_data.delete_one({'name': name})
        return jsonify({'message': f'Data with name {name} deleted successfully'})
    else:
        return jsonify({'error': f'Data with name {name} not found'}), 404


@issue_feedback_relation_bp.route('/get_saved_data_names', methods=['GET'])
def get_unique_names():
    # get names of saved data
    saved_data = list(collection_saved_data.find({}, {'_id': 0, 'name': 1}))
    unique_names = set(item['name'] for item in saved_data if 'name' in item)
    return jsonify(list(unique_names))


@issue_feedback_relation_bp.route('/restore_data/<name>', methods=['GET'])
def restore_data(name):
    saved_data = collection_saved_data.find_one({'name': name})

    if saved_data:
        data_imported_feedback = saved_data['imported_feedback']
        data_jira_issues = saved_data['jira_issues']
        data_assigned_feedback = saved_data['assigned_feedback']

        collection_imported_feedback.delete_many({})
        collection_jira_issues.delete_many({})
        collection_assigned_feedback.delete_many({})

        for item in data_imported_feedback:
            collection_imported_feedback.insert_one(item)

        for item in data_jira_issues:
            collection_jira_issues.insert_one(item)

        for item in data_assigned_feedback:
            collection_assigned_feedback.insert_one(item)

        #TODO: Load Annotation

        response = {
            'message': 'restored successful.',
            'type': saved_data['type'],
            'datasets': saved_data['datasets'],
            'name': name,
            'classifier': saved_data['classifier'],
            'threshold': saved_data['threshold']
        }
        return jsonify(response)
    else:
        return jsonify({'error': 'dataset not found.'}), 400


@issue_feedback_relation_bp.route('/save_data/<name>', methods=['POST'])
def save_data(name):
    print("save data")
    data = request.get_json()
    if collection_saved_data.find_one({'name': name}):
        return jsonify({'error': 'Name already exists!'}), 400

    data_imported_feedback = list(collection_imported_feedback.find())
    data_jira_issues = list(collection_jira_issues.find())
    data_assigned_feedback = list(collection_assigned_feedback.find())

    combined_data = {
        'name': name,
        'imported_feedback': data_imported_feedback,
        'jira_issues': data_jira_issues,
        'assigned_feedback': data_assigned_feedback,
        'datasets': data.get("datasets"),
        'type': data.get("type"),
        'annotation': "",
        'classifier': data.get("classifier"),
        'threshold': data.get("threshold")
    }
    print(list(collection_imported_feedback.find()))
    print(combined_data)

    collection_saved_data.insert_one(combined_data)

    return jsonify({'message': 'Saved successfully'})


@issue_feedback_relation_bp.route('/get_data_to_export/<feedback_name>', methods=['GET'])
def get_data_to_export(feedback_name):
    # get imported feedback
    imported_feedback = collection_imported_feedback.find({})
    # find all assigned elements
    assigned_feedback_documents = collection_assigned_feedback.find({})
    # iterate through feedback and find assigned feedback
    unique_issue_keys_with_feedback_ids = {}
    for document in assigned_feedback_documents:
        issue_key = document['issue_key']
        feedback_id = document['feedback_id']
        if issue_key not in unique_issue_keys_with_feedback_ids:
            unique_issue_keys_with_feedback_ids[issue_key] = []
        # add every assigned feedback id for each requirement
        unique_issue_keys_with_feedback_ids[issue_key].append(feedback_id)

    issue_info = {}
    for issue_key in unique_issue_keys_with_feedback_ids:
        # find requirements that are assigned to get the summary und description
        issue_data = collection_jira_issues.find_one({'issues.key': issue_key})
        if issue_data:
            issue_summary = None
            issue_description = None
            for issue in issue_data.get('issues', []):
                if issue['key'] == issue_key:
                    issue_summary = issue['summary']
                    issue_description = issue['description']
                    issue_description = re.sub(r'[^a-zA-Z0-9.,: ]', '', issue_description)
                    break
            if issue_summary is not None and issue_description is not None:
                issue_info[issue_key] = {
                    'issue_key': issue_key,
                    'issue_summary': issue_summary,
                    'issue_description': issue_description,
                    'feedback_data': []
                }
    feedback_info = {}
    # find feedback to get the id und text
    for document in imported_feedback:
        feedback_id = document['id']
        feedback_text = document['text']
        feedback_text = re.sub(r'[^a-zA-Z0-9.,: ]', '', feedback_text)
        feedback_info[feedback_id] = feedback_text
    # combine feedback and requirements
    for issue_key, feedback_ids in unique_issue_keys_with_feedback_ids.items():
        if issue_key in issue_info:
            # add feedback id and text for each requirement
            feedback_data = issue_info[issue_key]['feedback_data']
            for feedback_id in feedback_ids:
                if feedback_id in feedback_info:
                    feedback_text = feedback_info[feedback_id]
                    feedback_data.append({'feedback_id': feedback_id, 'feedback_text': feedback_text})

    combined_data = list(issue_info.values())

    return jsonify(combined_data)


@issue_feedback_relation_bp.route('/add_feedback_to_issue', methods=['POST'])
def add_feedback_to_issue():
    data = request.get_json()
    issue_key = data.get('issue_key')
    project_name = data.get('projectName')
    selected_feedback = data['selected_feedback']
    # iterate through the selected feedback
    for feedback_obj in selected_feedback:
        feedback_id = feedback_obj.get('id')
        # add the requirement to feedback and relate them for manual assignment
        new_relation = {
            'project_name': project_name,
            'issue_key': issue_key,
            'feedback_id': feedback_id,
            'similarity': "Manually inserted"
        }
        collection_assigned_feedback.insert_one(new_relation)
    return jsonify(
        {"message": "Feedback relations added successfully"})



@issue_feedback_relation_bp.route('/add_issue_to_feedback', methods=['POST'])
def add_issue_to_feedback():
    data = request.get_json()
    feedback_id = data.get('feedback_id')
    selected_issues = data['selected_issues']
    # iterate through the selected requirements
    for issue_obj in selected_issues:
        issue_key = issue_obj.get('key')
        project_name = issue_obj.get('projectName')
        # add the feedback to requirements and relate them for manual assignment
        new_relation = {
            'project_name': project_name,
            'issue_key': issue_key,
            'feedback_id': feedback_id,
            'similarity': "Manually inserted"
        }
        collection_assigned_feedback.insert_one(new_relation)

    return jsonify(
        {"message": "Feedback relations added successfully"})



@issue_feedback_relation_bp.route('/delete_feedback/<issue_key>/<feedback_id>', methods=['DELETE'])
def delete_feedback_from_issue(issue_key, feedback_id):
    # delete one feedback the is related to one requirement
    collection_assigned_feedback.delete_one({'issue_key': issue_key, 'feedback_id': feedback_id})
    return jsonify({"message": "Feedback deleted successfully"})



@issue_feedback_relation_bp.route('/delete_assigned_feedback_for_issue/<issue_key>', methods=['DELETE'])
def delete_assigned_feedback_for_issue(issue_key):
    # delete all feedback that are related to the chosen requirement
    collection_assigned_feedback.delete_many({'issue_key': issue_key})
    return jsonify({'error': 'Feedback deleted'})



@issue_feedback_relation_bp.route('/delete_assigned_issues_for_feedback/<feedback_id>', methods=['DELETE'])
def delete_assigned_issues_for_feedback(feedback_id):
    # delete all requirements that are related to the chosen feedback
    collection_assigned_feedback.delete_many({'feedback_id': feedback_id})
    return jsonify({'error': 'Feedback deleted'})


# embdding without using spaCy
def get_embeddings_without_spacy(text):
    # tokenize text with distilbert
    tokens = tokenizer(text, return_tensors="pt")
    # Calculate the contextualized token embeddings. that no gradients (backpropagation) is used
    with torch.no_grad():
        # unpack tokens into individual components
        outputs = model(**tokens)
    # the last hidden state - represents the contextualized representation of each token in the input sequence.
    # dim 0 - calculates the mean along the specified dimension
    # results in a single vector that represents the mean of all token embeddings across the sequence or batch.
    # squeeze - removes any singleton dimensions from the tensor
    # numpy - converts the PyTorch tensor to a NumPy array
    embedding = outputs.last_hidden_state.mean(dim=0).squeeze().numpy()
    # calculates the mean of the embedded vectors along the first dimension and stores the result
    summary_embedding = np.mean(embedding, axis=0)
    return summary_embedding

# get embeddings for standard approach
def get_embeddings(text):
    # tokenize text with distilbert
    tokens = tokenizer(text, return_tensors="pt")
    # Calculate the contextualized token embeddings. that no gradients (backpropagation) is used
    with torch.no_grad():
        # unpack tokens into individual components
        outputs = model(**tokens)
    # represents the contextualized representation of each token in the input sequence.
    distilbert_embeddings = outputs.last_hidden_state
    #
    # Extract the token vectors only for nouns and verbs with spaCy
    # and convert to lowercase to make it case-insensitive.
    nouns_and_verbs = set(token.text.lower() for token in nlp(text) if token.pos_ in {"NOUN", "VERB"})
    relevant_embeddings = []

    for word in nouns_and_verbs:
        # tokenize word from nouns_and_verbs
        word_tokens = tokenizer.tokenize(word)
        # convert token-sequenz to String
        tokenized_text = tokenizer.convert_ids_to_tokens(tokens["input_ids"][0])
        # search for word in tokenized String, iterate through the tokenized text
        for i in range(len(tokenized_text) - len(word_tokens) + 1):
            # finds word_token in sequence of tokenized_text
            if tokenized_text[i:i + len(word_tokens)] == word_tokens:
                # The list embeddings then contains the embeddings for all identified nouns and verbs in the text.
                # These embeddings represent the context of each individual word in relation to its surrounding tokens.
                word_embedding = distilbert_embeddings[0, i:i + len(word_tokens), :].numpy()
                relevant_embeddings.extend(word_embedding)
    # This average (summary_embedding) then represents the context formed by the identified
    # nouns and verbs throughout the entire text.
    # It serves as a kind of summary of the context contributed by each individual word.
    if relevant_embeddings:
        average_embedding = np.mean(relevant_embeddings, axis=0)
    else:
        average_embedding = np.mean(distilbert_embeddings.squeeze().numpy(), axis=0)
    return average_embedding


@issue_feedback_relation_bp.route('/assign_feedback_to_issues/<feedback_name>/<max_similarity_value>', methods=['POST'])
def assign_feedback_to_issues(feedback_name, max_similarity_value):
    max_similarity_value = float(max_similarity_value)
    # delete all assignments to create new
    collection_assigned_feedback.delete_many({})
    jira_collection = collection_jira_issues.find({})
    # calculate embeddings for all feedback
    feedback_embeddings = calculate_feedback_embedding(feedback_name)
    for project in jira_collection:
        # find requirements that are chosen for assignment
        is_selected = project.get("selectedToAssign")
        if is_selected:
            project_issues = project.get("issues", [])
            for issue in project_issues:
                summary = issue.get("summary")
                description = issue.get("description")
                issue_text = summary
                # combine summary and description
                if description is not None:
                    issue_text = summary + ": " + description
                # calculate embedding for requirement
                summary_embedding = get_embeddings(issue_text)
                similarities = []
                for embedded_feedback in feedback_embeddings:
                    # calculate cosine similarity for each feedback and requirement
                    similarity = cosine_similarity([summary_embedding], [embedded_feedback.get('embedding')])[0][0]
                    # if similarity is over threshold (max_similarity_value) add it to list of assigned elements
                    if similarity > max_similarity_value:
                        assigned_feedback = {
                            'feedback_id': embedded_feedback.get('feedback_id'),
                            "issue_key": issue["key"],
                            "project_name": issue["projectName"],
                            "similarity": str(round(float(similarity), 3)),
                        }
                        similarities.append(assigned_feedback)
                        collection_assigned_feedback.insert_one(assigned_feedback)
    return jsonify({'message': 'assignment was successful'})


@issue_feedback_relation_bp.route('/assign_many_feedback_to_issues/<max_similarity_value>', methods=['POST'])
def assign_many_feedback_to_issues(max_similarity_value):
    feedback_list = request.get_json().get('datasets')
    max_similarity_value = float(max_similarity_value)
    # delete all assignments to create new
    collection_assigned_feedback.delete_many({})
    jira_collection = collection_jira_issues.find({})
    # calculate embeddings for all feedback
    #feedback_list = feedback_name.split(",")

    # Clear imported_feedback table
    collection_imported_feedback.delete_many({})

    all_feedback_embeddings = []
    for feedback_item in feedback_list:
        feedback_embeddings = calculate_feedback_embedding(feedback_item)
        all_feedback_embeddings.extend(feedback_embeddings)
    for project in jira_collection:
        # find requirements that are chosen for assignment
        is_selected = project.get("selectedToAssign")
        if is_selected:
            project_issues = project.get("issues", [])
            for issue in project_issues:
                summary = issue.get("summary")
                description = issue.get("description")
                issue_text = summary
                # combine summary and description
                if description is not None:
                    issue_text = summary + ": " + description
                # calculate embedding for requirement
                summary_embedding = get_embeddings(issue_text)
                similarities = []
                for embedded_feedback in all_feedback_embeddings:
                    # calculate cosine similarity for each feedback and requirement
                    similarity = cosine_similarity([summary_embedding], [embedded_feedback.get('embedding')])[0][0]
                    # if similarity is over threshold (max_similarity_value) add it to list of assigned elements
                    if similarity > max_similarity_value:
                        assigned_feedback = {
                            'feedback_id': embedded_feedback.get('feedback_id'),
                            "issue_key": issue["key"],
                            "project_name": issue["projectName"],
                            "similarity": str(round(float(similarity), 3)),
                        }
                        similarities.append(assigned_feedback)
                        collection_assigned_feedback.insert_one(assigned_feedback)
    return jsonify({'message': 'assignment was successful'})

def calculate_feedback_embedding(feedback_name):
    #feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    feedback_document = collection_feedback.find_one({"name": feedback_name})

    feedback_array = feedback_document.get("documents", [])
    feedback_embeddings = []
    # iterate through all feedback and calculate embedding of each one
    for feedback in feedback_array:
        # Write all feedback items to imported_feedback_array
        imported_feedback_item = {
            "id": feedback.get("id"),
            "text": feedback.get("text")
        }
        collection_imported_feedback.insert_one(imported_feedback_item)

        feedback_text = feedback.get("text")
        text_embedding = get_embeddings(feedback_text)
        feedback_embedding = {
            'feedback_id': feedback.get('id'),
            'embedding': text_embedding
        }
        feedback_embeddings.append(feedback_embedding)
    return feedback_embeddings