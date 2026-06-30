import streamlit as st
import os
import io
import re
import base64
from PIL import Image
from pypdf import PdfReader
import pdf2image
import google.generativeai as genai
from dotenv import load_dotenv

# Load all the environment variables from your .env file
load_dotenv()

# Configure the Google Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_gemini_response(input_prompt, pdf_content, job_description):
    """Sends the job description, the resume image, and the instructions to Gemini"""
    # Using the standard multi-modal model
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content([input_prompt, pdf_content[0], job_description])
    return response.text

def input_pdf_setup(uploaded_file):
    """Converts the uploaded PDF file into a clean JPEG image structure for Gemini"""
    if uploaded_file is not None:
        # Read the file into memory bytes
        pdf_bytes = uploaded_file.read()
        
        # Convert the first page of the PDF into a PIL Image object
        # Convert the first page of the PDF into a PIL Image object
        images = pdf2image.convert_from_bytes(pdf_bytes, poppler_path=r".\poppler-26.02.0\Library\bin")
        first_page = images[0]
        
        # Convert the PIL image into raw bytes formatted as JPEG
        img_byte_arr = io.BytesIO()
        first_page.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Structure it perfectly into the base64 format that the Google API expects
        pdf_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_byte_arr).decode()
            }
        ]
        return pdf_parts
    else:
        raise FileNotFoundError("No file uploaded")

import re

def traditional_text_parser(uploaded_file, job_description):
    """Parses raw text and computes a classic Boolean keyword match score"""
    if uploaded_file is None or job_description.strip() == "":
        return None
        
    # 1. Extract raw text from all pages
    uploaded_file.seek(0) # Reset file reader pointer
    from pypdf import PdfReader
    reader = PdfReader(uploaded_file)
    raw_text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            raw_text += page_text + "\n"
            
    # 2. Normalize text to lowercase for exact case-insensitive matches
    resume_lower = raw_text.lower()
    jd_lower = job_description.lower()
    
    # 3. Simple Traditional Dictionary Rule: Common Technical Keywords
    skills_database = ["python", "sql", "aws", "tableau", "power bi", "machine learning", "excel", "data science", "statistics"]
    
    # Filter keywords that are actually requested in the Job Description
    required_keywords = [skill for skill in skills_database if skill in jd_lower]
    
    if not required_keywords:
        return {"score": 0, "matched": [], "missing": []}
        
    # Check which of those required keywords exist in the applicant's resume text
    matched_skills = []
    missing_skills = []
    
    for skill in required_keywords:
        # Use regex word boundaries \b to ensure exact word matches (e.g., matching "Java" but not "JavaScript")
        if re.search(r'\b' + re.escape(skill) + r'\b', resume_lower):
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)
            
    # Calculate a flat mathematically driven keyword percentage match
    match_percentage = int((len(matched_skills) / len(required_keywords)) * 100) if required_keywords else 0
    
    return {
        "score": match_percentage,
        "matched": matched_skills,
        "missing": missing_skills,
        "raw_text_length": len(raw_text)
    }

# --- STREAMLIT WEB INTERFACE ---
st.set_page_config(page_title="AI ATS Resume Expert", layout="centered")
st.header("Smart Application Tracking System (ATS)")

# Field 1: The Job Description box
st.subheader("Job Description")
jd_text = st.text_area("Paste the job description here:", height=200, help="Copy and paste the full job posting details.")

# Field 2: The File Uploader
st.subheader("Resume Upload")
uploaded_file = st.file_uploader("Upload your resume in PDF format:", type=["pdf"])

if uploaded_file is not None:
    st.success("Resume uploaded successfully!")

# --- AI PROMPT TEMPLATES ---
prompt_analysis = """
You are an experienced Technical Human Resource Manager. Your task is to review the provided resume against the job description.
Please share a professional evaluation on whether the candidate's profile aligns with the role. 
Highlight the core strengths and noticeable gaps/weaknesses of the candidate relative to the requirements.
"""

prompt_match = """
You are a highly advanced Application Tracking System (ATS) scanner specializing in parsing professional technical profiles.
Your task is to evaluate the resume against the provided job description.
Please provide:
1. An overall percentage match score (e.g., 85%).
2. A list of critical keywords or skills that are missing from the resume but present in the job description.
3. A brief final summary/conclusion evaluating if the candidate should be moved forward.
"""


# Action Buttons
col1, col2, col3 = st.columns(3)

with col1:
    submit_analysis = st.button("AI HR Evaluation")

with col2:
    submit_match = st.button("AI Match Score")

with col3:
    submit_traditional = st.button("Traditional Database Scan")

st.write("---")


# --- HANDLING BUTTON CLICKS ---
if submit_analysis:
    if uploaded_file is not None and jd_text.strip() != "":
        with st.spinner("Analyzing resume structure and experience..."):
            pdf_data = input_pdf_setup(uploaded_file)
            ai_response = get_gemini_response(prompt_analysis, pdf_data, jd_text)
            st.subheader("HR Evaluation Result:")
            st.write(ai_response)
    else:
        st.error("Please provide both a Job Description and a uploaded Resume PDF.")

if submit_match:
    if uploaded_file is not None and jd_text.strip() != "":
        with st.spinner("Calculating ATS matching algorithms..."):
            pdf_data = input_pdf_setup(uploaded_file)
            ai_response = get_gemini_response(prompt_match, pdf_data, jd_text)
            st.subheader("ATS Match Analysis:")
            st.write(ai_response)
    else:
        st.error("Please provide both a Job Description and a uploaded Resume PDF.")

if submit_traditional:
    if uploaded_file is not None and jd_text.strip() != "":
        with st.spinner("Running strict keyword text parsing..."):
            results = traditional_text_parser(uploaded_file, jd_text)
            
            st.subheader("📊 Traditional ATS Search Rank Report")
            
            if results["score"] == 0 and not results["matched"] and not results["missing"]:
                 st.info("No tracked keywords from the database were found in this Job Description.")
            else:
                st.metric(label="Exact Keyword Match Score", value=f"{results['score']}%")
                
                st.write("**Keywords Successfully Parsed:**")
                if results['matched']:
                    st.success(", ".join(results['matched']))
                else:
                    st.warning("None of the required keywords were found in your CV.")
                
                st.write("**Keywords Missing (Triggers Lower Ranking):**")
                if results['missing']:
                    st.error(", ".join(results['missing']))
                else:
                    st.success("None missing! You hit every tracked keyword.")
    else:
        st.error("Please provide both a Job Description and a uploaded Resume PDF.")