<!-- source: https://moondev.com/polymarket-redemption-bot -->
<!-- captured: 2026-10-07 -->
<!-- title: Polymarket Redemption Bot — Multi-Account & Batch MultiSend -->

Polymarket Redemption Bot — Multi-Account & Batch MultiSend | Moon Dev

Moon Dev Open Source

# Polymarket Redemption Bot

Two scripts for redeeming winning Polymarket positions across multiple Gnosis Safe accounts. Script 1 redeems one position at a time with retry logic. Script 2 batches everything into a single MultiSend transaction for ~50% gas savings. Both handle regular and neg-risk markets automatically.

By Moon Dev · March 23, 2026

## What Are These Scripts?

When you win a position on Polymarket, the USDC doesn't magically appear in your wallet. You need to **redeem** the winning conditional tokens back into USDC by calling the correct smart contract. If you're running multiple accounts through Gnosis Safe wallets, this becomes tedious fast. These two scripts automate the entire process.

**Script 1 — Sequential Redemption** loops through each account, finds all redeemable positions via the Polymarket data API, and redeems them one by one. It routes each redemption to the correct contract based on whether the market is a regular market (via CTF) or a neg-risk market (via NegRiskAdapter). Built-in retry logic handles nonce conflicts and RPC rate limits.

**Script 2 — Batch MultiSend** takes a completely different approach. Instead of one transaction per position, it packs ALL redeemable positions for an account into a single Gnosis Safe MultiSend transaction. This means one signature, one on-chain transaction, and roughly half the gas cost.

### Architecture Overview

**Chain** — Polygon (MATIC for gas)

**Wallets** — Gnosis Safe multisig wallets, each with an EOA signer

**Regular Markets** — CTF.redeemPositions(collateral, parentId, conditionId, indexSets)

**Neg-Risk Markets** — NegRiskAdapter.redeemPositions(conditionId, amounts)

**Batch Mode** — Gnosis Safe DELEGATECALL to MultiSend 1.3.0 contract

**Security** — All error messages are sanitized to strip wallet addresses and keys

## Script 1 — Sequential Redemption

The first script is the straightforward approach: loop through accounts, find redeemable positions, redeem each one individually. It's simpler and easier to debug, and it was the first version built before the batch optimization.

The flow starts with get_redeemable() which hits the Polymarket data API to find all positions for a wallet that have redeemable: true and a positive current value. For each position, the script checks whether it's a regular or neg-risk market and routes to the correct contract.

**Regular markets** call CTF.redeemPositions() with the USDC collateral address, a zero parent ID, the condition ID, and index sets [1, 2] to cover both outcomes. **Neg-risk markets** call NegRiskAdapter.redeemPositions() with the condition ID and an amounts array where only the held outcome has a non-zero balance.

The redeem() function handles the Gnosis Safe transaction flow: get the Safe nonce, compute the transaction hash via getTransactionHash(), sign it with the EOA key, verify with a static call first, then broadcast. The static call is a safety check — if it returns false, the script skips the position instead of wasting gas on a transaction that would revert.

Retry logic handles three common failure modes: nonce conflicts (another transaction landed first), RPC rate limits, and transient RPC errors. Each retry bumps the gas price by 25% and waits progressively longer (5s, 10s, 15s). The sanitize_error() function strips wallet addresses and hex strings from error messages before logging — a security measure to prevent leaking sensitive data to logs.

redeem.py — Complete source

