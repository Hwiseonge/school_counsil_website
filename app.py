import os
import json
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from PIL import Image
from markupsafe import Markup, escape

app = Flask(__name__)

# nl2br 필터 등록 (줄바꿈을 <br>로 변환)


def nl2br(value):
    if not isinstance(value, str):
        value = '' if value is None else str(value)
    escaped = escape(value)
    return Markup(escaped.replace('\n', '<br>\n'))

app.jinja_env.filters['nl2br'] = nl2br

app.secret_key = 'your_secret_key'

# 업로드 경로
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

IMAGES_JSON_PATH = os.path.join(app.root_path, 'images.json')
QNA_JSON_PATH = os.path.join(app.root_path, 'qna.json')
USERS_JSON_PATH = os.path.join(app.root_path, 'users.json')

IMAGE_SECTIONS = ['news', 'schedule', 'intro', 'mascot']

# --- 유저 정보 로드/저장 ---
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

# --- 이미지 데이터 로드/저장 ---
def load_images():
    if os.path.exists(IMAGES_JSON_PATH):
        with open(IMAGES_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 초기화 안된 섹션들 기본값 세팅
            for section in IMAGE_SECTIONS:
                if section not in data or not isinstance(data[section], dict):
                    data[section] = {"image": None, "text": ""}
            return data
    else:
        data = {section: {"image": None, "text": ""} for section in IMAGE_SECTIONS}
        with open(IMAGES_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

def save_images(images_dict):
    with open(IMAGES_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(images_dict, f, ensure_ascii=False, indent=2)

# --- QnA 데이터 로드/저장 ---
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

# --- 이미지 리사이즈 ---
from PIL import Image

def resize_image(image_path):
    with Image.open(image_path) as img:
        max_size = (900, 900)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)  # 고품질 리샘플링
        img.save(image_path)


# --- 루트 (index) 페이지 ---
@app.route('/')
def index():
    images = load_images()
    qna_list = load_qna()
    answered_qna = [q for q in qna_list if q.get("answer")]
    role = session.get('role', 'student')
    return render_template('index.html', images=images, answered_qna=answered_qna, role=role)

# --- 로그인 ---
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

# --- 로그아웃 ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- 편집 페이지 ---
@app.route('/edit')
def edit():
    section = request.args.get('section')
    if section not in IMAGE_SECTIONS:
        return "잘못된 섹션입니다.", 404
    images = load_images()
    role = session.get('role', 'student')
    if role != 'admin':
        return "권한이 없습니다.", 403
    return render_template('edit.html', section=section, images=images, role=role)

# --- 이미지 및 텍스트 업로드 처리 ---
@app.route('/upload_image', methods=['POST'])
def upload_image():
    if session.get('role') != 'admin':
        return "권한이 없습니다.", 403

    section = request.form.get('section')
    if section not in IMAGE_SECTIONS:
        return "잘못된 섹션입니다.", 400

    images = load_images()
    data_section = images.get(section, {"images": [], "representative": None, "text": ""})

    # 여러 이미지 처리
    files = request.files.getlist('images')
    uploaded_files = []

    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            resize_image(save_path)
            uploaded_files.append(filename)

    if 'images' not in data_section or not isinstance(data_section['images'], list):
        data_section['images'] = []

    # 기존 + 새로 업로드한 파일 합치기
    data_section['images'].extend(uploaded_files)

    # 대표 이미지 선택
    representative = request.form.get('representative')
    if representative:
        data_section['representative'] = representative
    elif uploaded_files:
        # 새로 업로드했는데 대표 이미지 안 골랐으면 첫 번째를 대표로
        data_section['representative'] = uploaded_files[0]

    # 텍스트 저장
    text_field = f"{section}_text"
    text_value = request.form.get(text_field, '').strip()
    if text_value:
        data_section['text'] = text_value

    images[section] = data_section
    save_images(images)
    return redirect(url_for('edit', section=section))




#딜레이트


@app.route('/delete_image', methods=['POST'])
def delete_image():
    section = request.form.get('section')
    filename = request.form.get('filename')

    # JSON 읽기
    with open('images.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    if section in data and 'images' in data[section]:
        if filename in data[section]['images']:
            data[section]['images'].remove(filename)
            # 대표 이미지가 삭제된 경우 초기화
            if data[section].get('representative') == filename:
                data[section]['representative'] = data[section]['images'][0] if data[section]['images'] else None

            # 서버에 저장된 파일도 삭제
            file_path = os.path.join(app.static_folder, 'uploads', filename)
            if os.path.exists(file_path):
                os.remove(file_path)

    # JSON 저장
    with open('images.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return redirect(url_for('edit', section=section))





# --- QnA 페이지 ---
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

# --- QnA 답변 ---
@app.route('/answer/<int:qna_id>', methods=['POST'])
def answer(qna_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    answer_text = request.form.get('answer', '').strip()
    answered_by = request.form.get('answered_by', '').strip()

    qna_list = load_qna()
    for q in qna_list:
        if q['id'] == qna_id:
            q['answer'] = answer_text
            q['answered_by'] = answered_by
            break
    save_qna(qna_list)
    return redirect(url_for('qna'))

# --- QnA 삭제 ---
@app.route('/delete/<int:qna_id>', methods=['POST'])
def delete(qna_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    qna_list = load_qna()
    qna_list = [q for q in qna_list if q['id'] != qna_id]
    save_qna(qna_list)
    return redirect(url_for('qna'))

# --- 섹션별 상세보기 페이지 ---
@app.route('/show_all/<section>')
def show_all(section):
    if section not in ['news', 'schedule', 'intro', 'mascot']:
        return "잘못된 섹션입니다.", 404
    images = load_images()
    data = images.get(section, {})
    return render_template('show_section.html', section=section, data=data)


@app.route('/details/<section>')
def details(section):
    # section에 따라 처리
    images = load_images()
    if section not in IMAGE_SECTIONS:
        return "잘못된 섹션입니다.", 404
    return render_template('details.html', section=section, images=images)


if __name__ == '__main__':
    app.run(debug=True)
