from pymongo import MongoClient

client = MongoClient("mongodb://mongo:27017/")

dbIssues = client["jira_dashboard"]
collection_jira_issues = dbIssues["jira_issue"]
collection_imported_feedback = dbIssues["imported_feedback"]
collection_assigned_feedback = dbIssues["assigned_feedback"]
collection_assigned_feedback_with_tore = dbIssues["assigned_feedback_with_tore"]
collection_saved_data = dbIssues["saved_data"]

dbFeedback = client["concepts_data"]
collection_feedback = dbFeedback["dataset"]
collection_annotations = dbFeedback["annotation"]
# collection_feedback = dbFeedback["test_ds"]
# collection_annotations = dbFeedback["test_anno"]