import json
import re
from datetime import date

import streamlit as st
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from dotenv import load_dotenv

load_dotenv()


# --------------------------------------------------
# Prompt
# --------------------------------------------------

NOTES_PROMPT = """You are a professional meeting note-taker.

Convert the meeting transcript into structured notes as JSON:

{
  "meeting_title": "inferred title",
  "date": "today or mentioned date",
  "participants": ["name1", "name2"],
  "duration_estimate": "X minutes",
  "summary": "2-3 sentence executive summary",
  "key_decisions": ["decision 1", "decision 2"],
  "action_items": [
    {
      "task": "description",
      "owner": "person name or TBD",
      "due": "date or timeframe or TBD"
    }
  ],
  "discussion_topics": ["topic 1", "topic 2"],
  "blockers": ["blocker 1 or none"],
  "next_meeting": "scheduled time or TBD",
  "follow_up_questions": ["question needing resolution"]
}

Rules:
- Infer information only when it is reasonably supported by the transcript.
- Use "TBD" when information is not available.
- Return ONLY valid JSON.
"""


# --------------------------------------------------
# JSON parsing
# --------------------------------------------------

def parse_json_response(text: str) -> dict:
    cleaned = text.strip()

    # Remove markdown code fences if the model adds them
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    # Extract JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)

    if not match:
        raise ValueError("The model did not return valid JSON.")

    return json.loads(match.group(0))


# --------------------------------------------------
# Generate meeting notes
# --------------------------------------------------

def generate_meeting_notes(transcript: str) -> dict:

    llm = ChatOllama(
        model="qwen3:8b",
        temperature=0,
    )

    messages = [
        SystemMessage(content=NOTES_PROMPT),
        HumanMessage(
            content=f"Meeting transcript:\n\n{transcript}"
        ),
    ]

    response = llm.invoke(messages)

    return parse_json_response(response.content)


# --------------------------------------------------
# Markdown formatter
# --------------------------------------------------

def format_notes(notes: dict) -> str:

    lines = [
        f"# {notes.get('meeting_title', 'Meeting Notes')}",
        "",
        f"**Date:** {notes.get('date', date.today().isoformat())}",
        f"**Duration Estimate:** {notes.get('duration_estimate', 'N/A')}",
        f"**Participants:** {', '.join(notes.get('participants', []))}",
        "",
        "## Summary",
        notes.get("summary", ""),
        "",
        "## Key Decisions",
    ]

    decisions = notes.get("key_decisions", [])

    if decisions:
        for decision in decisions:
            lines.append(f"- {decision}")
    else:
        lines.append("- None")

    lines += [
        "",
        "## Action Items",
    ]

    action_items = notes.get("action_items", [])

    if action_items:
        for item in action_items:
            lines.append(
                f"- [ ] **{item.get('task', 'Task')}** "
                f"— Owner: {item.get('owner', 'TBD')} "
                f"| Due: {item.get('due', 'TBD')}"
            )
    else:
        lines.append("- None")

    lines += [
        "",
        "## Discussion Topics",
    ]

    topics = notes.get("discussion_topics", [])

    if topics:
        for topic in topics:
            lines.append(f"- {topic}")
    else:
        lines.append("- None")

    lines += [
        "",
        "## Blockers",
    ]

    blockers = notes.get("blockers", [])

    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- None")

    if notes.get("next_meeting") and notes["next_meeting"] != "TBD":
        lines += [
            "",
            f"**Next Meeting:** {notes['next_meeting']}"
        ]

    lines += [
        "",
        "## Follow-up Questions",
    ]

    questions = notes.get("follow_up_questions", [])

    if questions:
        for question in questions:
            lines.append(f"- {question}")
    else:
        lines.append("- None")

    return "\n".join(lines)


# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------

st.set_page_config(
    page_title="Meeting Notes Agent",
    page_icon="📝",
    layout="wide",
)


# --------------------------------------------------
# Header
# --------------------------------------------------

st.title("📝 Meeting Notes Agent")

st.write(
    "Paste your meeting transcript below and let the AI "
    "turn it into structured meeting notes."
)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:

    st.header("Settings")

    model = st.text_input(
        "Ollama Model",
        value="qwen3:8b"
    )

    st.divider()

    st.markdown(
        """
        **How it works**

        1. Paste your transcript
        2. Click **Generate Notes**
        3. AI extracts:
           - Summary
           - Decisions
           - Action items
           - Participants
           - Blockers
           - Follow-ups
        """
    )


