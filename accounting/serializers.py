from models import Contact


def get_policy_name_insured(contact_id):
    return Contact.query.filter_by(id=contact_id).one()


def get_policy_agent(contact_id):
    return Contact.query.filter_by(id=contact_id).one()


def policy_serializer(policy, account_balance=None):
    named_insured = get_policy_name_insured(policy.named_insured)
    agent = get_policy_agent(policy.agent)
    return {
        'id': policy.id,
        'name': policy.policy_number,
        'effectiveDate': policy.effective_date.strftime('%d/%m/%Y'),
        'status': policy.status,
        'statusChangeDescription': policy.status_change_description or 'None',
        'statusChangeDate': policy.status_change_date or 'None',
        'billingSchedule': policy.billing_schedule,
        'annualPremium': policy.annual_premium,
        'namedInsured': named_insured.name,
        'agent': agent.name,
        'accountBalance': account_balance
    }


def invoice_serializer(invoice):
    return {
        'id': invoice.id,
        'billDate': invoice.bill_date.strftime('%d/%m/%Y'),
        'dueDate': invoice.due_date.strftime('%d/%m/%Y'),
        'cancelDate': invoice.cancel_date.strftime('%d/%m/%Y'),
        'amountDue': invoice.amount_due
    }


def payment_serializer(payment):
    return {
        'id': payment.id,
        'amountPaid': payment.amount_paid,
        'transactionDate': payment.transaction_date.strftime('%d/%m/%Y')
    }
