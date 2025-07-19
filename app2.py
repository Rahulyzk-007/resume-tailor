import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import json
import subprocess
import os
import re
from jinja2 import Environment, FileSystemLoader
import requests
import jinja2

# --- CONFIGURATION ---
genai.configure(api_key="AIzaSyBGLXsZ5vcgOHAxbD9gLflGNOuWjKfgywQ") # IMPORTANT: Replace with your actual API key
model = genai.GenerativeModel("gemini-2.5-flash")

st.set_page_config(page_title="Resume Tailor", layout="centered")
st.title("🎯 LaTeX Resume Tailor")
st.write("This tool tailors your resume to a job description and generates a professional, single-page PDF using a LaTeX template.")

# --- UI ELEMENTS ---
resume_file = st.file_uploader("📄 Upload your current Resume (PDF only)", type=["pdf"])
jd_text = st.text_area("🧾 Paste the Job Description here", height=250)


# --- MAIN LOGIC ---
if st.button("🚀 Tailor Resume with LaTeX"):
    if not resume_file or not jd_text:
        st.warning("Please upload a resume and paste the job description.")
    else:
        # 1. Extract text from the uploaded resume PDF
        with fitz.open(stream=resume_file.read(), filetype="pdf") as doc:
            resume_text = ""
            for page in doc:
                resume_text += page.get_text()

        # 2. Define the new prompt that asks for a JSON output
        json_prompt = f"""
        You are an expert resume writer and data extractor. Your task is to tailor the provided resume for the given job description and output the result as a structured JSON object.

        Prioritize the most relevant experience and skills from the original resume. If the job requires a skill not listed, you may add it if it's a logical extension of the candidate's experience. Re-write bullet points to be more impactful for the target role.

        **Original Resume Content:**
        ```
        {resume_text}
        ```

        **Target Job Description:**
        ```
        {jd_text}
        ```

        **Instructions:**
        Analyze the resume and job description. Populate the following JSON structure with the tailored content.
        - The "name" should be in title case (e.g., "Rahul Asam").
        - The "summary" should be a concise, 2-3 sentence paragraph targeting the job.
        - In "work_experience", list jobs with the most relevant one first.
        - In "projects", select the top 2-3 most relevant projects.
        - **IMPORTANT: All string values in the JSON must be plain text. Do NOT use any Markdown formatting (e.g., for links, use "https://linkedin.com/in/user" directly, NOT "[LinkedIn](https://...)").**
        - The entire output must be a single, valid JSON object and nothing else.
        - Return only a clean, stringified JSON object — no markdown, no explanation, no text before or after.
        Ensure:
        1. All keys have values.
        2. No trailing commas in objects or arrays.
        3. No markdown symbols like ```json.

        ```json
        {{
          "name": "Rahul Asam",
          "phone": "(+91) 9701597895",
          "email": "rahulasam007@gmail.com",
          "linkedin_url": "[linkedin.com/in/asam-rahul](https://linkedin.com/in/asam-rahul)",
          "github_url": "[github.com/Rahulyzk-007](https://github.com/Rahulyzk-007)",
          "summary": "A highly analytical and results-driven Computer Science student with a strong foundation in data structures, algorithms, and machine learning. Proven ability to translate data into actionable insights and eager to leverage these skills in an entry-level Data Scientist position.",
          "education": {{
            "university": "Osmania University",
            "duration": "Nov 2021 – May 2025",
            "degree": "Bachelor of Engineering in Computer Science",
            "gpa": "9.15/10.0"
          }},
          "work_experience": [
            {{
              "role": "Data Science Intern",
              "company": "Solix Technologies",
              "duration": "May 2024 – July 2024",
              "points": [
                "Developed a hybrid CNN+BILSTM architecture for accurate handwritten text recognition, achieving high accuracy in classifying handwritten and digital content.",
                "Built a user-friendly Streamlit web application for real-time document processing, enabling automated extraction and classification of unstructured documents.",
                "Managed data preprocessing, model training, testing, and debugging to ensure system reliability and performance."
              ]
            }},
            {{
              "role": "Research and Development Intern",
              "company": "Tejas Networks",
              "duration": "Jan 2025 – Present",
              "points": [
                "Developed and automated comprehensive test suites in Python for advanced switching features (802.1ad, ACL, STP), ensuring protocol compliance and system stability.",
                "Identified critical defects through deep debugging, regression, and stress testing, significantly improving feature reliability."
              ]
            }}
          ],
          "projects": [
            {{
                "name": "X-rays Detection Model",
                "technologies": "Python, TensorFlow, CNNs, VGG16, ResNet, Streamlit",
                "description": [
                    "Developed a convolutional neural network (CNN) model achieving over 90% accuracy in predicting diseases from X-ray images.",
                    "Created a user-friendly interface for easy interaction with the model's results."
                ]
            }},
            {{
                "name": "Social Media Account Legitimacy Check",
                "technologies": "Python, TensorFlow, ANN, Pandas",
                "description": [
                    "Built a machine learning model to identify fake social media accounts with high accuracy by analyzing username credentials."
                ]
            }}
          ],
          "skills": {{
            "Languages": "Python, Java, SQL (MySQL, PostgreSQL), JavaScript, HTML, CSS",
            "Libraries": "TensorFlow, Keras, Pandas, NumPy, Scikit-learn, Matplotlib, Seaborn",
            "Tools": "Git, Google Cloud Platform, VS Code, Jupyter Notebook",
            "Machine_Learning": "Classification, Regression, CNN, ANN, LSTM, Computer Vision"
          }},
          "achievements": [
            "Secured a full merit-based scholarship for outstanding academic excellence.",
            "Consistently ranked among the top 3% of students at Osmania University."
          ]
        }}
        ```
        """
        # Define the base filename before the try block starts
        filename_base = "Tailored_Resume_for_You"

        try:
            # This block for Gemini and Jinja remains the same
            with st.spinner("🚀 Contacting Gemini..."):
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

            st.success("✅ JSON Parsed Successfully!")

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

            # THIS IS THE NEW/FINAL PDF COMPILATION BLOCK
            with st.spinner("📄 Compiling PDF locally with LaTeX..."):
                tex_output_path = f"{filename_base}.tex"
                pdf_output_path = f"{filename_base}.pdf"

                # Write the final LaTeX content to a .tex file
                with open(tex_output_path, "w", encoding="utf-8") as f:
                    f.write(rendered_tex)
                

                # Paste the full path you copied from your terminal here
                pdflatex_path = "/Library/TeX/texbin/pdflatex" 

                cmd = [pdflatex_path, "-interaction=nonstopmode", tex_output_path]
                subprocess.run(cmd, capture_output=True, text=True)
                subprocess.run(cmd, capture_output=True, text=True)

            st.success("✅ Resume tailored and compiled successfully!")
            with open(pdf_output_path, "rb") as pdf_file:
                st.download_button(
                    label="📥 Download Tailored Resume (PDF)",
                    data=pdf_file,
                    file_name="Tailored_Resume.pdf",
                    mime="application/pdf"
                )

        except subprocess.CalledProcessError as e:
            st.error("❌ LaTeX Compilation Failed.")
            st.write("The `pdflatex` command failed. Below is the full output from the compiler, which should contain the error details.")
            
            # Create a full log by combining both stdout and stderr
            full_log = f"--- STANDARD OUTPUT ---\n{e.stdout}\n\n--- STANDARD ERROR ---\n{e.stderr}"
            
            # Display the full, combined log
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