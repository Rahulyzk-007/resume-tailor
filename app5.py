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

# --- CUSTOM STYLING (CSS) ---
st.markdown("""
<style>
    /* --- BASE STYLES (Light Theme) --- */
    .stApp {
        background-color: #f0f2f6;
    }
    .main .block-container {
        padding-top: 2rem; padding-bottom: 2rem; padding-left: 5rem; padding-right: 5rem;
    }
    h1 {
        color: #1a1a2e;
        text-align: center;
    }
    h3 {
        color: #4a4a6a;
    }
    .stButton>button {
        color: #ffffff;
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 16px;
        font-weight: bold;
        transition: all 0.3s ease-in-out;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }
    .stFileUploader {
        border: 2px dashed #4b6cb7;
        background-color: #ffffff;
        border-radius: 8px;
        padding: 20px;
    }
    .stTextArea textarea {
        border: 1px solid #ccc;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        min-height: 300px;
        background-color: #ffffff;
        color: #000000;
    }

    /* --- DARK THEME STYLES --- */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background-color: #0e1117; /* Streamlit's default dark background */
        }
        h1 {
            color: #ffffff;
        }
        h3 {
            color: #e1e1e1;
        }
        .stFileUploader {
            border-color: #5a5a77;
            background-color: #1c1c2e;
        }
        /* Style for text inside file uploader */
        .stFileUploader label {
            color: #e1e1e1;
        }
        .stTextArea textarea {
            background-color: #0e1117;
            color: #ffffff;
            border-color: #5a5a77;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- API CONFIGURATION ---
try:
    api_key = "AIzaSyBGLXsZ5vcgOHAxbD9gLflGNOuWjKfgywQ"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-pro")
except Exception as e:
    st.error("🔴 **Error:** Failed to configure Gemini API. Please ensure your `GEMINI_API_KEY` is set in your Streamlit secrets.")
    st.stop()

# --- SESSION STATE INITIALIZATION ---
# This robustly manages the app's state between user interactions.
if "stage" not in st.session_state:
    st.session_state.stage = "START"

def set_stage(stage_name):
    st.session_state.stage = stage_name

# --- UI LAYOUT ---
st.title("🎯 Resume Tailor Pro")
st.write("")

# The "Start Over" button gives users a way to clear the state.
if st.button("Start Over / Clear"):
    set_stage("START")
    # This clears the file uploader widget
    st.rerun()

col1, col2 = st.columns(2, gap="large")
with col1:
    st.subheader("1. Upload Your Resume")
    resume_file = st.file_uploader("Drop your resume here", type=["pdf"], label_visibility="collapsed")
with col2:
    st.subheader("2. Paste the Job Description")
    jd_text = st.text_area("Paste the full job description", height=300, label_visibility="collapsed")
st.write("")

col_button1, col_button2, col_button3 = st.columns([1,1,1])
with col_button2:
    if st.button("🚀 Tailor My Resume!", use_container_width=True):
        if not resume_file or not jd_text:
            st.warning("⚠️ Please upload a resume and paste the job description.")
        else:
            set_stage("PROCESS")

# --- MAIN LOGIC ---
if st.session_state.stage == "PROCESS":
    with st.spinner("Reading resume..."):
        resume_text = "".join(page.get_text() for page in fitz.open(stream=resume_file.read(), filetype="pdf"))


    # --- NEW DEBUG SECTION ---
        # This will show you exactly what text is being sent to the AI.
        with st.expander("👀 Click to verify the resume text being processed"):
            st.info("The text below was extracted from your uploaded PDF. If this is not the correct content, it confirms a server caching issue.")
            st.text_area("Extracted Text:", resume_text, height=200, disabled=True)
        # --- END DEBUG SECTION ---

    
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
        st.success("✅ AI content generated and parsed!")

        with st.spinner("📝 Injecting content into template..."):
            env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'), block_start_string='\\BLOCK{', block_end_string='}', variable_start_string='\\VAR{', variable_end_string='}', comment_start_string='\\#{', comment_end_string='}', line_statement_prefix='%%', line_comment_prefix='%#', trim_blocks=True, autoescape=False)
            template = env.get_template("resume_template.tex")
            rendered_tex = template.render(resume_data)

        with st.spinner("📄 Compiling PDF..."):
            tex_output_path = f"{filename_base}.tex"
            pdf_output_path = f"{filename_base}.pdf"
            with open(tex_output_path, "w", encoding="utf-8") as f:
                f.write(rendered_tex)
            
            pdflatex_path = "pdflatex"
            cmd = [pdflatex_path, "-interaction=nonstopmode", tex_output_path]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            subprocess.run(cmd, check=True, capture_output=True, text=True)

        st.success("✅ Your new resume is ready!")
        person_name = resume_data.get('name', 'Tailored').replace(' ', '_')
        download_filename = f"Tailored_Resume_for_{person_name}.pdf"
        with open(pdf_output_path, "rb") as pdf_file:
            st.download_button(label="📥 Download Tailored Resume (PDF)", data=pdf_file, file_name=download_filename, mime="application/pdf", use_container_width=True)

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
        set_stage("START") # Reset the stage after processing
        for ext in ['.tex', '.aux', '.log']:
            cleanup_path = f"{filename_base}{ext}"
            if os.path.exists(cleanup_path):
                os.remove(cleanup_path)

