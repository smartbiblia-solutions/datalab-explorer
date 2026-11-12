from flask import Blueprint, render_template

playground_generic_bp = Blueprint(
    'playground_generic',
    __name__,
    template_folder='templates'
)

@playground_generic_bp.route('/playground-generic')
def playground_generic():
    """Route to the generic playground."""
    return render_template('playground_generic.html')
