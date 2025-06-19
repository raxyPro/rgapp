// static/script.js

document.addEventListener('DOMContentLoaded', () => {
    // Get references to the table, save button, and message box elements
    const editableTable = document.getElementById('editableTable');
    const saveButton = document.getElementById('saveButton');
    const messageBox = document.getElementById('messageBox');

    // Function to display messages to the user
    // type can be 'success' or 'error'
    function showMessage(message, type) {
        messageBox.textContent = message; // Set the message text
        messageBox.className = `p-3 text-sm rounded-lg mb-6 w-full text-center ${type}`; // Apply classes for styling
        messageBox.classList.remove('hidden'); // Make the message box visible

        // Hide the message after 3 seconds
        setTimeout(() => {
            messageBox.classList.add('hidden'); // Add 'hidden' class to hide it
        }, 3000);
    }

    // Add click event listener to the Save Button
    saveButton.addEventListener('click', async () => {
        const tableData = []; // Array to store the table content
        const rows = editableTable.querySelectorAll('tbody tr'); // Get all rows in the table body

        // Iterate through each row
        rows.forEach(row => {
            const rowData = []; // Array to store cell data for the current row
            // Get all contenteditable cells within the current row
            const cells = row.querySelectorAll('td[contenteditable="true"]');
            
            // Iterate through each cell and push its text content to rowData
            cells.forEach(cell => {
                rowData.push(cell.textContent.trim()); // .trim() removes leading/trailing whitespace
            });
            tableData.push(rowData); // Add the rowData to the main tableData array
        });

        console.log("Table data to save:", tableData); // Log the data being sent

        try {
            // Send the table data to the Flask backend using the Fetch API
            const response = await fetch('/save_data', {
                method: 'POST', // Use POST method to send data
                headers: {
                    'Content-Type': 'application/json' // Specify that the body is JSON
                },
                body: JSON.stringify(tableData) // Convert the JavaScript array to a JSON string
            });

            // Check if the request was successful
            if (response.ok) {
                const result = await response.json(); // Parse the JSON response from the server
                showMessage(result.message, 'success'); // Show success message
            } else {
                const errorResult = await response.json(); // Parse error message if available
                showMessage(`Error: ${errorResult.message || 'Failed to save data.'}`, 'error'); // Show error message
                console.error('Failed to save data:', response.status, errorResult);
            }
        } catch (error) {
            // Catch any network or other unexpected errors
            showMessage(`Network error: ${error.message}`, 'error');
            console.error('Fetch error:', error);
        }
    });

    // Optional: Add a subtle effect when cells are focused
    editableTable.addEventListener('focusin', (event) => {
        if (event.target.tagName === 'TD' && event.target.contentEditable === 'true') {
            event.target.classList.add('focused-cell');
        }
    });

    editableTable.addEventListener('focusout', (event) => {
        if (event.target.tagName === 'TD' && event.target.contentEditable === 'true') {
            event.target.classList.remove('focused-cell');
        }
    });
});
