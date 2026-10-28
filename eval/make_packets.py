"""Write the 12 fictional MSAI packets used for the local benchmark.

Every person, school detail, project, and letter is invented. These files are
test fixtures, not applications.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent
PACKET_DIR = ROOT / "packets"
FONT = Path(r"C:\Windows\Fonts\arial.ttf")


def packet(
    name: str,
    school: str,
    degree: str,
    gpa: str,
    sop: str,
    research: str,
    projects: str,
    work: str,
    honors: str,
    letters: str,
) -> str:
    return f"""FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: {name}

STATEMENT OF PURPOSE

{sop.strip()}

EDUCATION

Undergraduate institution: {school}
Degree: {degree}
Cumulative GPA: {gpa}

RESEARCH

{research.strip()}

PROJECTS

{projects.strip()}

WORK EXPERIENCE

{work.strip()}

HONORS AND AWARDS

{honors.strip()}

LETTERS OF RECOMMENDATION

{letters.strip()}
"""


PACKETS: list[tuple[str, str]] = []

PACKETS.append(
    (
        "01_avery_chen.txt",
        packet(
            "Avery Chen",
            "University of Michigan",
            "B.S. Computer Science, 2025",
            "3.86",
            """
I am applying to the Master of Science in Artificial Intelligence at Northwestern because I want to train retrieval systems that clinicians can actually query. For two years I was a research assistant in a clinical natural language processing group. I built the indexing pipeline for a set of de-identified discharge summaries, and I was first author on a workshop paper about that indexer.

The paper, "Sparse Plus Dense Retrieval for Discharge Summaries," appeared in the proceedings of the Upper Midwest NLP Workshop in 2025. I designed the experiment, wrote the retrieval code, and ran the error analysis. The useful result was not a leaderboard number. Dense retrieval missed negation. A hybrid index recovered those cases, and I wrote that up with the counts.

At Northwestern I want the systems and language courses in MSAI, then a project on retrieval for notes where the label is a clinical concept rather than a web query. I have the linear algebra, probability, algorithms, and machine learning sequence from Michigan, and I have already maintained the code other students in the lab ran. I am not looking for a general tour of artificial intelligence. I want a year in which the coursework and a faculty project are the same problem.
            """,
            """
Research assistant, University of Michigan, September 2023 to May 2025, about 15 hours a week during term and full time in summer 2024. Built a hybrid retrieval index over 80,000 de-identified discharge summaries. First-author workshop paper, Upper Midwest NLP Workshop, 2025. I wrote the code, the experiments, and the first draft.
            """,
            """
Discharge-summary retriever. Python, FAISS, and a small BM25 index. Other students in the lab used the repository for their own error analysis. I reviewed their pull requests.
            """,
            """
Undergraduate research assistant, clinical NLP group, University of Michigan, 2023-2025. Teaching assistant for EECS 445, Introduction to Machine Learning, winter 2025, two discussion sections.
            """,
            """
EECS 445 teaching award, departmental nominee, 2025. University Honors, 2023-2025.
            """,
            """
Letter 1. Professor Helen Park, University of Michigan. "Avery is the student I trust with the lab repository. The workshop paper is Avery's experiment, not a footnote on mine. I would fund this student in a PhD program. The retrieval work is careful, and the error analysis is the part I send to new students."

Letter 2. Dr. Omar Shah, University of Michigan. "I co-taught the machine learning course Avery assisted. Avery could explain a confusion matrix to a student who was lost, and then go back and fix a leaking index in the lab. I recommend Avery without reservation for a technical master's program."
            """,
        ),
    )
)

PACKETS.append(
    (
        "02_priya_shah.txt",
        packet(
            "Priya Shah",
            "University of Illinois Urbana-Champaign",
            "B.S. Computer Engineering, 2024",
            "3.91",
            """
I am applying to Northwestern's MSAI program to move from shipping ranking models to understanding when those models fail. At an internship with a retail search team I owned the feature pipeline for a learning-to-rank model. The model went to production for a category page. I also wrote the note that said we should not launch a second page because the offline gain did not survive a holdout week.

