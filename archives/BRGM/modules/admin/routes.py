from flask import Blueprint, jsonify, render_template, request, send_from_directory, flash
from flask_login import login_required
import pandas as pd
import os
import json
from extensions import db
from models import PublishedView

admin_bp = Blueprint('admin', __name__, template_folder='templates', url_prefix='/admin')

# --- Constants and Helpers ---
UPLOAD_FOLDER = 'static/data/uploads'
ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx'}
CONFIG_FOLDER = 'static/configs'

os.makedirs(CONFIG_FOLDER, exist_ok=True)

def get_upload_folder(context):
    return os.path.join(UPLOAD_FOLDER, context)

def process_lab_data(df):
    dg = df.copy()
    dg = dg.astype(str)
    required_cols = ['Collaborations', 'PAYS','CO-PUBLICATION','AFFILIATION et Partenaires BRGM',
                     'AUTEURS BRGM','Position auteur BRGM','Auteur correspondant','DIRECTIONS REORG 2025','PROGRAMME DOCTORAL','Discipline BRGM',
                     'PROG 2025 RETENU','GEO AFFILIATION BRGM DAT','FINANCEMENTS','Document type','PY2','OA','open_access.oa_status','Times Cited','doi','display_name','RESUME']
    for col in required_cols:
        if col not in dg.columns:
            dg[col] = ""
    dg = dg[required_cols]
    characters_to_remove = [";", ","]
    for col in dg.columns:
        for char in characters_to_remove:
            dg[col] = dg[col].apply(lambda x: x[1:] if x.startswith(char) else x)
            dg[col] = dg[col].apply(lambda x: x[:-1] if x.endswith(char) else x)
    dg["premier_auteur_BRGM"] = dg["Position auteur BRGM"].astype(str).apply(lambda x: "oui" if x.split(";")[0] == "1" else "non")
    dg.drop(columns=["Position auteur BRGM"], inplace=True)
    dg["open_access.oa_status"] = dg["open_access.oa_status"].astype(str).apply(lambda x: x.lower() if x else "")
    new_cols = [{col: col.lower().replace(" ","_")} for col in dg.columns]
    new_cols_dict = {}
    for d in new_cols:
        new_cols_dict.update(d)
    dg = dg.rename(columns=new_cols_dict)
    dg.fillna("", inplace=True)
    dg.replace("nan", "", inplace=True)
    dg = dg.astype(str)
    return dg

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Admin Routes ---

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    published_views = PublishedView.query.order_by(PublishedView.created_at.desc()).all()
    return render_template('explorer.html', published_views=published_views)

@admin_bp.route('/list-files')
@login_required
def list_files():
    context = request.args.get('context', 'explorer')
    upload_folder = get_upload_folder(context)
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        return jsonify([])
    files = [f for f in os.listdir(upload_folder) if f.endswith('.json')]
    return jsonify(files)

@admin_bp.route('/delete-file/<filename>', methods=['DELETE'])
@login_required
def delete_file(filename):
    context = request.args.get('context', 'explorer')
    upload_folder = get_upload_folder(context)
    try:
        file_path = os.path.join(upload_folder, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True}), 200
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/process-data', methods=['POST'])
@login_required
def process_data():
    context = request.args.get('context', 'explorer')
    upload_folder = get_upload_folder(context)
    os.makedirs(upload_folder, exist_ok=True)
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename_wo_ext = os.path.splitext(file.filename)[0]
            json_filename = f"{filename_wo_ext}.json"
            json_filepath = os.path.join(upload_folder, json_filename)
            df = None
            if ext == 'xlsx':
                df = pd.read_excel(file, engine="openpyxl", sheet_name=0)
                if context in ['explorer', 'playground-lab']:
                    df = process_lab_data(df)
            elif ext == 'csv':
                df = pd.read_csv(file)
            elif ext == 'json':
                df = pd.read_json(file)
            if df is not None:
                processed_data = df.to_dict(orient='records')
                with open(json_filepath, 'w', encoding='utf-8') as f_json:
                    json.dump(processed_data, f_json, ensure_ascii=False, indent=2)
                return jsonify(processed_data), 200
            else:
                return jsonify({'error': 'Unsupported file type'}), 400
        else:
            return jsonify({'error': 'File type not allowed'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/upload-config', methods=['POST'])
@login_required
def upload_config():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.js'):
        filename = file.filename
        file.save(os.path.join(CONFIG_FOLDER, filename))
        return jsonify({'message': f'Config file {filename} uploaded successfully'}), 200
    return jsonify({'error': 'Invalid file type'}), 400

@admin_bp.route('/list-configs')
@login_required
def list_configs():
    files = [f for f in os.listdir(CONFIG_FOLDER) if f.endswith('.js')]
    return jsonify(files)

@admin_bp.route('/publish', methods=['POST'])
@login_required
def publish_view():
    data_file = request.form.get('data_file')
    config_file = request.form.get('config_file')
    public_name = request.form.get('public_name')
    if not all([data_file, config_file, public_name]):
        return jsonify({'error': 'Missing required form data.'}), 400
    existing_view = PublishedView.query.filter_by(public_name=public_name).first()
    if existing_view:
        return jsonify({'error': f'A view with the name "{public_name}" already exists.'}), 409
    new_view = PublishedView(
        public_name=public_name,
        data_file=data_file,
        config_file=config_file
    )
    db.session.add(new_view)
    db.session.commit()
    flash(f'La vue "{public_name}" a été publiée avec succès !', 'success')
    return jsonify({'success': True, 'message': 'Vue publiée avec succès !'})

@admin_bp.route('/unpublish/<int:view_id>', methods=['POST'])
@login_required
def unpublish_view(view_id):
    view_to_delete = PublishedView.query.get_or_404(view_id)
    db.session.delete(view_to_delete)
    db.session.commit()
    flash(f'La vue "{view_to_delete.public_name}" a été dé-publiée.', 'success')
    return jsonify({'success': True})
