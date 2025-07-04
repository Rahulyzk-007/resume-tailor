import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import markdown2
from xhtml2pdf import pisa
import tempfile
import os

# Set Gemini API Key
genai.configure(api_key="AIzaSyBGLXsZ5vcgOHAxbD9gLflGNOuWjKfgywQ")
model = genai.GenerativeModel("gemini-1.5-flash")

# Streamlit UI Setup
st.set_page_config(page_title="Resume Tailor", layout="centered")
st.title("🎯 Resume Tailor — Harvard Format Generator")

# File uploader
resume_file = st.file_uploader("📄 Upload your Resume (PDF only)", type=["pdf"])
jd_text = st.text_area("🧾 Paste the Job Description here")

# Markdown → HTML
def markdown_to_html(md_text: str) -> str:
    return markdown2.markdown(md_text, extras=["fenced-code-blocks"])

# HTML → PDF
def html_to_pdf(html_content: str, output_path: str) -> bool:
    with open(output_path, "w+b") as result_file:
        pisa_status = pisa.CreatePDF(html_content, dest=result_file)
    return pisa_status.err == 0

# Optional: Wrap HTML in style block for formatting
def wrap_html_in_style(content):
    return f"""
<html>
<head>
  <style>
    body {{
      font-family: Arial, sans-serif;
      font-size: 12pt;
      line-height: 1.3;
      margin: 30px;
    }}
    h1, h2 {{
      text-transform: uppercase;
      font-weight: bold;
      margin-bottom: 6px;
    }}
    hr {{
      border: none;
      border-top: 1px solid #ccc;
      margin: 10px 0;
    }}
    ul {{
      margin: 0 0 0 16px;
    }}
    li {{
      margin-bottom: 4px;
    }}
  </style>
</head>
<body>
{content}
</body>
</html>
"""

# Extract reference format from your best resume (optional for prompting)
def extract_text_from_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text

# Load and extract your template resume for layout reference
reference_resume_text = extract_text_from_pdf("Copy of RAHUL RESUME.pdf") if os.path.exists("Copy of RAHUL RESUME.pdf") else ""

# Main Button Logic
if st.button("🚀 Tailor Resume"):
    if not resume_file or not jd_text:
        st.warning("Please upload a resume and paste the job description.")
    else:
        # Extract resume text from uploaded file
        with fitz.open(stream=resume_file.read(), filetype="pdf") as doc:
            resume_text = ""
            for page in doc:
                resume_text += page.get_text()

        # Prompt Gemini to tailor the resume
        prompt = f"""
You are a resume tailoring expert.

Below is the reference resume layout. Use it as a structural and formatting guide. Keep sections, headings (ALL CAPS), and order the same.

Reference Format:
{reference_resume_text}

Now tailor the following resume to match the job description.

Resume:
{resume_text}

Job Description:
{jd_text}

➤ Output the tailored resume in **Markdown** format:
- Use `#` or `##` for section headings
- Use `-` for bullet points
- Use `---` to separate sections
- Keep it compact and readable

Return only the final Markdown content. No explanations.
"""

        try:
            st.info("✍️ Generating tailored resume with Gemini...")
            response = model.generate_content(prompt)
            md_resume = response.text

            # Convert Markdown → HTML
            html_body = markdown_to_html(md_resume)
            html_wrapped = wrap_html_in_style(html_body)

            # Save to PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as pdf_file:
                success = html_to_pdf(html_wrapped, pdf_file.name)
                if success:
                    st.success("✅ Resume tailored successfully!")
                    with open(pdf_file.name, "rb") as f:
                        st.download_button(
                            label="📥 Download Tailored Resume (PDF)",
                            data=f,
                            file_name="Tailored_Resume.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.error("❌ Failed to generate PDF from formatted resume.")
                os.remove(pdf_file.name)

        except Exception as e:
            st.error(f"❌ Error: {e}")