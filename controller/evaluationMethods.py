import pandas as pd
from mongo import (collection_assigned_feedback,
                   collection_assigned_feedback_with_tore,
                   collection_saved_data,
                   collection_jira_issues)

ground_truth = "Ground_truth"


# ground_truth = "ground_test"


class RecallPrecisionCalculator:
    def __init__(self, saved_data_collection, assigned_feedback_collection, jira_issues_collection):
        self.saved_data_collection = saved_data_collection
        self.assigned_feedback_collection = assigned_feedback_collection
        self.jira_issues_collection = jira_issues_collection
        self.results_df = pd.DataFrame(columns=["Issue Key", "Recall", "Precision", "F1-Score"])

    def get_issue_keys_set(self):
        jira_keys_set = set()
        # Iteriere über alle Dokumente in der jira_issues Collection
        for item in self.jira_issues_collection.find():
            issues_array = item.get("issues", [])
            for issue_item in issues_array:
                key = issue_item.get("key")
                if key:
                    jira_keys_set.add(key)
        return list(jira_keys_set)

    def get_feedback_ids(self, collection, issue_key):
        feedback_ids = set()

        for item in collection.find({"issue_key": issue_key}):
            feedback_id = item["feedback_id"]
            feedback_ids.add(feedback_id)

        return feedback_ids

    def calculate_recall(self, true_positives, false_negatives):
        return true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0

    def calculate_precision(self, true_positives, false_positives):
        return true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0

    def calculate_f1_score(self, precision, recall):
        return 2 * ((precision * recall) / (precision + recall)) if (precision + recall) > 0 else 0

    def calculate_metrics(self, name):
        issue_keys_set = self.get_issue_keys_set()

        total_recall = 0
        total_precision = 0
        total_f1 = 0
        avg_assigned_feedback_ids = 0
        for issue_key in issue_keys_set:
            assigned_feedback_ids = self.get_feedback_ids(self.assigned_feedback_collection, issue_key)
            avg_assigned_feedback_ids += len(assigned_feedback_ids)
            document = self.saved_data_collection.find_one({"name": ground_truth})
            assigned_feedback_array = document.get("assigned_feedback", [])
            saved_data_feedback_ids = set()
            for feedback_item in assigned_feedback_array:
                if issue_key in feedback_item.get("issue_key"):
                    feedback_id = feedback_item.get("feedback_id")
                    if feedback_id:
                        saved_data_feedback_ids.add(feedback_id)

            if not assigned_feedback_ids and not saved_data_feedback_ids:
                true_positives = 1
                false_negatives = 0
                false_positives = 0
            else:
                true_positives = len(assigned_feedback_ids.intersection(saved_data_feedback_ids))
                false_negatives = len(saved_data_feedback_ids.difference(assigned_feedback_ids))
                false_positives = len(assigned_feedback_ids.difference(saved_data_feedback_ids))

            recall = self.calculate_recall(true_positives, false_negatives)
            total_recall += recall
            precision = self.calculate_precision(true_positives, false_positives)
            total_precision += precision
            f1_score = self.calculate_f1_score(precision, recall)
            total_f1 += f1_score

            self.results_df = pd.concat([self.results_df, pd.DataFrame(
                {"Issue Key": [issue_key], "Recall": [recall], "Precision": [precision], "F1-Score": [f1_score]})],
                                        ignore_index=True, sort=False)

        avg_recall = total_recall / len(issue_keys_set)
        avg_precision = total_precision / len(issue_keys_set)
        avg_f1_score = total_f1 / len(issue_keys_set)

        avg_df = pd.DataFrame({
            "Issue Key": ["Average"],
            "Recall": [avg_recall],
            "Precision": [avg_precision],
            "F1-Score": [avg_f1_score],
            "Avg-Assigned": [avg_assigned_feedback_ids/111],
            "Similarity-limit": [name]
        })
        self.results_df = pd.concat([self.results_df, avg_df], ignore_index=True)

        try:
            self.results_df.to_csv(f"{name}.csv", index=False)
            print(f"CSV-Datei erfolgreich erstellt: {name}.csv")
        except Exception as e:
            print(f"Fehler beim Erstellen der CSV-Datei: {e}")


if __name__ == '__main__':
    calculator = RecallPrecisionCalculator(collection_saved_data, collection_assigned_feedback, collection_jira_issues)
    calculator.calculate_metrics("sim")
