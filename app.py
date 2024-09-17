from flask import Flask
#need to be activated when run locally
#from flask_cors import CORS
from controller.feedback import feedback_bp
from controller.jira import jira_issue_bp
from controller.issue_feedback_relation import issue_feedback_relation_bp
from controller.dashboard import dashboard_bp

app = Flask(__name__)
#need to be activated when run locally
#CORS(app, resources={r"/*": {"origins": "*"}})

app.register_blueprint(feedback_bp, url_prefix='/hitec/jira/feedback')
app.register_blueprint(jira_issue_bp, url_prefix='/hitec/jira/issues')
app.register_blueprint(issue_feedback_relation_bp, url_prefix='/hitec/jira/issue_feedback')
app.register_blueprint(dashboard_bp, url_prefix='/hitec/uvldashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9647)
