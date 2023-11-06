from flask import jsonify, Blueprint, request
from pymongo import MongoClient
import re

feedback_bp = Blueprint('feedback', __name__)

client = MongoClient("mongodb://mongo:27017/")
dbIssues = client["jira_dashboard"]
dbFeedback = client["concepts_data"]
collection_feedback = dbFeedback["dataset"]
collection_annotations = dbFeedback["annotation"]
collection_imported_feedback = dbIssues["imported_feedback"]
collection_assigned_feedback = dbIssues["assigned_feedback"]
collection_assigned_feedback_with_tore = dbIssues["assigned_feedback_with_tore"]


@feedback_bp.route('/assign_tore_to_feedback/<annotation_name>/<feedback_name>', methods=['GET'])
def set_tore_categories(annotation_name, feedback_name):
    try:
        feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
        feedback_collection = feedback_document.get("feedback", [])
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
                                feedback["tore"] = set_issue_type_by_tore_category(tore_list)
                                tore_list.clear()
        update_criteria = {"_id": feedback_document["_id"]}
        update_operation = {"$set": {"feedback": feedback_collection}}
        collection_imported_feedback.update_one(update_criteria, update_operation)
        return jsonify({"message": "tore assignment was successful"})
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
        selected_document = collection_imported_feedback.find_one({"dataset": feedback_name})
        if selected_document:
            return jsonify({"message": "found feedback"})
        else:
            feedback_collection = collection_feedback.find({})
            ids_and_texts = []
            imported_feedback = []
            for feedback in feedback_collection:
                feedback_name_ds = feedback.get('name')
                if feedback_name_ds == feedback_name:
                    documents = feedback.get('documents', [])
                    for doc in documents:
                        doc_id = doc.get('id')
                        doc_text = doc.get('text')
                        filtered_text = re.sub(r'^\d+\s+#{3}|#{3}$', '', doc_text)
                        filtered_text = re.sub(r'\r\n|\r|\n', ' ', filtered_text)

                        id_and_text = {
                            'id': doc_id,
                            'text': filtered_text,
                        }
                        ids_and_texts.append(id_and_text)
                    imported_feedback = {
                        'dataset': feedback_name_ds,
                        'feedback': ids_and_texts
                    }
                    collection_imported_feedback.insert_one(imported_feedback)
            return jsonify(imported_feedback)
    except Exception as e:
        return jsonify({"message": str(e)})


@feedback_bp.route('/get_feedback', methods=['GET'])
def get_feedback():
    feedback_name = request.args.get("selectedFeedbackFileName")
    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    if feedback_name and feedback_document:
        try:
            feedback_array = feedback_document.get("feedback", [])

            page = int(request.args.get("page", default=1))
            size = int(request.args.get("size", default=-1))

            if size == -1:
                size = len(feedback_array)

            skip = (page - 1) * size
            feedback_list = feedback_array[skip:skip + size]

            if feedback_list:
                total_items = len(feedback_array)
                total_pages = (total_items + size - 1)
                res = {
                    "feedback": feedback_list,
                    "currentPage": page,
                    "totalItems": total_items,
                    "totalPages": total_pages
                }
            else:
                res = {
                    "feedback": feedback_list,
                    "currentPage": page,
                    "totalItems": 0,
                    "totalPages": 0
                }

            return jsonify(res), 200
        except Exception as e:
            return jsonify({"error": "Internal Server Error"}), 500
    else:
        res = {
            "feedback": [],
            "currentPage": 0,
            "totalItems": 0,
            "totalPages": 0
        }
        return jsonify(res), 200



@feedback_bp.route('/get_feedback_names', methods=['GET'])
def get_feedback_names():
    feedback = collection_feedback.find({})
    names_list = [doc["name"] for doc in feedback]
    return names_list


@feedback_bp.route('/get_annotations_names/<selectedFeedbackFileName>', methods=['GET'])
def get_annotations_names(selectedFeedbackFileName):
    annotations = collection_annotations.find({"dataset": selectedFeedbackFileName})
    names_list = [doc["name"] for doc in annotations]
    return names_list


