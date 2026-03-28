import gradio as gr
from lab_rag_sparql_gen import load_graph, build_schema_summary, answer_no_rag, answer_with_rag

# ----------------------------
# Load graph once at startup
# ----------------------------
print("Chargement du graphe...")
g      = load_graph("kg_artifacts/initial_graph.ttl")
schema = build_schema_summary(g)
print("Prêt.")

# ----------------------------
# Gradio handler
# ----------------------------
def query(question: str):
    if not question.strip():
        return "", "", "", False

    baseline = answer_no_rag(question)
    result   = answer_with_rag(g, schema, question)

    sparql   = result.get("query", "")
    repaired = result.get("repaired", False)
    error    = result.get("error", "")
    rows     = result.get("rows", [])
    vars_    = result.get("vars", [])

    if error:
        rag_answer = f"Erreur : {error}"
    elif not rows:
        rag_answer = "Aucun résultat trouvé dans le graphe."
    else:
        header = " | ".join(vars_)
        lines  = [header, "-" * len(header)]
        for r in rows[:20]:
            lines.append(" | ".join(
                v.split("/")[-1] if v.startswith("http") else v
                for v in r
            ))
        if len(rows) > 20:
            lines.append(f"... ({len(rows)} résultats total)")
        rag_answer = "\n".join(lines)

    status = "Réparé automatiquement" if repaired else "OK"
    return baseline, sparql, rag_answer, status

# ----------------------------
# Gradio UI
# ----------------------------
with gr.Blocks(title="Flags Knowledge Graph RAG") as demo:
    gr.Markdown("""
    # 🌍 Flags Knowledge Graph — RAG Demo
    Pose une question en anglais. Le système génère une requête SPARQL sur le graphe des drapeaux du monde.
    """)

    with gr.Row():
        question = gr.Textbox(
            label="Question",
            placeholder="e.g. List all countries, Which countries have a flag?",
            scale=4,
        )
        btn = gr.Button("Ask", variant="primary", scale=1)

    gr.Examples(
        examples=[
            ["List all countries in the graph"],
            ["Which countries have a flag?"],
            ["List all flags in the graph"],
            ["What is affiliated with France?"],
            ["When was the flag of China adopted?"],
        ],
        inputs=question,
    )

    with gr.Row():
        with gr.Column():
            gr.Markdown("### Baseline (LLM sans RAG)")
            baseline_out = gr.Textbox(label="Réponse LLM", lines=6)

        with gr.Column():
            gr.Markdown("### RAG (SPARQL + graphe)")
            sparql_out  = gr.Code(label="SPARQL généré", language="sql", lines=6)
            rag_out     = gr.Textbox(label="Résultats", lines=6)
            status_out  = gr.Textbox(label="Statut", lines=1)

    btn.click(
        fn=query,
        inputs=question,
        outputs=[baseline_out, sparql_out, rag_out, status_out],
    )
    question.submit(
        fn=query,
        inputs=question,
        outputs=[baseline_out, sparql_out, rag_out, status_out],
    )

if __name__ == "__main__":
    demo.launch(share=False)
