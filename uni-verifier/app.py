from flask import Flask, render_template
import requests
import json
import time
from pathlib import Path

app = Flask(__name__)

base_url = 'http://localhost:8021/'


@app.route("/")
def home():
    return render_template("home.html")


@app.route('/create_invitation', methods=['POST'])
def create_invitation():
    resp = http_post_json("connections/create-invitation?alias=Verifier", body={"my_label": "Verifier University"}).json()
    resp['invitation'] = format_json(resp['invitation'])
    return render_template("invitation_created.html", response=resp)


@app.route('/complete_connection_to_student', methods=['POST'])
def complete_connection_to_student():
    # Get connections
    conns = http_get("connections").json()['results']
    for conn in conns:
        # Find the one from alice with state "request"
        if conn['state'] == "request" and 'alice' in conn['their_label']:
            print("found")
            resp = http_post_json(resource=f"connections/{conn['connection_id']}/accept-request", body=None).json()
            print(resp)
            time.sleep(5)
            latest_conns = http_get("connections").json()['results']
            print(latest_conns)
            for c in latest_conns:
                if c['state'] == "active" and 'alice' in c['their_label']:
                    print("found accepted")
                    return render_template("connection_completed.html", conn=format_json(c))

    return render_template("connection_completed.html", conn=None)


@app.route('/active_connections')
def active_connections():
    conns = http_get("connections?alias=Verifier").json()['results']
    print(format_json(conns))
    return render_template("active_connections.html", conns=conns)


@app.route('/issue_credential_to_student')
def issue_credential_to_student():
    connections = http_get("connections").json()['results']
    if connections and len(connections) > 0:
        issuer_did = http_get("wallet/did/public").json()['result']['did']
        schema_id =  http_get("schemas/created").json()['schema_ids'][0]
        cred_def_id = http_get("credential-definitions/created").json()['credential_definition_ids'][0]

        schema_version = schema_id.split(':')[-1]
        schema_name = schema_id.split(':')[2]

        credential = None
        with open("data/issue_credential_template.json", "r") as f:
            credential = json.load(f)

        credential['connection_id'] = connections[0]['connection_id']

        credential['filter']['indy']['issuer_did'] = issuer_did
        credential['filter']['indy']['schema_id'] = schema_id
        credential['filter']['indy']['cred_def_id'] = cred_def_id
        credential['filter']['indy']['schema_version'] = schema_version
        credential['filter']['indy']['schema_name'] = schema_name
        credential['filter']['indy']['schema_issuer_did'] = issuer_did

        # Issue credential
        resp = http_post_json(resource="issue-credential-2.0/send", body=credential).json()

        return render_template("credential_issued.html", response=resp)
    else:
        return render_template("credential_issued.html", response=None)


@app.route('/issue_proof_request', methods=['POST'])
def issue_proof_request():

    connections = http_get("connections?alias=Verifier").json()['results']
    if connections and len(connections) > 0:
        proof_request = None
        with open("data/proof_request_template.json", "r") as f:
            proof_request = json.load(f)
        proof_request['connection_id'] = connections[0]['connection_id']
        cred_def_id = http_get("credential-definitions/created").json()['credential_definition_ids'][0]
        proof_request['presentation_request']['indy']['requested_attributes']['0_name_uuid']['restrictions'][0]['cred_def_id'] = cred_def_id
        proof_request['presentation_request']['indy']['requested_attributes']['0_date_uuid']['restrictions'][0][
            'cred_def_id'] = cred_def_id
        proof_request['presentation_request']['indy']['requested_attributes']['0_degree_uuid']['restrictions'][0][
            'cred_def_id'] = cred_def_id
        proof_request['presentation_request']['indy']['requested_attributes']['0_score_uuid']['restrictions'][0][
            'cred_def_id'] = cred_def_id
        proof_request['presentation_request']['indy']['requested_predicates']['0_age_GE_uuid']['restrictions'][0][
            'cred_def_id'] = cred_def_id

        resp = http_post_json(resource="present-proof-2.0/send-request", body=proof_request).json()
        # print(resp)

        time.sleep(5)

        resp = http_get(resource=f"present-proof-2.0/records/{resp['pres_ex_id']}").json()
        resp['by_format']['pres']['indy']['proof']['aggregated_proof']['c_list'] = None 
        # print(json.dumps(resp, indent=1))
        return render_template("proof_request_completed.html", resp=resp)


@app.route('/reset')
def reset():
    resp = http_get("connections?alias=Verifier").json()
    for conn in resp['results']:
        http_delete(f"connections/{conn['connection_id']}")
        print("Deleted connection: " + conn['connection_id'])

    cred_records = http_get("issue-credential-2.0/records").json()
    for record in cred_records['results']:
        http_delete(f"issue-credential-2.0/records/{record['cred_ex_record']['cred_ex_id']}")
        print("Deleted record: " + record['cred_ex_record']['cred_ex_id'])

    return render_template("home.html")


def http_post_json(resource, body):
    final_url = base_url + resource
    print(f"Posting to: {final_url}")
    return requests.post(final_url, json=body)


def http_get(resource):
    final_url = base_url + resource
    print(f"Get from: {final_url}")
    return requests.get(final_url)


def http_delete(resource):
    final_url = base_url + resource
    print(f"Deleting: {final_url}")
    requests.delete(final_url)


def format_json(json_obj):
    return json.dumps(json_obj, indent=4)


if __name__ == "__main__":
    app.run(debug=True, port=5001)

