# Research: The Impact of Retrieval-Augmented Generation on LLM Accuracy

Retrieval-Augmented Generation (RAG) is a technique that enhances large language model responses by incorporating external knowledge retrieval steps before generation. Rather than relying solely on parametric knowledge encoded during training, RAG systems query a document corpus at inference time and inject relevant passages into the LLM context window.

## Key Findings

A 2024 study by Lewis et al. demonstrated that RAG reduces hallucination rates by up to 43% on factual question-answering benchmarks. The improvement was most pronounced for questions about events that occurred after the model's training cutoff date.

RAG systems face several challenges: latency overhead from retrieval, context window limitations when injecting long documents, and the risk of retrieving irrelevant passages that distract the model. Chunking strategies—how documents are split into retrievable segments—significantly affect retrieval quality.

Vector similarity search using embeddings is the dominant retrieval method. However, hybrid approaches combining keyword matching (BM25) with dense vector search have shown 15-20% improvements in recall on technical document collections.
