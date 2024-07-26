from flask import jsonify, Blueprint, request
import re
import logging
from mongo import mongo_db

collection_feedback = mongo_db.collection_feedback
collection_assigned_feedback = mongo_db.collection_assigned_feedback
collection_annotations = mongo_db.collection_annotations

feedback_bp = Blueprint('feedback', __name__)


@feedback_bp.route('/get_feedback_without_assigned_elements/<feedback_name>', methods=['GET'])
def get_issues_without_assigned_elements(feedback_name):
    unassigned_feedback = []
    # find all feedback of the used feedback dataset by name
    feedback_document = collection_feedback.find_one({"name": feedback_name})
    # get the feedback array of the dataset with all feedback texts
    feedback_collection = feedback_document.get("feedback", [])
    # iterate through all feedback and find the ones who were not assigned via standard or TORE
    for feedback in feedback_collection:
        feedback_id = feedback.get('id')

        assigned_feedback = collection_assigned_feedback.find_one({'feedback_id': feedback_id})

        if not assigned_feedback:
            unassigned_feedback.append(feedback)

    # pagination
    page = int(request.args.get('page', default=1))
    size = int(request.args.get('size', default=-1))

    if size == -1:
        size = len(unassigned_feedback)

    start_index = (page - 1) * size
    end_index = min(start_index + size, len(unassigned_feedback))

    paginated_unassigned_issues = unassigned_feedback[start_index:end_index]

    return jsonify({
        "unassigned_feedback": paginated_unassigned_issues,
        "currentPage": page,
        "totalItems": len(unassigned_feedback),
        "totalPages": (len(unassigned_feedback) + size - 1) // size
    })


@feedback_bp.route("/load/<feedback_name>", methods=["GET"])
def load_feedback(feedback_name):
    try:
        # get chosen feedback dataset
        selected_document = collection_feedback.find_one({"name": feedback_name})
        # if the feedback already found, then return
        if selected_document:
            return jsonify({"message": "found feedback"})
        # if the feedback not in collection, get it from the collection of all available feedback datasets
        else: #TODO: Eigentlich dürfte dieser Fall nie mehr auftreten
            # find chosen feedback dataset in all available datasets
            feedback = collection_feedback.find_one({"name": feedback_name})
            ids_and_texts = []
            # get feedback id and text of all feedback from datasets
            documents = feedback.get('documents', [])
            for doc in documents:
                doc_id = doc.get('id')
                doc_text = doc.get('text')
                # remove star review, hashtags and line breaks from text
                filtered_text = re.sub(r'^\d+\s*', '', doc_text)
                filtered_text = re.sub(r'[#\\]', '', filtered_text)
                filtered_text = re.sub(r'\r\n|\r|\n', ' ', filtered_text)
                id_and_text = {
                    'id': doc_id,
                    'text': filtered_text,
                }
                ids_and_texts.append(id_and_text)
            imported_feedback = {
                'name': feedback_name,
                'documents': ids_and_texts
            }
            # save the new feedback dataset in collection
            collection_feedback.insert_one(imported_feedback)
            return jsonify(imported_feedback)
    except Exception as e:
        return jsonify({"message": str(e)})


@feedback_bp.route('/get_feedback', methods=['GET'])
def get_feedback():
    # get feedback to show in table with pagination
    feedback_name = request.args.get("selectedFeedbackFileName")
    feedback_document = collection_feedback.find_one({"name": feedback_name})
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

            return jsonify(res)
        except Exception as e:
            return jsonify({"error": "Internal Server Error"}), 500
    else:
        res = {
            "feedback": [],
            "currentPage": 0,
            "totalItems": 0,
            "totalPages": 0
        }
        return jsonify(res)


@feedback_bp.route('/get_feedback_names', methods=['GET'])
def get_feedback_names():
    # find all feedback names in all available feedback datasets
    feedback = collection_feedback.find({})
    logging.error(collection_feedback.find({}))
    names_list = [doc["name"] for doc in feedback]
    return names_list


@feedback_bp.route('/get_annotations_names/<selectedFeedbackFileName>', methods=['GET'])
def get_annotations_names(selectedFeedbackFileName):
    # find annotation dataset names that are made for the chosen feedback in all available annotation datasets
    annotations = collection_annotations.find({"dataset": selectedFeedbackFileName})
    names_list = [doc["name"] for doc in annotations]
    return names_list


@feedback_bp.route('/get_assigned_feedback/<issue_key>', methods=['GET'])
def get_assigned_feedback(issue_key):
    try:
        # pagination
        page = int(request.args.get("page", default=1))
        size = int(request.args.get("size", default=-1))
        # find all relations for the requirement
        assigned_feedback = list(collection_assigned_feedback.find({'issue_key': issue_key}))
        # sort the list
        assigned_feedback = sorted(assigned_feedback, key=lambda x: x.get('similarity', 0), reverse=True)
        # filter all feedback to find those how are assigned to the requirement
        feedback_ids = [feedback['feedback_id'] for feedback in assigned_feedback]

        if size == -1:
            size = len(feedback_ids)

        start_index = (page - 1) * size
        end_index = min(start_index + size, len(feedback_ids))

        feedbacks = []
        # get feedback ids with start and end index for pagination
        for feedback_id in feedback_ids[start_index:end_index]:
            feedback = collection_feedback.find_one({'feedback.id': feedback_id})
            if feedback:
                feedback_array = feedback.get("feedback", [])
                # find all feedback
                matching_feedback = next((fb for fb in feedback_array if fb.get('id') == feedback_id), None)
                # find all feedback that is assigned
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

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500


@feedback_bp.route('/get_unassigned_feedback/<issue_key>/<feedback_name>', methods=['GET'])
def get_unassigned_feedback(issue_key, feedback_name):
    # get all feedback ids that are assigned to a specific requirement
    assigned_feedback_ids = set(
        item['feedback_id'] for item in collection_assigned_feedback.find({'issue_key': issue_key}, {'feedback_id': 1}))
    feedback_document = collection_feedback.find_one({"name": feedback_name})
    feedback_array = feedback_document.get("feedback", [])
    unassigned_feedback = []
    # get all feedback that is not assigned to the requirement
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
    # all unassigned feedback for the chosen requirement with pagination
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
    # delete all assigned elements of the feedback
    collection_assigned_feedback.delete_many({'feedback_id': feedback_id})
    # find the feedback dataset and remove it from this collection
    feedback_document = collection_feedback.find_one({"name": feedback_name})
    feedback_array = feedback_document.get("feedback", [])
    updated_feedback = [feedback for feedback in feedback_array if feedback['id'] != feedback_id]
    collection_feedback.update_one({'_id': feedback_document['_id']}, {'$set': {'feedback': updated_feedback}})

    return jsonify({'message': 'Feedback deleted'})


@feedback_bp.route('/delete_all_feedback/<feedback_name>', methods=['DELETE'])
def delete_all_feedback(feedback_name):
    # delete all relations
    collection_assigned_feedback.delete_many({})
    # remove all feedback from this collection
    feedback_document = collection_feedback.find_one({"name": feedback_name})
    if feedback_document:
        collection_feedback.delete_one({"_id": feedback_document["_id"]})
        return jsonify({"message": "Feedback deleted."})
    else:
        return jsonify({"message": "Dataset not found."}, 404)
