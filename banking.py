import random
import sqlite3 as sql


class Account:
    """
    Used to generate proper account numbers, card numbers, and pins for
    storage in a database.
    Not intended to be used for accessing card info outside of the creation
    process.
    """
    all_accounts = []

    def __init__(self, connection):
        self.db = connection  # Connection object to a database
        self.account_number = None  # stored as str for proper formatting
        self.checksum = None
        self.card_number = None  # stored as str for proper formatting
        self.pin = None  # stored as str for proper formatting
        self.balance = 0

        self.generate_account_number()
        self.generate_checksum()
        self.generate_card_number()
        self.generate_pin()

        self.all_accounts.append(self)

    def generate_account_number(self):
        number = '{:09d}'.format(random.randint(000000000, 999999999))
        # ensure that a card with this number does not already exist in the db
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM card WHERE number=?', (number,))
        result = cursor.fetchone()
        while result is not None:
            number = '{:09d}'.format(random.randint(000000000, 999999999))
            cursor.execute('SELECT * FROM card WHERE number=?', (number,))
            result = cursor.fetchone()
        # when an unused number is found, use it!
        self.account_number = number
        cursor.close()

    def generate_checksum(self):
        """Generates the 16th checksum digit via the Luhn algorithm."""
        x = '400000' + self.account_number
        x_list = [int(y) for y in x]
        # multiply odd digits (even indices) by 2
        for i, num in enumerate(x_list):
            if i % 2 == 0:
                x_list[i] = num * 2
        # subtract 9 from all numbers over 9
        for i in range(len(x_list)):
            if x_list[i] > 9:
                x_list[i] -= 9
        # sum all numbers and find checksum
        control = sum(x_list)
        self.checksum = (10 - (control % 10)) % 10

    def generate_card_number(self):
        self.card_number = f'400000{self.account_number}{self.checksum}'

    def generate_pin(self):
        self.pin = '{:04d}'.format(random.randint(0000, 9999))


def print_start_menu():
    """Prints the starting menu"""
    print()
    print('1. Create an account')
    print('2. Log into account')
    print('0. Exit')


def print_account_menu():
    """Prints the menu for logged-in users"""
    print()
    print('1. Balance')
    print('2. Add income')
    print('3. Do transfer')
    print('4. Close account')
    print('5. Log out')
    print('0. Exit')


def create_card(database):
    """
    Creates a new Account object and stores the generated card information in
    an external database (sqlite3 Connection object).
    """
    new_account = Account(database)
    print()
    print('Your card has been created')
    print('Your card number:')
    print(new_account.card_number)
    print('Your card PIN:')
    print(new_account.pin)

    cursor = database.cursor()
    cursor.execute(f'INSERT INTO card VALUES (?, ?, ?, ?)',
                   (new_account.account_number, new_account.card_number,
                    new_account.pin, new_account.balance))
    database.commit()
    cursor.close()


def login(database):
    """
    Attempts to log into an existing account (in a sqlite3 Connection object)
    with a correct card number and PIN taken from the input.
    Successful login returns the relevant card number.
    Failed login returns None.
    """
    print()
    card_number = input('Enter your card number: ').strip()
    pin = input('Enter your PIN: ').strip()

    cursor = database.cursor()
    cursor.execute('SELECT * FROM card '
                   'WHERE ('
                   '    number = CAST(? AS TEXT) '
                   '    AND pin = CAST(? AS TEXT)'
                   ');',
                   (card_number, pin))

    # get query result
    result = cursor.fetchone()
    cursor.close()
    if result is not None:
        print('You have successfully logged in!')
        return result[1]  # card number
    else:
        print()
        print('Wrong card number or PIN!')
        return None


def set_up_database():
    """Initializes the database and table used to store card info.
    Returns a sqlite3 Connection object."""
    connection = sql.connect('card.s3db')
    cur = connection.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS card ('
                '   id INTEGER,'
                '   number TEXT,'
                '   pin TEXT,'
                '   balance INTEGER DEFAULT 0'
                ');')
    connection.commit()
    cur.close()
    return connection


