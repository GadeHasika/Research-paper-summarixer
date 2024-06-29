 
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import PyPDF2
import nltk
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords
import pyttsx3
import re
import io
import difflib
import fitz  # PyMuPDF

# Download NLTK resources if not already downloaded
nltk.download('punkt')
nltk.download('stopwords')

class ResearchPaperSummarizer:
    def __init__(self, win):
        self.win = win
        self.win.title("Research Paper Summarizer")
        self.win.config(bg='#E0FFFF')
        self.pdf_path = ""
        self.translator = None  # Optional: For translation
        self.engine = pyttsx3.init()  # For text-to-speech
        self.create_widgets()

    def create_widgets(self):
        self.file_frame = ttk.LabelFrame(self.win, text="Upload Research Paper", padding=(10, 10))
        self.file_frame.pack(pady=10, padx=10, fill="x")

        self.file_button = tk.Button(self.file_frame, text="Upload PDF File", bg="#4CAF50", fg='white', command=self.upload_file, font=('Arial', 10))
        self.file_button.pack(side=tk.LEFT, padx=(0, 10))

        self.file_label = tk.Label(self.file_frame, text="", font=('Arial', 10))
        self.file_label.pack(side=tk.LEFT, fill="x", expand=True)

        self.summarize_button = tk.Button(self.win, text="Summarize Paper", bg="#008CBA", fg='white', font=('Arial', 12, 'bold'), command=self.summarize_paper)
        self.summarize_button.pack(pady=10)

        # Create tab control
        self.tab_control = ttk.Notebook(self.win)
        
        # Summary tab
        self.summary_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.summary_tab, text='Summary')
        
        self.result_frame = ttk.LabelFrame(self.summary_tab, text="Summary", padding=(10, 10))
        self.result_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.result_text = tk.Text(self.result_frame, wrap=tk.WORD, height=25, width=120, font=('Arial', 10))
        self.result_text.pack(pady=10, padx=10, fill="both", expand=True)

        self.voice_button = tk.Button(self.summary_tab, text="Read Aloud", bg="#f44336", fg='white', font=('Arial', 12, 'bold'), command=self.read_aloud)
        self.voice_button.pack(pady=10)

        # Images tab
        self.images_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.images_tab, text='Images')
        
        # Canvas for displaying images with scrollbars
        self.image_canvas = tk.Canvas(self.images_tab, bg='white')
        self.image_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.v_scrollbar = tk.Scrollbar(self.images_tab, orient=tk.VERTICAL, command=self.image_canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.image_canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.h_scrollbar = tk.Scrollbar(self.images_tab, orient=tk.HORIZONTAL, command=self.image_canvas.xview)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.image_canvas.configure(xscrollcommand=self.h_scrollbar.set)

        self.image_frame = tk.Frame(self.image_canvas, bg='white')
        self.image_canvas.create_window((0, 0), window=self.image_frame, anchor=tk.NW)

        # Plagiarism tab
        self.plagiarism_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.plagiarism_tab, text='Plagiarism Check')
        
        self.plagiarism_frame = ttk.LabelFrame(self.plagiarism_tab, text="Plagiarism Check", padding=(10, 10))
        self.plagiarism_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.plagiarism_text = tk.Text(self.plagiarism_frame, wrap=tk.WORD, height=25, width=120, font=('Arial', 10))
        self.plagiarism_text.pack(pady=10, padx=10, fill="both", expand=True)

        self.tab_control.pack(expand=1, fill="both")

    def upload_file(self):
        self.pdf_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if self.pdf_path:
            self.file_label.config(text=f"File selected: {self.pdf_path}")

    def summarize_paper(self):
        if not self.pdf_path:
            messagebox.showerror("Error", "Upload a PDF file.")
            return
        
        try:
            file_text = self.get_text_from_pdf(self.pdf_path)
            summarized_text = self.create_summary(file_text)
    
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, summarized_text)

            keywords = self.get_main_keywords(summarized_text, 10)
            print("Main Keywords:", keywords)

            for keyword in keywords:
                for match in re.finditer(r'\b' + re.escape(keyword) + r'\b', summarized_text, re.IGNORECASE):
                    start, end = match.span()
                    start_idx = f"1.0 + {start} chars"
                    end_idx = f"1.0 + {end} chars"
                    self.result_text.tag_add("highlight", start_idx, end_idx)
            
            self.result_text.tag_config("highlight", background="yellow", foreground="black")

            self.extract_images_from_pdf(self.pdf_path)

            # Perform plagiarism check
            reference_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
            similarity_ratio = self.check_plagiarism(summarized_text, reference_text)
            self.display_plagiarism_result(similarity_ratio)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_text_from_pdf(self, pdf_path):
        pdf_reader = PyPDF2.PdfReader(pdf_path)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        return text

    def create_summary(self, text):
        sentences = sent_tokenize(text)
        
        # Remove stopwords
        stop_words = set(stopwords.words('english'))
        
        # Calculate TF-IDF scores for each sentence
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(sentences)
        tfidf_scores = tfidf_matrix.toarray()

        # Calculate sentence scores and rank sentences
        sentence_scores = [(i, sentence, sum(tfidf_scores[i])) for i, sentence in enumerate(sentences)]
        sentence_scores.sort(key=lambda x: x[2], reverse=True)

        # Select top sentences to create the summary
        summary_size_in_sentences = min(5, len(sentences))  # Summarize to 5 sentences if possible
        selected_sentences = sentence_scores[:summary_size_in_sentences]

        # Extract only the sentences from selected_sentences
        selected_sentences = [sentence for _, sentence, _ in selected_sentences]

        # Join selected sentences to form the summarized text
        summarized_text = '\n'.join(selected_sentences)

        return summarized_text

    def get_main_keywords(self, text, n_keywords=5):
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        tfidf_scores = tfidf_matrix.toarray().flatten()
        
        top_indices = tfidf_scores.argsort()[-n_keywords:][::-1]
        keywords = [feature_names[i] for i in top_indices]
        
        return keywords

    def read_aloud(self):
        text = self.result_text.get(1.0, tk.END)
        self.engine.say(text)
        self.engine.runAndWait()

    def extract_images_from_pdf(self, pdf_path):
        doc = fitz.open(pdf_path)
        self.clear_image_frame()  # Clear previously displayed images

        for i in range(len(doc)):
            page = doc.load_page(i)
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                image = Image.open(io.BytesIO(image_bytes))
                photo = ImageTk.PhotoImage(image)

                image_label = tk.Label(self.image_frame, image=photo, bg='white')
                image_label.image = photo
                image_label.pack(pady=10)

                self.image_frame.update_idletasks()
                self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))

    def clear_image_frame(self):
        for widget in self.image_frame.winfo_children():
            widget.destroy()

    def check_plagiarism(self, text1, text2):
        # Using SequenceMatcher to compare similarity
        similarity_ratio = difflib.SequenceMatcher(None, text1, text2).ratio()
        return similarity_ratio 
    def display_plagiarism_result(self, similarity_ratio):
        self.plagiarism_text.delete(1.0, tk.END)
        self.plagiarism_text.insert(tk.END, f"Similarity Ratio with reference text: {similarity_ratio:.2%}")

def main():
    win = tk.Tk() 
    app = ResearchPaperSummarizer(win)
    win.mainloop()

if __name__ == "__main__":
    main()
