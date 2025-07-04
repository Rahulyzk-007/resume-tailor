import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
from xhtml2pdf import pisa
import tempfile
import os

# Configure Gemini API
genai.configure(api_key="AIzaSyBGLXsZ5vcgOHAxbD9gLflGNOuWjKfgywQ")
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="Resume Tailor", layout="centered")
st.title("🎯 Resume Tailor — Harvard Format Generator")

# File uploader
resume_file = st.file_uploader("📄 Upload your Resume (PDF only)", type=["pdf"])
jd_text = st.text_area("🧾 Paste the Job Description here")

def wrap_html_in_style(content):
    return f"""
<html>
<head>
  <style>
    body {{
      font-family: Arial, sans-serif;
      font-size: 11pt;
      line-height: 1.1;
      margin: 20px;
    }}
    hr {{
      border: 1px solid #999;
      margin: 6px 0;
    }}
    h2, h3 {{
      text-transform: uppercase;
      margin-bottom: 4px;
    }}
    ul {{
      margin: 4px 0 4px 16px;
      padding: 0;
    }}
    li {{
      margin-bottom: 2px;
    }}
  </style>
</head>
<body>
{content}
</body>
</html>
"""
import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text

reference_resume_text = extract_text_from_pdf("Copy of RAHUL RESUME.pdf")


# Function to convert HTML to PDF using xhtml2pdf
def convert_html_to_pdf(html_content, output_path):
    with open(output_path, "w+b") as result_file:
        pisa_status = pisa.CreatePDF(html_content, dest=result_file)
    return pisa_status.err == 0

if st.button("🚀 Tailor Resume"):
    if not resume_file or not jd_text:
        st.warning("Please upload a resume and paste the job description.")
    else:
        # Step 1: Extract text from uploaded PDF
        with fitz.open(stream=resume_file.read(), filetype="pdf") as doc:
            resume_text = ""
            for page in doc:
                resume_text += page.get_text()

        # Step 2: Send resume text + JD to Gemini
        prompt = f"""
You are a resume rewriting expert.

Here is the ideal resume format I want you to learn and always follow. It includes the desired section order, heading styles (ALL CAPS), compact layout, minimal line spacing, and bullet point structure.

📄 Reference Resume Format:
{reference_resume_text}  ← (this is plain text extracted from your best PDF — Harvard_Tailored_Resume-5.pdf)

Now, tailor the following resume to match the job description, and rewrite it **in the exact same format and layout** as above.

📋 Resume to Tailor:
{resume_text}

📌 Job Description:
{jd_text}

➤ Return only the rewritten resume in **clean HTML**, keeping the same structure, section names, layout, bullet styles, heading formatting, and single-page structure as the reference. No explanation, no markdown, no comments.
"""
        try:
            st.info("✍️ Generating tailored resume with Gemini...")
            response = model.generate_content(prompt)
            html_resume = response.text

            # Step 3: Convert HTML to PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as pdf_file:
                html_wrapped=wrap_html_in_style(html_resume)
                success = convert_html_to_pdf(html_wrapped, pdf_file.name)
                if success:
                    st.success("✅ Resume tailored successfully!")

                    # Step 4: Download link
                    with open(pdf_file.name, "rb") as f:
                        st.download_button(
                            label="📥 Download Tailored Harvard Resume (PDF)",
                            data=f,
                            file_name="Harvard_Tailored_Resume.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.error("❌ Failed to generate PDF. HTML may contain unsupported elements.")

                os.remove(pdf_file.name)

        except Exception as e:
            st.error(f"❌ Error: {e}")