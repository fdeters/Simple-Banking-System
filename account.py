import random


class Account:
    all_accounts = []

    def __init__(self):
        self.account_number = None
        self.card_number = None
        self.pin = None
        self.balance = 0

        self.generate_account_number()
        self.generate_card_number()
        self.generate_pin()

        self.all_accounts.append(self)

    def generate_account_number(self):
        number = random.randint(000000000, 999999999)
        all_account_numbers = [a.account_number for a in self.all_accounts]
        while number in all_account_numbers:
            number = random.randint(000000000, 999999999)
        self.account_number = number

    def generate_card_number(self):
        self.card_number = int(f'400000{self.account_number}0')

    def generate_pin(self):
        self.pin = random.randint(0000, 9999)
