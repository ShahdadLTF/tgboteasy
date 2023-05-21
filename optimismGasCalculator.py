from web3 import Web3, HTTPProvider
import rlp, os, json

def getOptimismGas():
    RPC_URL = os.getenv("ALCHEMY_OPTIMISM_API")
    # Connection to Optimism via Alchemy
    w3 = Web3(HTTPProvider(RPC_URL))

    # Variables (replace these with actual data)
    account_address = '0x000000000000000000000000000000000000dEaD'
    ovm_gasprice_oracle_address = '0x420000000000000000000000000000000000000F'

    # Contract ABI for OVM_GasPriceOracle (replace this with the actual ABI)
    ovm_gasprice_oracle_abi = json.loads('[{"inputs":[{"internalType":"address","name":"_owner","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"DecimalsUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"GasPriceUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"L1BaseFeeUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"OverheadUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"ScalarUpdated","type":"event"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"gasPrice","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes","name":"_data","type":"bytes"}],"name":"getL1Fee","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes","name":"_data","type":"bytes"}],"name":"getL1GasUsed","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"l1BaseFee","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"overhead","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"scalar","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_decimals","type":"uint256"}],"name":"setDecimals","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_gasPrice","type":"uint256"}],"name":"setGasPrice","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_baseFee","type":"uint256"}],"name":"setL1BaseFee","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_overhead","type":"uint256"}],"name":"setOverhead","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_scalar","type":"uint256"}],"name":"setScalar","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"}]')

    # Connecting to the contract
    contract = w3.eth.contract(address=ovm_gasprice_oracle_address, abi=ovm_gasprice_oracle_abi)

    # Fetching the gas price, overhead, scalar, and decimals from OVM_GasPriceOracle
    gas_price = contract.functions.gasPrice().call()

    # Estimating the gas for a simple ETH transfer
    gas_estimate = w3.eth.estimate_gas({
        'to': account_address,
        'from': account_address,
        'gas': 21000,
        'value': w3.to_wei(0.01, 'ether')
    })

    # Fetching the nonce
    nonce = w3.eth.get_transaction_count(account_address)

    # Creating an unsigned transaction
    transaction = {
        'nonce': nonce,
        'gasPrice': 0,
        'gas': 21000,
        'to': account_address,
        'value': w3.to_wei(0.001, 'ether'),
        'data': 0,
    }

    # RLP-encoding the unsigned transaction
    transaction_rlp = rlp.encode([transaction['nonce'], transaction['gasPrice'], transaction['gas'], transaction['to'], transaction['value'], transaction['data']])

    # Fetching the L1 gas used from OVM_GasPriceOracle
    l1_gas_used = contract.functions.getL1GasUsed(transaction_rlp).call()

    # Fetching the L1 base fee from OVM_GasPriceOracle
    l1_base_fee = contract.functions.l1BaseFee().call()

    # Fetching the L1 Fee Scalar
    l1_fee_scalar = contract.functions.scalar().call()

    # Calculating the L2 execution fee
    l2_execution_fee = gas_price * gas_estimate

    # Fetching decimals
    decimals = contract.functions.decimals().call()

    # Calculating the L1 data fee
    l1_data_fee = l1_base_fee * l1_gas_used * l1_fee_scalar/10**decimals

    # Summing the L2 execution fee and the L1 data fee to get the total cost
    total_cost = l2_execution_fee + l1_data_fee

    # Return the values in wei
    return gas_price, total_cost
