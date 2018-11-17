#!/user/bin/env python2.7

import unittest
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy
from utils import PolicyAccounting

"""
#######################################################
Test Suite for Accounting
#######################################################
"""

class TestBillingSchedules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        db.session.add(cls.policy)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        pass

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_annual_billing_schedule(self):
        self.policy.billing_schedule = "Annual"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 1)
        self.assertEquals(self.policy.invoices[0].amount_due, self.policy.annual_premium)

    def test_monthly_billing_schedule(self):
        self.policy.billing_schedule = "Monthly"
        self.assertFalse(self.policy.invoices)
        PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 12)
        for invoice in self.policy.invoices:
            self.assertEquals(invoice.amount_due, self.policy.annual_premium / 12)


class TestReturnAccountBalance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_annual_on_eff_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 1200)

    def test_quarterly_on_eff_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 300)

    def test_quarterly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[3].bill_date), 1200)

    def test_quarterly_on_second_installment_bill_date_with_full_payment(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                             date_cursor=invoices[1].bill_date, amount=600))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 0)


class TestChangeBillingSchedule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.commit()

    def setUp(self):
        self.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        self.policy.named_insured = self.test_insured.id
        self.policy.agent = self.test_agent.id
        self.policy.billing_schedule = "Quarterly"

        db.session.add(self.policy)
        db.session.commit()

        self.pa = PolicyAccounting(self.policy.id)
        invoice = self.policy.invoices[0]
        self.payment = self.pa.make_payment(
            contact_id=self.policy.named_insured,
            date_cursor=invoice.bill_date,
            amount=invoice.amount_due
        )

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.delete(self.payment)
        db.session.delete(self.policy)
        db.session.commit()

    def test_valid_billing_schedule(self):
        self.assertEquals(self.pa.return_account_balance(), 900)
        self.assertEquals(len(self.policy.invoices), 4)
        old_invoices = self.policy.invoices
        self.pa.change_billing_schedule("Monthly")
        self.assertEquals(self.pa.return_account_balance(), 900)
        self.assertEquals(len(self.policy.invoices), 16)
        self.assertEquals(self.policy.billing_schedule, "Monthly")
        for invoice in self.policy.invoices:
            if invoice not in old_invoices:
                self.assertEquals(invoice.amount_due, 100)
                self.assertEquals(invoice.policy_id, self.policy.id)
                self.assertEquals(invoice.deleted, False)
        for invoice in old_invoices:
            self.assertEquals(invoice.deleted, True)

    def test_invalid_billing_schedule(self):
        self.assertEquals(self.pa.return_account_balance(), 900)
        self.assertEquals(len(self.policy.invoices), 4)
        old_invoices = self.policy.invoices
        self.pa.change_billing_schedule("Invalid")
        self.assertEquals(self.pa.return_account_balance(), 900)
        self._old_data_remains_unchanged(old_invoices)

    def test_empty_billing_schedule(self):
        self.assertEquals(self.pa.return_account_balance(), 900)
        old_invoices = self.policy.invoices
        self.assertEquals(len(self.policy.invoices), 4)
        self.pa.change_billing_schedule()
        self.assertEquals(self.pa.return_account_balance(), 900)
        self._old_data_remains_unchanged(old_invoices)

    def test_same_billing_schedule(self):
        self.assertEquals(self.pa.return_account_balance(), 900)
        self.assertEquals(len(self.policy.invoices), 4)
        old_invoices = self.policy.invoices
        self.pa.change_billing_schedule("Quarterly")
        self.assertEquals(self.pa.return_account_balance(), 900)
        self._old_data_remains_unchanged(old_invoices)

    def _old_data_remains_unchanged(self, old_invoices):
        self.assertEquals(len(self.policy.invoices), 4)
        self.assertEquals(self.policy.billing_schedule, "Quarterly")
        self.assertEquals(old_invoices, self.policy.invoices)


class TestValidateBillingSchedule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        cls.policy.billing_schedule = "Quarterly"

        db.session.add(cls.policy)
        db.session.commit()

        cls.pa = PolicyAccounting(cls.policy.id)

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.commit()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_valid_billing_schedule(self):
        valid, error = self.pa.validate_billing_schedule("Annual")
        self.assertTrue(valid)
        self.assertEquals(error, '')

    def test_invalid_billing_schedule(self):
        valid, error = self.pa.validate_billing_schedule("Invalid")
        self.assertFalse(valid)
        self.assertEquals(error, 'Invalid billing schedule. Choices are "Annual", "Two-Pay", "Quarterly" and "Monthly"')

    def test_empty_billing_schedule(self):
        valid, error = self.pa.validate_billing_schedule()
        self.assertFalse(valid)
        self.assertEquals(error, 'You need to specify a billing schedule.')

    def test_same_billing_schedule(self):
        valid, error = self.pa.validate_billing_schedule("Quarterly")
        self.assertFalse(valid)
        self.assertEquals(error, 'Policy already has Quarterly billing schedule.')