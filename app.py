from flask import Flask, request, jsonify
import logging
import dbhelper

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

@app.route("/", methods=["POST"])
def handle_request():
    payload = request.json
    logging.info(f"Payload: {payload}")

    # Extract the intent name from the payload
    intent = payload.get('queryResult', {}).get('intent', {}).get('displayName', None)
    logging.info(f"Extracted Intent Name: {intent}")

    parameters = payload.get('queryResult', {}).get('parameters', {})
    output_contexts = payload.get('queryResult', {}).get('outputContexts', [])

    # Example check for specific intent name
    if intent == "track order: Context-Ongoing Tracking":
        return track_order(parameters)

    # Return a default response if no matching intent is found
    return jsonify({"fulfillmentText": "Sorry, I couldn't understand your request."})

def track_order(parameters):
    order_id = int(parameters['order_id'])
    order_status = dbhelper.get_order_status(order_id)
    if order_status:
        fulfillment_text = f"The order status for order id: {order_id} is: {order_status}"
    else:
        fulfillment_text = f"No order found with order id: {order_id}"

    return jsonify({"fulfillmentText": fulfillment_text})

if __name__ == "__main__":
    app.run(port=5000)
