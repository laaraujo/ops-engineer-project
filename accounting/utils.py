#!/user/bin/env python2.7

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy

"""
#######################################################
This is the base code for the engineer project.
#######################################################
"""

class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.
    """
    def __init__(self, policy_id):
        self.policy = Policy.query.filter_by(id=policy_id).one()

        if not self.policy.invoices:
            self.make_invoices()

    def return_account_balance(self, date_cursor=None):
        """
        :param date_cursor: Date at which the account balance is to be calculated.
        :return: Account balance / How much is left to pay.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= date_cursor, Invoice.deleted == False)\
                                .order_by(Invoice.bill_date)\
                                .all()
        due_now = 0
        for invoice in invoices:
            due_now += invoice.amount_due

        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()
        for payment in payments:
            due_now -= payment.amount_paid

        return due_now

    def change_billing_schedule(self, billing_schedule=None):
        """
        Changes billing schedle of the already existing policy.
        :param billing_schedule: New billing schedule.
        """

        valid_billing_schedule, error = self.validate_billing_schedule(billing_schedule)

        if not valid_billing_schedule:
            print(error)
            return

        old_invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                    .filter(Invoice.deleted == False)\
                                    .all()

        for invoice in old_invoices:
            invoice.deleted = True

        self.policy.billing_schedule = billing_schedule
        self.make_invoices()

        db.session.commit()

        print('Policy billing schedule changed.')

    def validate_billing_schedule(self, billing_schedule=None):
        if not billing_schedule:
            return False, 'You need to specify a billing schedule.'

        if self.policy.billing_schedule == billing_schedule:
            return False, 'Policy already has %s billing schedule.' % billing_schedule

        if billing_schedule not in ['Annual', 'Two-Pay', 'Quarterly', 'Monthly']:
            return False, 'Invalid billing schedule. Choices are "Annual", "Two-Pay", "Quarterly" and "Monthly"'

        return True, ''

    def make_payment(self, contact_id=None, date_cursor=None, amount=0):
        """
        :param contact_id: Foreign Key to Contact instance, defaults to policy's named_insured.
        :param date_cursor: Payment date, defaults to today's date.
        :param amount: Payment amount.
        :return: Payment instance.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()

        if not contact_id:
            try:
                contact_id = self.policy.named_insured
            except:
                pass

        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        db.session.add(payment)
        db.session.commit()

        return payment

    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        """
         If this function returns true, an invoice
         on a policy has passed the due date without
         being paid in full. However, it has not necessarily
         made it to the cancel_date yet.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()

        if self.return_account_balance(date_cursor) > 0:
            try:
                Invoice.query.filter_by(policy_id=self.policy.id) \
                    .filter(Invoice.due_date < date_cursor, date_cursor < Invoice.cancel_date, Invoice.deleted == False) \
                    .one()
                return True
            except:
                return False
        return False

    def change_policy_status(self, date_cursor=None, new_status=None, description=None):
        """
        :param date_cursor: Date at which status update is to be done.
        :param new_status: New status for the policy.
        :param description: Status change description
        :return: True if policy's changed, False and error message otherwise.
        """
        valid_policy_status, error = self.validate_status(new_status)

        if not valid_policy_status:
            return False, error

        if not date_cursor:
            date_cursor = datetime.now().date()
        elif date_cursor > datetime.now().date():
            return False, "You cannot change a policy's status in the future!"

        self.policy.status = new_status
        self.policy.status_change_date = date_cursor
        self.policy.status_change_description = description

        db.session.commit()

        return True, ''

    def validate_status(self, status=None):
        """
        :param status: Status that wants to be validated (string).
        :return: True if status is valid and False and error message otherwise.
        """
        if not status:
            return False, 'You need to specify a status"'

        if status not in ['Active', 'Canceled', 'Expired']:
            return False, 'Invalid status. Choices are "Canceled", "Active" and "Expired"'

        if status == self.policy.status:
            return False, 'Policy already has %s status.' % status

        return True, ''

    def cancel_policy(self, date_cursor=None, description=None):
        """
        Cancels policy if it it meets cancelation requirements.
        :param date_cursor: Date at which policy wants to be canceled, will default to now.
        :param description: Cancelation description.
        """

        if not date_cursor:
            date_cursor = datetime.now().date()
        elif date_cursor > datetime.now().date():
            print('You cannot cancel a policy in the future!')
            return

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.cancel_date <= date_cursor, Invoice.deleted == False)\
                                .order_by(Invoice.bill_date)\
                                .all()

        for invoice in invoices:
            if self.return_account_balance(invoice.cancel_date):
                status_changed, error = self.change_policy_status(date_cursor, 'Canceled', description)
                if not status_changed:
                    print(error)
                else:
                    print('Policy canceled successfully.')
                return
        print('Policy should not be canceled')
        return


    def make_invoices(self):
        """
        Creates invoices depending on policy's billing_schedule.
        """

        billing_schedules = {'Annual': 1, 'Two-Pay': 2, 'Quarterly': 4, 'Monthly': 12}
        months_after_eff_date_dict = {'Annual': 12, 'Two-Pay': 6, 'Quarterly': 3, 'Monthly': 1}

        invoices = []
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date, #bill_date
                                self.policy.effective_date + relativedelta(months=1), #due
                                self.policy.effective_date + relativedelta(months=1, days=14), #cancel
                                self.policy.annual_premium)
        invoices.append(first_invoice)

        if self.policy.billing_schedule in billing_schedules:
            invoices_quantity = billing_schedules.get(self.policy.billing_schedule)
            first_invoice.amount_due = first_invoice.amount_due / invoices_quantity
            months_between_invoices = months_after_eff_date_dict.get(self.policy.billing_schedule)
            for i in range(1, invoices_quantity):
                a = i * months_between_invoices
                bill_date = self.policy.effective_date + relativedelta(months=a)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        else:
            print "You have chosen a bad billing schedule."

        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()


################################
# The functions below are for the db and 
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"

def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.named_insured = john_doe_insured.id
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    p4 = Policy('Policy Four', date(2015, 2, 1), 500)
    p4.billing_schedule = 'Two-Pay'
    p4.named_insured = ryan_bucket.id
    p4.agent = john_doe_agent.id
    policies.append(p4)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()

