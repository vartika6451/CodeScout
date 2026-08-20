from langchain_text_splitters import RecursiveCharacterTextSplitter


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)


def chunk_code(path: str, content: str):
    chunks = text_splitter.split_text(content)

    return [
        {
            "file_path": path,
            "content": chunk,
            "chunk_index": index,
        }
        for index, chunk in enumerate(chunks)
    ]