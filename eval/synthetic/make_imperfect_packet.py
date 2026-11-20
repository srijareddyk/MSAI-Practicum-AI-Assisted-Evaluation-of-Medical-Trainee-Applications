"""Build a fictional imperfect ophthalmology packet for color demos."""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).with_name("Rivera,_Jordan_AU99999_OPHTH-R_SYNTHETIC.pdf")


class PDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", size=8)
        self.set_text_color(120)
        self.cell(0, 8, "FICTIONAL EVAL PACKET - not a real applicant", align="C")


def write_block(pdf: PDF, title: str, text: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(w=0, h=7, text=title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(w=0, h=5.2, text=text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def main() -> None:
    pdf = PDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(
        w=0,
        h=8,
        text="Ophthalmology Residency Application Coversheet",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(
        w=0,
        h=6,
        text="Applicant: Jordan Rivera | AAMC ID: AU99999 | FICTIONAL SYNTHETIC PACKET",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    # Designed GREEN: specific ophthalmology reason
    write_block(
        pdf,
        "PERSONAL STATEMENT",
        "During my third-year surgery clerkship I scrubbed into a cataract case for a patient "
        "who had stopped driving at night. When the lens was placed and the drape came off, "
        "the patient named the wall clock without guessing. That single, visible result is why "
        "ophthalmology appeals to me: pathology you can see, and care that changes daily function.\n\n"
        "I later spent a month on a retina service drafting notes and presenting imaging findings. "
        "I want residency training that ties clinic judgment to procedure skill. Northwestern's "
        "focus on careful bedside teaching matches how I learn.",
    )

    # Designed YELLOW: vague praise, no judgment/skill evidence
    write_block(
        pdf,
        "LETTERS OF RECOMMENDATION",
        "Letter 1 - Dr. A. Patel, Department of Medicine\n"
        "Jordan is nice and hard-working. I did not supervise Jordan closely. Based on brief hallway "
        "interactions, Jordan seems pleasant. I have no examples of clinical judgment, procedures, "
        "or teamwork to offer. I am willing to support the application in general terms only.\n\n"
        "Letter 2 - Dr. L. Chen, Department of Surgery\n"
        "Jordan attended clinic. I do not recall specific cases. Jordan is friendly. This letter "
        "contains no assessment of skill, reliability under pressure, or teaching ability.",
    )

    # Designed RED: titles only, no applicant role
    write_block(
        pdf,
        "RESEARCH",
        "No research role is described. The applicant did not design a study, analyze data, write a "
        "manuscript, or present work. The publications list below is name-only co-authorship without "
        "contribution statements. This file does not support a research-ready read.",
    )

    write_block(
        pdf,
        "PUBLICATIONS",
        "1. Rivera J, et al. Survey of screen time habits in first-year students. Campus Health Notes. 2022.\n"
        "2. Kim S, Rivera J, Ortiz M. Chart review of blood pressure documentation. Quality Bulletin. 2023.\n"
        "3. Poster: Attendance patterns in a student-run clinic. Regional Education Day. 2023.\n\n"
        "Contribution: none stated. Methods: none stated. Applicant role: unknown.",
    )

    # Designed GREEN: strong clinical narrative
    write_block(
        pdf,
        "MSPE",
        "Jordan Rivera demonstrated strong clinical performance on core clerkships. On Internal "
        "Medicine, evaluators noted careful differential building, clear presentations, and thoughtful "
        "follow-up on overnight events. On Surgery, faculty wrote that Jordan anticipated next steps "
        "in clinic, communicated plans to patients in plain language, and handled feedback without "
        "defensiveness.\n\n"
        "A clinic preceptor who observed Jordan during a short ophthalmology exposure wrote that Jordan "
        "prepared imaging reviews before rounds and asked focused questions about exam findings. Overall, "
        "the clinical narrative supports readiness for supervised residency care.",
    )

    # Designed YELLOW: thin academics, incomplete
    write_block(
        pdf,
        "EDUCATION",
        "Medical school: Midland State University College of Medicine.\n"
        "Step 1 status appears in the packet as Pass only.\n"
        "No school context, no comparative academic language, and no further academic narrative are "
        "included. Faculty should look again at the raw transcript outside this screen.",
    )

    # Designed RED: almost no ophthalmology commitment outside the statement
    write_block(
        pdf,
        "EXPERIENCES",
        "Ophthalmology exposure outside the personal statement: one half-day of shadowing in 2024.\n"
        "No ophthalmology elective.\n"
        "No ophthalmology mentor.\n"
        "No vision screening, eye clinic continuity, or longitudinal eye research.\n"
        "Other activities: student-run primary care clinic; surgery interest group meetings.\n"
        "This experiences section does not show sustained commitment to ophthalmology.",
    )

    pdf.output(str(OUT))
    print(OUT)
    print("bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
