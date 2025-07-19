import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import json
import subprocess
import os
import re
import jinja2

# --- CONFIGURATION ---
# Load API key from secrets
try:
    api_key = "AIzaSyBGLXsZ5vcgOHAxbD9gLflGNOuWjKfgywQ"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-pro")
except Exception as e:
    st.error(f"Failed to configure Gemini API. Please check your secrets.toml file. Error: {e}")
    st.stop()


st.set_page_config(page_title="Resume Tailor Pro", layout="centered")
st.title("🎯 Resume Tailor Pro")
st.write("This tool tailors your resume to a job description, reordering content for relevance and generating a professional PDF.")

# --- UI ELEMENTS ---
resume_file = st.file_uploader("📄 Upload your current Resume (PDF only)", type=["pdf"])
jd_text = st.text_area("🧾 Paste the Job Description here", height=250)


# --- MAIN LOGIC ---
if st.button("🚀 Tailor Resume"):
    if not resume_file or not jd_text:
        st.warning("Please upload a resume and paste the job description.")
    else:
        with fitz.open(stream=resume_file.read(), filetype="pdf") as doc:
            resume_text = "".join(page.get_text() for page in doc)

        # 2. Define the new prompt that asks for reordering instead of removal

        json_prompt = f"""
        You are an expert resume writer and data extractor. Your task is to analyze the provided resume and job description, then output a structured JSON object.

        **Original Resume Content:**
        ```
        {resume_text}
        ```

        **Target Job Description:**
        ```
        {jd_text}
        ```

        **Instructions:**
        1.  Extract all information **exclusively** from the "Original Resume Content" provided above.
        2.  Rewrite the "summary" to be a concise, 2-3 sentence paragraph targeting the job.
        3.  Sort all "work_experience" and "projects" into two groups: "relevant" (matches the job description) and "other" (less relevant).
        4.  **Do not discard any items.**
        5.  **IMPORTANT:** All string values in the JSON must be plain text. Do NOT use any Markdown formatting.
        6.  The entire output must be a single, valid JSON object, following the structure in the example below.

        ```json
        {{
        "name": "Full Name from Resume",
        "phone": "Phone Number from Resume",
        "email": "Email Address from Resume",
        "linkedin_url": "LinkedIn URL from Resume",
        "github_url": "GitHub URL from Resume",
        "summary": "A tailored professional summary based on the resume and job description...",
        "education": {{
            "university": "University Name from Resume",
            "duration": "Dates from Resume",
            "degree": "Degree Name from Resume",
            "gpa": "GPA from Resume"
        }},
        "work_experience": {{
            "relevant": [
            {{
                "role": "Relevant Job Role",
                "company": "Company Name",
                "duration": "Dates",
                "points": ["Description of a relevant achievement...", "Another relevant achievement..."]
            }}
            ],
            "other": [
            {{
                "role": "Other Job Role",
                "company": "Company Name",
                "duration": "Dates",
                "points": ["Description of another achievement...", "And another..."]
            }}
            ]
        }},
        "projects": {{
            "relevant": [
            {{
                "name": "Relevant Project Name",
                "technologies": "Technologies Used",
                "description": ["Description of the relevant project..."]
            }}
            ],
            "other": [
            {{
                "name": "Other Project Name",
                "technologies": "Technologies Used",
                "description": ["Description of the other project..."]
            }}
            ]
        }},
        "skills": {{
            "Category 1": "List of skills...",
            "Category 2": "List of skills..."
        }},
        "achievements": [
            "Achievement from resume...",
            "Another achievement from resume..."
        ]
        }}
        ```
        """
        
        filename_base = "Tailored_Resume_Pro"
        
        try:
            with st.spinner("🚀 Contacting Gemini for tailored content..."):
                response = model.generate_content(json_prompt)
                response_text = response.text

            with st.spinner("📝 Parsing and validating AI response..."):
                start_index = response_text.find('{')
                end_index = response_text.rfind('}') + 1
                if start_index != -1 and end_index != 0:
                    json_string = response_text[start_index:end_index]
                    json_string_cleaned = json_string.strip().encode('utf-8').decode('utf-8-sig')
                    resume_data = json.loads(json_string_cleaned)
                else:
                    st.error("Fatal Error: Could not find a JSON object in the AI's response.")
                    st.code(response_text)
                    st.stop()
            # st.success("✅ JSON Parsed Successfully!")

            with st.spinner("📝 Injecting content into LaTeX template..."):
                env = jinja2.Environment(
                    loader=jinja2.FileSystemLoader('.'),
                    block_start_string='\\BLOCK{', block_end_string='}',
                    variable_start_string='\\VAR{', variable_end_string='}',
                    comment_start_string='\\#{', comment_end_string='}',
                    line_statement_prefix='%%', line_comment_prefix='%#',
                    trim_blocks=True, autoescape=False
                )
                template = env.get_template("resume_template.tex")
                rendered_tex = template.render(resume_data)

            with st.spinner("📄 Compiling PDF locally with LaTeX..."):
                tex_output_path = f"{filename_base}.tex"
                pdf_output_path = f"{filename_base}.pdf"
                with open(tex_output_path, "w", encoding="utf-8") as f:
                    f.write(rendered_tex)
                
                pdflatex_path = "pdflatex"
                cmd = [pdflatex_path, "-interaction=nonstopmode", tex_output_path]
                subprocess.run(cmd, capture_output=True, text=True)
                subprocess.run(cmd, capture_output=True, text=True)

            st.success("✅ Resume tailored and compiled successfully!")
            with open(pdf_output_path, "rb") as pdf_file:
                st.download_button(
                    label="📥 Download Tailored Resume (PDF)",
                    data=pdf_file,
                    file_name="Tailored_Resume_Pro.pdf",
                    mime="application/pdf"
                )

        except subprocess.CalledProcessError as e:
            st.error("❌ LaTeX Compilation Failed.")
            st.write("The `pdflatex` command failed. Below is the full output from the compiler:")
            full_log = f"--- STDOUT ---\n{e.stdout}\n\n--- STDERR ---\n{e.stderr}"
            st.code(full_log, language="log")
        except Exception as e:
            st.error(f"❌ An Unexpected Error Occurred: {e}")
            import traceback
            st.code(traceback.format_exc())
        finally:
            for ext in ['.tex', '.aux', '.log']:
                cleanup_path = f"{filename_base}{ext}"
                if os.path.exists(cleanup_path):
                    os.remove(cleanup_path)