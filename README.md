# campus_lf

Campus Lost & Found is a Flask application for reporting lost and found items on campus.

## Prepare repository

1. Initialize git (if needed):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```
2. Create a GitHub repository and connect it:
   ```bash
   git remote add origin https://github.com/<your-user>/<your-repo>.git
   git push -u origin main
   ```

## Deploy to PythonAnywhere

1. Create a PythonAnywhere account.
2. Open a Bash console and clone your repository:
   ```bash
   cd ~
   git clone https://github.com/<your-user>/<your-repo>.git
   cd campus_lf
   ```
3. Create and activate virtualenv:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 campus_lf
   pip install -r requirements.txt
   ```
4. Set up the file upload folder:
   ```bash
   mkdir -p ~/campus_lf/static/uploads
   ```
5. Configure the web app on PythonAnywhere:
   - Source code: `/home/<username>/campus_lf`
   - Working directory: `/home/<username>/campus_lf`
   - Virtualenv: `/home/<username>/.virtualenvs/campus_lf`
   - WSGI file should import `application` from `wsgi.py`

6. Add environment variables in the PythonAnywhere Web tab:
   - `SECRET_KEY`
   - `DATABASE_URL` (optional; defaults to SQLite at `campus_lf.db`)
   - `CLOUDINARY_URL` (optional for image uploads)

7. Reload the web app and visit the PythonAnywhere URL.

## Notes

- The app uses SQLite by default. For production, you can switch to an external database using `DATABASE_URL`.
- Image uploads are stored in `static/uploads/` unless `CLOUDINARY_URL` is configured.
- The PythonAnywhere web app should use `wsgi.py` as the WSGI entry point.
