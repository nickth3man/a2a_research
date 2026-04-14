# Claim Verification Methodologies for AI Systems

Claim verification is the process of assessing whether a statement is supported by evidence. In AI systems, this typically involves three stages: claim decomposition, evidence retrieval, and verdict assignment.

## Decomposition

Complex claims are broken into atomic verifiable units. For example, "RAG reduces hallucinations by 43% and was invented by Facebook in 2020" decomposes into:
1. RAG reduces hallucinations
2. The reduction rate is 43%
3. RAG was invented by Facebook
4. The invention year was 2020

Each sub-claim can be verified independently against the evidence corpus.

## Evidence Retrieval

For each atomic claim, the system retrieves potentially relevant documents using semantic search. The retrieval step should optimize for recall rather than precision—missing a critical document is worse than retrieving an irrelevant one.

## Verdict Assignment

Verdicts typically use a three-class schema: SUPPORTED, REFUTED, or INSUFFICIENT_EVIDENCE. Some systems add a CONFIDENCE score (0.0-1.0) to each verdict. The confidence calibration problem—ensuring that a 0.8 confidence verdict is correct 80% of the time—remains an open research challenge.

## Multi-Agent Verification

Using separate agents for decomposition, retrieval, and verdict assignment provides natural error isolation. If the decomposition agent produces poor sub-claims, this can be detected and corrected before propagating to downstream agents.