# --------------------------------------------------
# Transcript input
# --------------------------------------------------

transcript = st.text_area(
    "Meeting Transcript",
    height=400,
    placeholder="""Paste your meeting transcript here...

Example:

Sarah: Let's discuss the Q4 product roadmap.

John: We need to decide on the feature freeze date.

Sarah: I think we should freeze by November 15th.

Mike: That works for me.

Lisa: I'm still waiting for the payment API documentation.

John: I'll contact the payment provider today.
""",
)


# --------------------------------------------------
# Generate button
# --------------------------------------------------

generate_button = st.button(
    "✨ Generate Meeting Notes",
    type="primary",
    use_container_width=True,
)


# --------------------------------------------------
# Generate notes
# --------------------------------------------------

if generate_button:

    if not transcript.strip():
        st.warning("Please paste a meeting transcript first.")

    else:

        try:

            with st.spinner("Analyzing meeting transcript..."):

                # Create LLM using selected model
                llm = ChatOllama(
                    model=model,
                    temperature=0,
                )

                messages = [
                    SystemMessage(content=NOTES_PROMPT),
                    HumanMessage(
                        content=f"Meeting transcript:\n\n{transcript}"
                    ),
                ]

                response = llm.invoke(messages)

                notes = parse_json_response(response.content)

            st.success("Meeting notes generated successfully!")

            # Save in session state
            st.session_state["notes"] = notes

        except Exception as e:

            st.error(
                f"Something went wrong:\n\n{str(e)}"
            )


# --------------------------------------------------
# Display results
# --------------------------------------------------

if "notes" in st.session_state:

    notes = st.session_state["notes"]

    st.divider()

    st.header(
        notes.get(
            "meeting_title",
            "Meeting Notes"
        )
    )

    # Basic information
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Date",
            notes.get("date", "TBD")
        )

    with col2:
        st.metric(
            "Duration Estimate",
            notes.get(
                "duration_estimate",
                "TBD"
            )
        )

    with col3:
        st.metric(
            "Participants",
            len(notes.get("participants", []))
        )

    # Participants
    st.subheader("👥 Participants")

    participants = notes.get("participants", [])

    if participants:
        st.write(", ".join(participants))
    else:
        st.write("TBD")

    # Summary
    st.subheader("📋 Summary")

    st.write(
        notes.get(
            "summary",
            "No summary available."
        )
    )

    # Decisions
    st.subheader("✅ Key Decisions")

    decisions = notes.get("key_decisions", [])

    if decisions:
        for decision in decisions:
            st.markdown(f"- {decision}")
    else:
        st.write("No decisions recorded.")

    # Action items
    st.subheader("📌 Action Items")

    action_items = notes.get("action_items", [])

    if action_items:

        for item in action_items:

            task = item.get("task", "Task")
            owner = item.get("owner", "TBD")
            due = item.get("due", "TBD")

            st.markdown(
                f"""
                - [ ] **{task}**
                  - **Owner:** {owner}
                  - **Due:** {due}
                """
            )

    else:
        st.write("No action items recorded.")

    # Discussion topics
    st.subheader("💬 Discussion Topics")

    topics = notes.get("discussion_topics", [])

    if topics:
        for topic in topics:
            st.markdown(f"- {topic}")
    else:
        st.write("No discussion topics recorded.")

    # Blockers
    st.subheader("🚧 Blockers")

    blockers = notes.get("blockers", [])

    if blockers:
        for blocker in blockers:
            st.markdown(f"- {blocker}")
    else:
        st.write("No blockers.")

    # Next meeting
    st.subheader("📅 Next Meeting")

    st.write(
        notes.get(
            "next_meeting",
            "TBD"
        )
    )

    # Follow-up questions
    st.subheader("❓ Follow-up Questions")

    questions = notes.get("follow_up_questions", [])

    if questions:
        for question in questions:
            st.markdown(f"- {question}")
    else:
        st.write("No follow-up questions.")

    # --------------------------------------------------
    # Download
    # --------------------------------------------------

    st.divider()

    markdown_output = format_notes(notes)

    st.download_button(
        label="⬇️ Download Meeting Notes",
        data=markdown_output,
        file_name="meeting_notes.md",
        mime="text/markdown",
        use_container_width=True,
    )