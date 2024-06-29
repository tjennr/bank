from datetime import date, timedelta
from sqlalchemy import Float, Integer, String, ForeignKey, Date
from sqlalchemy.orm import mapped_column
from db_base import *

class Transaction(Base):
    '''Stores the amount, date, and type of a transaction'''

    __tablename__ = 'transaction'

    _id = mapped_column(Integer, primary_key=True)
    _acc_num = mapped_column(Integer, ForeignKey('account._acc_num'))
    _amount = mapped_column(Float(asdecimal=True))
    _date = mapped_column(Date)
    _type = mapped_column(String)


    def __init__(self, amount, date, type):
        self._amount = amount
        self._date = date
        self._type = type

    
    def get_amount(self):
        '''Returns amount of a transaction'''
        return self._amount


    def get_date(self):
        '''Returns date of a transaction'''
        return self._date
    

    def get_type(self):
        '''Returns type of a transaction'''
        return f"{self._type}"
    

    def format_interest_date(self):
        '''Returns a formatted interest/fees date as last day of month of last transaction'''
        first_of_next_month = date(self._date.year + self._date.month // 12,
                                    self._date.month % 12 + 1, 
                                    1)
        return first_of_next_month - timedelta(days=1)


    def __lt__(self, value):
        '''Returns true if transaction called on comes before transaction passed as argument'''
        return self._date < value._date
    
    
    def __str__(self):
        '''Returns formatted transaction information'''
        return f"{self._date}, ${self._amount:,.2f}"