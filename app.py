from flask import Flask
from flask_cors import CORS
from controller.feedback import feedback_bp
from controller.jira import jira_issue_bp
from controller.issue_feedback_relation import issue_feedback_relation_bp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:8080"}})

app.register_blueprint(feedback_bp, url_prefix='/hitec/jira/feedback')
app.register_blueprint(jira_issue_bp, url_prefix='/hitec/jira/issues')
app.register_blueprint(issue_feedback_relation_bp, url_prefix='/hitec/jira/issue_feedback')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9647)
