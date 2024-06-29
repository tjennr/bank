from bank import Bank, Base
from decimal import Decimal, InvalidOperation, setcontext, BasicContext
from datetime import datetime
from account import OverdrawError, TransactionSequenceError, TransactionLimitError
import logging
import tkinter as tk
import tkinter.messagebox
import sqlalchemy
from sqlalchemy.orm.session import Session, sessionmaker
from db_base import *

setcontext(BasicContext)

logging.basicConfig(filename='bank.log', level=logging.DEBUG,
                    format="%(asctime)s|%(levelname)s|%(message)s", datefmt="%Y-%m-%d %H:%M:%S" )

def handle_exception(exception, value, traceback):
    tkinter.messagebox.showerror("Sorry! Something unexpected happened. Check the logs or contact the developer for assistance.")
    logging.error(f"{type(exception).__name__}: '{getattr(exception, 'message', exception)}'")
    exit(0)


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

        self._window = tk.Tk()
        self._window.title("My Bank")
        self._window.report_callback_exception = handle_exception

        self._menu_frame = tk.Frame(self._window)

        tk.Button(self._menu_frame,
                  text="Open account",
                  command=self._open_account).grid(row=1, column=1)
        tk.Button(self._menu_frame,
                  text="Add transaction",
                  command=self._add_transaction).grid(row=1, column=2)
        tk.Button(self._menu_frame,
                  text="Interests and fee",
                  command=self._interest_fee).grid(row=1, column=4)

        self._menu_frame.grid(row=0, column=1, columnspan=2)

        self._accounts_frame = tk.Frame(self._window)
        self._accounts_frame.grid(row=2, column=1, columnspan=8, sticky="ew")

        self._transactions_frame = tk.Frame(self._window)
        self._transactions_frame.grid(row=2, column=3, columnspan=8, sticky="ew")

        self._summary()
        self._window.mainloop()


    # Open account
    def _open_account(self):
        self._clear_window()

        def _openaccount():
            acc_type = account_type_var.get()
            self._bank.add_account(acc_type, self._session)
            self._session.commit()
            logging.debug("Saved to bank.db")
            self._summary()
            account_frame.destroy()

        # Frame
        account_frame = tk.Frame(self._window)
        account_frame.grid(row=1, column=1, padx=10, pady=10)

        # Prompt for account type
        account_type_label = tk.Label(account_frame, text="Select account type:")
        account_type_label.grid(row=0, column=0, padx=5, pady=5)
        account_type_var = tk.StringVar()
        account_type_options = ["checking", "savings"]
        account_type_menu = tk.OptionMenu(account_frame, account_type_var, *account_type_options)
        account_type_menu.grid(row=0, column=1, padx=5, pady=5)

        # Enter button
        enter_button = tk.Button(account_frame, text="Enter", command=_openaccount)
        enter_button.grid(row=0, column=2, columnspan=2, padx=5, pady=5)

        # Cancel button
        def _cancel():
            account_frame.destroy()
        cancel_button = tk.Button(account_frame, text="Cancel", command=_cancel)
        cancel_button.grid(row=0, column=4, columnspan=2, padx=5, pady=5)


    # Select account
    def _select_account(self, account):
        self._currentacc = account


    # Add transaction
    def _add_transaction(self):
        self._clear_window()

        def _addtransaction():
            amount = None
            valid_amount = True
            try:
                amount = Decimal(amount_entry.get())
            except InvalidOperation:
                valid_amount = False
                tkinter.messagebox.showwarning(title=None, message="Please try again with a valid dollar amount.")

            date = None
            valid_date = True
            try:
                date = date_entry.get()
                date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                valid_date = False
                tkinter.messagebox.showwarning(title=None, message="Please try again with a valid date in the format YYYY-MM-DD.")

            if valid_amount and valid_date:
                try:
                    self._currentacc.add_transaction(amount, date, "Transaction", self._session)
                    self._session.commit()
                    logging.debug("Saved to bank.db")
                    transaction_frame.destroy()
                    self._summary()
                    self._list_transactions()
                except AttributeError:
                    tkinter.messagebox.showwarning(title=None, message="This command requires that you first select an account.")
                except OverdrawError as e:
                    tkinter.messagebox.showwarning(title=None, message=e.message)
                except TransactionLimitError as e:
                    tkinter.messagebox.showwarning(title=None, message=e.message)
                except TransactionSequenceError as e:
                    tkinter.messagebox.showwarning(title=None, message=e.message)
            
        # Change entry box color depending on if amount and date inputs are valid
        def _validate_amount(event=None):
            amount_str = amount_entry.get()
            if amount_str.startswith('-'):      # remove '-' if negative number to check
                amount_str = amount_str[1:]
            if amount_str.replace('.', '', 1).isdigit():
                amount_entry.config({"background": "white", "highlightbackground": "green"})
            else:
                amount_entry.config({"background": "white", "highlightbackground": "red"})

        def _validate_date(event=None):
            date_str = date_entry.get()
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                date_entry.config({"background": "white", "highlightbackground": "green"})
            except ValueError:
                date_entry.config({"background": "white", "highlightbackground": "red"})

        # Frame
        transaction_frame = tk.Frame(self._window)
        transaction_frame.grid(row=1, column=1, padx=10, pady=10)

        # Prompt for amount and date
        amount_label = tk.Label(transaction_frame, text="Amount:")
        amount_label.grid(row=0, column=0, padx=5, pady=5)
        amount_entry = tk.Entry(transaction_frame)
        amount_entry.grid(row=0, column=1, padx=5, pady=5)
        amount_entry.bind("<KeyRelease>", _validate_amount)

        date_label = tk.Label(transaction_frame, text="Date:")
        date_label.grid(row=1, column=0, padx=5, pady=5)
        date_entry = tk.Entry(transaction_frame)
        date_entry.grid(row=1, column=1, padx=5, pady=5)
        date_entry.bind("<KeyRelease>", _validate_date)

        # Enter button
        enter_button = tk.Button(transaction_frame, text="Enter", command=_addtransaction)
        enter_button.grid(row=0, column=2, columnspan=2, padx=5, pady=5)

        # Cancel button
        def _cancel():
            transaction_frame.destroy()
        cancel_button = tk.Button(transaction_frame, text="Cancel", command=_cancel)
        cancel_button.grid(row=1, column=2, columnspan=2, padx=5, pady=5)


    # List transactions
    def _list_transactions(self):
        for widget in self._transactions_frame.winfo_children():
            widget.destroy()

        transactions = self._currentacc.get_transactions()
        for i, transaction in enumerate(transactions):
            color = "green" if transaction.get_amount() >= 0 else "red"
            transaction_label = tk.Label(self._transactions_frame, text=str(transaction), fg=color)
            transaction_label.grid(row=i, column=3, padx=5, pady=5)


    # Displays all accounts and their info
    def _summary(self):
        # Clear the existing accounts display
        for widget in self._accounts_frame.winfo_children():
            widget.destroy()

        accounts = self._bank.get_all_accounts()
        self._account_radio_var = tk.StringVar(value=self._currentacc)

        for i, account in enumerate(accounts):
            account_label = tk.Label(self._accounts_frame, text=str(account))
            account_label.grid(row=i, column=1, padx=5, pady=5)

            # Radio button for each account
            radio_button = tk.Radiobutton(self._accounts_frame, variable=self._account_radio_var, value=str(account))
            radio_button.grid(row=i, column=0, padx=5, pady=5)
            
            # Bind the radio button to a callback function
            radio_button.bind("<Button-1>", lambda event, acc=account: self._select_account_and_list_transactions(acc))

        # Adjust window size if needed
        self._window.update_idletasks()
        self._window.geometry("")


    # Interests and fees
    def _interest_fee(self):
        self._clear_window()

        try:
            self._currentacc.apply_interest_and_fees(self._session)
            self._session.commit()
            logging.debug("Saved to bank.db")
            self._summary()
            self._list_transactions()
        except AttributeError:
            tkinter.messagebox.showwarning(title=None, message="This command requires that you first select an account.")
        except TransactionSequenceError as e:
            tkinter.messagebox.showwarning(title=None, message=e.message)
        except IndexError:
            tkinter.messagebox.showwarning(title=None, message="No transactions have been added to apply interest to.")


    # Allows us to both update current account and list transactions when an account is selected
    def _select_account_and_list_transactions(self, account):
        self._select_account(account)
        self._list_transactions()


    # Clears the window except for the menu, accounts, and transactions frame
    def _clear_window(self):
        for widget in self._window.winfo_children():
            if widget != self._menu_frame and widget != self._accounts_frame and widget != self._transactions_frame:
                widget.destroy()


if __name__ == "__main__":
    engine = sqlalchemy.create_engine(f"sqlite:///bank.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine) 
    
    BankCLI()