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
    "AIzaSyDfEOjC1u7SSAD7snGfvsxkMrq00p9yTlI",
    "AIzaSyDLWxkzz1iGuTKUbm79tZBxb8WvZ0Z44pc",
    "AIzaSyBIQtkVYEh-17j-4QjNjn_QR--r6jMXfxg",
    "AIzaSyBM9HMxr3hMxjFpXGQiIi9T4Mz2DwAwkk0",
    "AIzaSyCf6_dNwM6N0s85Q-Pb_t8WBii00cP8bxY"
]

CONFIDENCE_THRESHOLD = 0.60
SYNTAX_THRESHOLD = 0.40
