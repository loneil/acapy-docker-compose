import requests
import time
import sys
from dotenv import load_dotenv
import os
import urllib.parse
import qrcode

# Load environment variables from .env file down in the docker folder
load_dotenv(dotenv_path="./docker/.env")

# ANSI  colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def log_and_post(url, data):
    print(f"POST {url} with data: {data}")
    response = requests.post(url, json=data)
    # print(f"Response: {response.status_code} {response.text}")
    if response.status_code not in [200, 201]:
        print(f"{RED}Error: Failed to POST data.")
        print(f"Response: {response.status_code} {response.text}{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}Success {response.status_code}{RESET}")
    return response


def log_and_get(url):
    print(f"GET {url}")
    response = requests.get(url)
    # print(f"Response: {response.status_code} {response.text}")
    return response


def check_status(get_url, resource_id=None, status_field=None, desired_state=None):
    for attempt in range(10):
        time.sleep(2)
        response = log_and_get(f"{get_url}/{resource_id}" if resource_id else get_url)
        if response.status_code not in [200, 201]:
            print(
                f"Failed to get resource status: Response is {response.status_code}. Try again"
            )
            continue

        # if not checking status_field just return the response
        if not status_field:
            return response

        status = response.json().get(status_field)
        if status == desired_state:
            print(f"{GREEN}{status_field} is {desired_state}{RESET}")
            return True
        else:
            print(
                f"Attempt {attempt + 1}: {status_field} is {status}. Expected {desired_state}"
            )

    print(f"{RED}Failed to get completed {status_field} after 10 attempts{RESET}")
    sys.exit(1)
    return False


# ACA-PY admin URL root
base_url = "http://localhost:8077"

# Step 0: Check if the wallet DID is already created, skip all setup if so
wallet_did = os.getenv("WALLET_DID")

if not wallet_did:
    # Step 1: Connect to endorser
    print("\n=================================================================")
    print("Step 1: Connect to endorser")
    endorser_did = os.getenv("ACAPY_ENDORSER_PUBLIC_DID")
    endorser_name = "endorser"
    # Do a did exchange to endorser DID (find and supply DID above)
    didexchange_url = f"{base_url}/didexchange/create-request?their_public_did={endorser_did}&alias=endorser"
    didexchange_response = log_and_post(didexchange_url, {})
    endorser_connection_id = didexchange_response.json().get("connection_id")
    # Check Endorser connection goes to active
    connections_url = f"{base_url}/connections"
    print()
    check_status(connections_url, endorser_connection_id, "state", "active")

    # Step 2: Set the metadata on the connection to endorser
    print("\n=================================================================")
    print("Step 2: Set Connection Metadata")
    # POST to the connectons metadata endpoint and set transaction author
    metadata_url = f"{base_url}/connections/{endorser_connection_id}/metadata"
    metadata_data = {
        "metadata": {
            "endorser_info": {
                "endorser_did": endorser_did,
                "endorser_name": endorser_name,
            },
            "transaction_jobs": {
                "transaction_my_job": "TRANSACTION_AUTHOR",
                "transaction_their_job": "TRANSACTION_ENDORSER",
            },
        }
    }
    log_and_post(metadata_url, metadata_data)

    # Step 3: Create a DID by posting to wallet/did/create
    print("\n=================================================================")
    print("Step 3: Create a DID in the wallet")
    wallet_did_url = f"{base_url}/wallet/did/create"
    wallet_did_data = {
        "method": "sov",
        "options": {"key_type": "ed25519"},
    }
    wallet_did_response = log_and_post(wallet_did_url, wallet_did_data)
    # Get the did and verkey from the response
    verkey = wallet_did_response.json().get("result").get("verkey")
    wallet_did = wallet_did_response.json().get("result").get("did")
    print(f"Wallet DID: {wallet_did}")

    # Step 4: Register the DID on the ledger with /ledger/register-nym, check txn gets to acked
    print("\n=================================================================")
    print("Step 4: Register the DID on the ledger")
    # nym_url = f"{base_url}/ledger/register-nym?did={wallet_did}&verkey={verkey}&conn_id={endorser_connection_id}&create_transaction_for_endorser=true"
    nym_url = f"{base_url}/ledger/register-nym?did={wallet_did}&verkey={verkey}"
    nym_response = log_and_post(nym_url, {})
    # Check transaction state goes to active
    transaction_id = nym_response.json().get("txn").get("transaction_id")
    transactions_url = f"{base_url}/transactions"
    print()
    check_status(transactions_url, transaction_id, "state", "transaction_acked")

    # Step 5: Set the public DID
    print("\n=================================================================")
    print("Step 5: Set Public DID")
    public_did_url = f"{base_url}/wallet/did/public"
    public_did_url_post = f"{public_did_url}?did={wallet_did}"
    log_and_post(public_did_url_post, {})
    # Check public DID resolved
    public_did_response = check_status(public_did_url)
    public_did = public_did_response.json().get("result").get("did")
    print(f"{GREEN}Public DID {public_did}{RESET}")
