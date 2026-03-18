import streamlit as st
import anthropic
import json
import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# ── Load patient data ──────────────────────────────────────────────────────────
def load_patient():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "..", "patient_data.json")
    with open(json_path, "r") as f:
        return json.load(f)

# ── Days until appointment ─────────────────────────────────────────────────────
def days_until(date_str):
    appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    delta = (appt_date - date.today()).days
    return delta

# ── Call Claude API ────────────────────────────────────────────────────────────
def ask_claude(prompt):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

# ── Generate pre-visit questions using Claude ──────────────────────────────────
def generate_previsit(patient):
    missed_meds = [m["name"] for m in patient["medications"] if not m["taken"]]
    symptoms = patient["symptoms_today"]
    conditions = patient["conditions"]

    prompt = f"""
You are a helpful health assistant preparing {patient['patient']} for a doctor's visit.

Patient conditions: {', '.join(conditions)}
Missed medications today: {', '.join(missed_meds) if missed_meds else 'None'}
Symptoms reported today: {', '.join(symptoms) if symptoms else 'None'}

Generate a friendly, simple pre-visit preparation message for the patient. Include:
1. 3 to 4 specific questions they should ask their doctor based on their conditions and symptoms
2. What health information to bring (recent BP readings, medication list)
3. A brief reassuring note

Keep the language simple and warm. The patient is an elderly Singaporean.
"""
    return ask_claude(prompt)

# ── Generate clinician summary using Claude ────────────────────────────────────
def generate_clinician_summary(patient):
    missed_meds = [m["name"] for m in patient["medications"] if not m["taken"]]
    taken_meds = [m["name"] for m in patient["medications"] if m["taken"]]

    prompt = f"""
You are a medical AI assistant generating a concise pre-consultation summary for a doctor.

Patient: {patient['patient']}
Conditions: {', '.join(patient['conditions'])}
Medications taken today: {', '.join(taken_meds) if taken_meds else 'None'}
Medications missed today: {', '.join(missed_meds) if missed_meds else 'None'}
Symptoms reported today: {', '.join(patient['symptoms_today']) if patient['symptoms_today'] else 'None'}
Meals today: {', '.join(patient['meals_today'])}
Steps today: {patient['steps_today']}

Write a structured clinical summary with these sections:
1. Medication Adherence
2. Symptoms & Concerns
3. Lifestyle Observations
4. Suggested Discussion Points for Clinician

Be concise and clinical in tone. This is for the doctor, not the patient.
"""
    return ask_claude(prompt)

# ── Generate PDF ───────────────────────────────────────────────────────────────
def generate_pdf(patient, summary_text):
    filename = f"clinician_summary_{patient['patient'].replace(' ', '_')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                  fontSize=16, textColor=colors.HexColor('#1a365d'),
                                  spaceAfter=6)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                     fontSize=10, textColor=colors.grey, spaceAfter=20)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                 fontSize=11, leading=16, spaceAfter=8)

    content = []

    # Header
    content.append(Paragraph("Pre-Consultation Clinical Summary", title_style))
    content.append(Paragraph(f"Generated: {date.today().strftime('%d %B %Y')} | "
                              f"Patient: {patient['patient']} | "
                              f"Conditions: {', '.join(patient['conditions'])}",
                              subtitle_style))

    # Divider table
    content.append(Table([['']], colWidths=[6.5*inch],
                          style=TableStyle([
                              ('LINEABOVE', (0,0), (-1,0), 1, colors.HexColor('#1a365d'))
                          ])))
    content.append(Spacer(1, 12))

    # Summary content — split by newline for formatting
    for line in summary_text.split('\n'):
        if line.strip():
            if line.strip().startswith(('1.', '2.', '3.', '4.')):
                content.append(Paragraph(f"<b>{line.strip()}</b>",
                                          ParagraphStyle('Section',
                                                          parent=styles['Normal'],
                                                          fontSize=12,
                                                          textColor=colors.HexColor('#1a365d'),
                                                          spaceBefore=12,
                                                          spaceAfter=4)))
            else:
                content.append(Paragraph(line.strip(), body_style))

    content.append(Spacer(1, 20))
    content.append(Paragraph("— Generated by HealthCompanion AI | Not a substitute for clinical judgment —",
                               ParagraphStyle('Footer', parent=styles['Normal'],
                                               fontSize=8, textColor=colors.grey,
                                               alignment=1)))

    doc.build(content)
    return filename

# ── Streamlit UI ───────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Appointment & Clinician Agent", page_icon="🏥")
    st.title("🏥 Appointment & Clinician Bridge")

    patient = load_patient()
    st.markdown(f"### 👤 Patient: {patient['patient']}")
    st.markdown(f"**Conditions:** {', '.join(patient['conditions'])}")
    st.divider()

    # ── Appointment countdown ──────────────────────────────────────────────────
    st.subheader("📅 Upcoming Appointments")
    if patient["appointments"]:
        for appt in patient["appointments"]:
            days = days_until(appt["date"])
            if days >= 0:
                if days == 0:
                    countdown = "🔴 Today!"
                elif days <= 3:
                    countdown = f"🟠 In {days} day(s)"
                else:
                    countdown = f"🟢 In {days} day(s)"

                st.info(f"**{appt['type']}** with {appt['doctor']}  \n"
                        f"📆 {appt['date']}  |  {countdown}")
    else:
        st.write("No upcoming appointments.")

    st.divider()

    # ── Pre-visit prep ─────────────────────────────────────────────────────────
    st.subheader("📋 Pre-Visit Preparation")
    if st.button("Generate Pre-Visit Questions"):
        with st.spinner("Preparing your visit summary..."):
            previsit = generate_previsit(patient)
            st.session_state["previsit"] = previsit

    if "previsit" in st.session_state:
        st.markdown(st.session_state["previsit"])

    st.divider()

    # ── Clinician summary ──────────────────────────────────────────────────────
    st.subheader("🩺 Clinician Summary Report")
    if st.button("Generate Clinician Summary + Download PDF"):
        with st.spinner("Generating clinical summary..."):
            summary = generate_clinician_summary(patient)
            st.session_state["summary"] = summary
            pdf_path = generate_pdf(patient, summary)
            st.session_state["pdf_path"] = pdf_path

    if "summary" in st.session_state:
        st.markdown(st.session_state["summary"])

    if "pdf_path" in st.session_state:
        with open(st.session_state["pdf_path"], "rb") as f:
            st.download_button(
                label="📥 Download PDF for Doctor",
                data=f,
                file_name=st.session_state["pdf_path"],
                mime="application/pdf"
            )

# ── Run ────────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    main()
