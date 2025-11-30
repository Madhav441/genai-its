from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

class LocalHuggingFaceEmbeddings(HuggingFaceEmbeddings):
    def __init__(self):
        super().__init__(
            model_name="mixedbread-ai/mxbai-embed-large-v1",
            cache_folder="models/mxbai"
        )

def load_and_embed_pdf(pdf_path):
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    print(f"📄 Loaded {len(docs)} pages")

    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)
    chunks = splitter.split_documents(docs)
    print(f"✂️ Created {len(chunks)} text chunks")

    embeddings = LocalHuggingFaceEmbeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("data/vectorstore/")
    print("✅ Vectorstore saved at data/vectorstore/")