That note is the work I want more of. I can implement a ranker. I am less sure how to design the evaluation when the click log is biased. MSAI's machine learning systems and evaluation courses are the reason I am applying here rather than to a general computer science master's. I want a year of coursework in probabilistic modeling and a project on offline evaluation, then a role building models whose failures I can explain.

My record is a computer engineering degree with linear algebra, probability, algorithms, and two machine learning courses, plus the production system above. I am applying because the production work showed me the questions I cannot answer from an internship alone.
            """,
            """
No university laboratory appointment. The technical research in this packet is the internship evaluation study below, which I wrote up internally. I did not publish it.
            """,
            """
Category-page ranker, summer 2024, retail search internship. I trained a LightGBM ranker, built the daily feature job, and compared it with the previous heuristic on a one-week holdout. The first page shipped. I recommended against shipping the second page. The repository is internal. My mentor can describe the design.
            """,
            """
Machine learning engineering intern, Northline Retail, Champaign, May 2024 to August 2024. Course assistant for ECE 374, Algorithms, spring 2024.
            """,
            """
James Scholar, University of Illinois, 2022-2024. Dean's list each semester.
            """,
            """
Letter 1. Maya Krishnan, staff engineer, Northline Retail. "Priya owned the ranker that we shipped. More important, Priya is the intern who told us not to ship the second page. The memo was specific, with the holdout numbers, and it was right. I would hire Priya back as an engineer."

Letter 2. Professor David Lang, University of Illinois. "Priya was among the strongest students in my algorithms course and then assisted it. The homework solutions were correct, and the explanations in office hours were precise. I recommend Priya for a technical graduate program."
            """,
        ),
    )
)

PACKETS.append(
    (
        "03_marcus_hale.txt",
        packet(
            "Marcus Hale",
            "University of Wisconsin-Madison",
            "B.S. Mathematics and Computer Sciences, 2025",
            "3.74",
            """
I am applying to the MSAI program to study optimization for models that do not fit on one machine. I maintain an open-source library, SmallBatch, that implements a few stochastic solvers for people who want a readable PyTorch training loop rather than a framework. About forty GitHub accounts have starred it, and I have merged patches from six outside contributors. The users are students. I do not want to overstate that.

The mathematics degree is the other half. I have had linear algebra, real analysis, probability, numerical methods, and a graduate-level convex optimization course as an undergraduate. What I do not have is a lab appointment or a paper. The library is the technical artifact. Northwestern is the program I want because the MSAI curriculum pairs the optimization coursework with systems, which is the gap between my solvers and a model someone else can train.

I hope to spend the year on distributed training and a project that turns one of the SmallBatch solvers into something a course staff could assign. I am applying for that sequence, not for a general credential.
            """,
            """
No formal research appointment. Independent work on SmallBatch, described under projects, from June 2024 to the present.
            """,
            """
SmallBatch, an open-source PyTorch training library. I wrote the solvers, the tests, and the documentation. Six outside contributors have merged patches. The issue tracker shows students using it for class projects. Repository: a public GitHub project under my name, started June 2024.
            """,
            """
Tutor, Madison Mathematics Learning Center, September 2023 to May 2025, eight hours a week. I ran drop-in hours for linear algebra.
            """,
            """
Van Vleck scholarship for mathematics, 2024. Dean's list, four semesters.
            """,
            """
Letter 1. Professor Ruth Adler, University of Wisconsin. "Marcus took my convex optimization course and then built a library whose solvers match the algorithms in the course. I have read the documentation. It is accurate. Marcus is ready for graduate coursework in optimization, and I recommend him strongly."

Letter 2. Professor Ian Brooks, University of Wisconsin. "I supervised Marcus only as an instructor in numerical methods, not as a research advisor. Within that scope, the work was excellent. He is the student other students asked for by name in the tutoring center. I recommend him for MSAI."
            """,
        ),
    )
)

PACKETS.append(
    (
        "04_elena_vasquez.txt",
        packet(
            "Elena Vasquez",
            "Purdue University",
            "B.S. Electrical Engineering, 2025",
            "3.82",
            """
I am applying to Northwestern MSAI to work on perception for robots that share a room with people, not on benchmark vision. In the Purdue cooperative robotics lab I was the second author on a conference paper about a gripper that uses a wrist camera. My part was the data split and the calibration code. The first author designed the policy. I can say exactly what I did not do.

