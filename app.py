from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename  # <-- add this line
import os
import shutil

app = Flask(__name__, static_folder='assets', static_url_path='/assets')
app.secret_key = "secret123"
# Example admin check decorator
def admin_required(f):
    from functools import wraps
    from flask import session
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            flash("Admin login required")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function



# ---------------- DELETE SINGLE PHOTO ----------------
@app.route('/delete_photo/<folder>/<filename>')
@admin_required
def delete_photo(folder, filename):
    """Delete a single photo from a folder"""
    photo_path = os.path.join(PHOTO_FOLDER, folder, filename)
    if os.path.exists(photo_path):
        os.remove(photo_path)
        flash(f"Photo '{filename}' deleted successfully.")
    else:
        flash("Photo not found.")
    return redirect(url_for('admin_panel'))

# ---------------- DELETE ENTIRE EVENT ----------------
@app.route('/delete_event/<folder>')
@admin_required
def delete_event(folder):
    event_path = os.path.join(PHOTO_FOLDER, folder)
    if os.path.exists(event_path):
        shutil.rmtree(event_path)
        flash(f'Event "{folder}" deleted successfully.')
    else:
        flash("Event folder not found.")
    return redirect(url_for('admin_panel'))

@app.route("/update_description/<folder>", methods=["POST"])
def update_description(folder):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    folder_path = os.path.join(PHOTO_FOLDER, folder)
    if not os.path.exists(folder_path):
        flash("Event folder not found.")
        return redirect(url_for("admin_panel"))

    description = request.form.get("description", "")
    desc_file = os.path.join(folder_path, "description.txt")
    with open(desc_file, "w", encoding="utf-8") as f:
        f.write(description.strip())

    flash("Description updated successfully.")
    return redirect(url_for("admin_panel"))



# Add Photos to Existing Event
@app.route("/add-photos/<event_name>", methods=["GET", "POST"])
@admin_required
def add_photos_to_event(event_name):

    folder_path = os.path.join(PHOTO_FOLDER, event_name)

    if request.method == "POST":
        file = request.files.get("photo")   # single photo

        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(folder_path, filename))

            flash("Photo added successfully")

        return redirect(url_for("admin_panel"))

    return render_template("add_more_photos.html", event_name=event_name)
# Folder to save event photos
UPLOAD_FOLDER = "static/photos"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/create-event", methods=["GET", "POST"])
@admin_required
def create_event():
    if request.method == "POST":
        event_name = request.form.get("event_name")
        description = request.form.get("description")
        photo = request.files.get("photo")

        folder = secure_filename(event_name)
        folder_path = os.path.join(PHOTO_FOLDER, folder)
        os.makedirs(folder_path, exist_ok=True)

        filename = secure_filename(photo.filename)
        photo.save(os.path.join(folder_path, filename))

        # save default image name
        with open(os.path.join(folder_path, "default.txt"), "w") as f:
            f.write(filename)

        # save description
        with open(os.path.join(folder_path, "description.txt"), "w") as f:
            f.write(description or "")

        return redirect(url_for("admin_panel"))

    return render_template("create_event.html")

@app.route("/set-default/<folder>/<filename>")
@admin_required
def set_default_photo(folder, filename):

    folder_path = os.path.join(PHOTO_FOLDER, folder)
    default_file = os.path.join(folder_path, "default.txt")

    with open(default_file, "w") as f:
        f.write(filename)

    flash("Main photo updated")
    return redirect(url_for("admin_panel"))
# Static pages
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/publication-policy")
def publication_policy():
    return render_template("publication_policy.html")

@app.route("/previous-issues")
def previous_issues():
    return render_template("previous-issues.html")

@app.route("/pdfs")
def pdfs():
    pdf_list = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]
    is_admin = session.get("admin", False)
    return render_template("pdf.html", pdfs=pdf_list, is_admin=is_admin)

# ---------------- CONFIG ----------------
PDF_FOLDER = os.path.join('assets', 'events')
PHOTO_FOLDER = os.path.join('assets', 'photos')
os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(PHOTO_FOLDER, exist_ok=True)

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin-login", methods=["GET","POST"])
def admin_login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        else:
            error = "Invalid username or password"
    return render_template("admin_login.html", error=error)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.route("/admin", methods=["GET","POST"])
def admin_panel():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    # PDF upload
    if request.method == "POST" and 'pdf' in request.files:
        file = request.files.get("pdf")
        if file and file.filename.endswith(".pdf"):
            filename = secure_filename(file.filename)
            file.save(os.path.join(PDF_FOLDER, filename))

    pdf_list = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]

    events_list = []

    for folder in sorted(os.listdir(PHOTO_FOLDER)):
        folder_path = os.path.join(PHOTO_FOLDER, folder)

        if os.path.isdir(folder_path):

            images = [
                img for img in os.listdir(folder_path)
                if img.lower().endswith(('.png','.jpg','.jpeg'))
            ]

            # read description
            desc_file = os.path.join(folder_path, "description.txt")
            description = ""
            if os.path.exists(desc_file):
                with open(desc_file) as f:
                    description = f.read()

            # read default image
            default_file = os.path.join(folder_path, "default.txt")
            default = None

            if os.path.exists(default_file):
                with open(default_file) as f:
                    default = f.read().strip()
            elif images:
                default = images[0]

            events_list.append({
                'folder': folder,
                'title': folder.replace('_',' ').title(),
                'description': description,
                'default': default,
                'images': images
            })

    return render_template(
        "admin.html",
        pdfs=pdf_list,
        events=events_list
    )

# ---------------- DELETE PDF ----------------
@app.route("/delete/<filename>")
def delete_pdf(filename):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    path = os.path.join(PDF_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for("admin_panel"))

# ---------------- VIEW PDF ----------------
@app.route("/view/<filename>")
def view_pdf(filename):
    return send_from_directory(PDF_FOLDER, filename)

# ---------------- DOWNLOAD PDF ----------------
@app.route("/download/<filename>")
def download_pdf(filename):
    return send_from_directory(PDF_FOLDER, filename, as_attachment=True)

# ---------------- EVENTS PAGE ----------------
@app.route("/events")
def events():
    events_list = []

    for folder in sorted(os.listdir(PHOTO_FOLDER)):
        folder_path = os.path.join(PHOTO_FOLDER, folder)

        if os.path.isdir(folder_path):

            images = [
                img for img in os.listdir(folder_path)
                if img.lower().endswith(('.png','.jpg','.jpeg'))
            ]

            # read default
            default_file = os.path.join(folder_path, "default.txt")
            default = None

            if os.path.exists(default_file):
                with open(default_file) as f:
                    default = f.read().strip()
            elif images:
                default = images[0]

            events_list.append({
                'folder': folder,
                'title': folder.replace('_',' ').title(),
                'default': f"{folder}/{default}" if default else None,
                'images': [f"{folder}/{img}" for img in images]
            })

    return render_template("photos.html", events=events_list)

# ---------------- EVENT DETAIL PHOTOS ----------------
@app.route("/photos/<folder>")
def event_photos(folder):
    folder_path = os.path.join(PHOTO_FOLDER, folder)
    if not os.path.exists(folder_path):
        return "Event not found", 404
    images = [f"{folder}/{img}" for img in os.listdir(folder_path) if img.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return render_template("event_details.html", images=images, event_title=folder.replace('_', ' ').title())


if __name__ == "__main__":
    app.run(debug=True)