else:
    print(f"{GREEN}Wallet DID already exists: {wallet_did}{RESET}")

# Step -6: Check if the Cred Def is already created, skip all setup if so
cred_def_id = os.getenv("CRED_DEF_ID")

if not cred_def_id:
    # Step 6: Make a schema
    print("\n=================================================================")
    print("Step 6: Make a schema")
    schema_url = f"{base_url}/schemas"
    schema_data = {
        "schema_version": "1.6",
        "schema_name": "script",
        "attributes": ["name", "age"],
    }
    schema_response = log_and_post(schema_url, schema_data)
    schema_id = schema_response.json().get("sent").get("schema_id")
    print(f"Schema ID: {schema_id}")
    # Check the schema is created on the ledger
    schemas_url = f"{base_url}/schemas"
    print()
    check_status(schemas_url, schema_id)

    # Step 7: Make a credential definition
    print("\n=================================================================")
    print("Step 7: Make a Credential Definition")
    cred_def_url = f"{base_url}/credential-definitions"
    cred_def_data = {
        "schema_id": schema_id,
        "revocation_registry_size": 1000,
        "support_revocation": True,
        "tag": "script_cd",
    }
    cred_def_response = log_and_post(cred_def_url, cred_def_data)
    cred_def_id = cred_def_response.json().get("sent").get("credential_definition_id")
    print(f"Credential Definition ID: {cred_def_id}")
    # Check the cred def txn is acked
    print()
    cred_def_tx_id = cred_def_response.json().get("txn").get("transaction_id")
    transactions_url = f"{base_url}/transactions"
    check_status(transactions_url, cred_def_tx_id, "state", "transaction_acked")
    # Check the cred def is created on the ledger
    print()
    cred_defs_url = f"{base_url}/credential-definitions"
    check_status(cred_defs_url, cred_def_id)
    # Check rev reg is ther for the cred def
    print()
    rev_reg_url = f"{base_url}/revocation/registries/created?cred_def_id={urllib.parse.quote(cred_def_id)}"
    rev_reg_response = check_status(rev_reg_url)
    print(rev_reg_response.json())
else:
    print(f"{GREEN}Cred Def already exists: {cred_def_id}{RESET}")

# Step 8: Create an Out of Band invitation
print("\n=================================================================")
print("Step 8: Create an Out of Band invitation")
oob_url = f"{base_url}/out-of-band/create-invitation"
oob_data = {
    "accept": ["didcomm/aip1", "didcomm/aip2;env=rfc19"],
    "alias": "BC Wallet",
    "goal": "",
    "goal_code": "",
    "handshake_protocols": [
        "https://didcomm.org/didexchange/1.0",
        "https://didcomm.org/connections/1.0",
    ],
    "my_label": "Invitation to BC Wallet",
    "protocol_version": "1.1",
    "use_public_did": False,
}
oob_response = log_and_post(oob_url, oob_data)
oob_invitation_url = oob_response.json().get("invitation_url")
oob_invitation_msg_id = oob_response.json().get("invi_msg_id")
print(f"Out of Band invitation: {oob_invitation_url}")

# Generate and display QR code
print("\n=================================================================")
print("QR Code for Out of Band invitation")
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=1,
    border=4,
)
qr.add_data(oob_invitation_url)
qr.make(fit=True)

# Display QR code in terminal
qr.print_ascii()

# Step 9: Wait for the connection to be established
print("\n=================================================================")
print("Step 9: Wait for the connection to be established")
print(f"{YELLOW}Scan and accept the invitation in your wallet{RESET}")
# Wait for user to hit enter when they are connected
input("Press Enter when you have accepted the invitation in the BC Wallet")
# Find the connection with the invitation message id and check it is active
connections_url = f"{base_url}/connections?invitation_msg_id={oob_invitation_msg_id}"
print()
conn_response=check_status(connections_url)
conn_state = conn_response.json().get("results")[0].get("state")
print(f"Connection state: {conn_state}")
if conn_state == "active":
    print(f"{GREEN}Connection is active{RESET}")
else:
    print(f"{RED}Connection is not active{RESET}")
    sys.exit(1)
