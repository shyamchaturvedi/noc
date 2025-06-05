from flask import Flask, request, render_template_string, jsonify, send_file, session
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
import re
import pandas as pd
import io
from dotenv import load_dotenv
from io import BytesIO
import base64
import subprocess

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up file handler for logging
if not os.path.exists('logs'):
    os.makedirs('logs')
handler = RotatingFileHandler('logs/app.log', maxBytes=10000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))
logger.addHandler(handler)

# Create Flask app
app = Flask(__name__)

# Security configurations
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'your-secret-key-here'),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
    UPDATE_PASSWORD=os.getenv('UPDATE_PASSWORD', 'NOCTEAM@132')  # Password for update authorization
)

class DataError(Exception):
    """Custom exception for data loading errors"""
    pass

def load_data(file_path):
    """Load and validate data from the specified Excel file."""
    data = []
    invalid_rows = []
    try:
        if not os.path.exists(file_path):
            raise DataError(f"Data file not found: {file_path}")
        logger.info(f"Attempting to load Excel file: {file_path}")
        # Read Excel file
        df = pd.read_excel(file_path)
        logger.info(f"Excel file loaded. Found {len(df)} rows and columns: {list(df.columns)}")
        # Map column names (handle different possible column names)
        column_mapping = {
            'associate_name': ['ASSOCIATE NAME', 'associate_name', 'Associate Name', 'Name', 'NAME'],
            'associate_id': ['ASSOCIATE ID', 'associate_id', 'Associate ID', 'ID', 'id'],
            'receiver_name': ["RECEIVER'S NAME", 'receiver_name', 'Receiver Name', 'RECEIVER NAME', 'Receiver', 'RECEIVER'],
            'form_status': ['FORM STATUS', 'form_status', 'Form Status', 'Status', 'STATUS'],
            'line_no': ['LINE NO.', 'line_no', 'Line No', 'LINE NO', 'Line', 'LINE'],
            'set_no': ['SET-NO.OF FORM', 'set_no', 'Set No', 'SET NO', 'Set', 'SET']
        }
        # Find matching columns
        found_columns = {}
        for required_col, possible_names in column_mapping.items():
            found = False
            for possible_name in possible_names:
                if possible_name in df.columns:
                    found_columns[required_col] = possible_name
                    found = True
                    logger.info(f"Found column '{possible_name}' for '{required_col}'")
                    break
            if not found:
                raise DataError(f"Could not find column for '{required_col}'. Available columns: {list(df.columns)}")
        # Rename columns to standard names
        df = df.rename(columns={found_columns[k]: k for k in found_columns})
        logger.info(f"Renamed columns to: {list(df.columns)}")
        # Clean and validate data
        df = df.fillna("")  # Replace NaN with empty string
        # Convert all columns to string and strip whitespace
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            logger.info(f"Column '{col}' sample values: {df[col].head(3).tolist()}")
        # Process each row
        for index, row in df.iterrows():
            try:
                # Validate SET-NO.OF FORM format (should be SNF/number)
                if not str(row['set_no']).upper().startswith('SNF/'):
                    invalid_rows.append((index + 2, f"Invalid SET-NO format: {row['set_no']}"))
                    continue
                record = {
                    "associate_name": row['associate_name'],
                    "associate_id": row['associate_id'],
                    "receiver_name": row['receiver_name'],
                    "form_status": row['form_status'],
                    "line_no": row['line_no'],
                    "set_no": row['set_no']
                }
                data.append(record)
            except Exception as e:
                logger.error(f"Error processing row {index + 2}: {str(e)}")
                invalid_rows.append((index + 2, str(e)))
                continue
        if invalid_rows:
            logger.warning("Sample of invalid rows (up to 5):")
            for row_num, error in invalid_rows[:5]:
                logger.warning(f"Row {row_num}: {error}")
        logger.info(f"Successfully loaded {len(data)} records from Excel")
        if len(data) > 0:
            logger.info(f"Sample record: {data[0]}")
        return data
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        raise DataError(f"Failed to load data: {str(e)}")

# Load data once when app starts
try:
    data = load_data('data.xlsx')
except DataError as e:
    logger.error(f"Critical error loading data: {str(e)}")
    data = []