```python
"""
MOON DEV's Direct Polymarket Redemption - Multi-Account
========================================================
Redeems winning positions directly through Safe contract.
Handles BOTH regular AND neg-risk markets automatically.
Loops through all accounts, tracks MATIC spent per account.

Regular markets:  CTF.redeemPositions(collateral, parentId, conditionId, indexSets)
Neg-risk markets: NegRiskAdapter.redeemPositions(conditionId, amounts)

USAGE:
  1. Edit ACCOUNTS list below to choose which accounts to process
  2. Fund EOAs with ~0.1 MATIC for gas
  3. Run: python course/jan/redeem.py

Built by Moon Dev
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_abi import encode

# Add parent for .env
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# ============================================================================
# MOON DEV CONFIG - Edit this list to choose which accounts to redeem
# ============================================================================
# Available: "_MAY13", "_DEC11", "_FEB19", "_AUG14", "_APRIL7", "_JAN2", "_MARCH9", ""
# "" = Original account (no suffix)

ACCOUNTS = [
    "_MAY13",
    "_DEC11",
    "_FEB19",
    "_AUG14",
    "_APRIL7",
    "_JAN2",
    "_MARCH9",
]

# ============================================================================
# Contract Addresses (Don't change) - Moon Dev
# ============================================================================
CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
USDC = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
NEG_RISK_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"

SAFE_ABI = json.loads('''[
    {"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"},{"name":"data","type":"bytes"},{"name":"operation","type":"uint8"},{"name":"safeTxGas","type":"uint256"},{"name":"baseGas","type":"uint256"},{"name":"gasPrice","type":"uint256"},{"name":"gasToken","type":"address"},{"name":"refundReceiver","type":"address"},{"name":"signatures","type":"bytes"}],"name":"execTransaction","outputs":[{"name":"success","type":"bool"}],"stateMutability":"payable","type":"function"},
    {"inputs":[],"name":"nonce","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"},{"name":"data","type":"bytes"},{"name":"operation","type":"uint8"},{"name":"safeTxGas","type":"uint256"},{"name":"baseGas","type":"uint256"},{"name":"gasPrice","type":"uint256"},{"name":"gasToken","type":"address"},{"name":"refundReceiver","type":"address"},{"name":"_nonce","type":"uint256"}],"name":"getTransactionHash","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"}
]''')

# ============================================================================
# Functions
# ============================================================================

def sanitize_error(error_msg):
    """Remove any wallet addresses from error messages - Moon Dev security"""
    import re
    msg = str(error_msg)
    # Remove any 0x addresses (40 hex chars after 0x)
    msg = re.sub(r'0x[a-fA-F0-9]{40}', '[HIDDEN]', msg)
    # Remove any long hex strings that could be keys/hashes
    msg = re.sub(r'0x[a-fA-F0-9]{64}', '[HIDDEN]', msg)
    # Remove HexBytes which contain tx hashes
    msg = re.sub(r"HexBytes\('[^']*'\)", '[TX_HASH]', msg)
    # Clean up common RPC errors for readability
    if 'replacement transaction underpriced' in msg.lower():
        return "Nonce conflict - will retry"
    if 'internal_error' in msg.lower():
        return "RPC overloaded - will retry"
    return msg[:200]

def get_redeemable(wallet):
    """Get redeemable positions from Polymarket - Moon Dev"""
    try:
        url = f"https://data-api.polymarket.com/positions?user={wallet}"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return [p for p in r.json() if p.get('redeemable') and float(p.get('currentValue', 0)) > 0]
    except:
        pass
    return []

def encode_redeem_regular(condition_id):
    """Encode redeemPositions call for REGULAR markets via CTF - Moon Dev"""
    selector = Web3.keccak(text="redeemPositions(address,bytes32,bytes32,uint256[])")[:4]
    cid = condition_id[2:] if condition_id.startswith('0x') else condition_id
    args = encode(
        ['address', 'bytes32', 'bytes32', 'uint256[]'],
        [Web3.to_checksum_address(USDC), bytes(32), bytes.fromhex(cid), [1, 2]]
    )
    return selector + args

def encode_redeem_neg_risk(condition_id, token_balance, outcome_index):
    """Encode redeemPositions call for NEG-RISK markets via NegRiskAdapter - Moon Dev"""
    selector = Web3.keccak(text="redeemPositions(bytes32,uint256[])")[:4]
    cid = condition_id[2:] if condition_id.startswith('0x') else condition_id
    # amounts array: [yesAmount, noAmount] - set the held outcome, 0 for the other
    amounts = [0, 0]
    amounts[outcome_index] = token_balance
    args = encode(
        ['bytes32', 'uint256[]'],
        [bytes.fromhex(cid), amounts]
    )
    return selector + args

def get_token_balance(w3, safe_addr, token_id):
    """Get CTF token balance for a position - Moon Dev"""
    ctf_abi = [{'constant': True, 'inputs': [{'name': 'account', 'type': 'address'}, {'name': 'id', 'type': 'uint256'}], 'name': 'balanceOf', 'outputs': [{'name': '', 'type': 'uint256'}], 'type': 'function'}]
    ctf = w3.eth.contract(address=Web3.to_checksum_address(CTF), abi=ctf_abi)
    return ctf.functions.balanceOf(Web3.to_checksum_address(safe_addr), int(token_id)).call()

def redeem(w3, pk, safe_addr, position, gas_multiplier=1.0):
    """Redeem a single position (regular or neg-risk) - Moon Dev"""
    account = Account.from_key(pk)
    safe = w3.eth.contract(address=Web3.to_checksum_address(safe_addr), abi=SAFE_ABI)

    condition_id = position.get('conditionId')
    is_neg_risk = position.get('negativeRisk', False)

    if is_neg_risk:
        # Neg-risk: call NegRiskAdapter.redeemPositions(conditionId, amounts)
        token_id = position.get('asset')
        outcome_index = position.get('outcomeIndex', 0)
        token_bal = get_token_balance(w3, safe_addr, token_id)
        if token_bal == 0:
            print(f"       Moon Dev - No token balance, skipping")
            return False, "", 0.0
        data = encode_redeem_neg_risk(condition_id, token_bal, outcome_index)
        to = Web3.to_checksum_address(NEG_RISK_ADAPTER)
        print(f"       [NEG-RISK] via NegRiskAdapter, tokens: {token_bal/1e6:.2f}")
    else:
        # Regular: call CTF.redeemPositions(collateral, parentId, conditionId, indexSets)
        data = encode_redeem_regular(condition_id)
        to = Web3.to_checksum_address(CTF)
        print(f"       [REGULAR] via CTF")

    nonce = safe.functions.nonce().call()

    tx_hash = safe.functions.getTransactionHash(
        to, 0, data, 0, 0, 0, 0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        nonce
    ).call()

    # Sign
    try:
        signed = account.signHash(tx_hash)
    except AttributeError:
        signed = account.unsafe_sign_hash(tx_hash)
    sig = signed.r.to_bytes(32, 'big') + signed.s.to_bytes(32, 'big') + bytes([signed.v])

    # Static call first to verify - Moon Dev safety check
    safe_result = safe.functions.execTransaction(
        to, 0, data, 0, 0, 0, 0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        sig
    ).call({'from': account.address})

    if not safe_result:
        print(f"       Moon Dev - Static call returned FALSE, skipping to avoid wasting gas")
        return False, "", 0.0

    # Execute
    # Moon Dev - use 'pending' to get nonce past any stuck txs, bump gas on retries
    base_gas = w3.eth.gas_price
    bumped_gas = int(base_gas * max(gas_multiplier, 1.0))
    eoa_nonce = w3.eth.get_transaction_count(account.address, 'pending')

    tx = safe.functions.execTransaction(
        to, 0, data, 0, 0, 0, 0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        sig
    ).build_transaction({
        'from': account.address,
        'gas': 500000,
        'gasPrice': bumped_gas,
        'nonce': eoa_nonce,
    })

    signed_tx = w3.eth.account.sign_transaction(tx, pk)
    raw = getattr(signed_tx, 'rawTransaction', None) or getattr(signed_tx, 'raw_transaction', None)
    tx_hash = w3.eth.send_raw_transaction(raw)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    # Calculate gas used in MATIC
    gas_used = receipt['gasUsed']
    gas_price = receipt['effectiveGasPrice']
    matic_spent = w3.from_wei(gas_used * gas_price, 'ether')

    return receipt['status'] == 1, tx_hash.hex(), float(matic_spent)

def process_account(w3, account_suffix):
    """Process redemptions for a single account - Moon Dev"""
    result = {
        'account': account_suffix.replace("_", "") if account_suffix else "ORIGINAL",
        'matic_spent': 0.0,
        'redeemed_value': 0.0,
        'success_count': 0,
        'total_positions': 0,
        'skipped': False,
        'skip_reason': None
    }

    # Load credentials
    pk = os.getenv(f"PRIVATE_KEY{account_suffix}")
    safe = os.getenv(f"PUBLIC_KEY{account_suffix}")

    if not pk or not safe:
        result['skipped'] = True
        result['skip_reason'] = "Missing credentials"
        return result

    print(f"\n{'='*60}")
    print(f"MOON DEV - Account: {result['account']}")
    print(f"{'='*60}")

    # Get EOA and check MATIC (addresses never printed - Moon Dev security)
    eoa = Account.from_key(pk).address
    matic_before = float(w3.from_wei(w3.eth.get_balance(eoa), 'ether'))
    print(f"   MATIC Balance: {matic_before:.4f}")

    if matic_before < 0.05:
        result['skipped'] = True
        result['skip_reason'] = "Need MATIC"
        print(f"   SKIPPED - Need MATIC for gas!")
        return result

    # Get redeemable positions
    positions = get_redeemable(safe)
    result['total_positions'] = len(positions)

    if not positions:
        print(f"   No redeemable positions with value")
        return result

    total_value = sum(float(p.get('currentValue', 0)) for p in positions)
    print(f"   Found {len(positions)} positions worth ${total_value:.2f}")
    print(f"   Redeeming...")

    # Redeem each position with retry logic - Moon Dev
    for i, pos in enumerate(positions):
        title = pos.get('title', 'Unknown')
        value = float(pos.get('currentValue', 0))
        is_neg = pos.get('negativeRisk', False)

        print(f"\n   [{i+1}/{len(positions)}] {title}")
        print(f"       Value: ${value:.2f} {'(NEG-RISK)' if is_neg else '(REGULAR)'}")

        # Retry up to 3 times with increasing delays and gas bumps - Moon Dev
        max_retries = 3
        for attempt in range(max_retries):
            try:
                gas_mult = 1.0 + (attempt * 0.25)  # 1.0x, 1.25x, 1.5x gas on retries
                ok, tx, matic_used = redeem(w3, pk, safe, pos, gas_multiplier=gas_mult)
                if ok:
                    result['success_count'] += 1
                    result['redeemed_value'] += value
                    result['matic_spent'] += matic_used
                    print(f"       Redeemed! (Gas: {matic_used:.4f} MATIC)")
                    break
                else:
                    print(f"       Failed")
                    break
            except Exception as e:
                error_msg = sanitize_error(e)
                if attempt < max_retries - 1 and ("retry" in error_msg.lower() or "nonce" in error_msg.lower() or "rpc" in error_msg.lower()):
                    wait_time = (attempt + 1) * 5  # 5s, 10s, 15s - Moon Dev
                    print(f"       {error_msg} (retry in {wait_time}s...)")
                    time.sleep(wait_time)
                else:
                    print(f"       Error: {error_msg}")
                    break

        time.sleep(5)  # Moon Dev - delay between redemptions to avoid nonce issues

    # Final MATIC check
    matic_after = float(w3.from_wei(w3.eth.get_balance(eoa), 'ether'))
    actual_spent = matic_before - matic_after
    result['matic_spent'] = actual_spent

    print(f"\n   Account Summary:")
    print(f"   Redeemed: {result['success_count']}/{len(positions)} positions")
    print(f"   Value: ${result['redeemed_value']:.2f}")
    print(f"   MATIC Spent: {result['matic_spent']:.4f}")

    return result

def main():
    print("\n" + "="*60)
    print("MOON DEV's MULTI-ACCOUNT REDEMPTION")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Accounts to process: {len(ACCOUNTS)}")

    # Connect to Polygon
    for rpc_url in ['https://1rpc.io/matic', 'https://polygon.drpc.org']:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
        if w3.is_connected():
            print(f"Connected to: {rpc_url}")
            break
    else:
        w3 = None
    if not w3 or not w3.is_connected():
        print("Failed to connect to Polygon RPC!")
        return

    # Process each account
    all_results = []
    for account_suffix in ACCOUNTS:
        result = process_account(w3, account_suffix)
        all_results.append(result)
        time.sleep(1)

    # ========================================================================
    # MOON DEV's GRAND SUMMARY
    # ========================================================================
    print("\n" + "="*60)
    print("MOON DEV's REDEMPTION SUMMARY")
    print("="*60)

    total_matic = 0.0
    total_redeemed = 0.0
    total_success = 0
    total_positions = 0

    print(f"\n   {'Account':<12} {'Redeemed':>10} {'MATIC':>10} {'Status':>15}")
    print(f"   {'-'*50}")

    for r in all_results:
        if r['skipped']:
            safe_reason = r['skip_reason'][:12] if r['skip_reason'] else "Unknown"
            status = f"SKIP: {safe_reason}"
            print(f"   {r['account']:<12} {'$0.00':>10} {'0.0000':>10} {status:>15}")
        else:
            total_matic += r['matic_spent']
            total_redeemed += r['redeemed_value']
            total_success += r['success_count']
            total_positions += r['total_positions']
            status = f"{r['success_count']}/{r['total_positions']} OK"
            print(f"   {r['account']:<12} ${r['redeemed_value']:>8,.2f} {r['matic_spent']:>10.4f} {status:>15}")

    print(f"   {'-'*50}")
    print(f"   {'TOTAL':<12} ${total_redeemed:>8,.2f} {total_matic:>10.4f} {total_success}/{total_positions} OK")

    # Cost analysis
    if total_redeemed > 0 and total_matic > 0:
        matic_price = 0.12
        cost_usd = total_matic * matic_price
        cost_percent = (cost_usd / total_redeemed) * 100
        cost_per_redeem_matic = total_matic / total_success if total_success > 0 else 0
        cost_per_redeem_usd = cost_usd / total_success if total_success > 0 else 0

        print(f"\n   {'='*50}")
        print(f"   MOON DEV's COST ANALYSIS")
        print(f"   {'='*50}")
        print(f"   Total MATIC Used:     {total_matic:.6f} MATIC")
        print(f"   Total USD Cost:       ${cost_usd:.4f} (at $0.12/MATIC)")
        print(f"   Cost as % of Value:   {cost_percent:.3f}%")
        print(f"   ")
        print(f"   COST PER REDEMPTION:")
        print(f"      MATIC: {cost_per_redeem_matic:.6f}")
        print(f"      USD:   ${cost_per_redeem_usd:.4f}")

    print("\n" + "="*60)
    print("MOON DEV - Redemption Complete!")
    print("="*60 + "\n")

    return all_results

if __name__ == "__main__":
    main()
```
Here is what each key function does:

