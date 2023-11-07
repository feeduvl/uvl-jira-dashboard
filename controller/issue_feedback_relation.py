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
    # jedes wort nur einmal in array, weil es trotzdem jede stelle findet
    nouns_and_verbs = set(token.text for token in doc if token.pos_ in ("NOUN", "VERB"))
    nouns_and_verbs = list(nouns_and_verbs)
    #tokenize text - konvertiert text in Abfolge von Tokens mit position in form von pytorch tensor
    tokens = tokenizer(text, return_tensors="pt")
    # das keine gradienten (Backpropagation verwendet wird)
    with torch.no_grad():
        #tokens in einzelne Komponenten entpacken
        outputs = model(**tokens)
    #durchschnittliches embedding für text + dim1=durchschnittswert für jeden token + squeeze entfernt überflüssige dim + numypy-array bildung
    embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

    embeddings = []

    if nouns_and_verbs:
        for word in nouns_and_verbs:
            # tokenize word from nouns_and_verbs
            word_tokens = tokenizer.tokenize(word)

            # convert token-sequenz to String gesamter Text
            tokenized_text = tokenizer.convert_ids_to_tokens(tokens["input_ids"][0])

            # search for word in tokenized String
            # iteriert durch tokenized text. -len verhindert out of bounce
            for i in range(len(tokenized_text) - len(word_tokens) + 1):
                # ist word_token in sequenz von tokenized_text die bei i beginnt und so land wie word_tokens ist
                if tokenized_text[i:i + len(word_tokens)] == word_tokens:
                    # [0, i:i + len(word_tokens), :] 0= erster Satz im text. rest wählt die tokens aus, die zum word_token gehören
                    # .mean(dim1) berechnet word embedding für aktueller wort = durchschnittswert über token des aktuellen wortes wird gebildet
                    # dim0 = durcshnitt des gesamten Satz ohne Kontext und sematische Bedeutung der einzelnen Wörter
                    word_embedding = outputs.last_hidden_state[0, i:i + len(word_tokens), :].mean(dim=0).numpy()
                    embeddings.append(word_embedding)
                    #Wenn der Satzkontext stärker berücksichtigt werden soll, ist dim=1 die bessere Wahl.
                    # Wenn jedoch nur die semantische Bedeutung der Nomen und Verben
                        # in Bezug auf den gesamten Text betrachtet werden soll, dim0
    # Creating an overall embedding for the set by averaging the embeddings
    if embeddings:
        # nötig für spezifische informationen über wörter im text
        summary_embedding = sum(embeddings) / len(embeddings)
        return summary_embedding
    else:
        return embedding


@issue_feedback_relation_bp.route('/assign_feedback_to_issues/<feedback_name>/<max_similarity_value>', methods=['POST'])
def assign_feedback_to_issues(feedback_name, max_similarity_value):
    max_similarity_value = float(max_similarity_value)
    collection_assigned_feedback.delete_many({})
    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    feedback_array = feedback_document.get("feedback", [])
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
                    issue_text = summary + ". " + description
                summary_embedding = get_embeddings(issue_text)
                for feedback in feedback_array:
                    feedback_text = feedback.get("text")
                    text_embedding = get_embeddings(feedback_text)

                    similarity = cosine_similarity([summary_embedding], [text_embedding])[0][0]

                    if similarity > max_similarity_value:
                        assigned_feedback = {
                                'feedback_id': feedback.get('id'),
                                "issue_key": issue["key"],
                                "project_name": issue["projectName"],
                                "similarity": round(float(similarity), 3),
                        }
                        collection_assigned_feedback.insert_one(assigned_feedback)

    return jsonify({'message': 'Feedbacks erfolgreich Issues zugewiesen'})


@issue_feedback_relation_bp.route('/assign_feedback_to_issues_by_tore/<feedback_name>/<max_similarity_value>', methods=['POST'])
def assign_feedback_to_issues_by_tore(feedback_name, max_similarity_value):
    max_similarity_value = float(max_similarity_value)
    collection_assigned_feedback_with_tore.delete_many({})
    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    feedback_array = feedback_document.get("feedback", [])
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
                    issue_text = summary + ". " + description
                summary_embedding = get_embeddings(issue_text)
                for feedback in feedback_array:
                    assigned_tore = feedback.get('tore', [])
                    feedback_text = feedback.get("text")
                    for tore in assigned_tore:
                        if issue_type == tore:
                            text_embedding = get_embeddings(feedback_text)

                            similarity = cosine_similarity([summary_embedding], [text_embedding])[0][0]

                            if similarity > max_similarity_value:
                                assigned_feedback_with_tore = {
                                    'feedback_id': feedback.get('id'),
                                    "issue_key": issue["key"],
                                    "project_name": issue["projectName"],
                                    "similarity": round(float(similarity), 3),
                                }
                                collection_assigned_feedback_with_tore.insert_one(assigned_feedback_with_tore)

    return jsonify({'message': 'the assignment was successful'})

