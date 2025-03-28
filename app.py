import json
import streamlit as st
import yaml

from analysis import detect_profanity, detect_privacy_violation
from metrics import calculate_metrics
from visualization import plot_metrics

st.title("Call Conversation Analysis Tool")

uploaded_file = st.file_uploader("Upload a JSON or YAML file", type=["json", "yaml"])

if uploaded_file:
    if uploaded_file.name.endswith(".yaml"):
        conversation_data = yaml.safe_load(uploaded_file)
    elif uploaded_file.name.endswith(".json"):
        conversation_data = json.load(uploaded_file)

    analysis_method = st.selectbox("Select Analysis Method", ["Regex", "LLM"])
    entity = st.selectbox(
        "Select Entity to Analyze", ["Profanity Detection", "Privacy Violation"]
    )

    if st.button("Analyze"):
        if entity == "Profanity Detection":
            results = detect_profanity(conversation_data, analysis_method)
        else:
            results = detect_privacy_violation(conversation_data, analysis_method)

        if results:
            st.warning("Flagged Utterances:")
            for res in results:
                st.write(res)
        else:
            st.success("No issues detected!")

    silence_pct, overtalk_pct = calculate_metrics(conversation_data)
    st.subheader("Call Quality Metrics")
    st.pyplot(plot_metrics(silence_pct, overtalk_pct))
