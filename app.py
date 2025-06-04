from flask import Flask, request, render_template_string, jsonify, send_file
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
import re
import pandas as pd
import io
from dotenv import load_dotenv

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
    PERMANENT_SESSION_LIFETIME=1800  # 30 minutes
)

class DataError(Exception):
    """Custom exception for data loading errors"""
    pass

def load_data(file_path):
    """Load and validate data from the specified file."""
    try:
        if not os.path.exists(file_path):
            raise DataError(f"Data file not found: {file_path}")
        
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
            if len(lines) < 2:  # Need at least header + 1 data row
                raise DataError("Data file is empty or missing header")
            
            for line_num, line in enumerate(lines[1:], 2):  # skip header
                try:
            parts = line.strip().split('\t')
                    if len(parts) < 6:
                        logger.warning(f"Invalid data format at line {line_num}")
                        continue
                    
                record = {
                        "associate_name": parts[0].strip(),
                        "associate_id": parts[1].strip(),
                        "receiver_name": parts[2].strip(),
                        "form_status": parts[3].strip(),
                        "line_no": parts[4].strip(),
                        "set_no": parts[5].strip()
                }
                data.append(record)
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {str(e)}")
                    continue
        
        logger.info(f"Successfully loaded {len(data)} records")
    return data
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        raise DataError(f"Failed to load data: {str(e)}")

