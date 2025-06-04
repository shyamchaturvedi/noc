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
            body {
                background-color: white;
            }

            .container {
                padding: 0;
            }

            .header, .results-header {
                display: none !important;  /* Hide both header and results header */
            }

            .search-container, .action-buttons {
                display: none !important;
            }

            .table-container {
                box-shadow: none;
                margin-top: 0;
            }

            table {
                border-collapse: collapse;
                width: 100%;
            }

            th {
                background-color: white !important;
                color: black !important;
                border-bottom: 2px solid var(--border-color) !important;
            }

            td {
                border-bottom: 1px solid var(--border-color) !important;
            }

            .highlight-row {
                background-color: white !important;
            }

            .status-badge, .location-badge {
                border: 1px solid var(--border-color);
            }

            /* Add page title for print */
            .table-container::before {
                content: "Search Results";
                display: block;
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 1rem;
                color: black;
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
                                <th>Location</th>
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