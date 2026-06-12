"""A small synthetic Zotero library so the app is fully usable with no keys.

Loaded via the "Load demo library" button or `?source=demo`. The papers
are invented but plausible, spread across overlapping research areas so
the cross-project connection finder has something to chew on.
"""
from __future__ import annotations


def _item(key, title, creators, year, abstract, publication, tags, item_type="journalArticle"):
    return {
        "key": key,
        "title": title,
        "creators": creators,
        "year": year,
        "item_type": item_type,
        "abstract": abstract,
        "doi": "",
        "url": "",
        "publication": publication,
        "tags": tags,
    }


_PROJECTS = {
    "DEMOGRAPH": {
        "name": "Graph Neural Networks",
        "short_name": "Graph Neural Networks",
        "items": [
            _item("G1", "Message Passing Schemes for Molecular Property Prediction",
                  "Okafor et al.", "2021",
                  "We benchmark message-passing graph neural networks on molecular property "
                  "prediction, showing that edge-conditioned aggregation improves generalization "
                  "to unseen scaffolds.",
                  "Journal of Chemical ML", ["GNN", "molecules", "message passing"]),
            _item("G2", "Over-smoothing in Deep Graph Convolutional Networks",
                  "Liang, Park", "2020",
                  "A theoretical analysis of why node representations converge as graph "
                  "convolution depth increases, with residual remedies.",
                  "Proc. ICLR", ["GNN", "over-smoothing", "theory"]),
            _item("G3", "Attention over Graphs: A Unifying View",
                  "Reyes et al.", "2022",
                  "We unify graph attention variants and relate them to transformer "
                  "self-attention, clarifying when attention helps on sparse graphs.",
                  "TMLR", ["GNN", "attention", "transformers"]),
            _item("G4", "Scalable Subgraph Sampling for Industrial Recommenders",
                  "Nakamura, Vidal", "2023",
                  "A neighbor-sampling strategy that lets graph networks train on "
                  "billion-edge recommendation graphs within a fixed memory budget.",
                  "Proc. KDD", ["GNN", "sampling", "recommenders", "scalability"]),
        ],
    },
    "DEMOFAIR": {
        "name": "Fairness in ML",
        "short_name": "Fairness in ML",
        "items": [
            _item("F1", "Calibration and Equalized Odds Cannot Always Coexist",
                  "Adeyemi, Strand", "2019",
                  "An impossibility result showing tension between calibration and equalized "
                  "odds across groups except in degenerate cases.",
                  "Proc. FAccT", ["fairness", "calibration", "impossibility"]),
            _item("F2", "Auditing Recommender Systems for Demographic Skew",
                  "Nakamura, Vidal", "2022",
                  "A practical audit framework that measures exposure disparities in deployed "
                  "recommender systems and traces them to feedback loops.",
                  "Proc. FAccT", ["fairness", "recommenders", "auditing"]),
            _item("F3", "Counterfactual Fairness with Latent Confounders",
                  "Reyes, Okafor", "2021",
                  "We extend counterfactual fairness to settings with unobserved confounding "
                  "using a graph-structured causal model.",
                  "Proc. NeurIPS", ["fairness", "causal", "counterfactual", "graphs"]),
        ],
    },
    "DEMOCAUSAL": {
        "name": "Causal Inference",
        "short_name": "Causal Inference",
        "items": [
            _item("C1", "Doubly Robust Estimation under Partial Overlap",
                  "Strand et al.", "2020",
                  "A doubly robust estimator for treatment effects that remains consistent "
                  "when propensity overlap is limited.",
                  "J. Causal Inference", ["causal", "treatment effects", "doubly robust"]),
            _item("C2", "Graph-Structured Causal Models: Identification Revisited",
                  "Reyes, Okafor", "2023",
                  "We revisit identification in causal graphical models and give a sound "
                  "algorithm for effect identification under latent variables.",
                  "Proc. UAI", ["causal", "graphs", "identification"]),
            _item("C3", "Instrumental Variables for Recommendation Feedback Loops",
                  "Vidal, Liang", "2022",
                  "Using instrumental variables to debias engagement estimates corrupted by "
                  "recommender feedback loops.",
                  "Proc. WWW", ["causal", "instrumental variables", "recommenders"]),
        ],
    },
    "DEMOEMPTY": {
        "name": "Empty folder (demo)",
        "short_name": "Empty folder (demo)",
        "items": [],
    },
    "DEMOLLM": {
        "name": "LLM Evaluation",
        "short_name": "LLM Evaluation",
        "items": [
            _item("L1", "Beyond Accuracy: Evaluating Reasoning Faithfulness",
                  "Park, Adeyemi", "2024",
                  "We propose faithfulness metrics for chain-of-thought reasoning and show that "
                  "accuracy alone hides unfaithful explanations.",
                  "Proc. ACL", ["LLM", "evaluation", "reasoning", "faithfulness"]),
            _item("L2", "Contamination Audits for Benchmark Leakage",
                  "Strand, Nakamura", "2024",
                  "A statistical audit that detects when evaluation benchmarks have leaked into "
                  "pretraining data.",
                  "Proc. EMNLP", ["LLM", "evaluation", "auditing", "contamination"]),
            _item("L3", "Calibrated Uncertainty for Language Model Predictions",
                  "Adeyemi, Strand", "2023",
                  "Methods for producing calibrated confidence estimates from language models, "
                  "connecting to classic calibration theory.",
                  "TMLR", ["LLM", "calibration", "uncertainty"]),
        ],
    },
}


def demo_projects() -> dict[str, dict]:
    projects: dict[str, dict] = {}
    for key, proj in _PROJECTS.items():
        projects[key] = {
            "key": key,
            "name": proj["name"],
            "short_name": proj["short_name"],
            "parent": None,
            "num_items": len(proj["items"]),
            "items": [dict(it) for it in proj["items"]],
        }
    return projects
