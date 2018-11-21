# You will probably need more methods from flask but this one is a good start.
from flask import render_template, jsonify, request
from datetime import datetime

# Import things from Flask that we need.
from accounting import app, db

# Import our models
from models import Contact, Invoice, Policy, Payment

# Import serializers
from serializers import policy_serializer, invoice_serializer, payment_serializer

# Import PolicyAccounting
from utils import PolicyAccounting


# Routing for the server.
@app.route("/")
def index():
    # You will need to serve something up here.
    return render_template('index.html')


@app.route("/policies", methods=['GET'])
def get_policies():
    policies = Policy.query.all()
    policies_dictionary = []
    for policy in policies:
        policies_dictionary.append(policy_serializer(policy))
    return jsonify({'policies': policies_dictionary})


@app.route("/policies/<int:policy_id>", methods=['POST'])
def get_policy(policy_id):
    date_cursor = datetime.strptime(request.values.get('dateCursor'), '%Y-%m-%d')
    policy_object = Policy.query.filter_by(id=policy_id).one()

    pa = PolicyAccounting(policy_object.id)
    account_balance = pa.return_account_balance(date_cursor=date_cursor)
    invoices_queryset = Invoice.query.filter_by(policy_id=policy_id).all()
    payments_queryset = Payment.query.filter_by(policy_id=policy_id).all()
    payments, invoices = [], []
    policy = policy_serializer(policy_object, account_balance)

    for payment in payments_queryset:
        payments.append(payment_serializer(payment))

    for invoice in invoices_queryset:
        invoices.append(invoice_serializer(invoice))

    return jsonify({'policy': policy, 'payments': payments, 'invoices': invoices})
