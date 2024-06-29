from account import SavingsAccount, CheckingAccount
import logging
from sqlalchemy import Integer, create_engine
from sqlalchemy.orm import relationship, backref, mapped_column
from db_base import *

logging.basicConfig(filename='bank.log', level=logging.DEBUG,
                    format="%(asctime)s|%(levelname)s|%(message)s", datefmt="%Y-%m-%d %H:%M:%S" )

class Bank(Base):
    __tablename__ = 'bank'

    _id = mapped_column(Integer, primary_key=True)
    _accounts = relationship('Account', backref=backref('bank'))


    def add_account(self, type, session):
        '''Creates bank account and adds to list of accounts'''
        acc_num = self._get_new_acc_num()
        if type == "savings":
            new_acc = SavingsAccount(acc_num)
        elif type == "checking":
            new_acc = CheckingAccount(acc_num)
        else:
            return None
        self._accounts.append(new_acc)
        session.add(new_acc)
        logging.debug(f"Created account: {acc_num}")


    def _get_new_acc_num(self):
        return len(self._accounts) + 1
 

    def get_all_accounts(self):
        '''Returns all accounts'''
        return self._accounts
    
    def get_account(self, acc_num):
        '''Returns an account based on the account number'''
        for account in self._accounts:
            if account._acc_num == acc_num:
                return account
        return None

    
if __name__ == "__main__":
    # if the db file already exists, this does nothing
    engine = create_engine(f"sqlite:///bank.db")
    Base.metadata.create_all(engine)