I also taught a lab section of a signals course for a year. The students who struggled were usually missing linear algebra, and I started writing short notes for them. That is the teaching I want to keep doing in graduate school.

MSAI is the program I am applying to because I need the vision and learning courses next to a robotics faculty project. My plan for the year is those courses and a project on calibration under bad lighting, which is the failure mode in our paper. I have probability, linear algebra, signals, and a machine learning elective. I am applying with a specific experiment in mind.
            """,
            """
Undergraduate researcher, Purdue cooperative robotics lab, January 2024 to May 2025. Second author: "Wrist-Camera Grasping Under Partial Occlusion," Great Lakes Robotics Meeting, 2025. I wrote the calibration code and constructed the train and test split. I did not design the policy.
            """,
            """
Calibration toolkit for the lab's wrist camera. Python and OpenCV. The current students still use the split script I wrote. It is in the lab repository, not a public project.
            """,
            """
Laboratory teaching assistant, ECE 301 signals and systems, fall 2024 and spring 2025.
            """,
            """
Purdue College of Engineering undergraduate research stipend, summer 2024.
            """,
            """
Letter 1. Professor Nina Cole, Purdue University. "Elena is the second author for a reason I can defend. She built the split that made the paper's claim measurable, and she refused to let us average away the lighting failures. I recommend her for a research master's without reservation."

Letter 2. Dr. Paul Ortega, Purdue University. "Elena taught my signals lab. Students improved, and Elena could tell me which problem set item caused it. She is organized, precise, and ready for graduate coursework. I recommend her strongly."
            """,
        ),
    )
)

PACKETS.append(
    (
        "05_jordan_hale.txt",
        packet(
            "Jordan Hale",
            "University of Michigan",
            "B.S. Computer Science, 2025",
            "3.78",
            """
I have always been passionate about artificial intelligence and I believe Northwestern is one of the best places in the world to study it. Ever since my first programming class I knew I wanted a career in AI. The MSAI program would help me achieve my dreams and become a leader in the field. I am a hard worker and a team player, and I love to learn new things. Northwestern's reputation and the city of Chicago are also very exciting to me.

In the future I hope to work at a top company or maybe start my own company. A master's degree from Northwestern would open those doors. I am eager to take whatever courses the program recommends and to meet other talented students. Thank you for considering my application. I would be honored to join the incoming class and contribute to the Northwestern community.
            """,
            """
Research assistant, University of Michigan information retrieval group, May 2024 to April 2025. I built a retrieval demo that the lab still runs for visitors.
            """,
            """
Lab retrieval demo. I implemented dense retrieval over a professor's lecture notes, with a small web interface. Two doctoral students used it during group open houses. The code is in the lab GitHub organization. I also built a course project that finetuned a classifier on public news data. That project stayed in the course repository.
            """,
            """
Software engineering intern, Lakeshore Analytics, summer 2024. I shipped an internal search box over support tickets. Teaching assistant for an introductory programming course, fall 2024.
            """,
            """
Dean's list, three semesters.
            """,
            """
Letter 1. Professor Helen Park, University of Michigan. "Jordan's retrieval demo is the one we turn on for visitors. The engineering is solid, the code is readable, and Jordan finished it without being managed. I recommend Jordan for a technical master's program."

Letter 2. Chris Feldman, engineering manager, Lakeshore Analytics. "Jordan shipped the support-ticket search and wrote tests for it. I would hire Jordan as a junior engineer. The work was specific and on time."
            """,
        ),
    )
)

PACKETS.append(
    (
        "06_sam_okonkwo.txt",
        packet(
            "Sam Okonkwo",
            "DePaul University",
            "B.A. Economics, 2023",
            "3.45",
            """
I am applying to Northwestern MSAI to learn the modeling I need for a project I have already started and cannot finish honestly. I work as an analyst in a city budget office. We publish spending tables. Residents ask which department grew, and I answer with spreadsheets. I want a model that can flag a line item that changed for a reason the table does not state, and I want to know when that model is wrong.