def get_balance(database, card_num):
    """Given a card number, retrieves the account balance from a database.
    Returns None if the card number is not in the database."""
    cursor = database.cursor()
    cursor.execute('SELECT * FROM card WHERE number=?', (card_num,))
    balance = cursor.fetchone()
    if balance is None:
        return None
    else:
        balance = balance[3]
        cursor.close()
        return balance


def update_balance(database, card_num, amount):
    """Updates the balance of an account (add or subtract).
    Args: database (Connection object), card number, amount to add/remove"""
    cursor = database.cursor()
    cursor.execute('SELECT balance FROM card WHERE number=?',
                   (card_num,))
    current_balance = int(cursor.fetchone()[0])
    cursor.execute('UPDATE card SET balance=? WHERE number=?',
                   (current_balance + amount, card_num))
    database.commit()
    cursor.close()


def close_account(database, card_num):
    """Deletes a record from the database."""
    cursor = database.cursor()
    cursor.execute('DELETE FROM card WHERE number=?',
                   (card_num,))
    database.commit()
    cursor.close()


def passes_luhn(card_num):
    """Checks a card number (str) to see if it passes the Luhn algorithm."""
    card_num_list = [int(y) for y in card_num]
    checksum = card_num_list[len(card_num_list)-1]
    del card_num_list[len(card_num_list)-1]

    # multiply odd digits (even indices) by 2
    for i, num in enumerate(card_num_list):
        if i % 2 == 0:
            card_num_list[i] = num * 2
    # subtract 9 from all numbers over 9
    for i in range(len(card_num_list)):
        if card_num_list[i] > 9:
            card_num_list[i] -= 9
    # sum all numbers and verify card number
    control = sum(card_num_list)
    final_sum = control + checksum

    return final_sum % 10 == 0


def do_transfer(database, from_card_num):
    """Transfers an amount (taken from input inside this function) from the
    balance of one record to that of another (taken from input) in the given database."""
    print()
    print('Transfer')
    to_card_num = input('Enter card number: ').strip()

    # check for input error
    if not passes_luhn(to_card_num):
        print('Probably you made a mistake in the card number. Please try again!')
        return
    elif from_card_num == to_card_num:
        print("You can't transfer money to the same account!")
        return

    # gather starting balances
    from_balance = get_balance(database, from_card_num)
    to_balance = get_balance(database, to_card_num)
    if to_balance is None:
        print('Such a card does not exist.')
        return

    # get transfer amount and do transfer
    amount = int(input('Enter how much money you want to transfer: ').strip())
    if amount > from_balance:
        print('Not enough money!')
    else:  # transaction
        update_balance(database, from_card_num, -amount)
        update_balance(database, to_card_num, amount)
        print('Success!')


if __name__ == '__main__':
    conn = set_up_database()

    # global variables
    action = ''
    logged_in = False
    active_card_number = None

    # main loop
    while True:
        # -- logged in menu -- #
        if logged_in:
            print_account_menu()
            action = int(input())

            if action == 0:  # exit
                print()
                print('Bye!')
                break
            elif action == 1:  # check balance
                print()
                print(f'Balance: {get_balance(conn, active_card_number)}')
            elif action == 2:  # add income
                print()
                amount_to_add = int(input('Enter income: '))
                update_balance(conn, active_card_number, amount_to_add)
                print('Income was added!')
            elif action == 3:  # do transfer
                do_transfer(conn, active_card_number)
            elif action == 4:  # close account
                close_account(conn, active_card_number)
                print()
                print('The account has been closed!')
                logged_in = False
                active_card_number = None
            elif action == 5:  # log out
                print()
                print('You have successfully logged out!')
                logged_in = False
                active_card_number = None
            else:
                print()
                print('Invalid input.')

        # -- logged out menu -- #
        else:
            print_start_menu()
            action = int(input())

            if action == 0:  # exit
                print()
                print('Bye!')
                break
            elif action == 1:  # create account
                create_card(conn)
            elif action == 2:  # log in
                active_card_number = login(conn)
                if active_card_number is not None:
                    logged_in = True
            else:
                print()
                print('Invalid input.')
