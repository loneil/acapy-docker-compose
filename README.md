In Bash, in `docker`
`./manage up`

localhost:8077
No PW required


Connect to endorser (do a did exchange to DID)
DfQetNSm7gGEHuzfUvpfPn
5d1e0767-2f68-46c3-af1c-efa7245aa562

Set connection metadata
5d1e0767-2f68-46c3-af1c-efa7245aa562
{
    "endorser_info": {
        "endorser_did": "DfQetNSm7gGEHuzfUvpfPn",
        "endorser_name": "bcovrin-test-endorser"
    },
    "transaction_jobs": {
        "transaction_my_job": "TRANSACTION_AUTHOR",
        "transaction_their_job": "TRANSACTION_ENDORSER"
    }
}



Make DID (wallet/did/create)
{
          method: 'sov',
          options: { key_type: 'ed25519' },
        }
RESULT not body below
{
  "result": {
    "did": "BtL9Krb7uuCo8CVoJKMQcB",
    "verkey": "6w6b6SGMR8jjd3aBy9r262hpjDFaacRqxnV3A7xkQQJ5",
    "posture": "wallet_only",
    "key_type": "ed25519",
    "method": "sov",
    "metadata": {}
  }
}

Register DID /ledger/register-nym
USe did and verkey
Set endorser connection ID

Set public DID
Use DID above
Set endorser conn ID

Make a schema
POST /schemas
(write txn?)
9rhTeEygeLmXnvuJAv3kvp:2:lucas_person:1.0

Make a cred def
POST /credential-definitions

OOb connection
{
  "accept": [
    "didcomm/aip1",
    "didcomm/aip2;env=rfc19"
  ],
  "alias": "BC Wallet",
  "goal": "",
  "goal_code": "",
  "handshake_protocols": [
    "https://didcomm.org/didexchange/1.0",
    "https://didcomm.org/connections/1.0"
  ],
  "my_label": "Invitation to BC Wallet",
  "protocol_version": "1.1",
  "use_public_did": false
}

send offer
{
  "auto_issue": true,
  "auto_remove": false,
  "connection_id": "9216fa53-451b-49ee-bffa-b2e04d10cd98",
  "credential_preview": {
    "@type": "issue-credential/2.0/credential-preview",
    "attributes": [
      { "name": "last", "value": "L" },
      { "name": "first", "value": "O" }
    ]
  },
  "filter": {
    "indy": { "cred_def_id": "BtL9Krb7uuCo8CVoJKMQcB:3:CL:2676976:lp_norev" }
  },
  "trace": false
}