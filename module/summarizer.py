from transformers import pipeline

# Load the summarization pipeline once
summarizer = pipeline("summarization")  

def summarize_text(text):
    if not text.strip():
        return []

    # Approximate max tokens as half of input length
    input_length = len(text.split())
    max_len = max(10, int(input_length * 0.8))

    summary_result = summarizer(text, max_length=max_len, do_sample=False)
    summary_text = summary_result[0]['summary_text']
    sentences = [s.strip() for s in summary_text.split('.') if s.strip()]
    return sentences
