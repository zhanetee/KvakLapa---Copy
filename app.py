from flask import Flask, render_template, url_for
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "kvak_lapa_secret_key" 

def get_db_connection():
    db = Path(__file__).parent / "KvakLapa.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    conn = sqlite3.connect('KvakLapa.db')
    cursor = conn.cursor()

    cursor.execute("SELECT filename FROM frog_faces")
    frog_faces = [{'filename': row[0]} for row in cursor.fetchall()]

    conn.close()

    return render_template('index.html', frog_faces=frog_faces)

@app.route("/par-mums")
def about():
    return render_template("about.html")

@app.route("/sugas")
def species():
    conn = get_db_connection()
    frogs = conn.execute("SELECT * FROM species").fetchall()
    conn.close()
    return render_template("species.html", species=frogs)

@app.route("/sugas/<int:species_id>")
def species_detail(species_id):
    conn = get_db_connection()
    frog = conn.execute("SELECT * FROM species WHERE id = ?", (species_id,)).fetchone()
    classification = conn.execute("SELECT * FROM classification WHERE species_id = ?", (species_id,)).fetchone()
    conservation = conn.execute("SELECT * FROM conservation_status WHERE species_id = ?", (species_id,)).fetchone()

    habitats = conn.execute("""
        SELECT h.habitat_type FROM habitat h
        JOIN species_habitats sh ON h.id = sh.habitat_id
        WHERE sh.species_id = ?
    """, (species_id,)).fetchall()

    conn.close()
    return render_template("species_detail.html", 
                           species=frog, 
                           classification=classification,
                           conservation=conservation,
                           habitats=habitats)

@app.route("/dzest-sugu/<int:species_id>", methods=["POST"])
def delete_species(species_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    species = conn.execute("SELECT image, detail_image FROM species WHERE id = ?", (species_id,)).fetchone()
    
    cursor.execute("DELETE FROM species_habitats WHERE species_id = ?", (species_id,))
    cursor.execute("DELETE FROM classification WHERE species_id = ?", (species_id,))
    cursor.execute("DELETE FROM conservation_status WHERE species_id = ?", (species_id,))
    
    cursor.execute("DELETE FROM species WHERE id = ?", (species_id,))
    
    conn.commit()
    conn.close()
    
    flash("Suga veiksmīgi dzēsta!", "success")
    return redirect(url_for("species"))

@app.route("/pievienot", methods=["GET", "POST"])
def add_species():
    if request.method == "POST":
        name = request.form["name"]
        scientific_name = request.form["scientific_name"]
        average_length_cm = request.form["average_length_cm"]
        found_in_latvia = 1 if "found_in_latvia" in request.form else 0
        latvia_location = request.form["latvia_location"] if found_in_latvia else ""
        
        image = request.files["image"]
        detail_image = request.files["detail_image"]
        
        image_filename = None
        detail_image_filename = None
        
        if image and image.filename:
            image_filename = secure_filename(image.filename)
            image.save(Path(app.static_folder) / "images" / "species" / image_filename)
            
        if detail_image and detail_image.filename:
            detail_image_filename = secure_filename(detail_image.filename)
            detail_image.save(Path(app.static_folder) / "images" / "species" / detail_image_filename)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO species (name, scientific_name, average_length_cm, 
                               found_in_latvia, latvia_location, image, detail_image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, scientific_name, average_length_cm, found_in_latvia, 
              latvia_location, image_filename, detail_image_filename))
        
        species_id = cursor.lastrowid
        
        order = request.form["order"]
        family = request.form["family"]
        cursor.execute("""
            INSERT INTO classification (species_id, "order", family)
            VALUES (?, ?, ?)
        """, (species_id, order, family))
        
        status = request.form["status"]
        notes = request.form["notes"]
        cursor.execute("""
            INSERT INTO conservation_status (species_id, status, notes)
            VALUES (?, ?, ?)
        """, (species_id, status, notes))
        
        selected_habitats = request.form.getlist("habitats")
        for habitat_id in selected_habitats:
            cursor.execute("""
                INSERT INTO species_habitats (species_id, habitat_id)
                VALUES (?, ?)
            """, (species_id, habitat_id))
        
        conn.commit()
        conn.close()
        
        flash("Jauna sugas veiksmīgi pievienota!", "success")
        return redirect(url_for("species"))
    
    conn = get_db_connection()
    habitats = conn.execute("SELECT id, habitat_type FROM habitat").fetchall()
    conn.close()
    
    return render_template("add_species.html", habitats=habitats)

