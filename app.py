from flask import Flask, render_template, request, redirect, session, url_for
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route("/")
def index():
    answered_qna = []
    if os.path.exists("qna.json"):
        with open("qna.json", "r", encoding="utf-8") as f:
            qna_list = json.load(f)
            answered_qna = [q for q in qna_list if q["answer"]]

    return render_template("index.html", answered_qna=answered_qna, role=session.get("role", "student"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if os.path.exists("users.json"):
            with open("users.json", "r", encoding="utf-8") as f:
                users = json.load(f)
        else:
            return "users.json 파일이 없습니다."

        if username in users and users[username]["password"] == password:
            session["username"] = username
            session["role"] = users[username]["role"]
            return redirect(url_for("qna"))
        else:
            return "❌ 로그인 실패: 아이디 또는 비밀번호가 올바르지 않아요!"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/qna", methods=["GET", "POST"])
def qna():
    role = session.get("role", "student")

    qna_list = []
    if os.path.exists("qna.json"):
        with open("qna.json", "r", encoding="utf-8") as f:
            qna_list = json.load(f)

    if request.method == "POST" and role == "student":
        question = request.form.get("question", "").strip()
        if question:
            qna_list.append({
                "username": session.get("username", "익명"),
                "question": question,
                "answer": "",
                "answered_by": ""
            })
            with open("qna.json", "w", encoding="utf-8") as f:
                json.dump(qna_list, f, ensure_ascii=False, indent=2)
        return redirect("/qna")

    unanswered = [q for q in qna_list if not q["answer"]]
    answered = [q for q in qna_list if q["answer"]]

    return render_template("qna.html", unanswered=unanswered, answered=answered, role=role)

@app.route("/answer/<int:index>", methods=["POST"])
def answer(index):
    if session.get("role") != "admin":
        return redirect("/login")

    answer_text = request.form.get("answer", "").strip()
    answered_by = request.form.get("answered_by", "")

    if not os.path.exists("qna.json"):
        return "qna.json 파일이 없습니다."

    with open("qna.json", "r", encoding="utf-8") as f:
        qna_list = json.load(f)

    if 0 <= index < len(qna_list):
        qna_list[index]["answer"] = answer_text
        qna_list[index]["answered_by"] = answered_by

        with open("qna.json", "w", encoding="utf-8") as f:
            json.dump(qna_list, f, ensure_ascii=False, indent=2)

    return redirect("/qna")

@app.route("/delete/<int:index>", methods=["POST"])
def delete(index):
    if session.get("role") != "admin":
        return redirect("/login")

    if not os.path.exists("qna.json"):
        return "qna.json 파일이 없습니다."

    with open("qna.json", "r", encoding="utf-8") as f:
        qna_list = json.load(f)

    if 0 <= index < len(qna_list):
        qna_list.pop(index)
        with open("qna.json", "w", encoding="utf-8") as f:
            json.dump(qna_list, f, ensure_ascii=False, indent=2)

    return redirect("/qna")

if __name__ == "__main__":
    app.run(debug=True)
