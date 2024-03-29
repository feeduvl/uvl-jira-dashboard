# flask_backend
#   u v l - j i r a - d a s h b o a r d 
 
## 1. Run Local:

- **Environment Variables:**
  - `password=...`
  - `username=...`
  - `FLASK_ENV=test`

- **Additional Options:** `--host=0.0.0.0 --port=9647`

## 2. For Evaluation (use `evaluationMetrics.py`):

- **Threshold (Standard and TORE):**
  - Run `calculate_metrics()`

- **Requirement Description Length:**
  - Run `calculate_metrics_for_str_length(str(maxNumber), maxNumber, minNumber)` 
    - Change `maxNumber` and `minNumber` for different boundaries

- **Top n Relations:**
  - Run `calculate_metrics_for_top_x(str(max), n)`
    - Change `n` for a different number of relations

- **Old Descriptions:**
  - Use the dataset "Old_descriptions" from `jira_dashboard.saved_data.json`
  - Evaluate with `calculate_metrics()`

- **Nouns Only:**
  - Remove "VERBS" from `get_embeddings()` method in `issue_feedback_relation.py` Line 376

- **Without spaCy:**
  - Change method calls from `get_embeddings()` to `get_embeddings_without_spacy()` in methods:
    - `assign_feedback_to_issues()` Line 423
    - `calculate_feedback_embedding()` Line 448
    - `assign_feedback_to_issues_by_tore()` Line 482
