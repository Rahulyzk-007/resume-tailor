import streamlit as st
import fitz
import google.generativeai as genai
import json
import subprocess
import os
import re
import jinja2
import time
import uuid

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Resume Tailor Pro", page_icon="🎯", layout="wide")

# --- API CONFIGURATION ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
except Exception as e:
    st.error("🔴 **Error:** Failed to configure Gemini API. Please ensure your `GEMINI_API_KEY` is set in your Streamlit secrets.")
    st.stop()

# --- DYNAMIC UI FUNCTION ---
def generate_step_bar_html(current_step):
    steps = ["Upload & Add Details", "Processing", "Download"]
    html = "<div class='step-bar'><div class='step-line'></div>"
    
    for i, title in enumerate(steps, 1):
        status = ""
        if i < current_step:
            status = "completed"
        elif i == current_step:
            status = "active"
        
        html += f"<div class='step {status}'>"
        if status == "completed":
            html += """<div class='step-number'><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg></div>"""
        else:
            html += f"<div class='step-number'>{i}</div>"
        html += f"<div>{title}</div></div>"
        
    html += "</div>"
    return html

# --- UI LAYOUT ---
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    .main .block-container { padding: 1rem 3rem; }
    h1 { color: #1a1a2e; text-align: center; font-size: 2.5rem; }
    h3 { color: #4a4a6a; }
    /* Step Bar CSS */
    .step-bar { display: flex; justify-content: space-between; align-items: flex-start; position: relative; margin: 2rem auto 3rem; max-width: 600px; }
    .step-line { position: absolute; top: 17px; width: calc(100% - 120px); height: 2px; background-color: #e5e7eb; z-index: 0; left: 60px; }
    .step { position: relative; z-index: 1; text-align: center; flex: 1; color: #9ca3af; font-size: 14px; font-weight: 500; }
    .step-number { width: 34px; height: 34px; border-radius: 50%; background-color: #f3f4f6; border: 2px solid #e5e7eb; color: #6b7280; font-weight: bold; margin: 0 auto 8px auto; transition: all 0.4s ease; display: flex; align-items: center; justify-content: center; }
    .step.active .step-number { background-color: #4f46e5; border-color: #4f46e5; color: white; transform: scale(1.1); }
    .step.active { color: #111827; font-weight: 600; }
    .step.completed .step-number { background-color: #22c55e; border-color: #22c55e; color: white; }
    .step.completed { color: #111827; }
    /* Widget Styling */
    .stFileUploader { border: 2px dashed #cbd5e1; background-color: #ffffff; border-radius: 8px; padding: 20px; }
    .stTextArea textarea { border: 1px solid #cbd5e1; border-radius: 8px; min-height: 300px; }
    .stButton>button {
        color: #ffffff; background: #4f46e5; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px;
        font-weight: bold; transition: all 0.3s ease-in-out; width: 100%;
    }
    .stButton>button:hover { background: #4338ca; transform: translateY(-2px); }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Resume Tailor Pro")

# Create a placeholder for the dynamic step bar
step_bar_placeholder = st.empty()
step_bar_placeholder.markdown(generate_step_bar_html(1), unsafe_allow_html=True)

# UI for inputs
col1, col2 = st.columns(2, gap="large")
with col1:
    resume_file = st.file_uploader("1. Upload Your Resume", type=["pdf"])
with col2:
    jd_text = st.text_area("2. Paste the Job Description", height=300)

# Main button
if st.button("🚀 Tailor My Resume!", use_container_width=True):
    if not resume_file or not jd_text.strip():
        st.warning("⚠️ Please upload a resume and paste the job description.")
    else:
        # --- MAIN LOGIC IS NOW INSIDE THE BUTTON CLICK ---
        step_bar_placeholder.markdown(generate_step_bar_html(2), unsafe_allow_html=True) # Update bar to "Processing"
        
        resume_text = "".join(page.get_text() for page in fitz.open(stream=resume_file.read(), filetype="pdf"))
        request_id = str(uuid.uuid4())
        
        json_prompt = f"""
    You are an expert resume writer. Your task is to analyze the provided resume and job description, then output a structured JSON object.
    # Unique Request ID (process this new request): {request_id}

    **Original Resume Content:**
    ```
    {resume_text}
    ```
    **Target Job Description:**
    ```
    {jd_text}
    ```
    **Instructions:**
    1. Extract all information **exclusively** from the "Original Resume Content" for request ID {request_id}.
    2. Rewrite the "summary" to be a concise paragraph targeting the job.
    3. Sort all "work_experience" and "projects" into "relevant" and "other" groups.
    4. **Do not discard any items.**
    5. **CRITICAL:** Do NOT use any special LaTeX characters like &, %, $, #, _, {{, }}. If you must use an ampersand, write the word "and" instead.
    6. The entire output must be a single, valid JSON object.

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
        
        filename_base = "Tailored_Resume"
        
        try:
            with st.spinner("✨ Contacting Gemini..."):
                response = model.generate_content(json_prompt)
                response_text = response.text

            with st.spinner("⚙️ Parsing AI response..."):
                start_index = response_text.find('{')
                end_index = response_text.rfind('}') + 1
                if start_index != -1 and end_index != 0:
                    json_string = response_text[start_index:end_index]
                    json_string_cleaned = json_string.strip().encode('utf-8').decode('utf-8-sig')
                    resume_data = json.loads(json_string_cleaned)
                else:
                    st.error("🔴 **Error:** Could not find a valid JSON object in the AI's response.")
                    st.code(response_text)
                    st.stop()

            with st.spinner("📝 Injecting content into template..."):
                env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'), block_start_string='\\BLOCK{', block_end_string='}', variable_start_string='\\VAR{', variable_end_string='}', comment_start_string='\\#{', comment_end_string='}', line_statement_prefix='%%', line_comment_prefix='%#', trim_blocks=True, autoescape=False)
                template = env.get_template("resume_template.tex")
                rendered_tex = template.render(resume_data)

            with st.spinner("📄 Compiling PDF..."):
                tex_output_path = f"{filename_base}.tex"
                pdf_output_path = f"{filename_base}.pdf"
                with open(tex_output_path, "w", encoding="utf-8") as f:
                    f.write(rendered_tex)
                
                pdflatex_path = "/Library/TeX/texbin/pdflatex"
                cmd = [pdflatex_path, "-interaction=nonstopmode", tex_output_path]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                subprocess.run(cmd, check=True, capture_output=True, text=True)

            step_bar_placeholder.markdown(generate_step_bar_html(3), unsafe_allow_html=True) # Update bar to "Download"
            st.success("✅ Your new resume is ready!")
            
            person_name = resume_data.get('name', 'Tailored').replace(' ', '_')
            download_filename = f"Tailored_Resume_for_{person_name}.pdf"
            
            with open(pdf_output_path, "rb") as pdf_file:
                st.download_button(
                    label="📥 Download Tailored Resume (PDF)",
                    data=pdf_file,
                    file_name=download_filename,
                    mime="application/pdf",
                    use_container_width=True
                )

        except subprocess.CalledProcessError as e:
            st.error("🔴 **Error:** LaTeX Compilation Failed.")
            st.write("The `pdflatex` command failed. Here is the log:")
            full_log = f"--- STDOUT ---\n{e.stdout}\n\n--- STDERR ---\n{e.stderr}"
            st.code(full_log, language="log")
        except Exception as e:
            st.error(f"🔴 **An Unexpected Error Occurred:** {e}")
            import traceback
            st.code(traceback.format_exc())
        finally:
            for ext in ['.tex', '.aux', '.log']:
                cleanup_path = f"{filename_base}{ext}"
                if os.path.exists(cleanup_path):
                    os.remove(cleanup_path)
