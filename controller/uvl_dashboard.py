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

