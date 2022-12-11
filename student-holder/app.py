from flask import Flask, render_template, request, redirect, url_for
import requests
import json

base_url = 'http://localhost:8031/'


app = Flask(__name__)


@app.route("/")
def home():
    return render_template("home.html")


@app.route('/receive_invitation', methods=['POST'])
def receive_invitation():
    # Receive
    print(request.form['invitation_object'])
    resp = http_post_json("connections/receive-invitation", body=json.loads(request.form['invitation_object'])).json()

    connection_id = resp['connection_id']

    # Accept
    resp = http_post_json(resource=f"connections/{connection_id}/accept-invitation", body=None).json()

    return render_template("invitation_accepted.html", connection_id=connection_id, accept_invitation_result=format_json(resp))


@app.route('/verify_active_connection', methods=['POST'])
def verify_active_connection():
    conns = http_get("connections").json()['results']
    for conn in conns:
        if conn['state'] == 'active':
            print("active conn found")
            return render_template("active_connection_available.html", conn=format_json(conn))


@app.route('/wallet')
def wallet():
    conns = http_get("connections").json()['results']
    print(conns)
    records = http_get("issue-credential-2.0/records").json()['results']

    return render_template("wallet.html", conns=conns, records=records)


@app.route('/issued_credentials')
def issued_credentials():
    records = http_get("issue-credential-2.0/records").json()['results']

    return render_template("issued_credentials.html", records=records)


@app.route('/store_credentials_in_wallet', methods=['POST'])
def store_credentials_in_wallet():

    http_post_json(resource=f"issue-credential-2.0/records/{request.form['cred_ex_id']}/store", body={}).json()
    return redirect(url_for("issued_credentials"))


@app.route('/reset')
def reset():
    resp = http_get("connections").json()
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
