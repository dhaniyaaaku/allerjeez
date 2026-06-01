from fastapi import FastAPI

app = FastAPI(
    title="Ingredient Safety Analyser",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Ingredient Safety Analyser is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
