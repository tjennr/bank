from transaction import Transaction
from decimal import Decimal, ROUND_HALF_UP
import logging
import calendar
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship, backref, mapped_column
from db_base import *

logging.basicConfig(filename='bank.log', level=logging.DEBUG,
                    format="%(asctime)s|%(levelname)s|%(message)s", datefmt="%Y-%m-%d %H:%M:%S" )

class Account(Base):
    '''Base class for a bank account. Maintains balance, account number, and transaction history'''
    
    __tablename__ = 'account'

    _id = mapped_column(Integer, ForeignKey('bank._id'))
    _acc_num = mapped_column(Integer, primary_key=True)
    _balance = mapped_column(Float(asdecimal=True))
    _account_type = Column(String(9))
    _transactions = relationship('Transaction', backref=backref('account'))

    __mapper_args__ = {
        'polymorphic_identity':'account',
        'polymorphic_on': _account_type
    }


    def __init__(self, acc_num):
        self._acc_num = acc_num
        self._balance = 0
        

    def _get_acct_num(self):
        return self._acc_num


    def add_transaction(self, amount, date, type, session):
        '''Creates and adds transaction to account, updates account balance
        Arguments:
            amount (Decimal): amount to add to account
            date (datetime): date of transaction
            type (string): whether it is a normal transaction, interest, or fees'''
        transaction = Transaction(amount, date, type)
        if self._transactions:                              # if not first transaction, check sequence
            self._check_transaction_sequence(transaction)
        if type == 'Transaction':                           # if normal transaction, check overdraft and limits
            balance_ok = self._no_overdraft(amount)
            limits_ok = self._doesnt_exceedlimit(date)
        else:
            balance_ok = True
            limits_ok = True

        if type == 'Interest' or type == 'Fees' or (balance_ok and limits_ok):
            self._balance += amount
            self._transactions.append(transaction)
            self._transactions = sorted(self._transactions)
            session.add(transaction)
            logging.debug(f"Created transaction: {self._acc_num}, {amount}")


    def _check_transaction_sequence(self, transaction):
        last_transaction = self._get_last_transaction()
        if transaction < last_transaction:
            raise TransactionSequenceError(last_transaction_date=last_transaction.get_date())


    def _no_overdraft(self, amount):
        if self._balance + amount > 0:
            return True
        else:
            raise OverdrawError()
        

    def _doesnt_exceedlimit(self, date):
        return True


    def apply_interest_and_fees(self, session):
        '''Applies interest and fees to account balance'''
        last_transaction = self._get_last_transaction()
        interest_fees_date = last_transaction.format_interest_date()
        if self._interestfees_already_applied(interest_fees_date):
            raise TransactionSequenceError(last_transaction_date=last_transaction.get_date(),
                                           interest_related=True)
        else:
            self._add_interest(interest_fees_date, session)
            self._add_fees(interest_fees_date, session)
            logging.debug("Triggered interest and fees")
    

    def _get_last_transaction(self):
        return self._transactions[-1]
    

    def _add_interest(self, date, session):
        interest = self._balance * self._interest_rate
        self.add_transaction(amount = interest, date = date, type= 'Interest', session=session)
        

    def _add_fees(self, date, session):
        pass
    

    def _interestfees_already_applied(self, date):
        input_year = date.year
        input_month = date.month
        # Count number of times interest/fees have been applies this month
        count = sum(1 for transaction in self._transactions if
                    transaction.get_date().year == input_year and 
                    transaction.get_date().month == input_month and 
                    (transaction.get_type() == 'Interest' or
                     transaction.get_type() == 'Fees'))
        if count > 0:
            return True
        else:
            return False


    def get_transactions(self):
        '''Returns list of all transactions for this account'''
        return self._transactions

    def __str__(self):
        '''Formats the account number and balance of the account.'''
        rounded_balance = Decimal(self._balance).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return f"#{self._acc_num:09},\tbalance: ${rounded_balance:,.2f}"

    

class CheckingAccount(Account):
    '''A checking account'''

    __tablename__ = 'checking'

    _acc_num = mapped_column(Integer, ForeignKey('account._acc_num'), primary_key=True)
    _interest_rate = mapped_column(Float(asdecimal=True))
    _balance_threshold = mapped_column(Integer)
    _low_balance_fee = mapped_column(Float(asdecimal=True))

    __mapper_args__ = {
        'polymorphic_identity': 'checking',
    }
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interest_rate = Decimal("0.0008")
        self._balance_threshold = 100
        self._low_balance_fee = Decimal("-5.44")


    def _add_fees(self, date, session):
        if self._balance < self._balance_threshold:
            self.add_transaction(amount = self._low_balance_fee,
                                 date = date, 
                                 type = 'Fee',
                                 session = session)


    def __str__(self):
        return "Checking" + super().__str__()


class SavingsAccount(Account):
    '''A savings account'''

    __tablename__ = 'savings'

    _acc_num = mapped_column(Integer, ForeignKey('account._acc_num'), primary_key=True)
    _interest_rate = mapped_column(Float(asdecimal=True))
    _daily_limit = mapped_column(Integer)
    _monthly_limit = mapped_column(Integer)

    __mapper_args__ = {
        'polymorphic_identity': 'savings',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interest_rate = Decimal("0.0041")
        self._daily_limit = 2
        self._monthly_limit = 5


    def _doesnt_exceedlimit(self, date):
        # Get user inputted year/month/day
        input_year = date.year
        input_month = date.month
        input_day = date.day

        # Count number of transactions with the same day and month
        day_count = sum(1 for transaction in self._transactions if
                    transaction.get_date().year == input_year and 
                    transaction.get_date().month == input_month and 
                    transaction.get_date().day == input_day and
                    transaction.get_type() == 'Transaction')

        month_count = sum(1 for transaction in self._transactions if
                    transaction.get_date().year == input_year and 
                    transaction.get_date().month == input_month and
                    transaction.get_type() == 'Transaction')

        # Check if transaction adheres to limits  
        if day_count >= self._daily_limit:
            raise TransactionLimitError(message='This transaction could not be completed because this account already has 2 transactions in this day.')
        elif month_count >= self._monthly_limit:
            raise TransactionLimitError(message='This transaction could not be completed because this account already has 5 transactions in this month.')
        else:
            return True
    

    def __str__(self):
        '''Formats the type, account number, and balance of the account.'''
        return "Savings" + super().__str__()
    

class OverdrawError(Exception):
    '''Raised when a pending transaction would cause account balance to go below 0'''
    def __init__(self):
        self.message = "This transaction could not be completed due to an insufficient account balance."
        super().__init__(self.message)


class TransactionSequenceError(Exception):
    '''Raised when a pending transaction date is before the last transaction date
    or interest is applied more than 1 time a month'''
    def __init__(self, last_transaction_date=None, interest_related=False):
        self._latest_date = last_transaction_date
        if interest_related:
            month_name = calendar.month_name[self._latest_date.month]
            self.message = f"Cannot apply interest and fees again in the month of {month_name}."
        else:
            self.message = f"New transactions must be from {self._latest_date} onward."
        super().__init__(self.message)


class TransactionLimitError(Exception):
    '''Raised when a pending transaction violates the savings account daily/monthly transaction limit'''
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)