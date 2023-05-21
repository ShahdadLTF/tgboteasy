import os
import telebot
from eth_account import Account
from web3 import Web3, exceptions
from walletFileChecker import walletFileNormalizer
import time
import json
shared_variables = {}

RPC_URL = os.getenv("ETHEREUM_RPC_URL")

# Connect to the Ethereum network
w3 = Web3(Web3.HTTPProvider(RPC_URL))

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(bot_token)

# New function to handle wallet generation and file creation
def create_wallet_file(wallets, chat_id):
    # Save the wallets in a temporary file
    with open('wallets.txt', 'w') as f:
        for wallet in wallets:
            f.write(f"Address: {wallet['address']}\nPrivate Key: {wallet['private_key']}\n\n")

    # Send the file to the user
    with open('wallets.txt', 'rb') as f:
        bot.send_document(chat_id, f)

    # Delete the temporary file
    os.remove('wallets.txt')

def parse_wallets_from_file(file):
    """Parse wallet addresses and private keys from a file."""
    with open(file, 'r') as f:
        lines = f.readlines()

    wallets = []
    for line in lines:
        if 'Address' in line:
            address = line.split(': ')[1].strip()
        if 'Private Key' in line:
            key = line.split(': ')[1].strip()
            wallets.append({'address': address, 'private_key': key})
    return wallets

def generate_wallets(n: int):
    """Generate a number of Ethereum wallets."""
    wallets = []
    for i in range(n):
        acct = Account.create()
        wallets.append({
            'address': acct.address,
            'private_key': acct.key.hex()
        })
    return wallets



def transfer_eth(from_wallets, to_wallets):
    """Transfer Ethereum from one set of wallets to another."""
    for i in range(len(from_wallets)):
        from_wallet = from_wallets[i]
        to_wallet = to_wallets[i]

        gas_pump = 10 # In gwei
        acct = Account.from_key(from_wallet['private_key'])
        balance = w3.eth.get_balance(from_wallet['address'])
        gas_price = w3.eth.gas_price + gas_pump * 10 ** 9  # Add extra Gwei

        if balance > gas_price * 21000:
            value = balance - gas_price * 21000

            # Prepare transaction
            transaction = {
                'to': to_wallet['address'],
                'value': value,
                'gas': 21000,
                'gasPrice': gas_price,
                'nonce': w3.eth.get_transaction_count(from_wallet['address']),
                'chainId': w3.eth.chain_id,  # Include chain ID
            }

            # Sign and send transaction
            signed = acct.sign_transaction(transaction)
            try:
                tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
                print(f"Transaction successful for {from_wallet['address']}. The Gas price was {round(w3.eth.gas_price / 10 ** 9, 1)} gwei & Gas used is {round(gas_price / 10 ** 9, 1)} gwei. Transaction hash: https://etherscan.io/tx/{tx_hash.hex()}")
            except Exception as e:  # Catch broad exception
                print(f"Transaction failed for {from_wallet['address']}. Error: {e}")
        else:
            print(f"Gas price is higher than balance for {from_wallet['address']}. Balance: {w3.from_wei(balance, 'ether')} ETH. The Gas price is {round(w3.eth.gas_price / 10 ** 9, 1)}.")

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton('Create wallets', callback_data='create_wallets'),
        telebot.types.InlineKeyboardButton('Change sniper wallets', callback_data='change_sniper_wallets')
    )
    bot.send_message(message.chat.id, "Welcome to Wallet Generator bot. Using this bot you can create a new set of wallets or transfer in batch from your old sniper wallets to fresh ones. Choose an option:", reply_markup=keyboard)

