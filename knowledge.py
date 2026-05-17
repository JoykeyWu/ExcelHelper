"""RAG module: build vector store from knowledge_base/*.md and retrieve relevant context."""
import os
from pathlib import Path

# Use HF mirror for users in regions where huggingface.co is blocked
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).parent
KB_DIR = BASE_DIR / "knowledge_base"
CHROMA_DIR = BASE_DIR / "chroma_db"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _load_documents() -> list:
    """Load all markdown files from knowledge_base/."""
    loader = DirectoryLoader(
        str(KB_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    return loader.load()


def _split_documents(docs: list) -> list:
    """Split documents into chunks for embedding."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n## ", "\n### ", "\n# ", "\n", " "],
    )
    return splitter.split_documents(docs)


def build_vectorstore(force: bool = False) -> Chroma:
    """Build (or load) the Chroma vector store from knowledge base docs."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    if force or not _store_exists():
        docs = _load_documents()
        chunks = _split_documents(docs)
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=str(CHROMA_DIR),
        )
        print(f"[RAG] 向量库已构建: {len(chunks)} 个文本块, 来自 {len(docs)} 个文档")
        return vectorstore

    return _load_vectorstore()


def _store_exists() -> bool:
    """Check if a persisted Chroma store already exists."""
    col_path = CHROMA_DIR / "chroma.sqlite3"
    return col_path.exists()


def _load_vectorstore() -> Chroma:
    """Load an existing Chroma vector store."""
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
    )


def get_retriever(k: int = 4):
    """Get a LangChain retriever for the knowledge base.

    If the vector store doesn't exist yet, it will be built first.
    """
    vectorstore = build_vectorstore(force=False)
    return vectorstore.as_retriever(search_kwargs={"k": k})


def retrieve_context(query: str, k: int = 4) -> str:
    """Retrieve relevant business context for a user query.

    Returns formatted string of relevant document chunks, or empty string.
    """
    try:
        retriever = get_retriever(k=k)
        docs = retriever.invoke(query)
        if not docs:
            return ""
        lines = []
        for i, doc in enumerate(docs, 1):
            src = Path(doc.metadata.get("source", "")).name
            lines.append(f"【相关知识 {i}】(来源: {src})\n{doc.page_content}")
        return "\n\n".join(lines)
    except Exception as e:
        print(f"[RAG] 检索失败: {e}")
        return ""
