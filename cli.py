from bank import Bank, Base
from decimal import Decimal, InvalidOperation, setcontext, BasicContext
from datetime import datetime
from account import OverdrawError, TransactionSequenceError, TransactionLimitError
import logging
import sqlalchemy
from sqlalchemy.orm.session import Session, sessionmaker

setcontext(BasicContext)

logging.basicConfig(filename='bank.log', level=logging.DEBUG,
                    format="%(asctime)s|%(levelname)s|%(message)s", datefmt="%Y-%m-%d %H:%M:%S" )

class BankCLI:
    '''Implements a read-eval-print loop CLI which allows user to interact with the bank'''

    def __init__(self):
        self._session = Session()
        self._currentacc = None
        self._bank = self._session.query(Bank).first()
        if not self._bank:
            self._bank = Bank()
            self._session.add(self._bank)
            self._session.commit()
            logging.debug("Saved to bank.db")
        else:
            logging.debug("Loaded from bank.db")

        self._choices = {
            "1": self._open_account,
            "2": self._summary,
            "3": self._select_account,
            "4": self._add_transaction,
            "5": self._list_transactions,
            "6": self._interest_fee,
            "7": self._quit
        }
        

    def run(self):
        '''Displays read-eval-loop CLI with menu options'''
        try:
            while True:
                print(f'''--------------------------------
Currently selected account: {self._currentacc}
Enter command
1: open account
2: summary
3: select account
4: add transaction
5: list transactions
6: interest and fees
7: quit''')
                choice = input(">")
                action = self._choices.get(choice)
                if action:
                    action()
                else:
                    print("Choose a valid command")
        except Exception as e:
            print("Sorry! Something unexpected happened. Check the logs or contact the developer for assistance.")
            logging.error(f"{type(e).__name__}: '{getattr(e, 'message', e)}'")
            exit(0)


    # Open account
    def _open_account(self):
        acc_type = input("Type of account? (checking/savings)\n>")
        self._bank.add_account(acc_type, self._session)
        self._session.commit()
        logging.debug("Saved to bank.db")


    # Summary
    def _summary(self):
        for account in self._bank.get_all_accounts():
            print(account)


    # Select account
    def _select_account(self):
        acc_num = int(input("Enter account number\n>"))
        self._currentacc = self._bank.get_account(acc_num)


    # Add transaction
    def _add_transaction(self):
        try:
            while True:
                try:
                    amount = Decimal(input("Amount?\n>"))
                except (ValueError, InvalidOperation):
                    print("Please try again with a valid dollar amount.")
                    continue

                date_input = False
                while not date_input:
                    try:
                        date = input("Date? (YYYY-MM-DD)\n>")
                        date = datetime.strptime(date, "%Y-%m-%d").date()
                        date_input = True
                    except ValueError:
                        print("Please try again with a valid date in the format YYYY-MM-DD.")
                
                self._currentacc.add_transaction(amount, date, "Transaction", self._session)
                self._session.commit()
                logging.debug("Saved to bank.db")
                break
        except AttributeError:
            print("This command requires that you first select an account.")
        except OverdrawError as e:
            print(e.message)
        except TransactionLimitError as e:
            print(e.message)
        except TransactionSequenceError as e:
            print(e.message)


    # List transactions
    def _list_transactions(self):
        try:
            for transaction in self._currentacc.get_transactions():
                print(transaction)
        except AttributeError:
            print("This command requires that you first select an account.")


    # Interests and fees
    def _interest_fee(self):
        try:
            self._currentacc.apply_interest_and_fees(self._session)
            self._session.commit()
            logging.debug("Saved to bank.db")
        except AttributeError:
            print("This command requires that you first select an account.")
        except TransactionSequenceError as e:
            print(e.message)
        except IndexError:
            print("No transactions have been added to apply interest to.")


    # Quit
    def _quit(self):
        exit(0)


if __name__ == "__main__":
    engine = sqlalchemy.create_engine(f"sqlite:///bank.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)

    BankCLI().run()