Since 2024 I have taken linear algebra, probability, and an introductory machine learning course through a university extension program, at night. I have not held a research job. My one project is a small classifier on ten years of public budget rows. It overfits. I can show the learning curve. I cannot yet fix it.

MSAI is the program I want because the coursework is the thing I am missing, and because I can keep the budget data as the project. I am not claiming a research record I do not have. I am applying so the first-year sequence, especially probability and machine learning, is the job I do next. If the committee wants a student who already ships models, I am not that student. If it wants a student with a defined public-data question and the start of the mathematics, I am.
            """,
            """
No research appointment. Independent study of public budget data, evenings, 2024 to the present, described under projects. I have not published.
            """,
            """
Budget-line classifier. A scikit-learn model on publicly posted city expenditure rows, ten years, one city. I held out the last year. Training accuracy was high and the holdout was near chance. I wrote a short memo about the leak, which was a feature that included the label. The code is in a public repository.
            """,
            """
Budget analyst, City of Evanston finance department, July 2023 to the present. I prepare the quarterly spending tables. This is not a machine learning role. Extension coursework at night: linear algebra (A), probability (A-), introduction to machine learning (B+), 2024-2025.
            """,
            """
Departmental honor in economics, DePaul, 2023.
            """,
            """
Letter 1. Director June Alvarez, City of Evanston. "Sam is the analyst I ask to explain a table to a resident. The writing is clear and the numbers are checked. Sam told me about the machine learning courses. I cannot evaluate that work. I can say the analyst work is reliable, and I support this application."

Letter 2. Dr. Robert Klein, university extension instructor. "Sam took my linear algebra and probability courses after work. The homework was complete and the exam grades were A and A-. I do not know Sam's research. I recommend Sam for further quantitative study."
            """,
        ),
    )
)

PACKETS.append(
    (
        "07_riley_nguyen.txt",
        packet(
            "Riley Nguyen",
            "Loyola University Chicago",
            "B.S. Data Science, 2025",
            "3.62",
            """
I am applying to Northwestern MSAI to go past the capstone I just finished. The capstone was a classifier for campus club event attendance, built with two classmates. I cleaned the registration table, another student trained the model, and I wrote the report. It was a good class project. It is not a system anyone maintained after the term.

I want the MSAI year for the core machine learning sequence and a project that lasts longer than a semester. I am interested in how universities schedule events, which is a small version of a recommendation problem. I have had linear algebra, statistics, a machine learning course, and a databases course. I have not worked in a research group.

I am applying because the program is in the city where I already go to school, and because I want a master's that assumes I will take the foundational courses rather than skip them. I can start from the core. I do not have a paper or an internship model to bring.
            """,
            """
No research appointment.
            """,
            """
Senior capstone, fall 2024, with two classmates. We predicted whether a student would attend a club event from the registration form. I cleaned the data and wrote the final report. I did not train the model. The code is in a course GitHub classroom and was not used after the class ended.
            """,
            """
Peer tutor, Loyola data science help room, spring 2024 and fall 2024, four hours a week. Front desk assistant, campus recreation, 2022-2023.
            """,
            """
Dean's list, two semesters.
            """,
            """
Letter 1. Professor Amy Walsh, Loyola University Chicago. "Riley wrote the clearest capstone report in the section. The modeling was a group effort, and Riley's piece was the data and the writing. Riley is ready for a master's core, and I recommend Riley."

Letter 2. Professor Chris Bell, Loyola University Chicago. "Riley tutored in my help room and was patient and prepared. I recommend Riley for graduate study. I have not supervised research."
            """,
        ),
    )
)

PACKETS.append(
    (
        "08_taylor_brooks.txt",
        packet(
            "Taylor Brooks",
            "University of Iowa",
            "B.S. Statistics, 2024",
            "3.51",
            """
I am applying to MSAI because my statistics degree taught me to fit a model and my internship taught me that fitting it is the easy part. At an insurance internship I rebuilt a churn notebook that a team had been copying forward. I put the split in the right place and wrote down the features. The team used the notebook the rest of the summer. I did not design a new model.

I want Northwestern's program for the machine learning core and for a project with more consequence than a summer notebook. I am interested in how claims models get checked, not in a particular lab. I have had probability, mathematical statistics, regression, and one applied machine learning course. My grades in the theory courses were B's. I am straightforward about that.

