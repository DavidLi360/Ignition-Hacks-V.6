from transformers import pipeline
import docx
import nltk
from nltk.tokenize import sent_tokenize

# Load the summarization pipeline once
summarizer = pipeline("summarization")  

def summarize_text(text):
    if not text.strip():
        return []

    # Approximate max tokens as half of input length
    input_length = len(text.split())
    max_len = max(10, int(input_length * 0.8)) # 80% of the text
    min_len = max(10, int(input_length * 0.4)) # 80% of the text

    summary_result = summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)
    summary_text = summary_result[0]['summary_text']
    sentences = [s.strip() for s in summary_text.split('.') if s.strip()]
    return sentences

# returns a list of sentences
def docx_to_sentences(file_path):
    """
    Reads a DOCX file and returns a list of sentences.
    """
    # Load the DOCX file
    doc = docx.Document(file_path)
    
    # Extract all text from paragraphs
    full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    
    # Split into sentences using NLTK
    sentences = sent_tokenize(full_text)
    
    return sentences