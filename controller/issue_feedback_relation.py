from transformers import DistilBertTokenizer, DistilBertModel
import torch
from flask import jsonify, Blueprint, request
from sklearn.metrics.pairwise import cosine_similarity
import spacy
import re
import numpy as np
#from controller.evaluationMethods import RecallPrecisionCalculator
from mongo import (collection_jira_issues,
                   collection_assigned_feedback,
                   collection_assigned_feedback_with_tore,
                   collection_imported_feedback,
                   collection_saved_data)

nlp = spacy.load("en_core_web_sm")

issue_feedback_relation_bp = Blueprint('issue_feedback_relation', __name__)

tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
model = DistilBertModel.from_pretrained('distilbert-base-uncased')


@issue_feedback_relation_bp.route('/delete_data/<name>', methods=['DELETE'])
def delete_data(name):
    if collection_saved_data.find_one({'name': name}):
        collection_saved_data.delete_one({'name': name})
        return jsonify({'message': f'Data with name {name} deleted successfully'})
    else:
        return jsonify({'error': f'Data with name {name} not found'}), 404


@issue_feedback_relation_bp.route('/get_saved_data_names', methods=['GET'])
def get_unique_names():
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
        data_tore_assigned_feedback = saved_data['tore_assigned_feedback']

        collection_imported_feedback.delete_many({})
        collection_jira_issues.delete_many({})
        collection_assigned_feedback.delete_many({})
        collection_assigned_feedback_with_tore.delete_many({})

        for item in data_imported_feedback:
            collection_imported_feedback.insert_one(item)

        for item in data_jira_issues:
            collection_jira_issues.insert_one(item)

        for item in data_assigned_feedback:
            collection_assigned_feedback.insert_one(item)

        for item in data_tore_assigned_feedback:
            collection_assigned_feedback_with_tore.insert_one(item)

        return jsonify({'message': 'restored successful.'})
    else:
        return jsonify({'error': 'dataset not found.'}), 400


@issue_feedback_relation_bp.route('/save_data/<name>', methods=['POST'])
def save_data(name):
    if collection_saved_data.find_one({'name': name}):
        return jsonify({'error': 'Name already exists!'}), 400

    data_imported_feedback = list(collection_imported_feedback.find())
    data_jira_issues = list(collection_jira_issues.find())
    data_assigned_feedback = list(collection_assigned_feedback.find())
    data_tore_assigned_feedback = list(collection_assigned_feedback_with_tore.find())

    combined_data = {
        'name': name,
        'imported_feedback': data_imported_feedback,
        'jira_issues': data_jira_issues,
        'assigned_feedback': data_assigned_feedback,
        'tore_assigned_feedback': data_tore_assigned_feedback
    }

    collection_saved_data.insert_one(combined_data)

    return jsonify({'message': 'Saved successfully'})


@issue_feedback_relation_bp.route('/get_data_to_export/<feedback_name>', methods=['GET'])
def get_data_to_export(feedback_name):
    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    imported_feedback = feedback_document.get("feedback", [])

    assigned_feedback_documents = collection_assigned_feedback.find({})

    unique_issue_keys_with_feedback_ids = {}
    for document in assigned_feedback_documents:
        issue_key = document['issue_key']
        feedback_id = document['feedback_id']
        if issue_key not in unique_issue_keys_with_feedback_ids:
            unique_issue_keys_with_feedback_ids[issue_key] = []
        unique_issue_keys_with_feedback_ids[issue_key].append(feedback_id)

    issue_info = {}
    for issue_key in unique_issue_keys_with_feedback_ids:
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
    for document in imported_feedback:
        feedback_id = document['id']
        feedback_text = document['text']
        feedback_text = re.sub(r'[^a-zA-Z0-9.,: ]', '', feedback_text)
        feedback_info[feedback_id] = feedback_text

    for issue_key, feedback_ids in unique_issue_keys_with_feedback_ids.items():
        if issue_key in issue_info:
            feedback_data = issue_info[issue_key]['feedback_data']
            for feedback_id in feedback_ids:
                if feedback_id in feedback_info:
                    feedback_text = feedback_info[feedback_id]
                    feedback_data.append({'feedback_id': feedback_id, 'feedback_text': feedback_text})

    combined_data = list(issue_info.values())

    return jsonify(combined_data)


