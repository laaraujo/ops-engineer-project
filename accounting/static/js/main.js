function Payment(data) {
    this.id = ko.observable(data.id);
    this.amountPaid = ko.observable(data.amountPaid);
    this.transactionDate = ko.observable(data.transactionDate);
}

function Invoice(data) {
    this.id = ko.observable(data.id);
    this.billDate = ko.observable(data.billDate);
    this.dueDate = ko.observable(data.dueDate);
    this.cancelDate = ko.observable(data.cancelDate);
    this.amountDue = ko.observable(data.amountDue);
}

function Policy(data) {
    this.id = ko.observable(data.id);
    this.name = ko.observable(data.name);
    this.effectiveDate = ko.observable(data.effectiveDate);
    this.status = ko.observable(data.status);
    this.statusChangeDescription = ko.observable(data.statusChangeDescription);
    this.statusChange_date = ko.observable(data.statusChangeDate);
    this.billingSchedule = ko.observable(data.billingSchedule);
    this.annualPremium = ko.observable(data.annualPremium);
    this.namedInsured = ko.observable(data.namedInsured);
    this.agent = ko.observable(data.agent);
    this.accountBalance = ko.observable(data.accountBalance);
}

function PolicyViewModel() {
    var self = this;

    self.policyList = ko.observableArray([]);
    self.policy = ko.observable();
    self.invoices = ko.observableArray([]);
    self.payments = ko.observableArray([]);
    self.policyId = ko.observable();
    self.dateCursor = ko.observable();
    self.errorMessage = ko.observable();

    self.showPolicyDetail = function(){
        self.errorMessage('')
        var data = {
            'dateCursor': self.dateCursor
        }

        $.post("/policies/" + self.policyId(), data)
            .done(
                function(allData) {
                    self.policy( new Policy( allData['policy'] ) );
                    var mappedInvoices = $.map(allData['invoices'], function(item) { return new Invoice(item) });
                    self.invoices(mappedInvoices);
                    var mappedPayments = $.map(allData['payments'], function(item) { return new Payment(item) });
                    self.payments(mappedPayments);
                })
            .fail(
                function(err) {
                    self.errorMessage('Invalid Policy ID or date')
                });
    }

    self.showPolicyList = function() {
        self.policyId('')
        self.errorMessage('')
        var date = new Date();
        var dateString = date.getFullYear() + "-" + (date.getMonth()+1) + "-" + date.getDate()
        self.dateCursor(dateString)
        $.getJSON("/policies", function(allData) {
            self.policy(false)
            var mappedPolicies = $.map(allData['policies'], function(item) { return new Policy(item) });
            self.policyList(mappedPolicies);
        });
    }

    self.clickPolicy = function(policy) {
        self.policyId(policy.id());
        self.showPolicyDetail();
    }

    self.showPolicyList();
    
}

ko.applyBindings(new PolicyViewModel())