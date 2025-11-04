import whisper
from sentence_transformers import SentenceTransformer, util
import torch

# โหลดโมเดลครั้งเดียวตอนเริ่มระบบ
whisper_model = whisper.load_model("base")
embedder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def transcribe_audio(filepath, lang="en"):
    result = whisper_model.transcribe(filepath, fp16=False, language=lang)
    return result["text"].strip()

def compare_similarity(text1, text2, lang="en"):
    emb1 = embedder.encode(text1.lower().strip(), convert_to_tensor=True)
    emb2 = embedder.encode(text2.lower().strip(), convert_to_tensor=True)
    score = util.cos_sim(emb1, emb2).item()
    return score
