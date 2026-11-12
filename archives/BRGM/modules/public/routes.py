from flask import Blueprint, render_template, send_from_directory, request, jsonify
from models import PublishedView
import os
import json

public_bp = Blueprint('public', __name__, template_folder='templates')

# Constants for data/config locations.
CONFIG_FOLDER = 'static/configs'
UPLOAD_FOLDER = 'static/data/uploads'

@public_bp.route('/')
def home():
    """Public homepage listing all published visualizations."""
    published_views = PublishedView.query.order_by(PublishedView.created_at.desc()).all()
    return render_template('home.html', published_views=published_views)

@public_bp.route('/view/<int:view_id>')
def view_visualization(view_id):
    """Public page to view a single visualization."""
    view = PublishedView.query.get_or_404(view_id)
    print(vars(view))
    return render_template('viewer.html', view=view)

@public_bp.route('/load-config/<filename>')
def load_config(filename):
    """Publicly serves config files."""
    return send_from_directory(CONFIG_FOLDER, filename)

@public_bp.route('/load-file/<filename>')
def load_file(filename):
    """Publicly serves data files."""
    # The context is still needed for the admin dashboard to load its own data.
    context = request.args.get('context', 'explorer')
    upload_folder = os.path.join(UPLOAD_FOLDER, context)
    file_path = os.path.join(upload_folder, f"{filename}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'File not found'}), 404