@issue_feedback_relation_bp.route('/get_data_tore_to_export/<feedback_name>', methods=['GET'])
def get_data_tore_to_export(feedback_name):
    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    imported_feedback = feedback_document.get("feedback", [])

    assigned_feedback_documents = collection_assigned_feedback_with_tore.find({})

    unique_issue_keys_with_feedback_ids = {}
    for document in assigned_feedback_documents:
        issue_key = document['issue_key']
        feedback_id = document['feedback_id']
        if issue_key not in unique_issue_keys_with_feedback_ids:
            unique_issue_keys_with_feedback_ids[issue_key] = []
        unique_issue_keys_with_feedback_ids[issue_key].append(feedback_id)

    issue_info = {}
    for issue_key in unique_issue_keys_with_feedback_ids:
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
    for document in imported_feedback:
        feedback_id = document['id']
        feedback_text = document['text']
        feedback_text = re.sub(r'[^a-zA-Z0-9.,: ]', '', feedback_text)
        feedback_info[feedback_id] = feedback_text

    for issue_key, feedback_ids in unique_issue_keys_with_feedback_ids.items():
        if issue_key in issue_info:
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
    nouns_and_verbs = set(token.text for token in doc if token.pos_ in ("NOUN", "VERB"))
    nouns_and_verbs = list(nouns_and_verbs)
    tokens = tokenizer(text, return_tensors="pt")
    # das keine gradienten (Backpropagation verwendet wird)
    with torch.no_grad():
        # tokens in einzelne Komponenten entpacken
        outputs = model(**tokens)

    embeddings = []

    if nouns_and_verbs:
        for word in nouns_and_verbs:
            # tokenize word from nouns_and_verbs
            word_tokens = tokenizer.tokenize(word)
            # convert token-sequenz to String gesamter Text
            tokenized_text = tokenizer.convert_ids_to_tokens(tokens["input_ids"][0])
            # Hier wird für jedes identifizierte Nomen oder Verb im Text ein Embedding erstellt. Der entsprechende Abschnitt des
            # outputs.last_hidden_state-Tensors, der zu diesem spezifischen Wort gehört, wird ausgewählt. Dann wird der
            # Durchschnitt über die Token-Dimension (dim=0) genommen, um das Embedding für dieses spezielle Wort zu berechnen.
            # # search for word in tokenized String
            # # iteriert durch tokenized text. -len verhindert out of bounce
            for i in range(len(tokenized_text) - len(word_tokens) + 1):
                # ist word_token in sequenz von tokenized_text die bei i beginnt und so land wie word_tokens ist
                if tokenized_text[i:i + len(word_tokens)] == word_tokens:
                    # Die Liste embeddings enthält dann die Einbettungen für alle identifizierten Nomen und Verben im Text.
                    # Diese Einbettungen repräsentieren den Kontext jedes einzelnen Worts im Bezug auf seine umgebenden Tokens.
                    word_embedding = outputs.last_hidden_state[0, i:i + len(word_tokens), :].mean(dim=0).numpy()
                    embeddings.append(word_embedding)

    # Dieser Durchschnitt (summary_embedding) repräsentiert dann den Kontext, der durch die identifizierten Nomen und
    # Verben im gesamten Text gebildet wird. Es ist eine Art Zusammenfassung des Kontexts, der durch die einzelnen
    # Wörter beigetragen wird.
    if embeddings:
        summary_embedding = np.mean(embeddings, axis=0)
        return summary_embedding
    else:
        return outputs.last_hidden_state.mean(dim=0).squeeze().numpy() # if no NOUNS and VERBS where found
