import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import json
import subprocess
import os
import re
import jinja2
import time # Import the time library

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Resume Tailor Pro",
    page_icon="🎯",
    layout="wide"
)

# --- CUSTOM STYLING (CSS) ---
# (Your custom CSS styling remains here, no changes needed)
st.markdown("""
<style>
    /* General body styling */
    .stApp {
        background-color: #f0f2f6;
    }
    .main .block-container {
        padding-top: 2rem; padding-bottom: 2rem; padding-left: 5rem; padding-right: 5rem;
    }
    h1 { color: #1a1a2e; text-align: center; }
    h3 { color: #4a4a6a; }
    .stButton>button {
        color: #ffffff; background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px;
        font-weight: bold; transition: all 0.3s ease-in-out;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3); }
    .stButton>button:active { transform: translateY(0); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2); }
    .stFileUploader { border: 2px dashed #4b6cb7; background-color: #ffffff; border-radius: 8px; padding: 20px; }
    .stTextArea textarea { border: 1px solid #ccc; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); min-height: 300px; }
</style>
""", unsafe_allow_html=True)


# --- API CONFIGURATION ---
try:
    # api_key = st.secrets["GEMINI_API_KEY"]
    api_key = "AIzaSyBGLXsZ5vcgOHAxbD9gLflGNOuWjKfgywQ"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-pro")
except Exception as e:
    st.error("🔴 **Error:** Failed to configure Gemini API. Please ensure your `GEMINI_API_KEY` is set in your Streamlit secrets.")
    st.stop()


# --- UI LAYOUT ---
st.title("🎯 Resume Tailor Pro")
st.write("")
col1, col2 = st.columns(2, gap="large")
with col1:
    st.subheader("1. Upload Your Resume")
    resume_file = st.file_uploader("Drop your resume here (PDF only)", type=["pdf"], label_visibility="collapsed")
with col2:
    st.subheader("2. Paste the Job Description")
    jd_text = st.text_area("Paste the full job description here", height=300, label_visibility="collapsed")
st.write("")
col_button1, col_button2, col_button3 = st.columns([1,1,1])
with col_button2:
    tailor_button = st.button("🚀 Tailor My Resume!", use_container_width=True)


# --- MAIN LOGIC ---
if tailor_button:
    if not resume_file or not jd_text:
        st.warning("⚠️ Please upload a resume and paste the job description.")
    else:
        with fitz.open(stream=resume_file.read(), filetype="pdf") as doc:
            resume_text = "".join(page.get_text() for page in doc)

        # --- FIX #1: CACHE BUSTING ---
        # Add a unique timestamp to the prompt to force a fresh response from the AI
        cache_buster = time.time()

        json_prompt = f"""
        You are an expert resume writer and data extractor. Your task is to analyze the provided resume and job description, then output a structured JSON object.
        # Cache Buster: {cache_buster}

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
        3.  Sort all "work_experience" and "projects" into two groups: "relevant" and "other".
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
        
        filename_base = "Tailored_Resume"
        
        try:
            with st.spinner("✨ Contacting Gemini... Crafting your new resume..."):
                response = model.generate_content(json_prompt)
                response_text = response.text

            with st.spinner("⚙️ Parsing and validating AI response..."):
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
            st.success("✅ AI content generated and parsed successfully!")

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

            with st.spinner("📄 Compiling your new PDF..."):
                tex_output_path = f"{filename_base}.tex"
                pdf_output_path = f"{filename_base}.pdf"
                with open(tex_output_path, "w", encoding="utf-8") as f:
                    f.write(rendered_tex)
                
                pdflatex_path = "pdflatex"
                cmd = [pdflatex_path, "-interaction=nonstopmode", tex_output_path]
                subprocess.run(cmd, capture_output=True, text=True)
                subprocess.run(cmd, capture_output=True, text=True)

            st.success("✅ Your new resume is ready!")

            # --- FIX #2: DYNAMIC FILENAME ---
            # Create a unique filename based on the person's name
            person_name = resume_data.get('name', 'Tailored').replace(' ', '_')
            download_filename = f"Tailored_Resume_for_{person_name}.pdf"

            with open(pdf_output_path, "rb") as pdf_file:
                st.download_button(
                    label="📥 Download Tailored Resume (PDF)",
                    data=pdf_file,
                    file_name=download_filename, # Use the new dynamic filename
                    mime="application/pdf",
                    use_container_width=True
                )

        except subprocess.CalledProcessError as e:
            st.error("🔴 **Error:** LaTeX Compilation Failed.")
            st.write("The `pdflatex` command failed. This can happen with unusual characters or formatting. Here is the log:")
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