def main_menu(chat_id):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton('Create wallets', callback_data='create_wallets'),
        telebot.types.InlineKeyboardButton('Change sniper wallets', callback_data='change_sniper_wallets')
    )
    bot.send_message(chat_id, "Choose an option:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == 'create_wallets')
def ask_wallet_count(call):
    msg = bot.reply_to(call.message, "How many wallets do you want to create?")
    bot.register_next_step_handler(msg, create_wallets)


def create_wallets(message):
    try:
        n = int(message.text)
    except ValueError:
        msg = bot.reply_to(message, "Please provide a valid number.")
        bot.register_next_step_handler(msg, create_wallets)  # Ask again for valid private key
        return

    wallets = generate_wallets(n)
    for wallet in wallets:
        bot.send_message(message.chat.id, f"Address: {wallet['address']}\nPrivate Key: {wallet['private_key']}")

    create_wallet_file(wallets, message.chat.id)

    bot.send_message(message.chat.id, "Wallets are created, enjoy.")
    main_menu(message.chat.id)  # Go back to the main menu


@bot.callback_query_handler(func=lambda call: call.data == 'change_sniper_wallets')

def ask_old_wallets_file(call):
    msg = bot.reply_to(call.message, "Please send the file containing old wallets. In case of a single wallet change, write down the private key of your old wallet.")
    bot.register_next_step_handler(msg, process_old_wallets_file)

def process_old_wallets_file(message):
    if message.document is not None:
        # User sent a file, handle it as before
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with open('old_wallets.txt', 'wb') as f:
            f.write(downloaded_file)

        # Normalize the wallet file and overwrite the original file
        walletFileNormalizer('old_wallets.txt', 'old_wallets.txt')
        old_wallets = parse_wallets_from_file('old_wallets.txt')

        shared_variables['old_wallets'] = old_wallets

    else:
        # User sent a text message, treat it as a single private key
        private_key = message.text.strip()
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key  # Prepend '0x' if it's not there

        # Check if the private key is valid
        try:
            acct = Account.from_key(private_key)
            old_wallets = [{'address': acct.address, 'private_key': private_key}]

            # Write to old_wallets.txt file
            with open('old_wallets.txt', 'w') as f:
                f.write(f"Address: {old_wallets[0]['address']}\nPrivate Key: {old_wallets[0]['private_key']}")

        except ValueError:
            msg = bot.reply_to(message, "Invalid private key. Please send a valid private key.")
            bot.register_next_step_handler(msg, process_old_wallets_file)  # Ask again for valid private key
            return

    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton('Create new wallets', callback_data='create_new_wallets'),
        telebot.types.InlineKeyboardButton('Provide new wallets', callback_data='provide_new_wallets')
    )
    bot.send_message(message.chat.id, "Do you want me to create new wallets or will you provide them?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == 'create_new_wallets')
def create_new_wallets(call):
    old_wallets = parse_wallets_from_file('old_wallets.txt')
    new_wallets = generate_wallets(len(old_wallets))
    create_wallet_file(new_wallets, call.message.chat.id)
    transfer_eth(old_wallets, new_wallets)
    bot.send_message(call.message.chat.id, "Transfer complete.")
    main_menu(call.message.chat.id)  # Go back to the main menu

@bot.callback_query_handler(func=lambda call: call.data == 'provide_new_wallets')
def ask_new_wallets_file(call):
    msg = bot.reply_to(call.message, "Please send the file containing new wallets. In case of a single wallet change, write down the public address of your new wallet")
    bot.register_next_step_handler(msg, process_new_wallets_file)


def process_new_wallets_file(message):
    if message.document is not None:
        # User sent a file, handle it as before
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with open('new_wallets.txt', 'wb') as f:
            f.write(downloaded_file)

        # Normalize the wallet file and overwrite the original file
        walletFileNormalizer('new_wallets.txt', 'new_wallets.txt')
        new_wallets = parse_wallets_from_file('new_wallets.txt')

    else:
        # User sent a text message, treat it as a single address
        address = message.text.strip()

        # Check if the address is valid
        if w3.is_address(address):
            new_wallets = [{'address': address, 'private_key': ''}]

            # Write to new_wallets.txt file
            with open('new_wallets.txt', 'w') as f:
                f.write(f"Address: {new_wallets[0]['address']}\nPrivate Key: {new_wallets[0]['private_key']}")
        else:
            msg = bot.reply_to(message, "Invalid Ethereum address. Please send a valid address.")
            bot.register_next_step_handler(msg, process_new_wallets_file)  # Ask again for valid address
            return

    old_wallets = shared_variables.get('old_wallets')

    if len(new_wallets) < len(old_wallets):
        msg = bot.reply_to(message, "The new wallets file does not contain enough wallets. Please send another file.")
        bot.register_next_step_handler(msg, process_new_wallets_file)  # Register next step handler again
    else:
        print(f"Old wallets are:", old_wallets)
        print(f"New wallets are:", new_wallets)

        transfer_eth(old_wallets, new_wallets[:len(old_wallets)])


        # Send the wallet files to the user
        bot.send_document(message.chat.id, open('old_wallets.txt', 'rb'))
        bot.send_document(message.chat.id, open('new_wallets.txt', 'rb'))

        # Add a delay to make sure files are sent before deletion
        time.sleep(10)

        # Remove the wallet files from the server
        os.remove('old_wallets.txt')
        os.remove('new_wallets.txt')
        bot.send_message(message.chat.id, "Transfer complete.")
        main_menu(message.chat.id)  # Go back to the main menu
        
bot.polling()
