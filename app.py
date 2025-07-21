import os
import io
from flask import Flask, render_template, request, send_file, flash
from werkzeug.utils import secure_filename
import openai
from fpdf import FPDF
from PyPDF2 import PdfReader
from docx import Document

app = Flask(__name__)
app.secret_key = 'secret'

# Configure OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text(file_path, file_ext):
    if file_ext == 'pdf':
        reader = PdfReader(file_path)
        text = "\n".join(page.extract_text() or '' for page in reader.pages)
        return text
    elif file_ext == 'docx':
        doc = Document(file_path)
        text = "\n".join(p.text for p in doc.paragraphs)
        return text
    elif file_ext == 'txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    else:
        return ''


def summarize_text(text):
    prompt = (
        "Summarize the following research paper in plain English. "
        "Provide the summary with sections for:\n"
        "1. Problem Statement\n2. Methodology\n3. Results\n4. Conclusion\n\n"
        f"Paper text:\n{text}"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error summarizing text: {e}"


def create_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content.splitlines():
        pdf.multi_cell(0, 10, line)
    data = pdf.output(dest='S').encode('latin-1')
    return io.BytesIO(data)


@app.route('/', methods=['GET', 'POST'])
def index():
    summary = None
    pdf_data = None
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return render_template('index.html')
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return render_template('index.html')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower()
            temp_path = os.path.join('/tmp', filename)
            file.save(temp_path)
            text = extract_text(temp_path, file_ext)
            os.remove(temp_path)
            summary = summarize_text(text)
            pdf_data = create_pdf(summary)
            return send_file(
                pdf_data,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='summary.pdf'
            )
        else:
            flash('Invalid file type')
    return render_template('index.html', summary=summary)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