I will need the first-year courses. I am applying because I want them, and because I can already do a careful split. I do not have a publication.
            """,
            """
No university research appointment. Internship analysis described under work experience.
            """,
            """
Churn notebook, internship, summer 2023. I replaced a random split that had leaked the renewal month. I documented the features in a README the team kept. I did not deploy a model.
            """,
            """
Actuarial intern, Prairie Mutual, Iowa City, May 2023 to August 2023. After graduation, data coordinator at the same office, September 2024 to the present. I check monthly reports. It is not a modeling job.
            """,
            """
None beyond the degree.
            """,
            """
Letter 1. Supervisor Erin Walsh, Prairie Mutual. "Taylor fixed a notebook the team had been copying, wrote down what it did, and left it in a state we still open. I recommend Taylor for further study. Taylor was reliable this summer."

Letter 2. Supervisor Mark Dalton, Prairie Mutual. "Taylor has been on time and pleasant since joining the reporting team. The monthly checks are accurate. I do not have a view of Taylor's technical research. Taylor is a fine colleague."
            """,
        ),
    )
)

PACKETS.append(
    (
        "09_casey_morgan.txt",
        packet(
            "Casey Morgan",
            "Illinois State University",
            "B.S. Information Systems, 2025",
            "3.20",
            """
Artificial intelligence is the future, and I want to be part of that future at Northwestern. I have always loved technology and I think MSAI would be an amazing experience. I am a people person and I work hard. In my classes I did several projects with AI, including a to-do app and a digit recognizer, and I learned a lot from them.

I believe I would contribute to the Northwestern community and make the most of every opportunity. My dream is to work in tech and use AI to help businesses. I am open to any specialization the faculty think is best. Thank you for your time and for considering me for this prestigious program. I know I can succeed if I am given the chance.
            """,
            """
No research experience.
            """,
            """
Course project, fall 2024: a to-do list web app for an information systems class. It stores tasks in a database. It does not use a learned model. Course project, spring 2025: a digit recognizer using a tutorial neural network on the MNIST images supplied by the instructor. I followed the tutorial and submitted the notebook.
            """,
            """
Help desk student employee, Illinois State technology support, 2023-2025. I reset passwords and imaged laptops.
            """,
            """
None.
            """,
            """
Letter 1. Supervisor Pat Nolan, campus help desk. "Casey is a hard worker and a pleasure to have on the desk. Students like Casey. I recommend Casey."

Letter 2. Instructor Jamie Cole, Illinois State. "Casey completed the required projects and attended class. Casey is a hardworking student. I am happy to support the application."
            """,
        ),
    )
)

PACKETS.append(
    (
        "10_drew_patel.txt",
        packet(
            "Drew Patel",
            "Boston University",
            "B.S. Biology, 2025",
            "3.88",
            """
I hope to study artificial intelligence at Northwestern so I can bring AI to medicine. Biology has been my whole education, and I have done well in it. I believe the next generation of doctors will need AI, and I want to be ready. MSAI is a famous program and Boston has shown me that I can handle hard classes. I am sure I can handle these classes too.

I have not taken a machine learning course. I took one introduction to Python as an elective in my junior year and I enjoyed it. I learn quickly. My plan is to arrive and take the courses, then apply AI to cancer or maybe medical images. I do not have a specific project yet. I am excited to find one with a professor. I know my grades show that I am serious, and I hope the committee will see that potential.
            """,
            """
No computational research. I volunteered in a wet lab for one semester washing glassware, fall 2023. I did not design an experiment.
            """,
            """
Introduction to Python, spring 2024, course assignments only. The final assignment was a script that plotted a CSV of heart rates from the instructor. I have no other programming projects.
            """,
            """
Peer tutor for introductory biology, Boston University, 2023-2025.
            """,
            """
College of Arts and Sciences prize for biology coursework, 2025. Dean's list every semester.
            """,
            """
Letter 1. Professor Laura Kim, Boston University. "Drew earned an A in both of my biology courses and tutored students who were failing the first exam. Drew is diligent and kind. I have not seen Drew write research code. On the academic record I do have, I recommend Drew."