sanitize_error() strips wallet addresses, hex strings, and transaction hashes from error messages before they hit the console. This prevents accidental leaking of sensitive data in logs or screenshots.

get_redeemable() queries the Polymarket data API for all positions belonging to a wallet, then filters to only those marked as redeemable with a positive value. This is the discovery step — it tells us what needs to be claimed.

encode_redeem_regular() and encode_redeem_neg_risk() build the raw calldata for each contract type. Regular markets always pass index sets [1, 2] to cover both Yes and No outcomes. Neg-risk markets need the actual token balance and the outcome index to build the amounts array.

redeem() orchestrates the full Gnosis Safe transaction: get nonce, compute hash, sign, static-call verify, then broadcast. The static call is critical — it simulates the transaction without spending gas. If it returns false, the transaction would revert on-chain, so we skip it.

process_account() ties it all together for one account: load credentials from environment variables, check MATIC balance, fetch positions, and loop through redemptions with retry logic. The main() function loops over all accounts and prints a summary table with cost analysis at the end.

## Script 2 — Batch MultiSend

The batch version is the gas-optimized evolution. Instead of N separate transactions for N positions, it packs all redemptions into a single Gnosis Safe DELEGATECALL to the MultiSend 1.3.0 contract. One signature, one transaction, one base gas cost — regardless of how many positions are being redeemed.

