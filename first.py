from flask import Flask, request, jsonify
import logging
import pymysql

# Initialize the Flask application
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

inprogress_order = {}
# Function to create a MySQL connection
def create_db_connection():
    try:
        cnx = pymysql.connect(
            host="localhost",
            user="root",
            password="root",
            database="athletix_hub"
        )
        print("Connected to the database successfully.")
        return cnx
    except pymysql.Error as err:
        logging.error(f"Error connecting to MySQL: {err}")
        return None



@app.route("/", methods=['POST'])
def main():
    data = request.get_json()
    if not data:
        return jsonify({"fulfillmentText": "Invalid JSON data received."})

    # Extracting intent and parameters
    intent = data['queryResult']['intent']['displayName']
    parameters = data['queryResult']['parameters']
    session_path = data.get('session', '')
    session_id = session_path.split('/')[-1] if session_path else None

    # print(intent,' ',session_id,' ansh')
    if intent == 'track order: Context-Ongoing Tracking':
        return track_order(parameters)
    elif intent == 'add order: Context-Ongoing Order':
        return add_order(parameters,session_id)
    elif intent == 'Order Complete:Context-Ongoing Order':
        return complete_order(parameters,session_id)
    elif intent == 'Remove Order: Context-Ongoing Order':
        return remove_order(parameters, session_id)
    # Default response for unmatched intents
    return jsonify({"fulfillmentText": "Sorry, I couldn't understand your request."})

def remove_order(parameters, session_id):
    if session_id not in inprogress_order:
        fulfillment_text = f"I'm having a trouble finding your order. Sorry! Can you place a new order please?"

    food_items = parameters["supplements_name"]
    current_order = inprogress_order[session_id]

    removed_items = []
    no_such_items = []

    for item in food_items:
        if item not in current_order:
            no_such_items.append(item)
        else:
            removed_items.append(item)
            del current_order[item]
    if len(removed_items) > 0:
        fulfillment_text = f'Removed {",".join(removed_items)} from your order!'

    if len(no_such_items) > 0:
        fulfillment_text = f' Your current order does not have {",".join(no_such_items)}'

    if len(current_order.keys()) == 0:
        fulfillment_text += " Your order is empty!"
    else:
        order_str = get_str_from_supplement_dic(current_order)
        fulfillment_text += f" Here is what is left in your order: {order_str}"

    return jsonify({"fulfillmentText": fulfillment_text})
def complete_order(parameters,session_id):
    if session_id not in inprogress_order:
        fulfillment_text = f"I'm Having a trouble to find your order. Sorry! Can You Please your order again??"
    else:
        order = inprogress_order[session_id]
        print('order',order)
        order_id = save_to_db(order)
        print('order_id',order_id)
        if order_id == -1:
            fulfillment_text = "Sorry, I couldn't process your order due to a backend error. " \
                               "Please place a new order again"
        else:
            order_total = get_total_order_price(order_id)
            print('Total',order_total)
            fulfillment_text = f"Awesome. We have placed your order. " \
                               f"Here is your order id # {order_id}. " \
                               f"Your order total is {order_total} which you can pay at the time of delivery!"
        del inprogress_order[session_id]
    return jsonify({"fulfillmentText": fulfillment_text})

def add_order(parameters,session_id):
    try:
        supplement_number = (parameters['number'])
        supplement_name = parameters['supplements_name']

        # print(supplement_name,' ',supplement_number)
        new_stack = dict(zip(supplement_name,supplement_number))


        if session_id in inprogress_order:
            current = inprogress_order[session_id]
            current.update(new_stack)
            inprogress_order[session_id] = current
        else:
            inprogress_order[session_id] = new_stack

        order_str = get_str_from_supplement_dic(inprogress_order[session_id])
        print('inprogress_order[session_id]',inprogress_order[session_id])
        fulfillment_text = f"So Far you have {order_str}.Do you need Anything else??"

        return jsonify({"fulfillmentText": fulfillment_text})

    except Exception as e:
        logging.error(f"Error in add_order: {e}")
        return jsonify({"fulfillmentText": "An error occurred while adding the order."})
def track_order(parameters):
    try:
        order_id = int(parameters['number'])
        order_status = get_order_status(order_id)
        if order_status:
            fulfillment_text = f"The order status for order id {order_id} is: {order_status}."
        else:
            fulfillment_text = f"No order found with order id {order_id}."


        return jsonify({"fulfillmentText": fulfillment_text})

    except Exception as e:
        logging.error(f"Error in track_order: {e}")
        return jsonify({"fulfillmentText": "An error occurred while tracking the order."})

def get_total_order_price(order_id):
    cnx = create_db_connection()
    cursor = cnx.cursor()

    # Executing the SQL query to get the total order price
    query = f"SELECT get_total_order_price({order_id})"
    cursor.execute(query)

    # Fetching the result
    result = cursor.fetchone()[0]

    # Closing the cursor
    cursor.close()

    return result
def get_order_status(order_id):
    cnx = create_db_connection()
    if not cnx:
        return None

    try:
        cursor = cnx.cursor()
        # query = "SELECT status FROM order WHERE order_id = %s"
        query = f"SELECT status FROM `ansh_orders` WHERE order_id = {order_id}"
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()

        return result[0] if result else None
    except pymysql.Error as err:
        logging.error(f"MySQL error: {err}")
        return None
    finally:
        cnx.close()



def insert_order_item(item,quantity,order_id):
    try:
        cnx = create_db_connection()
        cursor = cnx.cursor()

        # Calling the stored procedure
        cursor.callproc('insert_order_item', (item, quantity, order_id))
        # Committing the changes
        cnx.commit()
        # Closing the cursor
        cursor.close()
        print("Order item inserted successfully!")
        return 1

    except pymysql.Error as err:
        print(f"Error inserting order item: {err}")
        # Rollback changes if necessary
        cnx.rollback()
        return -1

    except Exception as e:
        print(f"An error occurred: {e}")
        # Rollback changes if necessary
        cnx.rollback()
        return -1

# Function to get the next available order_id
def get_next_order_id():
    cnx = create_db_connection()
    cursor = cnx.cursor()

    # Executing the SQL query to get the next available order_id
    query = "SELECT MAX(order_id) FROM ansh_order_tracking"
    cursor.execute(query)

    # Fetching the result
    result = cursor.fetchone()[0]

    # Closing the cursor
    cursor.close()

    # Returning the next available order_id
    if result is None:
        return 1
    else:
        return result + 1
def save_to_db(order):

    next_order_id = get_next_order_id()
    print('next_order_id',next_order_id)

    # Insert individual items along with quantity in orders table
    for supplement_item, quantity in order.items():
        rcode = insert_order_item(
            supplement_item,
            quantity,
            next_order_id
        )
        if rcode == -1:
            return -1

    # Now insert order tracking status
    insert_order_tracking(next_order_id, "in progress")

    return next_order_id
# Function to insert a record into the order_tracking table
def insert_order_tracking(order_id, status):
    cnx = create_db_connection()
    cursor = cnx.cursor()

    # Inserting the record into the order_tracking table
    insert_query = f"INSERT INTO ansh_orders (order_id, status) VALUES ({order_id}, '{status}')"
    cursor.execute(insert_query)

    # Committing the changes
    cnx.commit()

    # Closing the cursor
    cursor.close()

def get_str_from_supplement_dic(supplement):
    result = ", ".join([f"{int(value)} {key}" for key, value in supplement.items()])
    return result


if __name__ == '__main__':
    app.run(debug=True, port=5000)