Letter 2. Dr. Steven Cho, Boston University. "Drew was reliable in my laboratory as a volunteer. The tasks were preparatory. Drew followed instructions. I support Drew's interest in further study and I cannot speak to preparation in computer science."
            """,
        ),
    )
)

PACKETS.append(
    (
        "11_quinn_alvarez.txt",
        packet(
            "Quinn Alvarez",
            "Arizona State University",
            "B.S. Computer Science, 2024",
            "2.95",
            """
I am applying to MSAI because I want a fresh start in artificial intelligence at a top school. I think Northwestern can give me the environment I need to focus. I am interested in all areas of AI, from robotics to language, and I will work harder in graduate school than I did as an undergraduate. I had some research experience and I know what labs are like.

Please consider the person I am becoming and not only my GPA. I am passionate and I will contribute. A master's degree is my path into the industry. I would be grateful for an offer and I will make the most of it.
            """,
            """
Unpaid observer in a robotics lab, May 2024, about four weeks. I attended two group meetings and watched a doctoral student collect data. I did not write code for the lab and I am not on a paper.
            """,
            """
Course projects required by the degree: a socket chat program, a small web scraper, and a class assignment that trained a decision tree on a provided CSV. I do not have an independent project.
            """,
            """
Seasonal retail associate, 2022 and 2023 summers.
            """,
            """
None.
            """,
            """
Letter 1. Professor Alan Ruiz, Arizona State University. "Quinn completed my course. The project met the minimum specification. Quinn missed two deadlines and submitted the scraper a week late. I can confirm the degree progress. I do not have a stronger recommendation than that."

Letter 2. Graduate student Morgan Lee, Arizona State University. "Quinn visited our lab for a few weeks. Quinn was polite. Quinn did not take on a task. I cannot recommend Quinn for a research program on the basis of that visit."
            """,
        ),
    )
)

PACKETS.append(
    (
        "12_harper_singh.txt",
        packet(
            "Harper Singh",
            "University of Iowa",
            "B.A. Communications, 2024",
            "3.10",
            """
I am writing to apply for the MSAI program because artificial intelligence is changing communication and I want to be at the center of that change. I have a communications degree and I completed an online certificate in AI for everyone. The videos were inspiring. I believe my background in writing and presentations is exactly what technical teams are missing, and Northwestern is where I want to learn the technical side.

I do not have programming courses beyond the certificate quizzes. I am a fast learner and a strong communicator, and I know I can pick up the coding once I am in the classroom. My goal is to lead AI product teams. I would bring energy and storytelling to the cohort. I hope you will give me the chance to show that a nontraditional student belongs in this program. I will not waste it.
            """,
            """
No research experience.
            """,
            """
Online certificate, "AI for Everyone," 2025, with short quizzes. I did not write code. Class presentation project in a communications course: a slide deck about how chatbots change customer service, based on news articles.
            """,
            """
Social media assistant, a campus arts series, 2023-2024. I wrote posts and a newsletter. Intern, a local radio station, summer 2023, where I booked guests.
            """,
            """
Student radio volunteer of the semester, fall 2023.
            """,
            """
Letter 1. Station manager Robin Blake. "Harper booked guests and wrote clear introductions. Harper is articulate and reliable in a newsroom. I recommend Harper for work that uses those skills. I have not seen technical or quantitative work."

Letter 2. Instructor Caroline Weiss, University of Iowa. "Harper writes well and spoke confidently in my course. The chatbot presentation was polished. It was not a technical analysis. Harper is a strong communications student, and that is the basis of this letter."
            """,
        ),
    )
)


def write_pdf(text: str, dest: Path) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("Body", "", str(FONT))
    pdf.set_font("Body", size=11)
    pdf.multi_cell(0, 5.5, text)
    pdf.output(str(dest))


def main() -> None:
    PACKET_DIR.mkdir(parents=True, exist_ok=True)
    for filename, text in PACKETS:
        txt = PACKET_DIR / filename
        txt.write_text(text, encoding="utf-8")
        write_pdf(text, txt.with_suffix(".pdf"))
        print(f"wrote {txt.name} and {txt.with_suffix('.pdf').name}")


if __name__ == "__main__":
    main()
