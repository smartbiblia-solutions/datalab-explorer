from flask import Blueprint, render_template, send_from_directory, jsonify, request
from flask_cors import CORS
import os

embedding_atlas_bp = Blueprint(
    'embedding_atlas',
    __name__,
    template_folder='templates'
)

# Apply CORS specifically to the cache route within this blueprint.
# This is required for the Nomic atlas to function correctly.
CORS(embedding_atlas_bp, resources={r"/data/cache/*": {"origins": "*"}})

@embedding_atlas_bp.route('/embedding-atlas')
def dashboard():
    """Route to embeddings atlas app."""
    return render_template('embedding-atlas.html')

@embedding_atlas_bp.route('/iframe')
def iframe():
    """Route to embeddings atlas app (iframe version)."""
    return render_template('iframe.html')

# The following routes serve the static assets required by the Nomic atlas client.
# The paths are kept identical to what the client-side library requests.

@embedding_atlas_bp.route('/data/metadata.json')
def serve_metadata():
    return send_from_directory('static/embedding-atlas-app/data', 'metadata.json')

@embedding_atlas_bp.route('/data/dataset.parquet')
def serve_parquet_dataset():
    return send_from_directory('static/embedding-atlas-app/data', 'dataset.parquet')

@embedding_atlas_bp.route('/duckdb-wasm/v1.1.1/wasm_eh/parquet.duckdb_extension.wasm')
def serve_parquet_extension():
    return send_from_directory('static/embedding-atlas-app/duckdb-wasm/v1.1.1/wasm_eh', 'parquet.duckdb_extension.wasm')

@embedding_atlas_bp.route('/data/cache/<path:filename>', methods=['GET', 'POST'])
def serve_cache_file(filename):
    """
    This route handles caching for the atlas, which improves performance on re-visits.
    It can receive data to cache (POST) and serve cached data (GET).
    """
    cache_dir = os.path.join('static', 'cache')
    file_path = os.path.join(cache_dir, filename)

    if request.method == 'GET':
        if os.path.exists(file_path):
            return send_from_directory(cache_dir, filename)
        return jsonify({'error': 'File not found'}), 404

    elif request.method == 'POST':
        # Save the posted file data to the cache directory
        os.makedirs(cache_dir, exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(request.data)
        return jsonify({'success': True, 'filename': filename}), 201
