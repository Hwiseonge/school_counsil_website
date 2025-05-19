from flask import Blueprint, render_template

file_bp = Blueprint('file_bp', __name__, url_prefix='/file')

@file_bp.route('/')
def file_index():
    # 예시 페이지
    return render_template('file_index.html')
