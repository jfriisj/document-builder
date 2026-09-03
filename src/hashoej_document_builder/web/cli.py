import uvicorn


def main() -> None:
    uvicorn.run("hashoej_document_builder.web.app:app", host="127.0.0.1", port=8000, reload=True)