# Modern HTML template with improved UI
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Professional Records Search</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>
        :root {
            --primary-color: #2563eb;
            --primary-hover: #1d4ed8;
            --success-color: #059669;
            --success-hover: #047857;
            --error-color: #dc2626;
            --text-primary: #1f2937;
            --text-secondary: #4b5563;
            --bg-light: #f3f4f6;
            --bg-white: #ffffff;
            --border-color: #e5e7eb;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            line-height: 1.5;
            color: var(--text-primary);
            background-color: var(--bg-light);
            min-height: 100vh;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        .header {
            background-color: var(--bg-white);
            padding: 1.5rem 2rem;
            border-radius: 0.5rem;
            box-shadow: var(--shadow-md);
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h2 {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--primary-color);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .button-group {
            display: flex;
            gap: 1rem;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border-radius: 0.375rem;
            font-weight: 500;
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            border: none;
        }

        .btn-primary {
            background-color: var(--primary-color);
            color: white;
        }

        .btn-primary:hover {
            background-color: var(--primary-hover);
        }

        .btn-success {
            background-color: var(--success-color);
            color: white;
        }

        .btn-success:hover {
            background-color: var(--success-hover);
        }

        .btn-outline {
            background-color: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
        }

        .btn-outline:hover {
            background-color: var(--bg-light);
        }

        .search-container {
            background-color: var(--bg-white);
            padding: 2rem;
            border-radius: 0.5rem;
            box-shadow: var(--shadow-md);
            margin-bottom: 2rem;
        }

        .error-message {
            background-color: #fee2e2;
            color: var(--error-color);
            padding: 1rem;
            border-radius: 0.375rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
        }

        .search-form {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .search-input-group {
            flex: 1;
            min-width: 300px;
            display: flex;
            gap: 1rem;
        }

        .search-type-select {
            padding: 0.75rem;
            border: 1px solid var(--border-color);
            border-radius: 0.375rem;
            background-color: var(--bg-white);
            color: var(--text-primary);
            font-size: 0.875rem;
            min-width: 180px;
        }

        .search-input-wrapper {
            flex: 1;
            position: relative;
        }

        .search-input-wrapper i {
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
        }

        .search-input-wrapper input {
            width: 100%;
            padding: 0.75rem 1rem 0.75rem 2.5rem;
            border: 1px solid var(--border-color);
            border-radius: 0.375rem;
            font-size: 0.875rem;
            transition: border-color 0.2s;
        }

        .search-input-wrapper input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        .results-header {
            background-color: var(--bg-white);
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            box-shadow: var(--shadow-sm);
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .results-count {
            font-weight: 500;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .table-container {
            background-color: var(--bg-white);
            border-radius: 0.5rem;
            box-shadow: var(--shadow-md);
            overflow: hidden;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            background-color: var(--bg-light);
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 0.875rem;
            border-bottom: 1px solid var(--border-color);
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.875rem;
        }

        tr:last-child td {
            border-bottom: none;
        }

        .highlight-row {
            background-color: var(--bg-light);
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .status-completed {
            background-color: #dcfce7;
            color: var(--success-color);
        }

        .status-pending {
            background-color: #fef3c7;
            color: #d97706;
        }

        .status-rejected {
            background-color: #fee2e2;
            color: var(--error-color);
        }

        .location-info {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .location-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            background-color: var(--bg-light);
            color: var(--text-secondary);
        }

        .no-results {
            text-align: center;
            padding: 3rem;
            color: var(--text-secondary);
        }

        .no-results i {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: var(--text-secondary);
        }

        @media print {
            @page {
                size: A4 portrait;
                margin: 0.5cm;
            }

            body {
                background-color: white;
                width: 100%;
                margin: 0;
                padding: 0;
                font-size: 8pt;
            }

            .container {
                padding: 0;
                width: 100%;
                max-width: none;
            }

            .header, .results-header {
                display: none !important;
            }

            .search-container, .action-buttons {
                display: none !important;
            }

            .table-container {
                box-shadow: none;
                margin: 0;
                padding: 0;
                width: 100%;
                page-break-inside: avoid;
            }

            table {
                border-collapse: collapse;
                width: 100%;
                table-layout: fixed;
                font-size: 8pt;
                line-height: 1.2;
            }

            /* Optimize column widths for A4 */
            th:nth-child(1), td:nth-child(1) { width: 22%; } /* Associate Name */
            th:nth-child(2), td:nth-child(2) { width: 12%; } /* Associate ID */
            th:nth-child(3), td:nth-child(3) { width: 22%; } /* Receiver's Name */
            th:nth-child(4), td:nth-child(4) { width: 12%; } /* Form Status */
            th:nth-child(5), td:nth-child(5) { width: 32%; } /* Location */

            th {
                background-color: white !important;
                color: black !important;
                border-bottom: 1px solid #000 !important;
                padding: 4px 2px;
                font-weight: 600;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                font-size: 8pt;
            }

            td {
                border-bottom: 1px solid #ccc !important;
                padding: 3px 2px;
                vertical-align: top;
                word-wrap: break-word;
                font-size: 8pt;
            }

            .highlight-row {
                background-color: white !important;
            }

            .status-badge {
                padding: 1px 4px;
                font-size: 7pt;
                white-space: nowrap;
                border: 0.5px solid #ccc;
                display: inline-block;
                min-width: 60px;
                text-align: center;
            }

            .location-info {
                display: flex;
                flex-direction: row;
                gap: 4px;
                flex-wrap: wrap;
            }

            .location-badge {
                padding: 1px 3px;
                font-size: 7pt;
                white-space: nowrap;
                border: 0.5px solid #ccc;
                display: inline-block;
            }

            /* Compact title for print */
            .table-container::before {
                content: "Search Results";
                display: block;
                font-size: 10pt;
                font-weight: 600;
                margin-bottom: 4px;
                color: black;
            }

            /* Ensure table headers repeat on each page */
            thead {
                display: table-header-group;
            }

            /* Remove icons in print */
            .location-badge i,
            .status-badge i {
                display: none;
            }

            /* Compact the location badges */
            .location-badge {
                margin: 0;
                padding: 1px 3px;
            }

            .line-no-badge::before {
                content: "L: ";
            }

            .set-no-badge::before {
                content: "S: ";
            }

            /* Add notice section after table */
            .table-container::after {
                content: "⚠️ Agar koi form nikalta hai aur galat number par wapas rakhta hai to uski zimmedari us vyakti ki hogi.\A\A 🛑 Unauthorized access ya mixing strictly prohibited.\A\A 📌 By Order: SHREYA GROUP | NOC Management Team";
                display: block;
                margin-top: 1cm;
                padding: 0.5cm;
                border: 1px solid #000;
                font-size: 9pt;
                line-height: 1.4;
                white-space: pre-line;
                text-align: center;
                page-break-inside: avoid;
            }

            /* Ensure notice stays with table */
            .table-container {
                page-break-after: avoid;
            }

            /* Add page number */
            @page {
                @bottom-center {
                    content: counter(page);
                    font-size: 8pt;
                }
            }
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .header {
                flex-direction: column;
                gap: 1rem;
                text-align: center;
            }

            .button-group {
                width: 100%;
                justify-content: center;
            }

            .search-input-group {
                flex-direction: column;
            }

            .search-type-select {
                width: 100%;
            }

            .results-header {
                flex-direction: column;
                gap: 1rem;
                text-align: center;
            }

            .action-buttons {
                width: 100%;
                display: flex;
                justify-content: center;
                gap: 1rem;
            }

            .table-container {
                overflow-x: auto;
            }

            table {
                min-width: 800px;
            }
        }

        /* Add sorting styles */
        th {
            position: relative;
            cursor: pointer;
            user-select: none;
        }

        th:hover {
            background-color: #e5e7eb;
        }

        th.sort-asc::after {
            content: ' ▲';
            font-size: 0.8em;
            color: #2563eb;
        }

        th.sort-desc::after {
            content: ' ▼';
            font-size: 0.8em;
            color: #2563eb;
        }

        /* Add tooltip to show sort direction */
        th[title] {
            position: relative;
        }

        th[title]:hover::before {
            content: attr(title);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            padding: 4px 8px;
            background-color: #1f2937;
            color: white;
            font-size: 12px;
            border-radius: 4px;
            white-space: nowrap;
            z-index: 1000;
        }
</style>
    <script>
    // Function to check update authorization
    function checkUpdateAuth() {
        var password = prompt("Please enter the update password:");
        if (!password) return false;
        
        return fetch('/check_update_auth', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ password: password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                return true;
            } else {
                alert(data.message || "Authentication failed");
                return false;
            }
        })
        .catch(error => {
            alert("Error during authentication");
            return false;
        });
    }

    // Function to update data from Excel
    async function updateDataFromExcel() {
        // First check authorization
        const isAuthorized = await checkUpdateAuth();
        if (!isAuthorized) return;
        
        var input = document.createElement('input');
        input.type = 'file';
        input.accept = '.xlsx,.xls';
        input.style.display = 'none';
        
        input.onchange = function(e) {
            var file = e.target.files[0];
            if (!file) { return; }
            
            // Show loading state
            var btn = document.getElementById('updateDataBtn');
            var originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
            btn.disabled = true;
            
            var reader = new FileReader();
            reader.onload = function(event) {
                var buffer = event.target.result;
                fetch('/update_data', {
                    method: 'POST',
                    body: buffer
                })
                .then(function(response) { return response.json(); })
                .then(function(result) {
                    if (result.success) {
                        alert('Data updated successfully!');
                        location.reload();
                    } else {
                        alert('Error: ' + result.message);
                        // Reset button state
                        btn.innerHTML = originalText;
                        btn.disabled = false;
                    }
                })
                .catch(function(error) {
                    alert('Error updating data: ' + error);
                    // Reset button state
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                });
            };
            reader.readAsArrayBuffer(file);
            document.body.removeChild(input);
        };
        
        document.body.appendChild(input);
        input.click();
    }
    
    // Show update button when Alt+U is pressed
    document.addEventListener('keydown', async function(e) {
        if (e.altKey && e.key.toLowerCase() === 'u') {
            e.preventDefault(); // Prevent default browser behavior
            var btn = document.getElementById('updateDataBtn');
            if (btn) {
                // First check authorization
                const isAuthorized = await checkUpdateAuth();
                if (isAuthorized) {
                    btn.click(); // Trigger the update function
                }
            }
        }
    });

    // Add sorting functionality
    let currentSort = {
        column: null,
        direction: 'asc'
    };

    function sortTable(column) {
        const table = document.querySelector('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Update sort direction
        if (currentSort.column === column) {
            currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort.column = column;
            currentSort.direction = 'asc';
        }

        // Sort the rows
        rows.sort((a, b) => {
            let aValue = a.querySelector(`td:nth-child(${column + 1})`).textContent.trim();
            let bValue = b.querySelector(`td:nth-child(${column + 1})`).textContent.trim();

            // Special handling for Location column (column 5)
            if (column === 4) {
                // Extract line number for sorting
                aValue = aValue.match(/Line: (\d+)/)?.[1] || '';
                bValue = bValue.match(/Line: (\d+)/)?.[1] || '';
            }

            // Handle numeric values
            if (!isNaN(aValue) && !isNaN(bValue)) {
                aValue = parseFloat(aValue);
                bValue = parseFloat(bValue);
            }

            // Compare values
            if (aValue < bValue) return currentSort.direction === 'asc' ? -1 : 1;
            if (aValue > bValue) return currentSort.direction === 'asc' ? 1 : -1;
            return 0;
        });

        // Update sort indicators
        const headers = table.querySelectorAll('th');
        headers.forEach((header, index) => {
            header.classList.remove('sort-asc', 'sort-desc');
            if (index === column) {
                header.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        });

        // Reorder rows in the table
        rows.forEach(row => tbody.appendChild(row));
    }

    // Add click handlers to table headers
    document.addEventListener('DOMContentLoaded', function() {
        const headers = document.querySelectorAll('th');
        headers.forEach((header, index) => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => sortTable(index));
        });
    });
    </script>
</head>
<body>
    <div class="container">
        <div class="header" data-print-date="{{ print_date }}">
            <h2><i class="fas fa-search"></i> Professional Records Search</h2>
            <div class="button-group">
                <button onclick="window.print()" class="btn btn-outline">
                    <i class="fas fa-print"></i> Print
                </button>
                <a href="/export" class="btn btn-success">
                    <i class="fas fa-file-excel"></i> Export to Excel
                </a>
                <button onclick="updateDataFromExcel()" class="btn btn-primary" id="updateDataBtn" title="Press Alt+U to update data">
                    <i class="fas fa-sync"></i> Update Data
                </button>
            </div>
        </div>
        
        <div class="search-container">
            {% if error %}
            <div class="error-message">
                <i class="fas fa-exclamation-circle"></i>
                {{ error }}
            </div>
            {% endif %}
            
            <form method="get" action="/" class="search-form">
                <div class="search-input-group">
                    <select name="search_type" class="search-type-select" title="Select search type">
                        <option value="all" {% if search_type == 'all' %}selected{% endif %}>Search All Fields</option>
                        <option value="associate_name" {% if search_type == 'associate_name' %}selected{% endif %}>Search by Associate Name</option>
                        <option value="associate_id" {% if search_type == 'associate_id' %}selected{% endif %}>Search by Associate ID</option>
                        <option value="receiver_name" {% if search_type == 'receiver_name' %}selected{% endif %}>Search by Receiver's Name</option>
                        <option value="set_no" {% if search_type == 'set_no' %}selected{% endif %}>Search by Set No</option>
                        <option value="line_no" {% if search_type == 'line_no' %}selected{% endif %}>Search by Line No</option>
                    </select>
                    <div class="search-input-wrapper">
                        <i class="fas fa-search"></i>
                        <input type="text" 
                               name="search" 
                               placeholder="Search by name, ID, or Set No..." 
                               value="{{ search_term }}"
                               required />
                    </div>
                </div>
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-search"></i> Search
                </button>
            </form>
        </div>

{% if results is not none %}
            <div class="results-header">
                <div class="results-count">
                    <i class="fas fa-list"></i>
                    Found {{ results|length }} result(s)
                </div>
                <div class="action-buttons">
                    <button onclick="window.print()" class="btn btn-outline">
                        <i class="fas fa-print"></i> Print Results
                    </button>
                    <a href="/export" class="btn btn-success">
                        <i class="fas fa-file-excel"></i> Export to Excel
                    </a>
                </div>
            </div>
            
  {% if results %}
                <div class="table-container">
    <table>
                        <thead>
      <tr>
        <th title="Click to sort by Associate Name">Associate Name</th>
        <th title="Click to sort by Associate ID">Associate ID</th>
        <th title="Click to sort by Receiver's Name">Receiver's Name</th>
        <th title="Click to sort by Form Status">Form Status</th>
        <th title="Click to sort by Location (Line Number)">Location</th>
      </tr>
                        </thead>
                        <tbody>
      {% for rec in results %}
                                <tr class="{% if loop.index is divisibleby 2 %}highlight-row{% endif %}">
        <td>{{ rec.associate_name }}</td>
        <td>{{ rec.associate_id }}</td>
        <td>{{ rec.receiver_name }}</td>
                                    <td>
                                        <span class="status-badge status-{{ rec.form_status.lower() }}">
                                            {{ rec.form_status }}
                                        </span>
                                    </td>
                                    <td>
                                        <div class="location-info">
                                            <span class="location-badge line-no-badge" title="Bundle/Form Number">
                                                <i class="fas fa-hashtag"></i> Line: {{ rec.line_no }}
                                            </span>
                                            <span class="location-badge set-no-badge" title="Location Identifier">
                                                <i class="fas fa-map-marker-alt"></i> Set: {{ rec.set_no }}
                                            </span>
                                        </div>
                                    </td>
      </tr>
      {% endfor %}
                        </tbody>
    </table>
                </div>
  {% else %}
                <div class="no-results">
                    <i class="fas fa-search"></i>
    <p>No matching records found.</p>
                </div>
  {% endif %}
{% endif %}
    </div>
</body>
</html>
'''

def validate_search_term(search_term):
    """Validate the search term."""
    if not search_term:
        return True, None
    
    # Only validate SNF/ format searches
    if search_term.upper().startswith('SNF/'):
        try:
            # Split by '/' and check both parts
            parts = search_term.split('/')
            if len(parts) != 2:
                return False, "Invalid SNF format. Please use format: SNF/number (e.g., SNF/251)"
            
            # First part must be exactly "SNF" (case insensitive)
            if parts[0].upper() != 'SNF':
                return False, "Invalid SNF format. Please use format: SNF/number (e.g., SNF/251)"
            
            # Second part must be a number and not empty
            number_part = parts[1].strip()
            if not number_part or not number_part.isdigit():
                return False, "Invalid SNF format. Only numbers are allowed after SNF/ (e.g., SNF/251)"
            
            return True, None
        except Exception as e:
            logger.error(f"Error validating SNF format: {str(e)}")
            return False, "Invalid SNF format. Please use format: SNF/number (e.g., SNF/251)"
    
    # For all other searches, allow any characters
    return True, None

@app.route('/', methods=['GET'])
def search():
    """Handle search requests."""
    try:
        search_term = request.args.get('search', '').strip()
        search_type = request.args.get('search_type', 'all')  # Default to 'all'
        error = None
        # Log the search attempt and current data state
        logger.info(f"Search attempt - Term: '{search_term}', Type: {search_type}")
        logger.info(f"Total records in memory: {len(data)}")
        if len(data) > 0:
            logger.info(f"Sample record for search: {data[0]}")
        # If search term starts with SNF/, force search_type to 'set_no'
        if search_term.upper().startswith('SNF/'):
            search_type = 'set_no'
            # Validate SNF format first
            is_valid, validation_error = validate_search_term(search_term)
            if not is_valid:
                return render_template_string(HTML_TEMPLATE, 
                                            results=None, 
                                            search_term='',
                                            search_type=search_type,
                                            error=validation_error)
        results = None
        if search_term:
            search_lower = search_term.lower()
            results = []
            # Log total records being searched
            logger.info(f"Searching through {len(data)} records")
            for rec in data:
                match = False
                try:
                    # Normalize record values and log for debugging
                    associate_name = str(rec['associate_name']).lower().strip()
                    associate_id = str(rec['associate_id']).lower().strip()
                    receiver_name = str(rec['receiver_name']).lower().strip()
                    set_no = str(rec['set_no']).upper().strip()
                    line_no = str(rec['line_no']).strip()
                    # Log first few records being searched
                    if len(results) < 3:
                        logger.info(f"Searching record - Name: {associate_name}, ID: {associate_id}, Set: {set_no}")
                    if search_type == 'all':
                        # Special handling for SNF/ format
                        if search_term.upper().startswith('SNF/'):
                            match = search_term.upper() == set_no
                        else:
                            # Regular search in all fields with better partial matching
                            search_parts = search_lower.split()
                            if len(search_parts) > 1:
                                # For multi-word searches, check if all words are present
                                match = all(part in associate_name or 
                                          part in associate_id or 
                                          part in receiver_name or 
                                          part in set_no.lower() or 
                                          part == line_no.lower() 
                                          for part in search_parts)
                            else:
                                # Single word search
                                match = (search_lower in associate_name or
                                       search_lower in associate_id or
                                       search_lower in receiver_name or
                                       search_lower in set_no.lower() or
                                       search_term == line_no)
                    elif search_type == 'associate_name':
                        match = search_lower in associate_name
                    elif search_type == 'associate_id':
                        match = search_lower in associate_id
                    elif search_type == 'receiver_name':
                        match = search_lower in receiver_name
                    elif search_type == 'set_no':
                        match = search_term.upper() == set_no
                    elif search_type == 'line_no':
                        match = search_term == line_no
                    if match:
                        results.append(rec)
                        # Log successful match
                        logger.info(f"Match found - Name: {rec['associate_name']}, ID: {rec['associate_id']}, Line: {rec['line_no']}, Set: {rec['set_no']}")
                except Exception as e:
                    logger.error(f"Error processing record during search: {str(e)}")
                    continue
            # Sort results by line number in ascending order
            if results:
                # Log the line numbers before sorting
                logger.info("Line numbers before sorting: " + ", ".join(str(r['line_no']) for r in results))
                
                def get_line_number(record):
                    try:
                        # Remove any non-digit characters and convert to integer
                        line_no = ''.join(filter(str.isdigit, str(record['line_no'])))
                        return int(line_no) if line_no else float('inf')
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid line number format: {record['line_no']}")
                        return float('inf')
                
                # Sort using the new function
                results.sort(key=get_line_number)
                
                # Log the line numbers after sorting
                logger.info("Line numbers after sorting: " + ", ".join(str(r['line_no']) for r in results))
                
            # If no results found, log potential matches for debugging
            if not results and search_type == 'all':
                potential_matches = []
                for rec in data:
                    if any(search_lower in str(v).lower() for v in rec.values()):
                        potential_matches.append(f"{rec['associate_name']} ({rec['set_no']})")
                if potential_matches:
                    logger.info(f"Potential matches found but not included: {', '.join(potential_matches[:5])}")
        # Add current date and time for print header
        print_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return render_template_string(HTML_TEMPLATE, 
                                    results=results, 
                                    search_term=search_term,
                                    search_type=search_type,
                                    error=error,
                                    print_date=print_date)
    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}")
        return render_template_string(HTML_TEMPLATE,
                                    results=None,
                                    search_term='',
                                    search_type='all',
                                    error="An error occurred while processing your request. Please try again.")

@app.route('/export')
def export_excel():
    """Export search results to Excel."""
    try:
        search_term = request.args.get('search', '').strip()
        if not search_term:
            return "No search term provided", 400
            
        # Get the search results
        search_lower = search_term.lower()
        is_set_no_search = search_term.upper().startswith('SNF/')
        is_line_no_search = search_term.isdigit()
        
        results = []
        for rec in data:
            if is_set_no_search and search_term.upper() == rec['set_no'].upper():
                results.append(rec)
            elif is_line_no_search and search_term == rec['line_no']:
                results.append(rec)
            elif (not is_set_no_search and not is_line_no_search and
                  (search_lower in rec['associate_name'].lower() or
               search_lower in rec['associate_id'].lower() or
                   search_lower in rec['receiver_name'].lower() or
                   search_lower in rec['set_no'].lower())):
                results.append(rec)
        
        if not results:
            return "No results to export", 404
            
        # Create DataFrame
        df = pd.DataFrame(results)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Search Results', index=False)
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Search Results']
            
            # Add some formatting
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#2196F3',
                'font_color': 'white',
                'border': 1
            })
            
            # Write header with format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 15)  # Set column width
                
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'search_results_{timestamp}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        return "Error exporting results", 500

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template_string(HTML_TEMPLATE,
                                results=None,
                                search_term='',
                                search_type='all',
                                error="Page not found."), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(error)}")
    return render_template_string(HTML_TEMPLATE,
                                results=None,
                                search_term='',
                                search_type='all',
                                error="An internal server error occurred. Please try again later."), 500

@app.route('/check_update_auth', methods=['POST'])
def check_update_auth():
    """Check if the provided password is correct for updates"""
    try:
        password = request.json.get('password')
        if password == app.config['UPDATE_PASSWORD']:
            session['update_authorized'] = True
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Incorrect password"})
    except Exception as e:
        logger.error(f"Error in check_update_auth: {str(e)}")
        return jsonify({"success": False, "message": "Authentication failed"})

@app.route('/update_data', methods=['POST'])
def update_data():
    """Hidden route to update data from Excel and update GitHub"""
    try:
        # Check if user is authorized
        if not session.get('update_authorized'):
            return jsonify({"success": False, "message": "Unauthorized access"})
            
        # Get Excel data from request
        excel_data = request.get_data()
        if not excel_data:
            return jsonify({"success": False, "message": "No data received"})
        
        # Clear the authorization after use
        session.pop('update_authorized', None)
        
        # Save the uploaded Excel file
        with open('data.xlsx', 'wb') as f:
            f.write(excel_data)
        
        # Reload data in memory
        global data
        data = load_data('data.xlsx')
        logger.info(f"Data reloaded successfully. Total records: {len(data)}")
        
        # Update GitHub
        try:
            # Add the updated Excel file to git
            subprocess.run(['git', 'add', 'data.xlsx'], check=True)
            
            # Commit the changes
            commit_message = f"Update data.xlsx - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            # Push to GitHub
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            
            logger.info("Successfully updated data.xlsx in GitHub")
            return jsonify({
                "success": True, 
                "message": f"Data updated successfully. Processed {len(data)} records and updated GitHub."
            })
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {str(e)}")
            return jsonify({
                "success": True,
                "message": f"Data updated locally but GitHub update failed: {str(e)}"
            })
            
    except Exception as e:
        logger.error(f"Error in update_data: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Get host from environment variable or use default
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Get debug mode from environment variable
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Run the app
    app.run(
        host=host,
        port=port,
        debug=debug,
        ssl_context='adhoc' if os.environ.get('USE_SSL', 'False').lower() == 'true' else None
    ) 