# Load data once when app starts
try:
data = load_data('data.txt')
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
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>
        :root {
            --primary-color: #2196F3;
            --secondary-color: #1976D2;
            --success-color: #4CAF50;
            --background-color: #f5f5f5;
            --text-color: #333;
            --border-color: #ddd;
            --header-bg: #fff;
            --card-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Roboto', sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background-color);
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: var(--card-shadow);
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .header h2 {
            color: var(--primary-color);
            margin: 0;
            font-weight: 500;
        }
        
        .search-container {
            background: var(--header-bg);
            padding: 20px;
            border-radius: 8px;
            box-shadow: var(--card-shadow);
            margin-bottom: 20px;
        }
        
        .search-form {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .search-input-group {
            flex: 1;
            min-width: 200px;
            position: relative;
            display: flex;
            gap: 10px;
        }
        
        .search-type-select {
            min-width: 150px;
            padding: 12px;
            border: 2px solid var(--border-color);
            border-radius: 4px;
            font-size: 16px;
            background-color: white;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .search-type-select:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
        }
        
        .search-input-wrapper {
            flex: 1;
            position: relative;
        }
        
        .search-input-group i {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: #666;
        }
        
        input[type=text] {
            width: 100%;
            padding: 12px 12px 12px 40px;
            border: 2px solid var(--border-color);
            border-radius: 4px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        input[type=text]:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
        }
        
        .button-group {
            display: flex;
            gap: 10px;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background-color: var(--primary-color);
            color: white;
        }
        
        .btn-primary:hover {
            background-color: var(--secondary-color);
        }
        
        .btn-success {
            background-color: var(--success-color);
            color: white;
        }
        
        .btn-success:hover {
            background-color: #388E3C;
        }
        
        .btn-outline {
            background-color: transparent;
            border: 2px solid var(--primary-color);
            color: var(--primary-color);
        }
        
        .btn-outline:hover {
            background-color: var(--primary-color);
            color: white;
        }
        
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 20px 0;
            padding: 10px;
            background: var(--header-bg);
            border-radius: 4px;
            box-shadow: var(--card-shadow);
        }
        
        .results-count {
            font-size: 16px;
            color: #666;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .action-buttons {
            display: flex;
            gap: 10px;
        }
        
        .table-container {
            overflow-x: auto;
            margin-top: 20px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: var(--card-shadow);
            background: white;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            position: sticky;
            top: 0;
            background-color: var(--header-bg);
            padding: 15px;
            text-align: left;
            font-weight: 500;
            color: var(--text-color);
            border-bottom: 2px solid var(--border-color);
            z-index: 1;
        }
        
        td {
            padding: 12px 15px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .highlight-row {
            background-color: #F8F9FA;
        }
        
        .highlight-row:hover {
            background-color: #F1F3F4;
        }
        
        .location-info {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .location-badge {
            display: inline-flex;
            align-items: center;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            white-space: nowrap;
        }
        
        .line-no-badge {
            background-color: #E3F2FD;
            color: #1976D2;
            border: 1px solid #BBDEFB;
        }
        
        .set-no-badge {
            background-color: #E8F5E9;
            color: #2E7D32;
            border: 1px solid #C8E6C9;
        }
        
        .status-badge {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .status-active {
            background-color: #E8F5E9;
            color: #2E7D32;
        }
        
        .status-pending {
            background-color: #FFF3E0;
            color: #E65100;
        }
        
        .no-results {
            text-align: center;
            padding: 40px 20px;
            background: white;
            border-radius: 8px;
            box-shadow: var(--card-shadow);
        }
        
        .no-results i {
            font-size: 48px;
            color: #BDBDBD;
            margin-bottom: 16px;
        }
        
        .error-message {
            background-color: #FFEBEE;
            color: #C62828;
            padding: 12px;
            border-radius: 4px;
            margin: 10px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        /* Print Styles */
        @media print {
            @page {
                size: A4 portrait;
                margin: 0.5cm;
            }
            
            html, body {
                width: 210mm;
                height: 297mm;
                margin: 0;
                padding: 0;
                background: white;
                font-size: 11pt;
                line-height: 1.2;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            
            .container {
                width: 100% !important;
                max-width: none !important;
                margin: 0 !important;
                padding: 0 !important;
                box-shadow: none !important;
                background: white !important;
            }
            
            .search-container,
            .action-buttons,
            .btn,
            .button-group,
            .no-results i,
            .location-header-icon,
            .tooltip-text {
                display: none !important;
            }
            
            .header {
                margin: 0 0 10px 0 !important;
                padding: 0 0 5px 0 !important;
                border-bottom: 1px solid #000 !important;
                page-break-after: avoid;
            }
            
            .header h2 {
                font-size: 14pt !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            
            .results-header {
                margin: 0 0 10px 0 !important;
                padding: 0 !important;
                box-shadow: none !important;
                border: none !important;
                display: block !important;
                page-break-after: avoid;
            }
            
            .results-count {
                font-size: 11pt !important;
                margin-bottom: 5px !important;
            }
            
            .table-container {
                box-shadow: none !important;
                border: none !important;
                margin: 0 !important;
                padding: 0 !important;
                width: 100% !important;
                page-break-inside: avoid;
            }
            
            table {
                width: 100% !important;
                border-collapse: collapse !important;
                margin: 0 !important;
                padding: 0 !important;
                font-size: 9pt !important;
                table-layout: fixed !important;
            }
            
            th {
                background-color: #f0f0f0 !important;
                color: #000 !important;
                border: 0.5px solid #000 !important;
                padding: 4px 6px !important;
                font-weight: bold !important;
                text-align: left !important;
                position: static !important;
                white-space: normal !important;
                word-wrap: break-word !important;
            }
            
            td {
                border: 0.5px solid #000 !important;
                padding: 3px 4px !important;
                vertical-align: top !important;
                white-space: normal !important;
                word-wrap: break-word !important;
            }
            
            /* Column widths for better fit */
            th:nth-child(1), td:nth-child(1) { width: 20% !important; } /* Associate Name */
            th:nth-child(2), td:nth-child(2) { width: 15% !important; } /* Associate ID */
            th:nth-child(3), td:nth-child(3) { width: 20% !important; } /* Receiver's Name */
            th:nth-child(4), td:nth-child(4) { width: 15% !important; } /* Form Status */
            th:nth-child(5), td:nth-child(5) { width: 30% !important; } /* Location */
            
            .location-info {
                display: block !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            
            .location-badge {
                display: inline-block !important;
                border: 0.5px solid #000 !important;
                padding: 1px 3px !important;
                margin: 1px 2px 1px 0 !important;
                font-size: 8pt !important;
                background: none !important;
                color: #000 !important;
                white-space: nowrap !important;
            }
            
            .status-badge {
                border: 0.5px solid #000 !important;
                padding: 1px 3px !important;
                background: none !important;
                color: #000 !important;
                font-size: 8pt !important;
            }
            
            /* Hide all icons and decorative elements */
            i, .fas, .fa, [class*="fa-"] {
                display: none !important;
            }
            
            /* Ensure proper page breaks */
            tr {
                page-break-inside: avoid !important;
            }
            
            thead {
                display: table-header-group !important;
            }
            
            tbody {
                display: table-row-group !important;
            }
            
            /* Page numbers */
            @page {
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 8pt;
                    font-family: Arial, sans-serif;
                }
            }
            
            /* Print header with date and time */
            .header::before {
                content: "Printed on: " attr(data-print-date);
                display: block !important;
                font-size: 8pt !important;
                color: #000 !important;
                margin-bottom: 5px !important;
                font-family: Arial, sans-serif !important;
            }
            
            /* Force background colors and images to print */
            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            
            /* Remove any shadows or effects */
            * {
                box-shadow: none !important;
                text-shadow: none !important;
            }
            
            /* Ensure proper scaling */
            @viewport {
                width: device-width;
                zoom: 1.0;
            }
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .header {
                flex-direction: column;
                gap: 15px;
                text-align: center;
            }
            
            .search-form {
                flex-direction: column;
            }
            
            .button-group {
                width: 100%;
            }
            
            .btn {
                width: 100%;
                justify-content: center;
            }
            
            .results-header {
                flex-direction: column;
                gap: 10px;
            }
            
            .action-buttons {
                width: 100%;
                justify-content: center;
            }
        }
</style>
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
                               pattern="[A-Za-z0-9\s\-]+"
                               title="Please enter only letters, numbers, spaces, and hyphens"
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
        <th>Associate Name</th>
        <th>Associate ID</th>
        <th>Receiver's Name</th>
        <th>Form Status</th>
                                <th class="location-column">
                                    <div class="location-header">
                                        <span>Location</span>
                                        <div class="location-tooltip">
                                            <span class="location-header-icon">ⓘ</span>
                                            <span class="tooltip-text">
                                                Line No: Bundle/Form Number<br>
                                                Set No: Location Identifier (e.g. SNF/25)
                                            </span>
                                        </div>
                                    </div>
                                </th>
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
    """Validate the search term.
    
    Args:
        search_term (str): The search term to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not search_term:
        return True
    
    # Special case for SNF/251 format
    if search_term.upper().startswith('SNF/'):
        try:
            # Check if the part after SNF/ is a valid number
            number_part = search_term[4:].strip()
            return number_part.isdigit()
        except:
            return False
    
    # Allow only letters, numbers, spaces, and hyphens for other searches
    return bool(re.match(r'^[A-Za-z0-9\s\-]+$', search_term))

@app.route('/', methods=['GET'])
def search():
    """Handle search requests."""
    try:
        search_term = request.args.get('search', '').strip()
        search_type = request.args.get('search_type', 'all')  # Default to 'all'
        error = None
        
        if search_term and not validate_search_term(search_term):
            if search_term.upper().startswith('SNF/'):
                error = "Invalid SNF format. Please use format: SNF/number (e.g., SNF/251)"
            else:
                error = "Invalid search term. Please use only letters, numbers, spaces, and hyphens"
            return render_template_string(HTML_TEMPLATE, 
                                        results=None, 
                                        search_term='',
                                        search_type=search_type,
                                        error=error)
        
    results = None
    if search_term:
            search_lower = search_term.lower()
            results = []
            
            for rec in data:
                match = False
                if search_type == 'all':
                    # Special handling for SNF/ format
                    if search_term.upper().startswith('SNF/'):
                        match = search_term.upper() == rec['set_no'].upper()
                    else:
                        # Regular search in all fields
                        match = (search_lower in rec['associate_name'].lower() or
                                search_lower in rec['associate_id'].lower() or
                                search_lower in rec['receiver_name'].lower() or
                                search_lower in rec['set_no'].lower() or
                                search_term == rec['line_no'])
                elif search_type == 'associate_name':
                    match = search_lower in rec['associate_name'].lower()
                elif search_type == 'associate_id':
                    match = search_lower in rec['associate_id'].lower()
                elif search_type == 'receiver_name':
                    match = search_lower in rec['receiver_name'].lower()
                elif search_type == 'set_no':
                    if search_term.upper().startswith('SNF/'):
                        match = search_term.upper() == rec['set_no'].upper()
                    else:
                        match = search_term.upper() == rec['set_no'].upper()
                elif search_type == 'line_no':
                    match = search_term == rec['line_no']
                
                if match:
                    results.append(rec)
            
            logger.info(f"Search for '{search_term}' in {search_type} returned {len(results)} results")
        
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
        is_set_no_search = '/' in search_term
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