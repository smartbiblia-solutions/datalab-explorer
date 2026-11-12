from flask import Blueprint, render_template
from flask_login import login_required

playground_lab_bp = Blueprint(
    'playground_lab',
    __name__,
    template_folder='templates'
)

@playground_lab_bp.route('/playground-lab')
@login_required
def playground_lab():
    """Route to the lab-specific playground."""
    return render_template('playground_lab.html')