The key difference is the pack_multisend_data() function. MultiSend expects a tightly packed byte array where each sub-transaction is encoded as: operation (1 byte) + to address (20 bytes) + value (32 bytes) + data length (32 bytes) + data (variable). All sub-transactions use operation 0 (CALL), while the Safe itself calls MultiSend via operation 1 (DELEGATECALL).

The batch_redeem() function builds all individual redeem calldata (same encoding as Script 1), packs them into the MultiSend format, then executes through the Safe. Gas estimation uses eth_estimateGas with a 20% buffer. If estimation fails (which can happen with complex multicalls), it falls back to a formula: 200,000 base + 100,000 per sub-call.

The summary at the end includes a **batch savings comparison** that estimates what the sequential approach would have cost and shows the percentage saved. In practice, batch transactions save roughly 40-60% on gas because you only pay the base transaction overhead once.

redeem_batch.py — Complete source

```python
"""
MOON DEV's Batch Polymarket Redemption - Multi-Account
=======================================================
Batches ALL redeemable positions per account into ONE transaction!
Uses Gnosis Safe MultiSend for ~50% gas savings.
Handles BOTH regular AND neg-risk markets automatically.

Regular markets:  CTF.redeemPositions(collateral, parentId, conditionId, indexSets)
Neg-risk markets: NegRiskAdapter.redeemPositions(conditionId, amounts)

USAGE:
  1. Edit ACCOUNTS list below to choose which accounts to process
  2. Fund EOAs with ~0.1 MATIC for gas
  3. Run: python course/jan/redeem_batch.py

Built by Moon Dev
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_abi import encode

# Add parent for .env
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# ============================================================================
# MOON DEV CONFIG - Edit this list to choose which accounts to redeem
# ============================================================================
ACCOUNTS = [
    "_MAY13",
    "_DEC11",
    "_FEB19",
    "_AUG14",
    "_APRIL7",
    "_JAN2",
    "_MARCH9",
]

# ============================================================================
# Contract Addresses (Don't change)
# ============================================================================
CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
USDC = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
NEG_RISK_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
MULTISEND = "0xA238CBeb142c10Ef7Ad8442C6D1f9E89e07e7761"  # Safe MultiSend 1.3.0 on Polygon

SAFE_ABI = json.loads('''[
    {"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"},{"name":"data","type":"bytes"},{"name":"operation","type":"uint8"},{"name":"safeTxGas","type":"uint256"},{"name":"baseGas","type":"uint256"},{"name":"gasPrice","type":"uint256"},{"name":"gasToken","type":"address"},{"name":"refundReceiver","type":"address"},{"name":"signatures","type":"bytes"}],"name":"execTransaction","outputs":[{"name":"success","type":"bool"}],"stateMutability":"payable","type":"function"},
    {"inputs":[],"name":"nonce","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"},{"name":"data","type":"bytes"},{"name":"operation","type":"uint8"},{"name":"safeTxGas","type":"uint256"},{"name":"baseGas","type":"uint256"},{"name":"gasPrice","type":"uint256"},{"name":"gasToken","type":"address"},{"name":"refundReceiver","type":"address"},{"name":"_nonce","type":"uint256"}],"name":"getTransactionHash","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"}
]''')

MULTISEND_ABI = json.loads('''[
    {"inputs":[{"internalType":"bytes","name":"transactions","type":"bytes"}],"name":"multiSend","outputs":[],"stateMutability":"payable","type":"function"}
]''')

# ============================================================================
# Functions
# ============================================================================

def sanitize_error(error_msg):
    """Remove any wallet addresses from error messages - Moon Dev security"""
    import re
    msg = str(error_msg)
    msg = re.sub(r'0x[a-fA-F0-9]{40}', '[HIDDEN]', msg)
    msg = re.sub(r'0x[a-fA-F0-9]{64}', '[HIDDEN]', msg)
    msg = re.sub(r"HexBytes\('[^']*'\)", '[TX_HASH]', msg)
    if 'replacement transaction underpriced' in msg.lower():
        return "Nonce conflict - will retry"
    if 'internal_error' in msg.lower():
        return "RPC overloaded - will retry"
    return msg[:200]

def get_redeemable(wallet):
    """Get redeemable positions from Polymarket - Moon Dev"""
    try:
        url = f"https://data-api.polymarket.com/positions?user={wallet}"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return [p for p in r.json() if p.get('redeemable') and float(p.get('currentValue', 0)) > 0]
    except:
        pass
    return []

def encode_redeem_regular(condition_id):
    """Encode redeemPositions call for REGULAR markets via CTF - Moon Dev"""
    selector = Web3.keccak(text="redeemPositions(address,bytes32,bytes32,uint256[])")[:4]
    cid = condition_id[2:] if condition_id.startswith('0x') else condition_id
    args = encode(
        ['address', 'bytes32', 'bytes32', 'uint256[]'],
        [Web3.to_checksum_address(USDC), bytes(32), bytes.fromhex(cid), [1, 2]]
    )
    return selector + args

def encode_redeem_neg_risk(condition_id, token_balance, outcome_index):
    """Encode redeemPositions call for NEG-RISK markets via NegRiskAdapter - Moon Dev"""
    selector = Web3.keccak(text="redeemPositions(bytes32,uint256[])")[:4]
    cid = condition_id[2:] if condition_id.startswith('0x') else condition_id
    amounts = [0, 0]
    amounts[outcome_index] = token_balance
    args = encode(
        ['bytes32', 'uint256[]'],
        [bytes.fromhex(cid), amounts]
    )
    return selector + args

def get_token_balance(w3, safe_addr, token_id):
    """Get CTF token balance for a position - Moon Dev"""
    ctf_abi = [{'constant': True, 'inputs': [{'name': 'account', 'type': 'address'}, {'name': 'id', 'type': 'uint256'}], 'name': 'balanceOf', 'outputs': [{'name': '', 'type': 'uint256'}], 'type': 'function'}]
    ctf = w3.eth.contract(address=Web3.to_checksum_address(CTF), abi=ctf_abi)
    return ctf.functions.balanceOf(Web3.to_checksum_address(safe_addr), int(token_id)).call()

def pack_multisend_data(calls):
    """
    Pack multiple calls into MultiSend format - Moon Dev
    Format per call: operation (1 byte) + to (20 bytes) + value (32 bytes) + dataLength (32 bytes) + data
    """
    packed = b''
    for call in calls:
        to_addr = bytes.fromhex(call['to'][2:])  # 20 bytes
        value = call.get('value', 0).to_bytes(32, 'big')  # 32 bytes
        data = call['data']
        data_length = len(data).to_bytes(32, 'big')  # 32 bytes
        operation = (0).to_bytes(1, 'big')  # 0 = CALL, 1 = DELEGATECALL

        packed += operation + to_addr + value + data_length + data

    return packed

def encode_multisend(calls):
    """Encode the multiSend function call with packed transactions"""
    packed_txs = pack_multisend_data(calls)
    selector = Web3.keccak(text="multiSend(bytes)")[:4]
    # Encode bytes parameter (offset + length + data)
    offset = (32).to_bytes(32, 'big')  # offset to data
    length = len(packed_txs).to_bytes(32, 'big')
    # Pad data to 32-byte boundary
    padding_needed = (32 - (len(packed_txs) % 32)) % 32
    padded_data = packed_txs + bytes(padding_needed)

    return selector + offset + length + padded_data

def batch_redeem(w3, pk, safe_addr, positions):
    """Batch redeem multiple positions in ONE transaction - Moon Dev
    Handles both regular and neg-risk markets automatically."""
    account = Account.from_key(pk)
    safe = w3.eth.contract(address=Web3.to_checksum_address(safe_addr), abi=SAFE_ABI)

    # Build all redeem calls - route to correct contract based on neg-risk flag
    calls = []
    for pos in positions:
        cid = pos.get('conditionId')
        is_neg_risk = pos.get('negativeRisk', False)

        if is_neg_risk:
            token_id = pos.get('asset')
            outcome_index = pos.get('outcomeIndex', 0)
            token_bal = get_token_balance(w3, safe_addr, token_id)
            if token_bal == 0:
                print(f"      Moon Dev - Skipping {pos.get('title', '?')[:30]}, no token balance")
                continue
            calls.append({
                'to': NEG_RISK_ADAPTER,
                'value': 0,
                'data': encode_redeem_neg_risk(cid, token_bal, outcome_index)
            })
            print(f"      [NEG-RISK] {pos.get('title', '?')[:40]} tokens={token_bal/1e6:.2f}")
        else:
            calls.append({
                'to': CTF,
                'value': 0,
                'data': encode_redeem_regular(cid)
            })
            print(f"      [REGULAR] {pos.get('title', '?')[:40]}")

    if not calls:
        print("      Moon Dev - No valid calls to batch")
        return False, "", 0.0

    # Encode MultiSend call
    multisend_data = encode_multisend(calls)

    # Get Safe nonce
    nonce = safe.functions.nonce().call()

    # Get transaction hash for signing (operation=1 for DELEGATECALL to MultiSend)
    tx_hash = safe.functions.getTransactionHash(
        Web3.to_checksum_address(MULTISEND),  # to: MultiSend contract
        0,                                      # value
        multisend_data,                         # data
        1,                                      # operation: 1 = DELEGATECALL
        0,                                      # safeTxGas
        0,                                      # baseGas
        0,                                      # gasPrice
        "0x0000000000000000000000000000000000000000",  # gasToken
        "0x0000000000000000000000000000000000000000",  # refundReceiver
        nonce
    ).call()

    # Sign the transaction hash
    signed = account.signHash(tx_hash)
    sig = signed.r.to_bytes(32, 'big') + signed.s.to_bytes(32, 'big') + bytes([signed.v])

    # Build tx first without gas to let web3 estimate
    tx_params = {
        'from': account.address,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    }

    # Execute the batched transaction
    tx = safe.functions.execTransaction(
        Web3.to_checksum_address(MULTISEND),
        0,
        multisend_data,
        1,  # DELEGATECALL
        0, 0, 0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        sig
    ).build_transaction(tx_params)

    # Let web3 estimate gas properly + 20% buffer
    try:
        estimated_gas = w3.eth.estimate_gas(tx)
        tx['gas'] = int(estimated_gas * 1.2)  # 20% buffer
        print(f"      Gas estimate: {estimated_gas:,} (limit: {tx['gas']:,})")
    except Exception as e:
        # Fallback to reasonable estimate if estimation fails
        tx['gas'] = 200000 + (len(calls) * 100000)
        print(f"      Gas estimate failed, using fallback: {tx['gas']:,}")

    gas_price_gwei = w3.from_wei(tx['gasPrice'], 'gwei')
    print(f"      Gas price: {gas_price_gwei:.1f} gwei")

    signed_tx = w3.eth.account.sign_transaction(tx, pk)
    raw = getattr(signed_tx, 'rawTransaction', None) or getattr(signed_tx, 'raw_transaction', None)
    tx_hash = w3.eth.send_raw_transaction(raw)

    print(f"      Tx sent, waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)  # 60s timeout

    # Calculate gas used in MATIC
    gas_used = receipt['gasUsed']
    gas_price = receipt['effectiveGasPrice']
    matic_spent = w3.from_wei(gas_used * gas_price, 'ether')

    print(f"      Actual gas used: {gas_used:,}")

    return receipt['status'] == 1, tx_hash.hex(), float(matic_spent)

def process_account(w3, account_suffix):
    """Process batch redemption for a single account - Moon Dev"""
    result = {
        'account': account_suffix.replace("_", "") if account_suffix else "ORIGINAL",
        'matic_spent': 0.0,
        'redeemed_value': 0.0,
        'success_count': 0,
        'total_positions': 0,
        'skipped': False,
        'skip_reason': None,
        'batched': False
    }

    # Load credentials
    pk = os.getenv(f"PRIVATE_KEY{account_suffix}")
    safe = os.getenv(f"PUBLIC_KEY{account_suffix}")

    if not pk or not safe:
        result['skipped'] = True
        result['skip_reason'] = "Missing credentials"
        return result

    print(f"\n{'='*60}")
    print(f"MOON DEV BATCH - Account: {result['account']}")
    print(f"{'='*60}")

    # Get EOA and check MATIC
    eoa = Account.from_key(pk).address
    matic_before = float(w3.from_wei(w3.eth.get_balance(eoa), 'ether'))
    print(f"   MATIC Balance: {matic_before:.4f}")

    if matic_before < 0.05:
        result['skipped'] = True
        result['skip_reason'] = "Need MATIC"
        print(f"   SKIPPED - Need MATIC for gas!")
        return result

    # Get redeemable positions
    positions = get_redeemable(safe)
    result['total_positions'] = len(positions)

    if not positions:
        print(f"   No redeemable positions with value")
        return result

    total_value = sum(float(p.get('currentValue', 0)) for p in positions)
    print(f"   Found {len(positions)} positions worth ${total_value:.2f}")

    # List all positions - Moon Dev
    for i, pos in enumerate(positions):
        title = pos.get('title', 'Unknown')[:40]
        value = float(pos.get('currentValue', 0))
        neg = "NEG-RISK" if pos.get('negativeRisk') else "REGULAR"
        print(f"      [{i+1}] ${value:.2f} [{neg}] - {title}...")

    # Filter positions with valid condition IDs
    valid_positions = [p for p in positions if p.get('conditionId')]

    if not valid_positions:
        print(f"   No valid condition IDs found")
        return result

    print(f"\n   BATCHING {len(valid_positions)} redeems into ONE transaction...")

    # Retry logic for batch redeem
    max_retries = 3
    for attempt in range(max_retries):
        try:
            ok, tx_hash, matic_used = batch_redeem(w3, pk, safe, valid_positions)
            if ok:
                result['success_count'] = len(valid_positions)
                result['redeemed_value'] = total_value
                result['matic_spent'] = matic_used
                result['batched'] = True
                print(f"   BATCH SUCCESS!")
                print(f"   Redeemed: {len(valid_positions)} positions")
                print(f"   Value: ${total_value:.2f}")
                print(f"   Gas: {matic_used:.6f} MATIC")
                print(f"   Cost per redeem: {matic_used/len(valid_positions):.6f} MATIC")
                break
            else:
                print(f"   Batch failed - tx reverted")
                break
        except Exception as e:
            error_msg = sanitize_error(e)
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"   Error: {error_msg}")
                print(f"   Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"   BATCH FAILED after {max_retries} attempts: {error_msg}")
                result['skip_reason'] = f"Batch failed: {error_msg[:30]}"

    # Final MATIC check
    matic_after = float(w3.from_wei(w3.eth.get_balance(eoa), 'ether'))
    actual_spent = matic_before - matic_after
    if actual_spent > 0:
        result['matic_spent'] = actual_spent

    return result

def main():
    print("\n" + "="*60)
    print("MOON DEV's BATCH REDEMPTION (MultiSend)")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Accounts to process: {len(ACCOUNTS)}")
    print(f"MultiSend Contract: {MULTISEND[:20]}...")

    # Connect to Polygon
    w3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL', 'https://polygon-rpc.com')))
    if not w3.is_connected():
        print("Failed to connect to Polygon RPC!")
        return

    # Process each account
    all_results = []
    for account_suffix in ACCOUNTS:
        result = process_account(w3, account_suffix)
        all_results.append(result)
        time.sleep(2)

    # ========================================================================
    # MOON DEV's GRAND SUMMARY
    # ========================================================================
    print("\n" + "="*60)
    print("MOON DEV's BATCH REDEMPTION SUMMARY")
    print("="*60)

    total_matic = 0.0
    total_redeemed = 0.0
    total_success = 0
    total_positions = 0
    total_batches = 0

    print(f"\n   {'Account':<12} {'Redeemed':>10} {'MATIC':>12} {'Per Redeem':>12} {'Status':>12}")
    print(f"   {'-'*60}")

    for r in all_results:
        if r['skipped']:
            safe_reason = r['skip_reason'][:12] if r['skip_reason'] else "Unknown"
            status = f"SKIP"
            print(f"   {r['account']:<12} {'$0.00':>10} {'0.000000':>12} {'N/A':>12} {status:>12}")
        elif r['success_count'] == 0:
            print(f"   {r['account']:<12} {'$0.00':>10} {'0.000000':>12} {'N/A':>12} {'No positions':>12}")
        else:
            total_matic += r['matic_spent']
            total_redeemed += r['redeemed_value']
            total_success += r['success_count']
            total_positions += r['total_positions']
            if r['batched']:
                total_batches += 1

            per_redeem = r['matic_spent'] / r['success_count'] if r['success_count'] > 0 else 0
            status = f"{r['success_count']} BATCHED" if r['batched'] else f"{r['success_count']} OK"
            print(f"   {r['account']:<12} ${r['redeemed_value']:>8.2f} {r['matic_spent']:>12.6f} {per_redeem:>12.6f} {status:>12}")

    print(f"   {'-'*60}")

    avg_per_redeem = total_matic / total_success if total_success > 0 else 0
    print(f"   {'TOTAL':<12} ${total_redeemed:>8.2f} {total_matic:>12.6f} {avg_per_redeem:>12.6f} {total_success} redeems")

    # Cost analysis
    if total_redeemed > 0 and total_matic > 0:
        matic_price = 0.12
        cost_usd = total_matic * matic_price
        cost_percent = (cost_usd / total_redeemed) * 100
        cost_per_redeem_usd = cost_usd / total_success if total_success > 0 else 0

        print(f"\n   {'='*60}")
        print(f"   MOON DEV's COST ANALYSIS")
        print(f"   {'='*60}")
        print(f"   Total MATIC Used:     {total_matic:.6f} MATIC")
        print(f"   Total USD Cost:       ${cost_usd:.4f} (at $0.12/MATIC)")
        print(f"   Total Value Redeemed: ${total_redeemed:.2f}")
        print(f"   Cost as % of Value:   {cost_percent:.3f}%")
        print(f"   ")
        print(f"   Redemptions:          {total_success} positions")
        print(f"   Batched Transactions: {total_batches}")
        print(f"   ")
        print(f"   COST PER REDEMPTION:")
        print(f"      MATIC: {avg_per_redeem:.6f}")
        print(f"      USD:   ${cost_per_redeem_usd:.4f}")

        # Compare to non-batched estimate
        estimated_single_cost = total_success * 0.0008  # ~0.0008 MATIC per single redeem
        savings = estimated_single_cost - total_matic
        savings_pct = (savings / estimated_single_cost * 100) if estimated_single_cost > 0 else 0

        if savings > 0:
            print(f"   ")
            print(f"   BATCH SAVINGS:")
            print(f"      Est. Single Cost:  {estimated_single_cost:.6f} MATIC")
            print(f"      Actual Batch Cost: {total_matic:.6f} MATIC")
            print(f"      Saved:             {savings:.6f} MATIC ({savings_pct:.1f}%)")

    print("\n" + "="*60)
    print("MOON DEV - Batch Redemption Complete!")
    print("="*60 + "\n")

    return all_results

if __name__ == "__main__":
    main()
```
Here are the key functions unique to the batch version:

