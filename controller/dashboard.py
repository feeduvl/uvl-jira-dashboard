from transformers import DistilBertTokenizer, DistilBertModel
from flask import jsonify, Blueprint, request
import spacy
from mongo import mongo_db

collection_jira_issues = mongo_db.collection_jira_issues
collection_assigned_feedback = mongo_db.collection_assigned_feedback
collection_imported_feedback = mongo_db.collection_imported_feedback
collection_feedback = mongo_db.collection_feedback
collection_saved_data = mongo_db.collection_saved_data
collection_annotations = mongo_db.collection_annotations

# load spacy library
nlp = spacy.load("en_core_web_sm")

dashboard_bp = Blueprint('dashboard', __name__)

# load tokenizer and distilbert model
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
model = DistilBertModel.from_pretrained('distilbert-base-uncased')


@dashboard_bp.route('/create_dashboard/<name>/<type>', methods=['POST'])
def create_dashboard(name, dashboard_type):
    if collection_saved_data.find_one({'name': name}):
        return jsonify({'error': 'Name already exists!'}), 400

    combined_data = {
        'name': name,
        'datasets': [],
        'type': dashboard_type,
        'threshold': "",
        'classifier': "",
        'imported_feedback': [],
        'jira_issues': [],
        'assigned_feedback': [],
        'annotation': [],
        'classifier_detail': "",
    }
    collection_imported_feedback.delete_many({})
    collection_jira_issues.delete_many({})
    collection_assigned_feedback.delete_many({})
    collection_saved_data.insert_one(combined_data)

    return jsonify({'message': 'Saved successfully'})


@dashboard_bp.route('/restore_data/<name>', methods=['GET'])
def restore_data(name):
    saved_data = collection_saved_data.find_one({'name': name})

    if saved_data:
        data_imported_feedback = saved_data['imported_feedback']
        data_jira_issues = saved_data['jira_issues']
        data_assigned_feedback = saved_data['assigned_feedback']
        data_annotation = saved_data['annotation']

        collection_imported_feedback.delete_many({})
        collection_jira_issues.delete_many({})
        collection_assigned_feedback.delete_many({})

        for item in data_imported_feedback:
            collection_imported_feedback.insert_one(item)

        for item in data_jira_issues:
            collection_jira_issues.insert_one(item)

        for item in data_assigned_feedback:
            collection_assigned_feedback.insert_one(item)

        if data_annotation:
            collection_annotations.update_one(
                {"name": name},
                {"$set": data_annotation},
                upsert=True
            )

        response = {
            'message': 'restored successful.',
            'type': saved_data['type'],
            'datasets': saved_data['datasets'],
            'name': name,
            'classifier': saved_data['classifier'],
            'classifier_detail': saved_data['classifier_detail'],
            'threshold': saved_data['threshold']
        }
        return jsonify(response)
    else:
        return jsonify({'error': 'dataset not found.'}), 400


@dashboard_bp.route('/return_dashboard/<name>', methods=['GET'])
def return_dashboard(name):
    saved_data = collection_saved_data.find_one({'name': name})

    if saved_data:
        data_imported_feedback = saved_data['imported_feedback']
        data_jira_issues = saved_data['jira_issues']
        data_assigned_feedback = saved_data['assigned_feedback']
        data_annotation = saved_data['annotation']

        if data_annotation:
            response = {
                    'message': 'Usage Information Dashboard return.',
                    'type': saved_data['type'],
                    'datasets': saved_data['datasets'],
                    'name': name,
                    'classifier': saved_data['classifier'],
                    'classifier_detail': saved_data['classifier_detail'],
                    'annotation': data_annotation
                }       
        else:
            response = {
                'message': 'Relation Dashboard return.',
                'type': saved_data['type'],
                'datasets': saved_data['datasets'],
                'name': name,
                'imported_feedback': data_imported_feedback,
                'jira_issues': data_jira_issues,
                'assigned_feedback': data_assigned_feedback,
            }   
            
        return jsonify(response)
    else:
        return jsonify({'error': 'dataset not found.'}), 400

@dashboard_bp.route('/save_data/<name>', methods=['POST'])
def save_data(name):
    print("save data")
    data = request.get_json()

    data_imported_feedback = list(collection_imported_feedback.find())
    data_jira_issues = list(collection_jira_issues.find())
    data_assigned_feedback = list(collection_assigned_feedback.find())
    data_annotation = collection_annotations.find_one({'name': name})
    datasets_with_dates = []
    for dataset in data.get("datasets"):
        dataset_with_date = {'name': dataset,
                            'uploaded_at': collection_feedback.find_one({"name": dataset}).get('uploaded_at')}
        datasets_with_dates.append(dataset_with_date)

    combined_data = {
        'name': name,
        'imported_feedback': data_imported_feedback,
        'jira_issues': data_jira_issues,
        'assigned_feedback': data_assigned_feedback,
        'datasets': datasets_with_dates,
        'type': data.get("type"),
        'annotation': data_annotation,
        'classifier': data.get("classifier"),
        'classifier_detail': data.get("classifier_detail"),
        'threshold': data.get("threshold")
    }
    print(list(collection_imported_feedback.find()))
    print(combined_data)
    if collection_saved_data.find_one({'name': name}):
        collection_saved_data.update_one(
            {"name": name},
            {"$set": combined_data}
        )
    else:
        collection_saved_data.insert_one(combined_data)

    return jsonify({'message': 'Saved successfully'})


@dashboard_bp.route('/get_saved_data_names', methods=['GET'])
def get_unique_names():
    # get names of saved data
    saved_data = list(collection_saved_data.find({}, {'_id': 0, 'name': 1}))
    unique_names = set(item['name'] for item in saved_data if 'name' in item)
    return jsonify(list(unique_names))
