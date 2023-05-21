from web3 import Web3
import os
import re
from eth_account import Account


def validate_ethereum_private_key(private_key):
    return bool(re.fullmatch(r'0x[0-9a-fA-F]{64}', private_key))


def walletFileNormalizer(input_file, output_file):
    # Get ETH RPC from environment variables
    eth_rpc = os.getenv('ETHEREUM_RPC_URL')
    if not eth_rpc:
        raise ValueError("Missing environment variable: ETH_RPC")

    w3 = Web3(Web3.HTTPProvider(eth_rpc))

    # Regular expression patterns
    address_pattern = r'(0x[0-9a-fA-F]{40})(?![0-9a-fA-F]{24})'
    private_key_pattern = r'(0x[0-9a-fA-F]{64})'

    address_to_key = {}
    key_to_address = {}

    with open(input_file, 'r') as in_file:
        content = in_file.read()
        addresses = re.findall(address_pattern, content)
        private_keys = re.findall(private_key_pattern, content)

        for address in addresses:
            try:
                address = w3.to_checksum_address(address)
                address_to_key[address] = None
            except ValueError as e:
                raise ValueError(f'Invalid Ethereum address: {address}') from e

        for key in private_keys:
            if not validate_ethereum_private_key(key):
                raise ValueError(f'Invalid Ethereum private key: {key}')
            account = Account.from_key(key)
            key_to_address[key] = account.address
            if account.address in address_to_key:
                address_to_key[account.address] = key

    unmatched_addresses = [address for address, key in address_to_key.items() if key is None]
    unmatched_keys = [key for key, address in key_to_address.items() if address not in address_to_key]

    if unmatched_keys and len(key_to_address) != len(unmatched_keys):
        raise ValueError("Invalid input file: Not all private keys have matching addresses")
    if unmatched_addresses and len(address_to_key) != len(unmatched_addresses):
        raise ValueError("Invalid input file: Not all addresses have matching private keys")
    if unmatched_addresses and unmatched_keys:
        raise ValueError("Invalid input file: both unmatched addresses and unmatched keys")

    with open(output_file, 'w') as out_file:
        if unmatched_keys:
            # Case 2: Only private keys are provided
            for key in key_to_address:
                out_file.write(f'Address: {key_to_address[key]}\nPrivate Key: {key}\n\n')
        elif unmatched_addresses:
            # Case 3: Only addresses are provided
            for address in address_to_key:
                out_file.write(f'Address: {address}\n\n')
        else:
            # Case 1: Both addresses and keys are provided
            for address, key in address_to_key.items():
                out_file.write(f'Address: {address}\nPrivate Key: {key}\n\n')
