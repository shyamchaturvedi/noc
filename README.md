# Professional Records Search Application

A Flask-based web application for searching and managing records with professional features including search, print, and export capabilities.

## Features
- Advanced search functionality
- Print-friendly output
- Excel export
- Professional UI
- Responsive design

## Deployment Instructions

### Deploying to PythonAnywhere

1. **Create a PythonAnywhere Account**
   - Go to [PythonAnywhere](https://www.pythonanywhere.com/)
   - Sign up for a free account

2. **Upload Your Code**
   - In PythonAnywhere dashboard, go to "Files" tab
   - Upload all your project files:
     - app.py
     - wsgi.py
     - requirements.txt
     - data.txt
     - (any other project files)

3. **Set Up Virtual Environment**
   ```bash
   # In PythonAnywhere bash console
   mkvirtualenv --python=/usr/bin/python3.10 myenv
   pip install -r requirements.txt
   ```

4. **Configure Web App**
   - Go to "Web" tab
   - Click "Add a new web app"
   - Choose "Manual configuration"
   - Select Python 3.10
   - In "Code" section:
     - Set Source code to your project directory
     - Set Working directory to your project directory
   - In "Virtualenv" section:
     - Enter path to your virtualenv (e.g., /home/yourusername/.virtualenvs/myenv)
   - In "WSGI configuration file" section:
     - Click on the WSGI file link
     - Replace contents with:
     ```python
     import sys
     path = '/home/yourusername/your-project-directory'
     if path not in sys.path:
         sys.path.append(path)
     
     from app import app as application
     ```

5. **Set Environment Variables**
   - In "Web" tab, go to "Environment variables"
   - Add any required environment variables

6. **Reload Web App**
   - Click the "Reload" button in the "Web" tab

### Accessing Your Application
- Your application will be available at: `yourusername.pythonanywhere.com`
- The free tier includes:
  - 512MB storage
  - 1 web app
  - Custom domain support
  - SSL certificate

### Maintenance
- Monitor your application in the "Web" tab
- Check logs for any issues
- Regular backups of your data.txt file
- Keep dependencies updated

## Local Development
1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Access the application at: `http://localhost:5000`

## Security Notes
- Keep your data.txt file secure
- Regular backups recommended
- Monitor application logs
- Update dependencies regularly

## Support
For any issues or questions, please contact the development team. 