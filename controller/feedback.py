from transformers import DistilBertTokenizer, DistilBertModel
import torch
from flask import jsonify, Blueprint
from pymongo import MongoClient
from sklearn.metrics.pairwise import cosine_similarity
import spacy

nlp = spacy.load("en_core_web_sm")

feedback_bp = Blueprint('feedback', __name__)

client = MongoClient("mongodb://mongo:27017/")
dbIssues = client["jira-issues"]
dbFeedback = client["concepts_data"]
collectionJiraIssues = dbIssues["jiraIssue"]
collectionFeedback = dbFeedback["dataset"]
collectionAnnotations = dbFeedback["annotation"]
collectionFeedbackWithToreCategories = dbIssues["feedback_with_tore"]

tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
model = DistilBertModel.from_pretrained('distilbert-base-uncased')


@feedback_bp.route('/assign_feedback_to_issues', methods=['POST'])
def calculate_similarities():
    feedback_collection = list(collectionFeedbackWithToreCategories.find({}))
    issues_collection = collectionJiraIssues.find({})

    results = []

    for issue in issues_collection:
        summary = issue.get("summary")
        similar_feedbacks = []

        summary_embedding = get_embeddings(summary)

        for feedback in feedback_collection:
            feedback_text = feedback.get("text")
            text_embedding = get_embeddings(feedback_text)

            similarity = cosine_similarity([summary_embedding], [text_embedding])[0][0]

            feedback_with_similarity = {
                'id': feedback.get('id'),
                "text": feedback_text,
                "similarity": float(similarity)
            }
            similar_feedbacks.append(feedback_with_similarity)

        if similar_feedbacks:
            issue_id = issue.get('_id')
            update_criteria = {"_id": issue_id}
            update_operation = {"$set": {"assigned_feedback": similar_feedbacks}}
            collectionJiraIssues.update_one(update_criteria, update_operation)

        results.append({"summary": summary, "similar_feedbacks": similar_feedbacks})

    return jsonify(results)


def get_embeddings(text):
    doc = nlp(text)
    nouns = [token.text for token in doc if token.pos_ == "NOUN"]
    embedded_text = ' '.join(nouns)

    inputs = tokenizer(embedded_text, return_tensors='pt', truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()


@feedback_bp.route('/assign_feedback_to_issues_by_tore', methods=['POST'])
def assign_feedback_to_issues_by_tore():
    feedback_collection = list(collectionFeedbackWithToreCategories.find({}))
    jira_issues = collectionJiraIssues.find({})
    for issue in jira_issues:
        issue_type = issue.get('issueType')
        summary = issue.get("summary")
        similar_feedbacks = []
        summary_embedding = get_embeddings(summary)
        for feedback in feedback_collection:
            assigned_tore = feedback.get('tore', [])
            feedback_text = feedback.get("text")
            for tore in assigned_tore:
                if issue_type == tore:
                    text_embedding = get_embeddings(feedback_text)

                    similarity = cosine_similarity([summary_embedding], [text_embedding])[0][0]

                    feedback_with_similarity = {
                        'id': feedback.get('id'),
                        "text": feedback_text,
                        "similarity": float(similarity)
                    }
                    similar_feedbacks.append(feedback_with_similarity)
        if similar_feedbacks:
            issue_id = issue.get('_id')
            update_criteria = {"_id": issue_id}
            update_operation = {"$set": {"assigned_feedback_with_tore": similar_feedbacks}}
            collectionJiraIssues.update_one(update_criteria, update_operation)
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
            issue_types.append("User Subtask")  # User Sub-Task?
            issue_types.append("User Story")
        elif category == "Domain Data":
            issue_types.append("Diagram")  # Domain Data Diagram?
            issue_types.append("User Task")
            issue_types.append("User Subtask")  # User Sub-Task?
        elif category == "Stakeholder":
            issue_types.append("Persona")
            issue_types.append("User Role")  # Role?
            issue_types.append("User Story")
        elif category == "Interaction":
            issue_types.append("System Function")
            issue_types.append("Diagram")  # UI-Structure Diagram?
        elif category == "Interaction Data":
            issue_types.append("System Function")
            issue_types.append("Workspace")
        elif category == "Workspace":
            issue_types.append("Workspace")
            issue_types.append("Diagram")  # UI-Structure Diagram?
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