# wenn Sie dim=0 verwenden, wird der Mittelwert über die Sätze berechnet und der resultierende Vektor
# repräsentiert sozusagen einen durchschnittlichen Kontext für den gesamten Text. Wenn Sie dim=1 verwenden,
# wird der Mittelwert für jeden Satz berechnet, wobei der Kontext auf die Token innerhalb jedes Satzes beschränkt ist.
# Die Wahl hängt davon ab, ob Sie den Gesamtkontext des gesamten Textes oder den Kontext innerhalb einzelner Sätze
# erfassen möchten.


@issue_feedback_relation_bp.route('/assign_feedback_to_issues/<feedback_name>/<max_similarity_value>', methods=['POST'])
def assign_feedback_to_issues(feedback_name, max_similarity_value):
    max_similarity_value = float(max_similarity_value)
    #while max_similarity_value <= 0.9:
    collection_assigned_feedback.delete_many({})
    jira_collection = collection_jira_issues.find({})
    feedback_embeddings = calculate_feedback_embedding(feedback_name)
    for project in jira_collection:
        is_selected = project.get("selectedToAssign")
        if is_selected:
            project_issues = project.get("issues", [])
            for issue in project_issues:
                summary = issue.get("summary")
                description = issue.get("description")
                issue_text = summary
                if description is not None:
                    issue_text = summary + ". " + description
                summary_embedding = get_embeddings(issue_text)
                for embedded_feedback in feedback_embeddings:
                    similarity = cosine_similarity([summary_embedding], [embedded_feedback.get('embedding')])[0][0]
                    if similarity > max_similarity_value:
                        assigned_feedback = {
                            'feedback_id': embedded_feedback.get('feedback_id'),
                            "issue_key": issue["key"],
                            "project_name": issue["projectName"],
                            "similarity": str(round(float(similarity), 3)),
                        }
                        collection_assigned_feedback.insert_one(assigned_feedback)

        # calculator = RecallPrecisionCalculator(collection_saved_data, collection_assigned_feedback, collection_jira_issues)
        # calculator.calculate_metrics("sim-"+str(max_similarity_value))
        # max_similarity_value += 0.01
        # max_similarity_value = round(max_similarity_value, 2)

    return jsonify({'message': 'assignment was successful'})


def calculate_feedback_embedding(feedback_name):
    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    feedback_array = feedback_document.get("feedback", [])
    feedback_embeddings = []
    for feedback in feedback_array:
        feedback_text = feedback.get("text")
        text_embedding = get_embeddings(feedback_text)
        feedback_embedding = {
            'feedback_id': feedback.get('id'),
            'embedding': text_embedding
        }
        feedback_embeddings.append(feedback_embedding)
    return feedback_embeddings


@issue_feedback_relation_bp.route('/assign_feedback_to_issues_by_tore/<feedback_name>/<max_similarity_value>',
                                  methods=['POST'])
def assign_feedback_to_issues_by_tore(feedback_name, max_similarity_value):
    max_similarity_value = float(max_similarity_value)
    collection_assigned_feedback_with_tore.delete_many({})
    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    feedback_array = feedback_document.get("feedback", [])
    jira_collection = list(collection_jira_issues.find({}))
    feedback_embeddings = calculate_feedback_embedding(feedback_name)
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
                    issue_text = summary + ". " + description
                summary_embedding = get_embeddings(issue_text)
                for feedback in feedback_array:
                    assigned_tore = feedback.get('tore', [])
                    for tore in assigned_tore:
                        if issue_type == tore:
                            matching_feedback = next((embedding['embedding'] for embedding in feedback_embeddings
                                                      if embedding.get('feedback_id') == feedback.get('id')), None)

                            similarity = cosine_similarity([summary_embedding], [matching_feedback])[0][0]

                            if similarity > max_similarity_value:
                                assigned_feedback_with_tore = {
                                    'feedback_id': feedback.get('id'),
                                    "issue_key": issue["key"],
                                    "project_name": issue["projectName"],
                                    "similarity": str(round(float(similarity), 3)),
                                }
                                collection_assigned_feedback_with_tore.insert_one(assigned_feedback_with_tore)

    return jsonify({'message': 'assignment was successful'})
