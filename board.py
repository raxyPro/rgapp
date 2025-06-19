# app.py
import os
from flask import Flask, render_template, request, jsonify
import xml.etree.ElementTree as ET

# Initialize the Flask application
app = Flask(__name__)

# Define the path for the XML data file
# This file will store the table content on the server
DATA_FILE = 'data.xml'

# --- XML Data Handling Functions ---

def load_table_data():
    """
    Loads table data from the XML file.
    If the file doesn't exist, it returns a default empty table (5x5).
    """
    table_data = []
    # Check if the data file exists
    if os.path.exists(DATA_FILE):
        try:
            tree = ET.parse(DATA_FILE)
            root = tree.getroot()
            # Iterate through each 'row' element in the XML
            for row_elem in root.findall('row'):
                row = []
                # Iterate through each 'cell' element in the current 'row'
                for cell_elem in row_elem.findall('cell'):
                    # Append the text content of the cell, default to empty string if no text
                    row.append(cell_elem.text if cell_elem.text is not None else "")
                table_data.append(row)
            
            # Ensure a minimum size for consistency, useful if XML is malformed or too small
            if not table_data: # If table_data is empty after parsing
                 return [['' for _ in range(5)] for _ in range(5)] # Default 5x5 empty table
            
            # Pad rows to ensure consistent column count if some rows have fewer cells
            max_cols = max(len(row) for row in table_data)
            for i in range(len(table_data)):
                while len(table_data[i]) < max_cols:
                    table_data[i].append('')
            
            return table_data
        except ET.ParseError as e:
            # Log the error and return a default table if parsing fails
            print(f"Error parsing XML file: {e}. Returning default table.")
            return [['' for _ in range(5)] for _ in range(5)] # Default 5x5 empty table
    else:
        # If the file doesn't exist, create a default 5x5 empty table
        print(f"'{DATA_FILE}' not found. Creating a default empty table.")
        return [['' for _ in range(5)] for _ in range(5)]

def save_table_data(data):
    """
    Saves the provided table data (list of lists) to the XML file.
    """
    root = ET.Element('table_data') # Create the root element for the XML

    # Iterate through each row in the input data
    for row_list in data:
        row_elem = ET.SubElement(root, 'row') # Create a 'row' sub-element
        # Iterate through each cell value in the current row
        for cell_value in row_list:
            cell_elem = ET.SubElement(row_elem, 'cell') # Create a 'cell' sub-element
            cell_elem.text = str(cell_value) # Set the text content of the cell

    # Create an ElementTree object and write it to the file
    tree = ET.ElementTree(root)
    # Use pretty_print for better readability of the XML file
    ET.indent(tree, space="\t", level=0) 
    tree.write(DATA_FILE, encoding='utf-8', xml_declaration=True)
    print(f"Data successfully saved to '{DATA_FILE}'.")


# --- Flask Routes ---

@app.route('/')
def index():
    """
    Renders the main index page, loading existing table data.
    """
    table_data = load_table_data()
    # Pass the loaded table data and enumerate to the HTML template
    return render_template('board.html', table_data=table_data, enumerate=enumerate)

@app.route('/save_data', methods=['POST'])
def save_data():
    """
    Handles POST requests to save table data sent from the frontend.
    """
    try:
        # Get the JSON data sent from the client
        data = request.json
        if data is None:
            # If no JSON data is provided, return a bad request error
            return jsonify({"status": "error", "message": "No JSON data received"}), 400

        # Save the received data to the XML file
        save_table_data(data)
        # Return a success response
        return jsonify({"status": "success", "message": "Data saved successfully!"}), 200
    except Exception as e:
        # Catch any errors during the process and return an error response
        print(f"Server error during save_data: {e}")
        return jsonify({"status": "error", "message": f"Failed to save data: {e}"}), 500

# Entry point for running the Flask application
if __name__ == '__main__':
    # Run the app in debug mode. In a production environment, use a production-ready server.
    app.run(debug=True)