@app.route("/rediget-sugu/<int:species_id>", methods=["GET", "POST"])
def edit_species(species_id):
    conn = get_db_connection()
    
    if request.method == "POST":
        name = request.form["name"]
        scientific_name = request.form["scientific_name"]
        average_length_cm = request.form["average_length_cm"]
        found_in_latvia = 1 if "found_in_latvia" in request.form else 0
        latvia_location = request.form["latvia_location"] if found_in_latvia else ""
        
        image = request.files["image"]
        detail_image = request.files["detail_image"]
        
        current_images = conn.execute("SELECT image, detail_image FROM species WHERE id = ?", 
                                   (species_id,)).fetchone()
        
        image_filename = current_images['image']
        detail_image_filename = current_images['detail_image']
        
        if image and image.filename:
            image_filename = secure_filename(image.filename)
            image.save(Path(app.static_folder) / "images" / "species" / image_filename)
            
        if detail_image and detail_image.filename:
            detail_image_filename = secure_filename(detail_image.filename)
            detail_image.save(Path(app.static_folder) / "images" / "species" / detail_image_filename)
        
        conn.execute("""
            UPDATE species
            SET name = ?, scientific_name = ?, average_length_cm = ?, 
                found_in_latvia = ?, latvia_location = ?, image = ?, detail_image = ?
            WHERE id = ?
        """, (name, scientific_name, average_length_cm, found_in_latvia, 
              latvia_location, image_filename, detail_image_filename, species_id))
        
        order = request.form["order"]
        family = request.form["family"]
        conn.execute("""
            UPDATE classification 
            SET "order" = ?, family = ?
            WHERE species_id = ?
        """, (order, family, species_id))
        
        status = request.form["status"]
        notes = request.form["notes"]
        conn.execute("""
            UPDATE conservation_status 
            SET status = ?, notes = ?
            WHERE species_id = ?
        """, (status, notes, species_id))
        
        conn.execute("DELETE FROM species_habitats WHERE species_id = ?", (species_id,))
        
        selected_habitats = request.form.getlist("habitats")
        for habitat_id in selected_habitats:
            conn.execute("""
                INSERT INTO species_habitats (species_id, habitat_id)
                VALUES (?, ?)
            """, (species_id, habitat_id))
        
        conn.commit()
        conn.close()
        
        flash("Suga veiksmīgi atjaunināta!", "success")
        return redirect(url_for("species_detail", species_id=species_id))
    
    species = conn.execute("SELECT * FROM species WHERE id = ?", (species_id,)).fetchone()
    classification = conn.execute("SELECT * FROM classification WHERE species_id = ?", 
                                (species_id,)).fetchone()
    conservation = conn.execute("SELECT * FROM conservation_status WHERE species_id = ?", 
                              (species_id,)).fetchone()
    
    habitats = conn.execute("SELECT id, habitat_type FROM habitat").fetchall()
    
    species_habitats = conn.execute("""
        SELECT habitat_id FROM species_habitats WHERE species_id = ?
    """, (species_id,)).fetchall()
    species_habitat_ids = [h['habitat_id'] for h in species_habitats]
    
    conn.close()
    
    return render_template("edit_species.html", 
                         species=species, 
                         classification=classification,
                         conservation=conservation,
                         habitats=habitats,
                         species_habitat_ids=species_habitat_ids)

if __name__ == "__main__":
    app.run(debug=True)