pack_multisend_data() is the core of the batching logic. It takes an array of call objects (each with to, value, and data) and packs them into the byte format that the MultiSend contract expects. Each sub-transaction is exactly: 1 byte operation + 20 bytes address + 32 bytes value + 32 bytes data length + variable data.

encode_multisend() wraps the packed data into a proper ABI-encoded function call to multiSend(bytes). This includes the function selector, the offset to the bytes parameter, the length, and the data padded to a 32-byte boundary.

batch_redeem() orchestrates everything: builds individual calldata for each position (routing regular vs neg-risk to the correct contract), packs them into MultiSend format, signs through the Safe with operation 1 (DELEGATECALL), estimates gas, and broadcasts. The DELEGATECALL is important — it means MultiSend executes in the context of the Safe, so the Safe is the msg.sender for each sub-call.

The savings comparison at the end estimates what sequential redemption would have cost (roughly 0.0008 MATIC per individual redeem) and shows how much the batch approach saved. With 5-10 positions per account, this typically saves 40-60% on total gas costs.

## Key Takeaways

### What to Take Away

**Two approaches, one goal** — Script 1 redeems positions individually with retry logic. Script 2 batches everything into one MultiSend transaction. Use Script 1 for debugging or small accounts. Use Script 2 for production with many positions.

