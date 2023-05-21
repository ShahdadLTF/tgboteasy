import os, time, requests, math, sys, contextlib
from web3 import Web3
from eth_account import Account
from decimal import Decimal
from optimismGasCalculator import getOptimismGas

# Load the API key and RPC URL from an environment variable
api_key = os.getenv('EASYBIT_API_KEY')
RPC_URL = os.getenv("ETHEREUM_RPC_URL")
RPC_URL_OPT = os.getenv("ALCHEMY_OPTIMISM_API")
headers = {'API-KEY': api_key}

# Connect to the Ethereum & Optimism node
w3 = Web3(Web3.HTTPProvider(RPC_URL))
wo3 = Web3(Web3.HTTPProvider(RPC_URL_OPT))

def round_down(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier


def eth_transfer(from_wallet, private_key, to_address, value, network, gas_price):
    gas_limit = 21000  # Gas limit for standard transaction

    # Determine the chain ID based on the network
    if network.upper() == 'ETH':
        chain_id = w3.eth.chain_id
        nonce = w3.eth.get_transaction_count(from_wallet)
    elif network.upper() == 'OPTIMISM':
        chain_id = wo3.eth.chain_id
        nonce = wo3.eth.get_transaction_count(from_wallet)
    else:
        print(f"Unsupported network: {network}. Only 'ETH' and 'OPTIMISM' are supported.")
        return

    transaction = {
        'to': to_address,
        'value': value,
        'gas': gas_limit,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': chain_id,

    }
    signed = Account.sign_transaction(transaction, private_key)
    try:
        if network.upper() == 'ETH':
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            print(
                f"Transaction successful for {from_wallet}. The Gas price used was {round(gas_price / 10 ** 9, 1)} gwei. Transaction hash: https://etherscan.io/tx/{tx_hash.hex()}")
        elif network.upper() == 'OPTIMISM':
            tx_hash = wo3.eth.send_raw_transaction(signed.rawTransaction)
            print(
                f"Transaction successful for {from_wallet}. The Gas price used was {round(gas_price / 10 ** 9, 1)} gwei. Transaction hash: https://optimistic.etherscan.io/tx/{tx_hash.hex()}")
        else:
            print(f"Unsupported network: {network}. Only 'ETH' and 'OPTIMISM' are supported.")
            return
    except Exception as e:  # Catch broad exception
        print(f"Transaction failed for {from_wallet}. Error: {e}")



def easyBitTransfer(transferNumber, chain1, chain2, wallet1, wallet1_private_key, wallet2, wallet2_private_key=None, wallet3=None, transfer_back=False, output_file='transfer.txt', ethAmount=None):

    chain1 = chain1.upper()
    chain2 = chain2.upper()

    # Define gas pump
    gasPump = 5  # In gwei
    optimismGasMultiplier = 1.1
    gas_limit = 21000  # Gas limit for standard transaction
    receiveAmount1Multiplier = 1.004  # considering a 0.4% fee on the second transfer



    with open(output_file, 'w') as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            transferNumber = int(transferNumber)
            print(f"Transfer number {transferNumber} starts:")
            print('++++ Order details ++++')
            print(f"Wallet1: {wallet1}, Wallet1 Private Key: {wallet1_private_key}")
            if transfer_back:
                print(f"Wallet2: {wallet2}, Wallet2 Private Key: {wallet2_private_key}")
                print(f"Wallet3: {wallet3}")
                print(f"Chain1: {chain1} --> Chain2: {chain2} --> Chain1: {chain1}")
            else:
                print(f"Wallet2: {wallet2}")
                print(f"Chain1: {chain1} --> Chain2: {chain2}")
            if ethAmount is None:
                print("Transferring the total balance of Wallet1")
            else:
                print(f"Transferring {ethAmount} ETH requested from Wallet1")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                # Step 1: Get balance of wallet 1 and the send amount
            if chain1 == 'ETH':
                wallet1_balance = w3.eth.get_balance(wallet1)  # in wei
                # Calculate send amount for wallet 1, subtracting gas price times gas limit
                eth_gas_price = w3.eth.gas_price + gasPump * 10 ** 9  # in wei
                if ethAmount is None:
                    sendAmount1temp = wallet1_balance - eth_gas_price * gas_limit  # in wei
                    sendAmount1 = w3.to_wei(round_down(w3.from_wei(sendAmount1temp, 'ether'), 8),
                                            'ether')  # needed to do this, cause easyBit accepts until 8 decimals
                else:
                    sendAmount1 = w3.to_wei(round_down(ethAmount, 8), 'ether')
                    if float(sendAmount1 + (eth_gas_price * gas_limit)) > float(wallet1_balance):
                        print(f"Transfer amount requested {ethAmount} ETH + the gas {w3.from_wei(eth_gas_price, 'gwei')} gwei is larger than the wallet balance of {w3.from_wei(wallet1_balance,'ether')}!")
                        exit()

            elif chain1 == 'OPTIMISM':
                optimismGasPrice, optimismTotalTxFee = getOptimismGas()
                optimismTotalTxFee = optimismTotalTxFee * optimismGasMultiplier  # to be on the safe side
                wallet1_balance = wo3.eth.get_balance(wallet1)  # in wei
                eth_gas_price = optimismGasPrice  # in wei
                if ethAmount is None:
                    sendAmount1temp = wallet1_balance - optimismTotalTxFee  # in wei
                    sendAmount1 = w3.to_wei(round_down(w3.from_wei(sendAmount1temp, 'ether'), 8),
                                            'ether')  # needed to do this, cause easyBit accepts until 8 decimals
                    print(f"Transferring the total balance ...")
                else:
                    sendAmount1 = w3.to_wei(round_down(ethAmount, 8), 'ether')
                    if float(sendAmount1 + optimismTotalTxFee) > float(wallet1_balance):
                        print(f"Transfer amount requested {ethAmount} ETH + the gas {w3.from_wei(optimismTotalTxFee, 'ether')} ETH is larger than the wallet balance of {w3.from_wei(wallet1_balance,'ether')}!")
                        exit()
                    print(f"Transferring {ethAmount} ETH requested ...")

            else:
                print(f"Chains chosen are not supported.")
                exit()

            # Getting minimum and maximum of amount of send in the pair
            params1 = {'send': 'ETH', 'receive': 'ETH', 'sendNetwork': chain1, 'receiveNetwork': chain2}
            params2 = {'send': 'ETH', 'receive': 'ETH', 'sendNetwork': chain2, 'receiveNetwork': chain1}
            response1 = requests.get('https://api.easybit.com/pairInfo', headers=headers, params=params1)
            response2 = requests.get('https://api.easybit.com/pairInfo', headers=headers, params=params2)
            minimumAmount1 = float(response1.json()['data']['minimumAmount'])
            maximumAmount1 = float(response1.json()['data']['maximumAmount'])
            minimumAmount2 = float(response2.json()['data']['minimumAmount'])
            maximumAmount2 = float(response2.json()['data']['maximumAmount'])

            if float(w3.from_wei(sendAmount1, 'ether')) < minimumAmount1 or float(
                    w3.from_wei(sendAmount1, 'ether')) > maximumAmount1:
                print(
                    f"The send amount {w3.from_wei(sendAmount1, 'ether')}, is smaller than minimum amount {minimumAmount1}, or larger than the maximum amount {maximumAmount1}")
                exit()

            # Step 2: Get receive amount for wallet 2 using rate endpoint
            params = {'send': 'ETH', 'receive': 'ETH', 'amount': w3.from_wei(sendAmount1, 'ether'),
                      'sendNetwork': chain1,
                      'receiveNetwork': chain2}  # sendAmount1 should be in ether for the parameter input
            response = requests.get('https://api.easybit.com/rate', headers=headers, params=params)
            receiveAmount1 = response.json()['data']['receiveAmount']

            if (float(receiveAmount1) * receiveAmount1Multiplier) < minimumAmount2 and transfer_back:
                print(
                    f"The receive amount {w3.from_wei(receiveAmount1, 'ether')} plus {round_down((receiveAmount1Multiplier - 1) * 100, 2)}% fee of the second transfer , is smaller than minimum amount {minimumAmount2} in the second transfer")
                exit()

            # Step 3: Create order 1
            order1 = {
                'send': 'ETH',
                'receive': 'ETH',
                'amount': str(w3.from_wei(sendAmount1, 'ether')),
                'receiveAddress': wallet2,
                'sendNetwork': chain1,
                'receiveNetwork': chain2,
            }
            response = requests.post('https://api.easybit.com/order', headers=headers, json=order1)
            order1_id = response.json()['data']['id']
            order1_sendAddress = response.json()['data']['sendAddress']
            order1_sendAddress = w3.to_checksum_address(order1_sendAddress)
            order1_sendAmount = response.json()['data']['sendAmount']
            order1_receiveAmount = response.json()['data']['receiveAmount']
            print(
                f"Order 1 ID: {order1_id}, sendAddress: {order1_sendAddress}, sendAmount {order1_sendAmount}, receiveAmount: {order1_receiveAmount}")
            time.sleep(150)  # to remove

            # Step 4: Initiate transfer from wallet 1
            eth_transfer(wallet1, wallet1_private_key, order1_sendAddress, sendAmount1, chain1,
                         eth_gas_price)  # sendAmount1 should be in wei in this function

            # Step 5: Check order status every 10 seconds until complete
            while True:
                response = requests.get('https://api.easybit.com/orderStatus', headers=headers,
                                        params={'id': order1_id})
                if response.json()['data']['status'] == 'Complete':
                    sys.stdout.write(
                        "\rOrder 1 completed successfully.                        \n")  # Clear line and print
                    sys.stdout.flush()
                    break
                else:
                    answer = response.json()['data']['status']
                    sys.stdout.write(
                        "\rThe status now is {}                        ".format(answer))  # Clear line and print
                    sys.stdout.flush()
                    time.sleep(20)
            # time.sleep(15)  # to remove

            if transfer_back:
                if wallet2_private_key is None or wallet3 is None:
                    raise ValueError("A private key for wallet 2 and wallet 3 must be provided for a transfer back.")
                else:
                    print(
                        '---------------------------------------------------------------------------------------------------')
                    #### BEGINNING OF THE SECOND TRANSFER ####
                    # Step 6: Get balance of wallet 2 and the send amount
                    if chain2 == 'ETH':
                        wallet2_balance = w3.eth.get_balance(wallet2)  # in wei
                        # Calculate send amount for wallet 2, subtracting gas price times gas limit
                        eth_gas_price = w3.eth.gas_price + gasPump * 10 ** 9  # in wei
                        if ethAmount is None:
                            sendAmount2temp = wallet2_balance - eth_gas_price * gas_limit  # in wei
                            sendAmount2 = w3.to_wei(round_down(w3.from_wei(sendAmount2temp, 'ether'), 8), 'ether')  # needed to do this, cause easyBit accepts until 8 decimals
                        else:
                            sendAmount2 = w3.to_wei(round_down(
                                Decimal(order1_receiveAmount) - w3.from_wei(eth_gas_price * gas_limit, 'ether'), 8),
                                                    'ether')  # needed to do this, cause easyBit accepts until 8 decimals

                    elif chain2 == 'OPTIMISM':
                        optimismGasPrice, optimismTotalTxFee = getOptimismGas()
                        optimismTotalTxFee = optimismTotalTxFee * optimismGasMultiplier  # to be on the safe side
                        wallet2_balance = wo3.eth.get_balance(wallet2)  # in wei
                        eth_gas_price = optimismGasPrice  # in wei
                        if ethAmount is None:
                            sendAmount2temp = wallet2_balance - optimismTotalTxFee  # in wei
                            sendAmount2 = w3.to_wei(round_down(w3.from_wei(sendAmount2temp, 'ether'), 8), 'ether')  # needed to do this, cause easyBit accepts until 8 decimals
                        else:
                            sendAmount2 = w3.to_wei(
                                round_down(Decimal(order1_receiveAmount) - w3.from_wei(optimismTotalTxFee, 'ether'), 8),
                                'ether')  # needed to do this, cause easyBit accepts until 8 decimals

                    else:
                        print(f"Chains chosen are not supported.")
                        exit()

                    # Step 7: Get receive amount for wallet 2 using rate endpoint
                    params = {'send': 'ETH', 'receive': 'ETH', 'amount': w3.from_wei(sendAmount2, 'ether'),
                              'sendNetwork': chain2,
                              'receiveNetwork': chain1}  # sendAmount2 should be in ether for the parameter input
                    response = requests.get('https://api.easybit.com/rate', headers=headers, params=params)
                    if float(w3.from_wei(sendAmount2, 'ether')) < minimumAmount2 or float(
                            w3.from_wei(sendAmount2, 'ether')) > maximumAmount2:
                        print(
                            f"The send amount {w3.from_wei(sendAmount2, 'ether')}, is smaller than minimum amount {minimumAmount2}, or larger than the maximum amount {maximumAmount2}")
                        exit()

                    # Step 8: Create order 2
                    order2 = {
                        'send': 'ETH',
                        'receive': 'ETH',
                        'amount': str(w3.from_wei(sendAmount2, 'ether')),
                        'receiveAddress': wallet3,
                        'sendNetwork': chain2,
                        'receiveNetwork': chain1,
                    }
                    response = requests.post('https://api.easybit.com/order', headers=headers, json=order2)
                    order2_id = response.json()['data']['id']
                    order2_sendAddress = response.json()['data']['sendAddress']
                    order2_sendAddress = w3.to_checksum_address(order2_sendAddress)
                    order2_sendAmount = response.json()['data']['sendAmount']  # to remove
                    order2_receiveAmount = response.json()['data']['receiveAmount']  # to remove
                    print(
                        f"Order 2 ID: {order2_id}, sendAddress: {order2_sendAddress}, sendAmount {order2_sendAmount}, receiveAmount: {order2_receiveAmount}")
                    # time.sleep(5)  # to remove

                    # Step 9: Initiate transfer from wallet 2
                    eth_transfer(wallet2, wallet2_private_key, order2_sendAddress, sendAmount2, chain2,
                                 eth_gas_price)  # sendAmount2 should be in wei in this function

                    # Step 10: Check order status every 10 seconds until complete
                    while True:
                        response = requests.get('https://api.easybit.com/orderStatus', headers=headers,
                                                params={'id': order2_id})
                        if response.json()['data']['status'] == 'Complete':
                            sys.stdout.write(
                                "\rOrder 2 completed successfully.                        \n")  # Clear line and print
                            sys.stdout.flush()
                            break
                        else:
                            answer = response.json()['data']['status']
                            sys.stdout.write(
                                "\rThe status now is {}                        ".format(answer))  # Clear line and print
                            sys.stdout.flush()
                            time.sleep(20)
            print("Transfer is complete.")
            print(
                '---------------------------------------------------------------------------------------------------')
            print(
                '---------------------------------------------------------------------------------------------------')
            print(
                '---------------------------------------------------------------------------------------------------')
