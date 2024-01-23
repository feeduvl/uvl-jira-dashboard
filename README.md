# flask_backend
#   u v l - j i r a - d a s h b o a r d 
 
1. run local:
   - Environment Variables:
       - password=...
       - username=...
       - FLASK_ENV=test
   - Additional options: --host=0.0.0.0 --port=9647
2. For Evaluation (use evaluationMetrics.py):
    - Threshold (Standard and TORE): run calculate_metrics()
    - Requirement Description length: run calculate_metrics_for_str_length(str(maxNumber), maxNumber, minNumber) - chang maxNumber and minNumer for different boundaries
    - Top n Relations: run calculate_metrics_for_top_x(str(max), n) - change n for different number of relations
    - Old Descriptions: use dataset "Old_descriptions" from jira_dashboard.saved_data.json - evaluate with calculate_metrics()
    - Nouns only: remove "VERBS" from get_embeddings() method in issue_feedback_relation.py Line 376
    - Without spaCy: change method calls from get_embeddings() to get_embeddings_without_spacy() in methods assign_feedback_to_issues() Line 423, calculate_feedback_embedding() Line 448 and assign_feedback_to_issues_by_tore() Line 482
 
