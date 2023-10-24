from flask import jsonify, Blueprint
from pymongo import MongoClient

feedback_bp = Blueprint('feedback', __name__)

client = MongoClient("mongodb://mongo:27017/")
dbIssues = client["jira_dashboard"]
dbFeedback = client["concepts_data"]
collection_feedback = dbFeedback["dataset"]
collection_annotations = dbFeedback["annotation"]
collection_imported_feedback = dbIssues["imported_feedback"]
collection_assigned_feedback = dbIssues["assigned_feedback"]
collection_assigned_feedback_with_tore = dbIssues["assigned_feedback_with_tore"]


@feedback_bp.route('/assign_tore_to_feedback/<annotation_name>', methods=['GET'])
def set_tore_categories(annotation_name):
    try:
        feedback_collection = collection_imported_feedback.find({})
        annotations = collection_annotations.find({})
        docs = collection_annotations.distinct('docs')
        codes = collection_annotations.distinct('codes')
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
                                collection_imported_feedback.update_one(update_criteria, update_operation)
                                tore_list.clear()
        feedback_new = list(collection_imported_feedback.find({}))
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
        if collection_imported_feedback.count_documents({}) > 0:
            collection_imported_feedback.delete_many({})

        feedback_collection = collection_feedback.find({})

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
                    collection_imported_feedback.insert_one(id_and_text)
        feedback_new = list(collection_imported_feedback.find({}))
        for element in feedback_new:
            element["_id"] = str(element["_id"])
        return jsonify(feedback_new)
    except Exception as e:
        return jsonify({"message": str(e)})

#add pagination
@feedback_bp.route('/get_feedback', methods=['GET'])
def get_feedback():
    issues = list(collection_imported_feedback.find({}))
    for element in issues:
        element["_id"] = str(element["_id"])
    return issues

#add pagination
@feedback_bp.route('/get_feedback_names', methods=['GET'])
def get_feedback_names():
    feedback = collection_feedback.find({})
    names_list = [doc["name"] for doc in feedback]
    return names_list

#add pagination
@feedback_bp.route('/get_annotations_names', methods=['GET'])
def get_annotations_names():
    annotations = collection_annotations.find({})
    names_list = [doc["name"] for doc in annotations]
    return names_list


@feedback_bp.route('/get_assigned_feedback/<issue_key>', methods=['GET'])
def get_assigned_feedback(issue_key):
    assigned_feedback = list(collection_assigned_feedback.find({'issue_key': issue_key}))

    feedback_ids = [feedback['feedback_id'] for feedback in assigned_feedback]

    feedbacks = []
    for feedback_id in feedback_ids:
        feedback = collection_imported_feedback.find_one({'id': feedback_id})
        if feedback:
            matching_assigned_feedback = next((af for af in assigned_feedback if af['feedback_id'] == feedback_id),
                                              None)

            if matching_assigned_feedback:
                similarity = matching_assigned_feedback.get('similarity')
                feedback_with_similarity = {
                    'id': feedback_id,
                    'text': feedback.get('text'),
                    'similarity': similarity
                }
                feedbacks.append(feedback_with_similarity)

    return jsonify(feedbacks)


@feedback_bp.route('/get_assigned_tore_feedback/<issue_key>', methods=['GET'])
def get_assigned_tore_feedback(issue_key):
    assigned_feedback = list(collection_assigned_feedback_with_tore.find({'issue_key': issue_key}))

    feedback_ids = [feedback['feedback_id'] for feedback in assigned_feedback]

    feedbacks = []
    for feedback_id in feedback_ids:
        feedback = collection_imported_feedback.find_one({'id': feedback_id})
        if feedback:
            matching_assigned_feedback = next((af for af in assigned_feedback if af['feedback_id'] == feedback_id),
                                              None)

            if matching_assigned_feedback:
                similarity = matching_assigned_feedback.get('similarity')
                feedback_with_similarity = {
                    'id': feedback_id,
                    'text': feedback.get('text'),
                    'similarity': similarity
                }
                feedbacks.append(feedback_with_similarity)

    return jsonify(feedbacks)


@feedback_bp.route('/get_unassigned_feedback/<issue_key>', methods=['GET'])
def get_unassigned_feedback(issue_key):
    assigned_feedback_ids = set(item['feedback_id'] for item in collection_assigned_feedback.find({'issue_key': issue_key}, {'feedback_id': 1}))
    unassigned_feedback = list(collection_imported_feedback.find({'id': {'$nin': list(assigned_feedback_ids)}}))
    for feedback in unassigned_feedback:
        feedback['_id'] = str(feedback['_id'])

    return jsonify(unassigned_feedback)


@feedback_bp.route('/get_unassigned_tore_feedback/<issue_key>', methods=['GET'])
def get_unassigned_tore_feedback(issue_key):
    assigned_feedback_ids = set(item['feedback_id'] for item in collection_assigned_feedback_with_tore.find({'issue_key': issue_key}, {'feedback_id': 1}))
    unassigned_feedback = list(collection_imported_feedback.find({'id': {'$nin': list(assigned_feedback_ids)}}))
    for feedback in unassigned_feedback:
        feedback['_id'] = str(feedback['_id'])

    return jsonify(unassigned_feedback)


@feedback_bp.route('/delete_feedback/<feedback_id>', methods=['DELETE'])
def delete_feedback(feedback_id):
    collection_assigned_feedback.delete_many({'feedback_id': feedback_id})
    collection_assigned_feedback_with_tore.delete_many({'feedback_id': feedback_id})
    collection_imported_feedback.delete_many({'id': feedback_id})
    return jsonify({'error': 'Feedback deleted'})

