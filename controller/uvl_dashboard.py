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
    data = request.get_json()
    if collection_saved_data.find_one({'name': name}):
        return jsonify({'error': 'Name already exists!'}), 400

    combined_data = {
        'name': name,
        'imported_feedback': [],
        'jira_issues': [],
        'assigned_feedback': [],
        'datasets': [],
        'type': type
    }
    collection_imported_feedback.delete_many({})
    collection_jira_issues.delete_many({})
    collection_assigned_feedback.delete_many({})
    # TODO: Clear annotation table
    collection_saved_data.insert_one(combined_data)

    return jsonify({'message': 'Saved successfully'})