**Regular vs neg-risk routing** — Polymarket has two types of markets with different smart contracts. Regular markets go through the CTF contract with index sets. Neg-risk markets go through the NegRiskAdapter with specific amounts. Both scripts handle this automatically based on the position metadata.

**Gnosis Safe flow** — Both scripts follow the same pattern: get Safe nonce, compute transaction hash, sign with EOA, execute through Safe. The batch version uses DELEGATECALL to MultiSend so the Safe is the caller for each sub-transaction.

**Security by default** — Error messages are sanitized to strip addresses and hex strings. Wallet addresses are never printed. Environment variables hold all secrets. The static call pre-check in Script 1 prevents wasting gas on transactions that would revert.

**Cost tracking** — Both scripts track MATIC spent per account and print a detailed cost analysis at the end. The batch version includes a savings comparison showing how much gas was saved versus the sequential approach.

## Getting Started

Both scripts require Polygon (MATIC) for gas and Gnosis Safe wallets with winning Polymarket positions.

### Requirements

**1. Python 3.10+** — Any recent Python version works.

**2. Install dependencies** — pip install web3 eth-account eth-abi requests python-dotenv

**3. Environment variables** — Create a .env file with PRIVATE_KEY_SUFFIX and PUBLIC_KEY_SUFFIX for each account. The private key is the EOA signer, the public key is the Gnosis Safe address.

