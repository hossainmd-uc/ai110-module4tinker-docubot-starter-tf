"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob
import re
from collections import Counter
from nltk.stem import PorterStemmer

_stemmer = PorterStemmer()

# Common English words filtered out of tokens so they don't drive relevance
# scoring or pollute the index.
STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "and", "or", "but", "if", "so", "of", "to", "in", "on", "at", "by",
    "for", "with", "about", "as", "into", "through", "over", "under",
    "this", "that", "these", "those", "it", "its", "i", "you", "your",
    "he", "she", "they", "them", "we", "us", "our",
    "what", "which", "who", "whom", "where", "when", "why", "how",
    "do", "does", "did", "can", "could", "should", "would", "will",
    "have", "has", "had", "not", "no", "than", "then",
})

# Minimum fraction of distinct, non-stopword query tokens that must appear
# in a document/paragraph for it to be considered relevant at all.
MIN_QUERY_COVERAGE = 0.5

class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        """
        docs_folder: directory containing project documentation files
        llm_client: optional Gemini client for LLM based answers
        """
        self.docs_folder = docs_folder
        self.llm_client = llm_client

        # Load documents into memory
        self.documents = self.load_documents()  # List of (filename, text)

        # Build a retrieval index (implemented in Phase 1)
        self.index = self.build_index(self.documents)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self):
        """
        Loads all .md and .txt files inside docs_folder.
        Returns a list of tuples: (filename, text)
        """
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")
        for path in glob.glob(pattern):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()
                filename = os.path.basename(path)
                docs.append((filename, text))
        return docs

    # -----------------------------------------------------------
    # Index Construction (Phase 1)
    # -----------------------------------------------------------

    @staticmethod
    def tokenize(text):
        """
        Lowercase and split text into alphanumeric tokens, stripping punctuation,
        dropping stopwords, then stemming each token (e.g. "endpoints" ->
        "endpoint") so matching is robust to plurals and common suffixes.
        Shared by build_index and score_document so matching is consistent.
        """
        words = re.findall(r"[a-z0-9]+", text.lower())
        return [_stemmer.stem(word) for word in words if word not in STOPWORDS]

    def build_index(self, documents):
        """
        Build a tiny inverted index mapping lowercase words to the documents
        they appear in.

        Example structure:
        {
            "token": ["AUTH.md", "API_REFERENCE.md"],
            "database": ["DATABASE.md"]
        }
        """
        index = {}
        for filename, text in documents:
            for token in set(self.tokenize(text)):
                index.setdefault(token, []).append(filename)
        return index

    # -----------------------------------------------------------
    # Scoring and Retrieval (Phase 1)
    # -----------------------------------------------------------

    def score_document(self, query, text):
        """
        Return a simple relevance score for how well the text matches the query.

        Tokenizes both query and text (stopwords already dropped by
        tokenize()), then requires at least MIN_QUERY_COVERAGE of the
        distinct query tokens to appear in text at all -- otherwise the
        document is considered irrelevant and scores 0. If coverage passes,
        the score is the summed term frequency of each query token found in
        text (repeats in the query and repeats in the text both increase
        the score).
        """
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return 0

        text_token_counts = Counter(self.tokenize(text))

        distinct_query_tokens = set(query_tokens)
        matched = sum(1 for token in distinct_query_tokens if text_token_counts[token] > 0)
        coverage = matched / len(distinct_query_tokens)
        if coverage <= MIN_QUERY_COVERAGE:
            return 0

        return sum(text_token_counts[token] for token in query_tokens)

    @staticmethod
    def chunk_document(text):
        """
        Split a document's text into paragraph-level chunks on blank lines.
        A lone markdown heading line (e.g. "## Token Generation") is glued to
        the paragraph that follows it, so headings provide context instead of
        forming their own content-less chunk.
        """
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip())]
        chunks = []
        pending_heading = None
        for block in blocks:
            if not block:
                continue
            if re.match(r"^#{1,6}\s", block) and "\n" not in block:
                pending_heading = block
                continue
            if pending_heading:
                block = f"{pending_heading}\n\n{block}"
                pending_heading = None
            chunks.append(block)
        if pending_heading:
            chunks.append(pending_heading)
        return chunks

    def retrieve(self, query, top_k=3):
        """
        Pick the single best-matching document, then split it into paragraphs
        and return the top_k highest-scoring (filename, paragraph) pairs,
        sorted by score descending. Returns [] if no document or paragraph
        matches any query terms.
        """
        doc_scores = [
            (self.score_document(query, text), filename, text)
            for filename, text in self.documents
        ]
        doc_scores = [s for s in doc_scores if s[0] > 0]
        if not doc_scores:
            return []

        _, best_filename, best_text = max(doc_scores, key=lambda s: s[0])

        chunk_scores = [
            (self.score_document(query, chunk), chunk)
            for chunk in self.chunk_document(best_text)
        ]
        chunk_scores = [c for c in chunk_scores if c[0] > 0]
        chunk_scores.sort(key=lambda c: c[0], reverse=True)
        return [(best_filename, chunk) for _, chunk in chunk_scores[:top_k]]

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=3):
        """
        Phase 1 retrieval only mode.
        Returns raw snippets and filenames with no LLM involved.
        """
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I don't have enough information to answer that."

        formatted = []
        for filename, text in snippets:
            formatted.append(f"[{filename}]\n{text}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query, top_k=3):
        """
        Phase 2 RAG mode.
        Uses student retrieval to select snippets, then asks Gemini
        to generate an answer using only those snippets.
        """
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )

        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I don't have enough information to answer that."

        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Bonus Helper: concatenated docs for naive generation mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """
        Returns all documents concatenated into a single string.
        This is used in Phase 0 for naive 'generation only' baselines.
        """
        return "\n\n".join(text for _, text in self.documents)
