import os
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

JSON_PATH = os.path.join(DATA_DIR, "error_database.json")
EMBEDDING_PATH = os.path.join(DATA_DIR, "embeddings.npy")
IDS_PATH = os.path.join(DATA_DIR, "snippet_ids.json")

EMBEDDING_MODEL_NAME = "microsoft/codebert-base"

# Define a list of keys
GEMINI_KEYS = [
    "enter your API key here",
    "enter another API key here",
    ...
]

CONFIDENCE_THRESHOLD = 0.60
SYNTAX_THRESHOLD = 0.40

