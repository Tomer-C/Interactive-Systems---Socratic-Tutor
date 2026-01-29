import json
import numpy as np
import torch
import os
from sentence_transformers import SentenceTransformer, util
from ast_analyzer import analyze_code_structure
from taxonomy import get_common_ancestor
import config


class CodeRetriever:
    def __init__(self):
        print("⚙️ Initializing Retriever (Lightweight Mode)...")

        # Load JSON
        try:
            with open(config.IDS_PATH, "r") as f:
                self.snippet_ids = json.load(f)

            with open(config.JSON_PATH, "r", encoding="utf-8") as f:
                full_data = json.load(f)
                self.snippet_map = {s['id']: s for s in full_data['snippets']}

                self.by_error_type = {}
                for s in full_data['snippets']:
                    err = s.get('error_type', 'Unknown')
                    if err not in self.by_error_type:
                        self.by_error_type[err] = []
                    self.by_error_type[err].append(s)

        except FileNotFoundError:
            print(f"⚠️ Warning: Database files not found in {config.DATA_DIR}.")
            print("   Run 'build_vector_db.py' to generate them.")
            self.snippet_ids = []
            self.snippet_map = {}
            self.by_error_type = {}

        self.model = None
        self.tensor_embeddings = None
        print("✅ Retriever Ready (Lazy Loading Enabled).")

    def _ensure_heavy_assets_loaded(self):
        """
        Checks if the heavy AI model is loaded. If not, loads it now.
        This prevents the app from crashing on startup if memory is tight.
        """
        if self.model is None:
            print(f"⏳ Loading Heavy Assets ({config.EMBEDDING_MODEL_NAME})...")
            try:
                self.model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)

                if os.path.exists(config.EMBEDDING_PATH):
                    embeddings = np.load(config.EMBEDDING_PATH)
                    self.tensor_embeddings = torch.from_numpy(embeddings)
                    print("   - Embeddings loaded.")
                else:
                    print(f"❌ Error: {config.EMBEDDING_PATH} is missing.")
            except Exception as e:
                print(f"❌ Error loading model: {e}")

    def find_similar(self, user_code, top_k=3):
        """
        Main function to find the most similar buggy code snippet from the database.
        """
        self._ensure_heavy_assets_loaded()

        if self.model is None or self.tensor_embeddings is None:
            return {
                "status": "error",
                "detected_concept": "System Error",
                "hint": "Database not initialized. Please run build_vector_db.py.",
                "top_match": None,
                "warmup_candidates": []
            }

        user_features = analyze_code_structure(user_code)
        is_syntax_error = "Syntax" in user_features

        # Convert user code to vector
        query_embedding = self.model.encode(user_code, convert_to_tensor=True)
        cos_scores = util.cos_sim(query_embedding, self.tensor_embeddings)[0]

        # We adjust the raw cosine score based on structural matches
        ranked_results = []
        for idx, score in enumerate(cos_scores):
            snippet_id = self.snippet_ids[idx]
            snippet = self.snippet_map.get(snippet_id)
            if not snippet: continue

            snippet_topic = snippet.get('topic', '')
            final_score = score.item()

            if is_syntax_error:
                if "Syntax" in snippet_topic:
                    final_score += 0.5
                else:
                    final_score -= 0.2
            elif "Loops" in snippet_topic and "Loops" not in user_features:
                final_score -= 0.6
            elif "Recursion" in snippet_topic and "Recursion" not in user_features:
                final_score -= 0.6

            ranked_results.append((final_score, snippet))

        ranked_results.sort(key=lambda x: x[0], reverse=True)

        if not ranked_results:
            return {
                "status": "low_confidence",
                "detected_concept": "General Debugging",
                "hint": "No matches found.",
                "top_match": None,
                "warmup_candidates": []
            }

        best_match = ranked_results[0]
        confidence_score = best_match[0]

        required_threshold = config.SYNTAX_THRESHOLD if is_syntax_error else config.CONFIDENCE_THRESHOLD

        if confidence_score < required_threshold:
            return {
                "status": "low_confidence",
                "detected_concept": "General Debugging",
                "hint": "Your code doesn't match our known error patterns.",
                "top_match": None,
                "warmup_candidates": []
            }

        top_snippet = best_match[1]
        error_type = top_snippet['error_type']

        candidates = self.by_error_type.get(error_type, [])
        siblings = [s for s in candidates if s['id'] != top_snippet['id']][:5]

        warmup_candidates = siblings if siblings else [top_snippet]

        return {
            "status": "success",
            "top_match": top_snippet,
            "warmup_candidates": warmup_candidates,
            "detected_concept": get_common_ancestor([error_type]),
            "confidence": round(confidence_score, 2)
        }