**4. Fund EOAs** — Each EOA signer needs ~0.05-0.1 MATIC for gas. The script checks and skips underfunded accounts.

**5. Edit ACCOUNTS** — Update the ACCOUNTS list to match your environment variable suffixes.

**6. Run** — python redeem.py for sequential or python redeem_batch.py for batched.

## Want to learn more?

Join the Moon Dev community to discuss Polymarket strategies, automation tools, and trading systems.

[Visit Moon Dev](https://moondev.com)

Built with love by Moon Dev

### Related Resources

[Polymarket 5-Minute Bot — Easy Hyper Gambler](https://moondev.com/polymarket-five-minute-bot)

— Keyboard-controlled bot for manual Polymarket trading

[Polymarket Hyperliquid Liquidation Statistical Arbitrage](https://moondev.com/polymarket-hyperliquid-liquidation-statistical-arbitrage)

— Cross-platform stat arb between Polymarket and Hyperliquid

[XGBoost Raw Candle ML Model — Polymarket BTC 5-Min Pipeline](https://moondev.com/xgboost-raw-candles-polymarket)

— ML pipeline for predicting BTC 5-minute markets

[MACD 5-Minute Backtest — Polymarket BTC Strategy](https://moondev.com/macd-five-minute-backtest)

— The original MACD crossover backtest for Polymarket

[Moon Dev API Documentation](https://moondev.com/docs)

— Tick data, liquidation data, funding rates, and more

[Live Liquidation Dashboard](https://moondev.com/liquidations)

— Watch real time liquidations
