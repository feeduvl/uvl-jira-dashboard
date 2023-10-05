# from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
# import torch
from flask import Flask
#from flask_cors import CORS
from controller.feedback import feedback_bp
from controller.jira import jira_issue_bp

app = Flask(__name__)
#CORS(app, resources={r"/*": {"origins": "http://localhost:8080"}})

# tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
# model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-uncased', num_labels=2)
# model.eval()

app.register_blueprint(feedback_bp, url_prefix='/hitec/jira/feedback')
app.register_blueprint(jira_issue_bp, url_prefix='/hitec/jira/issues')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9646)

# @app.route('/update_all_issues', methods=['GET'])
# def update_all_issues():
#     issues = list(collectionJiraIssues.find())
#
#     for issue in issues:
#         # Suchen Sie Feedbacks, die mit dem aktuellen Issue übereinstimmen
#         query = {"left_feedback_issue": issue["summary"]}
#         feedbacks = list(collectionFeedbackAssigned.find(query))
#
#         if feedbacks:
#             # Finden Sie das Feedback mit dem höchsten match_score
#             highest_score_feedback = max(feedbacks, key=lambda x: x["match_score"])
#
#             # Aktualisieren Sie das Issue mit dem gefundenen Feedback
#             collectionJiraIssues.update_one({"_id": issue["_id"]},
#                                         {"$set": {"right_feedback_issue": highest_score_feedback["right_feedback_issue"]}})
#
#     return jsonify({"message": "Feedback updated"})


# @app.route("/hitec/jira/feedback-assigned/load", methods=["GET"])
# def load_feedback_assigned():
#     feedback = list(collectionFeedbackAssigned.find({}))
#     for element in feedback:
#         element["_id"] = str(element["_id"])
#     return feedback


# @app.route('/save-feedback', methods=['POST'])
# def save_feedback():
#     feedback = request.json.get('feedback')
#
#     # classify with distilbert
#     inputs = tokenizer(feedback, return_tensors='pt', padding=True, truncation=True)
#     with torch.no_grad():
#         outputs = model(**inputs)
#     predicted_label = torch.argmax(outputs.logits).item()
#     predicted_category = "bug" if predicted_label == 0 else "feature"
#
#     # save in MongoDB
#     feedback_data = {'text': feedback, 'category': predicted_category}
#     collectionFeedback.insert_one(feedback_data)
#
#     return jsonify({'message': 'Feedback saved and classified successfully.'})

# @app.route("/hitec/jira/feedback/load", methods=["GET"])
# def load_feedback():
#     feedback_with_tore = list(collectionFeedbackWithToreCategories.find({}))
#     for element in feedback_with_tore:
#         element["_id"] = str(element["_id"])
#     return feedback_with_tore


# @app.route('/save_excel_data', methods=['POST'])
# def save_excel_data():
#     excel_data = request.json.get('data')
#
#     if excel_data:
#         try:
#             for row in excel_data:
#                 id_value = row[1]
#                 feedback_value = row[2]
#                 collectionFeedback.insert_one(
#                     {'ID': id_value, 'Feedback': feedback_value})  # Jede Zeile einzeln in die Datenbank einfügen
#             return jsonify({'message': 'Excel data saved successfully'})
#         except Exception as e:
#             return jsonify({'error': str(e)}), 500
#     else:
#         return jsonify({'error': 'No data provided'}), 400


# @app.route('/import_excel_to_mongodb', methods=['GET'])
# def import_excel_to_mongodb():
#     try:
#         # Read the Excel file into a Pandas DataFrame
#         excel_data = pd.read_excel('Komoot_AppReview.xlsx')
#
#         # Create a list to hold all the data
#         all_data = []
#
#         # Iterate over the rows of the DataFrame
#         for _, row in excel_data.iterrows():
#             document_data = {
#                 'text': row[1],
#                 'id': row[0]
#             }
#             all_data.append(document_data)
#
#         # Create the main document with all the data
#         main_document = {
#             'name': 'Komoot_AppReview',
#             'documents': all_data
#         }
#
#         # Insert the main document into MongoDB
#         collectionKomootFeedback.insert_one(main_document)
#
#         return jsonify({'message': 'Data successfully imported into MongoDB'})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


# @app.route('/hitec/jira/upload_feedback', methods=['POST'])
# def upload_feedback():
#     try:
#         uploaded_json = request.get_json()
#
#         collectionFeedback.insert_one(uploaded_json)
#         load_feedback()
#         return jsonify({'message': 'Upload succeeded'})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