@feedback_bp.route('/get_assigned_feedback/<issue_key>', methods=['GET'])
def get_assigned_feedback(issue_key):
    try:
        page = int(request.args.get("page", default=1))
        size = int(request.args.get("size", default=-1))

        assigned_feedback = list(collection_assigned_feedback.find({'issue_key': issue_key}))
        feedback_ids = [feedback['feedback_id'] for feedback in assigned_feedback]

        if size == -1:
            size = len(feedback_ids)

        start_index = (page - 1) * size
        end_index = min(start_index + size, len(feedback_ids))

        feedbacks = []
        for feedback_id in feedback_ids[start_index:end_index]:
            feedback = collection_imported_feedback.find_one({'feedback.id': feedback_id})
            if feedback:
                feedback_array = feedback.get("feedback", [])
                matching_feedback = next((fb for fb in feedback_array if fb.get('id') == feedback_id), None)
                matching_assigned_feedback = next((af for af in assigned_feedback if af['feedback_id'] == feedback_id), None)
                if matching_assigned_feedback:
                    similarity = matching_assigned_feedback.get('similarity')
                    feedback_with_similarity = {
                        'id': feedback_id,
                        'text': matching_feedback.get('text'),
                        'similarity': similarity
                    }
                    feedbacks.append(feedback_with_similarity)

        total_items = len(feedback_ids)
        total_pages = (total_items + size - 1) // size

        response = {
            "feedback": feedbacks,
            "currentPage": page,
            "totalItems": total_items,
            "totalPages": total_pages
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500


@feedback_bp.route('/get_assigned_tore_feedback/<issue_key>', methods=['GET'])
def get_assigned_tore_feedback(issue_key):
    try:
        page = int(request.args.get("page", default=1))
        size = int(request.args.get("size", default=-1))

        assigned_feedback = list(collection_assigned_feedback_with_tore.find({'issue_key': issue_key}))
        feedback_ids = [feedback['feedback_id'] for feedback in assigned_feedback]

        if size == -1:
            size = len(feedback_ids)

        start_index = (page - 1) * size
        end_index = min(start_index + size, len(feedback_ids))

        feedbacks = []
        for feedback_id in feedback_ids[start_index:end_index]:
            feedback = collection_imported_feedback.find_one({'feedback.id': feedback_id})
            if feedback:
                feedback_array = feedback.get("feedback", [])
                matching_feedback = next((fb for fb in feedback_array if fb.get('id') == feedback_id), None)
                matching_assigned_feedback = next((af for af in assigned_feedback if af['feedback_id'] == feedback_id),
                                                  None)
                if matching_assigned_feedback:
                    similarity = matching_assigned_feedback.get('similarity')
                    feedback_with_similarity = {
                        'id': feedback_id,
                        'text': matching_feedback.get('text'),
                        'similarity': similarity
                    }
                    feedbacks.append(feedback_with_similarity)
        total_items = len(feedback_ids)
        total_pages = (total_items + size - 1) // size

        response = {
            "feedback": feedbacks,
            "currentPage": page,
            "totalItems": total_items,
            "totalPages": total_pages
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500


@feedback_bp.route('/get_unassigned_tore_feedback/<issue_key>/<feedback_name>', methods=['GET'])
def get_unassigned_tore_feedback(issue_key, feedback_name):
    assigned_feedback_ids = set(item['feedback_id'] for item in collection_assigned_feedback_with_tore.find({'issue_key': issue_key}, {'feedback_id': 1}))
    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    feedback_array = feedback_document.get("feedback", [])
    unassigned_feedback = []
    for feedback_entry in feedback_array:
        feedback_id = feedback_entry.get("id")
        if feedback_id not in assigned_feedback_ids:
            unassigned_feedback.append(feedback_entry)
    page = int(request.args.get('page', default=1))
    size = int(request.args.get('size', default=-1))

    if size == -1:
        size = len(unassigned_feedback)

    start_index = (page - 1) * size
    end_index = min(start_index + size, len(unassigned_feedback))

    paginated_unassigned_feedback = unassigned_feedback[start_index:end_index]

    total_items = len(unassigned_feedback)
    total_pages = (total_items + size - 1) // size

    response = {
        "feedback": paginated_unassigned_feedback,
        "currentPage": page,
        "totalItems": total_items,
        "totalPages": total_pages
    }

    return jsonify(response)


@feedback_bp.route('/get_unassigned_feedback/<issue_key>/<feedback_name>', methods=['GET'])
def get_unassigned_feedback(issue_key, feedback_name):
    assigned_feedback_ids = set(item['feedback_id'] for item in collection_assigned_feedback.find({'issue_key': issue_key}, {'feedback_id': 1}))
    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    feedback_array = feedback_document.get("feedback", [])
    unassigned_feedback = []
    for feedback_entry in feedback_array:
        feedback_id = feedback_entry.get("id")
        if feedback_id not in assigned_feedback_ids:
            unassigned_feedback.append(feedback_entry)
    page = int(request.args.get('page', default=1))
    size = int(request.args.get('size', default=-1))
    if size == -1:
        size = len(unassigned_feedback)

    start_index = (page - 1) * size
    end_index = min(start_index + size, len(unassigned_feedback))

    paginated_unassigned_feedback = unassigned_feedback[start_index:end_index]

    total_items = len(unassigned_feedback)
    total_pages = (total_items + size - 1) // size

    response = {
        "feedback": paginated_unassigned_feedback,
        "currentPage": page,
        "totalItems": total_items,
        "totalPages": total_pages
    }

    return jsonify(response)


@feedback_bp.route('/delete_feedback/<feedback_id>/<feedback_name>', methods=['DELETE'])
def delete_feedback(feedback_id, feedback_name):
    collection_assigned_feedback.delete_many({'feedback_id': feedback_id})
    collection_assigned_feedback_with_tore.delete_many({'feedback_id': feedback_id})

    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    feedback_array = feedback_document.get("feedback", [])
    updated_feedback = [feedback for feedback in feedback_array if feedback['id'] != feedback_id]
    collection_imported_feedback.update_one({'_id': feedback_document['_id']}, {'$set': {'feedback': updated_feedback}})

    return jsonify({'message': 'Feedback deleted'})


@feedback_bp.route('/delete_all_feedback/<feedback_name>', methods=['DELETE'])
def delete_all_feedback(feedback_name):
    collection_assigned_feedback.delete_many({})
    collection_assigned_feedback_with_tore.delete_many({})
    feedback_document = collection_imported_feedback.find_one({"dataset": feedback_name})
    if feedback_document:
        collection_imported_feedback.delete_one({"_id": feedback_document["_id"]})
        return jsonify({"message": "Feedback deleted."})
    else:
        return jsonify({"message": "Dataset not found."}, 404)

