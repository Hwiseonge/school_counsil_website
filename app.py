import os
import json
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 파일 경로 설정
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

IMAGES_JSON_PATH = os.path.join(app.root_path, 'images.json')
QNA_JSON_PATH = os.path.join(app.root_path, 'qna.json')
USERS_JSON_PATH = os.path.join(app.root_path, 'users.json')

IMAGE_SECTIONS = ['news', 'schedule', 'intro', 'mascot']

# users.json 읽기
def load_users():
    if os.path.exists(USERS_JSON_PATH):
        with open(USERS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        default_users = {
            "admin": {"password": "password123", "role": "admin"},
            "student": {"password": "student123", "role": "student"}
        }
        with open(USERS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_users, f, ensure_ascii=False, indent=2)
        return default_users

# images.json 읽기/저장
def load_images():
    if os.path.exists(IMAGES_JSON_PATH):
        with open(IMAGES_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        data = {section: None for section in IMAGE_SECTIONS}
        with open(IMAGES_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

def save_images(images_dict):
    with open(IMAGES_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(images_dict, f, ensure_ascii=False, indent=2)

# qna.json 읽기/저장
def load_qna():
    if os.path.exists(QNA_JSON_PATH):
        with open(QNA_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(QNA_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []

def save_qna(qna_list):
    with open(QNA_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(qna_list, f, ensure_ascii=False, indent=2)

# 이미지 리사이즈 (300x300 최대, 비율 유지)
def resize_image(image_path):
    with Image.open(image_path) as img:
        img.thumbnail((300, 300))
        img.save(image_path)

@app.route('/')
def index():
    images = load_images()
    qna_list = load_qna()
    answered_qna = [q for q in qna_list if q.get("answer")]
    role = session.get('role', 'student')
    return render_template('index.html', images=images, answered_qna=answered_qna, role=role)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()
        user = users.get(username)
        if user and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            return "로그인 실패: 아이디 또는 비밀번호가 틀렸습니다.", 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if session.get('role') != 'admin':
        return "권한이 없습니다.", 403

    if 'image' not in request.files:
        return "파일이 없습니다.", 400

    file = request.files['image']
    if file.filename == '':
        return "파일이 선택되지 않았습니다.", 400

    section = request.form.get('section')
    if section not in IMAGE_SECTIONS:
        return "잘못된 섹션입니다.", 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    try:
        resize_image(save_path)
    except Exception as e:
        os.remove(save_path)
        return f"이미지 처리 중 오류가 발생했습니다: {e}", 500

    images = load_images()
    images[section] = filename
    save_images(images)

    return redirect(url_for('index'))

@app.route('/qna', methods=['GET', 'POST'])
def qna():
    role = session.get('role', 'student')
    qna_list = load_qna()

    if request.method == 'POST' and role == 'student':
        question = request.form.get('question', '').strip()
        if question:
            max_id = max([q['id'] for q in qna_list], default=0)
            qna_list.append({
                'id': max_id + 1,
                'username': session.get('username', '익명'),
                'question': question,
                'answer': '',
                'answered_by': ''
            })
            save_qna(qna_list)
        return redirect(url_for('qna'))

    unanswered = [q for q in qna_list if not q.get('answer')]
    answered = [q for q in qna_list if q.get('answer')]
    return render_template('qna.html', unanswered=unanswered, answered=answered, role=role)

@app.route('/answer/<int:qna_id>', methods=['POST'])
def answer(qna_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    answer_text = request.form.get('answer', '').strip()
    answered_by = session.get('username', '')

    qna_list = load_qna()
    for q in qna_list:
        if q['id'] == qna_id:
            q['answer'] = answer_text
            q['answered_by'] = answered_by
            break
    save_qna(qna_list)
    return redirect(url_for('qna'))

@app.route('/delete/<int:qna_id>', methods=['POST'])
def delete(qna_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    qna_list = load_qna()
    qna_list = [q for q in qna_list if q['id'] != qna_id]
    save_qna(qna_list)
    return redirect(url_for('qna'))


if __name__ == '__main__':
    app.run(debug=True)
