"""The Mohanty family of Bhubaneswar, 2021–2026: who they are, which lab they go to, and what each report shows.

Values in `set` are exact, in each test's canonical unit (mg/dL, g/dL, %, µIU/mL …); everything else is sampled
around the person's own baseline and kept inside the lab's range, so a report is abnormal only where the story says.
All people, doctors, labs and imaging centres are fictional.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Visit:
    when: date
    lab: str
    package: str
    set: dict[str, float] = field(default_factory=dict)
    referrer: str = ""  # defaults to the person's doctor
    photo: bool = False  # uploaded as a phone photo of page 1
    conditions: list[str] = field(default_factory=list)  # e.g. "infection" shifts the white-cell differential
    note: str | None = None  # the family's own note on the report


@dataclass
class Imaging:
    when: date
    centre: str
    title: str
    image: str  # file in data/imaging/
    history: str
    technique: str
    findings: list[str]
    impression: list[str]
    kind: str = "imaging"
    record_title: str = ""
    notes: str | None = None


@dataclass
class Person:
    name: str
    sex: str
    dob: date
    relationship: str
    language: str
    doctor: str
    collection_point: str
    visits: list[Visit]
    imaging: list[Imaging] = field(default_factory=list)


# Laboratories (layouts and unit styles as in tools/synthetic) and their look on paper.
LAB_DETAILS = {
    "Anvaya Diagnostics": dict(email="reports@anvayadiagnostics.example", colour="#0f6b5c",
                               technologist="Sushree Mishra, DMLT"),
    "Mahanadi Clinical Laboratory": dict(email="care@mahanadilab.example", colour="#1f4e8c",
                                         technologist="Bikash Behera, B.Sc. MLT"),
    "Sanjeevani Path Lab": dict(email="hello@sanjeevanipath.example", colour="#8a3b12",
                                technologist="Kavya Gowda, DMLT"),
    "Prakriti Diagnostic Centre": dict(email="labs@prakritidiagnostics.example", colour="#2e6b2e",
                                       technologist="Rohit Chauhan, B.Sc. MLT"),
    "Nirmaya Health Labs": dict(email="reports@nirmayalabs.example", colour="#6b2e5f",
                                technologist="Soma Ghosh, DMLT"),
    "Kalinga Test House": dict(email="info@kalingatesthouse.example", colour="#9a6a12",
                               technologist="Pradeep Sahoo, DMLT"),
}

IMAGING_CENTRES = {
    "Utkal Imaging & Diagnostics": dict(address="Rasulgarh Square, Bhubaneswar 751010",
                                        email="imaging@utkalimaging.example", radiologist="Dr. Ananta Panigrahi"),
    "Indiranagar Scan Centre": dict(address="100 Feet Road, Indiranagar, Bengaluru 560038",
                                    email="desk@indiranagarscan.example", radiologist="Dr. Meera Raghunath"),
    "Sector 62 MRI & Imaging": dict(address="Sector 62, Noida 201309", email="mri@sector62imaging.example",
                                    radiologist="Dr. Vikram Sethi"),
}

CREDITS = {
    "chest-xray-normal-pa.jpg": "Image: Mikael Häggström, M.D. · CC0 1.0 · Wikimedia Commons",
    "chest-xray-consolidation.jpg": "Image: Malvinder S Parmar, BMC Infectious Diseases 2005, 5:30 · CC BY 2.0 · "
                                    "Wikimedia Commons",
    "knee-xray-osteoarthritis.jpg": "Image: James Heilman, MD · CC BY-SA 4.0 · Wikimedia Commons",
    "lumbar-mri-t2-sagittal.jpg": "Image: Stillwaterising · CC0 1.0 · Wikimedia Commons",
    "knee-mri-t2-sagittal.jpg": "Image: Pil Kang, Walter Reed Army Medical Center · Public domain · Wikimedia Commons",
}

D = date
FAMILY = [
    Person(
        name="Priya Mohanty", sex="female", dob=D(1974, 6, 18), relationship="self", language="en",
        doctor="Dr. Sanjukta Rath", collection_point="Main Centre",
        visits=[
            # Tired and gaining weight: her doctor checks the thyroid; she photographs the report.
            Visit(D(2021, 7, 14), "Kalinga Test House", "Thyroid Profile", {"tsh": 9.8, "ft4": 0.82, "ft3": 2.6},
                  photo=True, note="Feeling tired for months"),
            Visit(D(2021, 10, 20), "Kalinga Test House", "Thyroid Profile", {"tsh": 5.9, "ft4": 1.02, "ft3": 2.9},
                  note="3 months after starting thyroid tablets"),
            Visit(D(2022, 2, 9), "Anvaya Diagnostics", "Comprehensive Health Check",
                  {"tsh": 3.2, "ft4": 1.18, "hb": 10.4, "rbc": 3.95, "rdw": 16.2, "vitamin_d": 14,
                   "vitamin_b12": 380, "chol_total": 186, "hdl": 54, "tg": 118}),
            Visit(D(2022, 2, 16), "Anvaya Diagnostics", "Anaemia Profile",
                  {"hb": 10.5, "rbc": 3.98, "rdw": 16.0, "ferritin": 7, "iron": 32, "tibc": 440, "vitamin_d": 14,
                   "vitamin_b12": 372}, note="Iron tests the doctor asked for"),
            Visit(D(2022, 6, 15), "Anvaya Diagnostics", "Anaemia Profile",
                  {"hb": 11.3, "rbc": 4.1, "rdw": 15.1, "ferritin": 16, "iron": 55, "tibc": 400, "vitamin_d": 24}),
            Visit(D(2023, 3, 8), "Anvaya Diagnostics", "Anaemia Profile",
                  {"hb": 12.6, "rbc": 4.3, "rdw": 13.4, "ferritin": 38, "iron": 82, "tibc": 340, "vitamin_d": 27}),
            Visit(D(2024, 3, 12), "Kalinga Test House", "Thyroid Profile", {"tsh": 2.4, "ft4": 1.21, "ft3": 3.0}),
            Visit(D(2025, 4, 10), "Anvaya Diagnostics", "Comprehensive Health Check",
                  {"tsh": 2.8, "ft4": 1.15, "hb": 12.9, "vitamin_d": 16, "chol_total": 212, "hdl": 52, "tg": 150},
                  note="Knee pain on stairs"),
            Visit(D(2026, 7, 22), "Anvaya Diagnostics", "Comprehensive Health Check",
                  {"tsh": 2.1, "ft4": 1.2, "hb": 13.1, "vitamin_d": 31, "chol_total": 178, "hdl": 56, "tg": 120}),
        ],
        imaging=[Imaging(
            D(2025, 4, 12), "Utkal Imaging & Diagnostics", "X-RAY LEFT KNEE (AP VIEW, WEIGHT-BEARING)",
            "knee-xray-osteoarthritis.jpg",
            history="Pain in the left knee on climbing stairs for 4 months. No injury.",
            technique="Single weight-bearing anteroposterior radiograph of the left knee.",
            findings=["Reduction of the joint space, more marked in the medial compartment.",
                      "Marginal osteophytes at the femoral condyles and tibial plateau.",
                      "Subchondral sclerosis of the medial tibial plateau.",
                      "No fracture or dislocation. No loose body. Soft tissues unremarkable."],
            impression=["Degenerative changes of the left knee, consistent with osteoarthritis "
                        "(Kellgren–Lawrence grade 2–3)."],
            record_title="X-ray left knee", notes="Orthopaedic review booked"),
        ],
    ),
    Person(
        name="Ramesh Mohanty", sex="male", dob=D(1968, 3, 14), relationship="spouse", language="en",
        doctor="Dr. Prakash Nayak", collection_point="Corporate Health Desk",
        visits=[
            # Bank health checks every year; diabetes found in 2022, followed every six months.
            Visit(D(2021, 3, 18), "Mahanadi Clinical Laboratory", "Comprehensive Health Check",
                  {"hba1c": 6.2, "glucose_fasting": 112, "glucose_pp": 168, "tg": 190, "chol_total": 205, "hdl": 40,
                   "alt": 58, "ast": 41, "ggt": 64, "creatinine": 1.02, "uric_acid": 6.8, "psa": 0.9},
                  referrer="Bank Annual Health Check"),
            Visit(D(2022, 4, 6), "Mahanadi Clinical Laboratory", "Comprehensive Health Check",
                  {"hba1c": 6.7, "glucose_fasting": 136, "glucose_pp": 212, "tg": 210, "chol_total": 214, "hdl": 38,
                   "alt": 66, "ast": 45, "ggt": 70, "creatinine": 1.08, "uric_acid": 7.0, "psa": 1.0},
                  referrer="Bank Annual Health Check"),
            Visit(D(2022, 10, 12), "Anvaya Diagnostics", "Diabetes Care Profile",
                  {"hba1c": 6.4, "glucose_fasting": 118, "glucose_pp": 172, "creatinine": 1.10, "urine_acr": 22,
                   "tg": 170, "chol_total": 190, "hdl": 41}, note="On diabetes tablets since May"),
            Visit(D(2023, 4, 19), "Anvaya Diagnostics", "Diabetes Care Profile",
                  {"hba1c": 6.5, "glucose_fasting": 121, "glucose_pp": 176, "creatinine": 1.15, "urine_acr": 25,
                   "tg": 176, "chol_total": 192, "hdl": 40}),
            Visit(D(2023, 11, 22), "Anvaya Diagnostics", "Diabetes Care Profile",
                  {"hba1c": 6.9, "glucose_fasting": 138, "glucose_pp": 205, "creatinine": 1.20, "urine_acr": 34,
                   "tg": 188, "chol_total": 201, "hdl": 39}, note="Festival month, walks stopped"),
            Visit(D(2024, 6, 5), "Mahanadi Clinical Laboratory", "Comprehensive Health Check",
                  {"hba1c": 7.3, "glucose_fasting": 148, "glucose_pp": 236, "chol_total": 228, "hdl": 38, "tg": 200,
                   "alt": 72, "ast": 52, "ggt": 78, "creatinine": 1.32, "uric_acid": 7.4, "psa": 1.1},
                  referrer="Bank Annual Health Check"),
            Visit(D(2025, 1, 15), "Anvaya Diagnostics", "Liver and Kidney Profile",
                  {"creatinine": 1.45, "urea": 46, "potassium": 5.1, "alt": 64, "ast": 47, "ggt": 70,
                   "uric_acid": 7.6}),
            Visit(D(2025, 8, 20), "Anvaya Diagnostics", "Diabetes Care Profile",
                  {"hba1c": 7.6, "glucose_fasting": 156, "glucose_pp": 248, "creatinine": 1.43, "urine_acr": 60,
                   "tg": 196, "chol_total": 205, "hdl": 38}),
            Visit(D(2026, 2, 11), "Mahanadi Clinical Laboratory", "Comprehensive Health Check",
                  {"hba1c": 7.0, "glucose_fasting": 132, "glucose_pp": 198, "chol_total": 176, "hdl": 42, "tg": 150,
                   "alt": 45, "ast": 36, "ggt": 52, "creatinine": 1.48, "uric_acid": 6.9, "psa": 1.2},
                  referrer="Bank Annual Health Check", note="Diet changed in September, walking daily"),
            Visit(D(2026, 8, 19), "Anvaya Diagnostics", "Diabetes Care Profile",
                  {"hba1c": 6.7, "glucose_fasting": 124, "glucose_pp": 181, "creatinine": 1.46, "urine_acr": 38,
                   "tg": 142, "chol_total": 170, "hdl": 43}),
        ],
        imaging=[Imaging(
            D(2024, 6, 5), "Utkal Imaging & Diagnostics", "X-RAY CHEST (PA VIEW)", "chest-xray-normal-pa.jpg",
            history="Annual health check. No complaints.",
            technique="Single posteroanterior radiograph of the chest in full inspiration.",
            findings=["Both lung fields are clear. No consolidation, mass or pleural effusion.",
                      "Cardiac size within normal limits (cardiothoracic ratio below 0.5).",
                      "Both hila and the mediastinum are normal. Costophrenic angles are clear.",
                      "Visualised bones are normal."],
            impression=["Normal chest radiograph."], record_title="Chest X-ray"),
        ],
    ),
    Person(
        name="Kamala Devi Mohanty", sex="female", dob=D(1947, 1, 5), relationship="parent", language="or",
        doctor="Dr. Bijay Kumar Das", collection_point="Home Collection",
        visits=[
            # Slowly failing kidneys, followed by her physician; one dangerous potassium in April 2025.
            Visit(D(2022, 8, 10), "Kalinga Test House", "Liver and Kidney Profile",
                  {"creatinine": 1.30, "urea": 52, "potassium": 4.8, "albumin": 3.8}, photo=True),
            Visit(D(2023, 2, 2), "Nirmaya Health Labs", "Liver and Kidney Profile",
                  {"creatinine": 1.42, "urea": 55, "potassium": 4.9, "albumin": 3.8},
                  referrer="Dr. Arindam Sen", note="Tested in Kolkata while visiting her brother"),
            Visit(D(2023, 9, 6), "Kalinga Test House", "Anaemia Profile",
                  {"hb": 10.1, "rbc": 3.5, "ferritin": 95, "iron": 58, "tibc": 290, "vitamin_b12": 320,
                   "folate": 7, "vitamin_d": 18}),
            Visit(D(2024, 5, 14), "Kalinga Test House", "Liver and Kidney Profile",
                  {"creatinine": 1.62, "urea": 62, "potassium": 5.3, "albumin": 3.7}),
            Visit(D(2025, 4, 3), "Kalinga Test House", "Liver and Kidney Profile",
                  {"creatinine": 1.90, "urea": 78, "potassium": 6.6, "sodium": 134, "bicarbonate": 19,
                   "albumin": 3.6}, note="Weak and dizzy; the doctor sent her to hospital the same evening"),
            Visit(D(2025, 4, 7), "Kalinga Test House", "Liver and Kidney Profile",
                  {"creatinine": 1.75, "urea": 70, "potassium": 5.0, "sodium": 137, "albumin": 3.6},
                  note="Repeat after the hospital stay"),
            Visit(D(2026, 1, 21), "Kalinga Test House", "Anaemia Profile",
                  {"hb": 10.4, "rbc": 3.6, "ferritin": 120, "iron": 62, "tibc": 285, "vitamin_d": 26}),
            Visit(D(2026, 7, 15), "Kalinga Test House", "Liver and Kidney Profile",
                  {"creatinine": 1.85, "urea": 74, "potassium": 5.2, "albumin": 3.6}),
        ],
        imaging=[Imaging(
            D(2024, 11, 20), "Utkal Imaging & Diagnostics", "MRI LUMBOSACRAL SPINE", "lumbar-mri-t2-sagittal.jpg",
            history="Low back pain for 6 months, worse on standing; no weakness.",
            technique="1.5 T MRI; sagittal T1 and T2, axial T2 images of the lumbosacral spine. Representative "
                      "sagittal T2 image shown.",
            findings=["Normal lumbar lordosis. Vertebral body heights are maintained.",
                      "Loss of T2 signal and mild loss of height of the L4–L5 and L5–S1 discs (desiccation).",
                      "Diffuse posterior disc bulge at L4–L5 indenting the thecal sac, with mild narrowing of "
                      "both lateral recesses. No nerve root compression.",
                      "Conus medullaris ends normally at L1. Paravertebral soft tissues are normal."],
            impression=["Degenerative disc disease at L4–L5 and L5–S1 with a disc bulge at L4–L5.",
                        "No significant spinal canal stenosis or nerve root compression."],
            record_title="MRI lower back"),
        ],
    ),
    Person(
        name="Ananya Mohanty", sex="female", dob=D(2002, 4, 9), relationship="child", language="en",
        doctor="Dr. Kiran Hegde", collection_point="Indiranagar Branch",
        visits=[
            Visit(D(2023, 9, 4), "Sanjeevani Path Lab", "Basic Health Check", referrer="Pre-employment Check"),
            # Fever and cough for five days: a phone photo sent to the family WhatsApp group.
            Visit(D(2024, 7, 18), "Sanjeevani Path Lab", "Fever Panel", {"wbc": 14.2, "crp": 48, "esr": 42},
                  photo=True, conditions=["infection"], note="Fever and cough for 5 days"),
            Visit(D(2024, 8, 8), "Sanjeevani Path Lab", "Fever Panel", {"wbc": 7.1, "crp": 2.1, "esr": 14},
                  note="After the antibiotic course"),
            Visit(D(2025, 2, 24), "Sanjeevani Path Lab", "Anaemia Profile",
                  {"vitamin_b12": 148, "hb": 12.1, "rbc": 3.7, "folate": 11, "ferritin": 42, "vitamin_d": 21},
                  note="Tingling in the feet"),
            Visit(D(2025, 9, 10), "Sanjeevani Path Lab", "Anaemia Profile",
                  {"vitamin_b12": 410, "hb": 12.8, "rbc": 4.2, "ferritin": 45, "vitamin_d": 24}),
            Visit(D(2026, 6, 12), "Sanjeevani Path Lab", "Comprehensive Health Check",
                  {"vitamin_d": 22, "vitamin_b12": 455}),
        ],
        imaging=[Imaging(
            D(2024, 7, 19), "Indiranagar Scan Centre", "X-RAY CHEST (PA VIEW)", "chest-xray-consolidation.jpg",
            history="Fever and productive cough for 5 days.",
            technique="Single posteroanterior radiograph of the chest.",
            findings=["Patchy consolidation in the right mid and lower zones, and in the left lower zone.",
                      "No pleural effusion. No pneumothorax.",
                      "Cardiac size and mediastinum within normal limits.",
                      "Visualised bones are normal."],
            impression=["Bilateral lower-zone consolidation, right more than left, suggestive of an infective "
                        "process. Follow-up radiograph after treatment is suggested."],
            record_title="Chest X-ray"),
        ],
    ),
    Person(
        name="Arjun Mohanty", sex="male", dob=D(1997, 11, 23), relationship="child", language="en",
        doctor="Dr. Neha Kapoor", collection_point="Sector 18 Centre",
        visits=[
            Visit(D(2022, 12, 7), "Prakriti Diagnostic Centre", "Basic Health Check",
                  {"tg": 212, "chol_total": 196, "hdl": 39}, referrer="Company Health Check"),
            Visit(D(2023, 6, 14), "Prakriti Diagnostic Centre", "Comprehensive Health Check",
                  {"alt": 88, "ast": 54, "ggt": 72, "tg": 240, "chol_total": 214, "hdl": 37, "uric_acid": 7.6,
                   "vitamin_d": 12}, note="Desk job, no exercise, lots of outside food"),
            Visit(D(2024, 6, 19), "Prakriti Diagnostic Centre", "Liver and Kidney Profile",
                  {"alt": 61, "ast": 42, "ggt": 55, "uric_acid": 7.2}, note="Gym three days a week since January"),
            Visit(D(2025, 6, 25), "Prakriti Diagnostic Centre", "Comprehensive Health Check",
                  {"alt": 36, "ast": 28, "ggt": 30, "tg": 140, "chol_total": 182, "hdl": 46, "uric_acid": 6.1,
                   "vitamin_d": 23.2}),
            Visit(D(2026, 5, 20), "Prakriti Diagnostic Centre", "Basic Health Check",
                  {"tg": 118, "chol_total": 172, "hdl": 48}, referrer="Company Health Check"),
        ],
        imaging=[Imaging(
            D(2023, 11, 9), "Sector 62 MRI & Imaging", "MRI RIGHT KNEE", "knee-mri-t2-sagittal.jpg",
            history="Twisting injury while playing football 3 weeks ago; pain and occasional locking.",
            technique="1.5 T MRI of the right knee; sagittal, coronal and axial PD and T2 images. Representative "
                      "sagittal image shown (arrow).",
            findings=["Small focal osteochondral lesion of the femoral condyle (arrow), with intact overlying "
                      "cartilage and no loose fragment.",
                      "Cruciate and collateral ligaments are intact.",
                      "Menisci show normal signal. No joint effusion of significance.",
                      "Patellofemoral joint is normal."],
            impression=["Small stable osteochondral lesion of the femoral condyle.",
                        "No ligament or meniscal tear."],
            record_title="MRI right knee", notes="Physiotherapy for 6 weeks; back to football in March"),
        ],
    ),
]
