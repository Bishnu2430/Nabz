"""Write data/catalogue/symptoms.csv: plain-language symptoms that can go along with an out-of-range result.

    python -m tools.catalogue_symptoms

Every list is taken from the "Why do I need this test?" section of the NLM MedlinePlus page for that test (public
domain), shortened to everyday words. `kind`:
- symptoms:    "can go along with symptoms such as …"
- often_none:  "often causes no symptoms at first; it can go along with …" (MedlinePlus says early stages are silent)
- none:        "usually doesn't cause symptoms" (lipids, phosphate)
Hindi and Odia are drafts for the native-speaker review (T2.5); the clinical advisor reviews the lists before M3.
"""

from __future__ import annotations

import csv
from pathlib import Path

from app.core.config import settings

# symptom key -> (English, Hindi, Odia)
V = {
    "tired": ("tiredness", "थकान", "ଥକାପଣ"),
    "weak": ("weakness", "कमज़ोरी", "ଦୁର୍ବଳତା"),
    "dizzy": ("dizziness", "चक्कर आना", "ମୁଣ୍ଡ ବୁଲାଇବା"),
    "breath": ("shortness of breath", "साँस फूलना", "ନିଶ୍ୱାସ ନେବାରେ କଷ୍ଟ"),
    "pale": ("pale skin", "फीकी त्वचा", "ଫିକା ଚର୍ମ"),
    "cold_hands": ("cold hands and feet", "हाथ-पैर ठंडे रहना", "ହାତଗୋଡ଼ ଥଣ୍ଡା ରହିବା"),
    "headache": ("headache", "सिरदर्द", "ମୁଣ୍ଡବିନ୍ଧା"),
    "vision": ("vision problems", "देखने में दिक़्क़त", "ଦେଖିବାରେ ଅସୁବିଧା"),
    "fever": ("fever", "बुखार", "ଜ୍ୱର"),
    "chills": ("chills", "ठंड लगकर कँपकँपी", "ଥରି ଥରି ଶୀତ ଲାଗିବା"),
    "aches": ("body aches", "बदन दर्द", "ଦେହ ବିନ୍ଧା"),
    "bruise": ("bruising easily", "आसानी से नील पड़ना", "ସହଜରେ କଳଙ୍କ ପଡ଼ିବା"),
    "nosebleed": ("nosebleeds", "नाक से खून आना", "ନାକରୁ ରକ୍ତ ବାହାରିବା"),
    "bleed_long": ("bleeding for a long time after small cuts", "छोटी चोट पर देर तक खून बहना",
                   "ଛୋଟ କଟାରୁ ଅଧିକ ସମୟ ରକ୍ତ ବାହାରିବା"),
    "red_spots": ("tiny red spots on the skin", "त्वचा पर छोटे लाल धब्बे", "ଚର୍ମରେ ଛୋଟ ନାଲି ଦାଗ"),
    "numb": ("numbness or tingling in the hands or feet", "हाथ-पैरों में सुन्नपन या झनझनाहट",
             "ହାତଗୋଡ଼ରେ ଅବଶ ବା ଝିମ୍ଝିମ୍ ଲାଗିବା"),
    "thirst": ("feeling very thirsty", "बहुत प्यास लगना", "ବହୁତ ଶୋଷ ଲାଗିବା"),
    "urinate_often": ("passing urine often", "बार-बार पेशाब आना", "ବାରମ୍ବାର ପରିସ୍ରା ହେବା"),
    "blurred": ("blurred vision", "धुंधला दिखना", "ଝାପସା ଦେଖାଯିବା"),
    "slow_heal": ("sores that heal slowly", "घाव देर से भरना", "ଘା ଧୀରେ ଶୁଖିବା"),
    "weight_loss": ("losing weight without trying", "बिना कोशिश वज़न घटना", "ଚେଷ୍ଟା ବିନା ଓଜନ କମିବା"),
    "shaky": ("feeling shaky", "कँपकँपी महसूस होना", "ଥରିବା"),
    "hunger": ("hunger", "भूख लगना", "ଭୋକ ଲାଗିବା"),
    "fast_heart": ("a fast heartbeat", "तेज़ धड़कन", "ଦ୍ରୁତ ହୃଦସ୍ପନ୍ଦନ"),
    "swelling": ("swelling in the legs, ankles or face", "पैरों, टखनों या चेहरे पर सूजन",
                 "ଗୋଡ଼, ଗୋଇଠି ବା ମୁହଁରେ ଫୁଲା"),
    "urine_change": ("passing more or less urine than usual", "सामान्य से ज़्यादा या कम पेशाब आना",
                     "ସାଧାରଣଠାରୁ ଅଧିକ ବା କମ୍ ପରିସ୍ରା ହେବା"),
    "itch": ("itching", "खुजली", "କୁଣ୍ଡାଇ ହେବା"),
    "joint_sudden": ("sudden joint pain, often in the big toe", "जोड़ों में अचानक दर्द, अक्सर पैर के अँगूठे में",
                     "ଗଣ୍ଠିରେ ହଠାତ୍ ଯନ୍ତ୍ରଣା, ପ୍ରାୟତଃ ଗୋଡ଼ର ବୁଢ଼ା ଆଙ୍ଗୁଠିରେ"),
    "joint_red": ("swelling or redness around a joint", "जोड़ के आसपास सूजन या लाली", "ଗଣ୍ଠି ପାଖରେ ଫୁଲା ବା ନାଲି"),
    "confusion": ("confusion", "उलझन महसूस होना", "ଦ୍ୱନ୍ଦ୍ୱ ଲାଗିବା"),
    "twitch": ("muscle twitching", "मांसपेशियों का फड़कना", "ମାଂସପେଶୀ ଥରିବା"),
    "little_urine": ("passing very little urine", "बहुत कम पेशाब आना", "ବହୁତ କମ୍ ପରିସ୍ରା ହେବା"),
    "irregular_heart": ("an irregular heartbeat", "अनियमित धड़कन", "ଅନିୟମିତ ହୃଦସ୍ପନ୍ଦନ"),
    "muscle_weak": ("muscle weakness", "मांसपेशियों में कमज़ोरी", "ମାଂସପେଶୀ ଦୁର୍ବଳତା"),
    "nausea": ("nausea", "जी मिचलाना", "ବାନ୍ତି ଭାବ"),
    "cramps": ("muscle cramps", "मांसपेशियों में ऐंठन", "ମାଂସପେଶୀ ଟାଣି ହେବା"),
    "constipation": ("constipation", "कब्ज़", "କୋଷ୍ଠକାଠିନ୍ୟ"),
    "aches_bone": ("bone or muscle aches", "हड्डियों या मांसपेशियों में दर्द", "ହାଡ଼ ବା ମାଂସପେଶୀ ବିନ୍ଧା"),
    "tingle_lips": ("tingling in the lips, fingers or feet", "होंठों, उँगलियों या पैरों में झनझनाहट",
                    "ଓଠ, ଆଙ୍ଗୁଠି ବା ପାଦରେ ଝିମ୍ଝିମ୍"),
    "yellow": ("yellow skin or eyes", "त्वचा या आँखों का पीला पड़ना", "ଚର୍ମ ବା ଆଖି ହଳଦିଆ ହେବା"),
    "dark_urine": ("dark urine", "गहरे रंग का पेशाब", "ଗାଢ଼ ରଙ୍ଗର ପରିସ୍ରା"),
    "pale_stool": ("pale stools", "हल्के रंग का मल", "ଫିକା ରଙ୍ଗର ମଳ"),
    "belly_pain": ("belly pain", "पेट दर्द", "ପେଟ ବିନ୍ଧା"),
    "appetite": ("loss of appetite", "भूख न लगना", "ଭୋକ ନ ଲାଗିବା"),
    "swelling_belly": ("swelling in the feet, ankles or belly", "पैरों, टखनों या पेट में सूजन",
                       "ପାଦ, ଗୋଇଠି ବା ପେଟରେ ଫୁଲା"),
    "weight_gain": ("weight gain", "वज़न बढ़ना", "ଓଜନ ବଢ଼ିବା"),
    "feel_cold": ("feeling cold easily", "जल्दी ठंड लगना", "ଶୀଘ୍ର ଥଣ୍ଡା ଲାଗିବା"),
    "dry_skin": ("dry skin", "रूखी त्वचा", "ଶୁଖିଲା ଚର୍ମ"),
    "nervous": ("feeling nervous or irritable", "घबराहट या चिड़चिड़ापन", "ଅସ୍ଥିରତା ବା ଚିଡ଼ଚିଡ଼ାପଣ"),
    "sleep": ("trouble sleeping", "नींद न आना", "ନିଦ ନ ହେବା"),
    "feel_hot": ("feeling hot and sweaty", "गर्मी और पसीना ज़्यादा लगना", "ଅଧିକ ଗରମ ଓ ଝାଳ ହେବା"),
    "bone_pain": ("bone pain", "हड्डियों में दर्द", "ହାଡ଼ ବିନ୍ଧା"),
    "muscle_aches": ("aching, weak muscles", "मांसपेशियों में दर्द और कमज़ोरी", "ମାଂସପେଶୀ ବିନ୍ଧା ଓ ଦୁର୍ବଳତା"),
    "memory": ("memory problems", "याददाश्त की दिक़्क़त", "ସ୍ମୃତି ସମସ୍ୟା"),
    "joint_pain": ("joint pain", "जोड़ों में दर्द", "ଗଣ୍ଠି ଯନ୍ତ୍ରଣା"),
    "skin_colour": ("changes in skin colour", "त्वचा के रंग में बदलाव", "ଚର୍ମ ରଙ୍ଗ ବଦଳିବା"),
    "stiff": ("joint stiffness", "जोड़ों में अकड़न", "ଗଣ୍ଠି ଶକ୍ତ ହେବା"),
    "painful_urine": ("pain when passing urine", "पेशाब में जलन या दर्द", "ପରିସ୍ରାରେ ଯନ୍ତ୍ରଣା"),
    "blood_urine": ("blood in the urine", "पेशाब में खून", "ପରିସ୍ରାରେ ରକ୍ତ"),
    "back_pain": ("back or belly pain", "पीठ या पेट में दर्द", "ପିଠି ବା ପେଟ ବିନ୍ଧା"),
}

LAB = "https://medlineplus.gov/lab-tests/"
ANAEMIA = ["tired", "weak", "dizzy", "breath", "pale"]
HIGH_SUGAR = ["thirst", "urinate_often", "blurred", "tired", "slow_heal"]
LOW_SUGAR = ["shaky", "hunger", "dizzy", "headache", "fast_heart"]
KIDNEY = ["swelling", "tired", "urine_change", "itch"]
LIVER = ["tired", "appetite", "nausea", "yellow", "dark_urine"]
HYPO_THYROID = ["tired", "weight_gain", "feel_cold", "dry_skin", "constipation"]
HYPER_THYROID = ["weight_loss", "fast_heart", "nervous", "sleep", "feel_hot"]
LOW_IRON = ["tired", "weak", "dizzy", "breath", "pale"]
HIGH_IRON = ["tired", "joint_pain", "belly_pain", "skin_colour"]

# (test_code, direction, kind, symptom keys, MedlinePlus page)
ROWS = [
    ("hb", "low", "symptoms", ANAEMIA + ["cold_hands"], "hemoglobin-test"),
    ("hct", "low", "symptoms", ANAEMIA, "hematocrit-test"),
    ("hct", "high", "symptoms", ["headache", "dizzy", "tired", "breath"], "hematocrit-test"),
    ("rbc", "low", "symptoms", ANAEMIA, "red-blood-cell-rbc-count"),
    ("rbc", "high", "symptoms", ["headache", "dizzy", "vision"], "red-blood-cell-rbc-count"),
    ("mcv", "low", "symptoms", ANAEMIA, "mcv-mean-corpuscular-volume"),
    ("mcv", "high", "symptoms", ANAEMIA, "mcv-mean-corpuscular-volume"),
    ("mch", "low", "symptoms", ANAEMIA + ["cold_hands"], "red-blood-cell-rbc-indices"),
    ("mchc", "low", "symptoms", ANAEMIA + ["cold_hands"], "red-blood-cell-rbc-indices"),
    ("rdw", "high", "symptoms", ANAEMIA, "rdw-red-cell-distribution-width"),
    ("wbc", "high", "symptoms", ["fever", "chills", "aches", "headache"], "white-blood-count-wbc"),
    ("plt", "low", "symptoms", ["bruise", "nosebleed", "bleed_long", "red_spots"], "platelet-tests"),
    ("plt", "high", "symptoms", ["headache", "dizzy", "weak", "numb"], "platelet-tests"),
    ("esr", "high", "symptoms", ["headache", "fever", "weight_loss", "stiff"], "erythrocyte-sedimentation-rate-esr"),
    ("crp", "high", "symptoms", ["fever", "chills", "fast_heart", "nausea"], "c-reactive-protein-crp-test"),
    ("hs_crp", "high", "none", [], "c-reactive-protein-crp-test"),
    ("glucose_fasting", "high", "symptoms", HIGH_SUGAR, "blood-glucose-test"),
    ("glucose_pp", "high", "symptoms", HIGH_SUGAR, "blood-glucose-test"),
    ("glucose_random", "high", "symptoms", HIGH_SUGAR, "blood-glucose-test"),
    ("glucose_fasting", "low", "symptoms", LOW_SUGAR, "blood-glucose-test"),
    ("glucose_pp", "low", "symptoms", LOW_SUGAR, "blood-glucose-test"),
    ("glucose_random", "low", "symptoms", LOW_SUGAR, "blood-glucose-test"),
    ("hba1c", "high", "symptoms", ["thirst", "urinate_often", "blurred", "numb", "tired"], "hemoglobin-a1c-hba1c-test"),
    ("eag", "high", "symptoms", ["thirst", "urinate_often", "blurred", "numb", "tired"], "hemoglobin-a1c-hba1c-test"),
    ("chol_total", "high", "none", [], "cholesterol-levels"),
    ("ldl", "high", "none", [], "cholesterol-levels"),
    ("non_hdl", "high", "none", [], "cholesterol-levels"),
    ("vldl", "high", "none", [], "cholesterol-levels"),
    ("chol_hdl_ratio", "high", "none", [], "cholesterol-levels"),
    ("hdl", "low", "none", [], "cholesterol-levels"),
    ("tg", "high", "none", [], "triglycerides-test"),
    ("creatinine", "high", "often_none", KIDNEY, "creatinine-test"),
    ("urea", "high", "often_none", KIDNEY, "bun-blood-urea-nitrogen"),
    ("bun", "high", "often_none", KIDNEY, "bun-blood-urea-nitrogen"),
    ("egfr", "low", "often_none", KIDNEY, "glomerular-filtration-rate-gfr-test"),
    ("urine_acr", "high", "none", [], "microalbumin-creatinine-ratio"),
    ("uric_acid", "high", "symptoms", ["joint_sudden", "joint_red"], "uric-acid-test"),
    ("sodium", "low", "symptoms", ["weak", "tired", "confusion", "twitch"], "sodium-blood-test"),
    ("sodium", "high", "symptoms", ["thirst", "little_urine", "confusion", "twitch"], "sodium-blood-test"),
    ("potassium", "high", "symptoms", ["irregular_heart", "tired", "muscle_weak", "nausea"], "potassium-blood-test"),
    ("potassium", "low", "symptoms", ["irregular_heart", "cramps", "muscle_weak", "constipation"],
     "potassium-blood-test"),
    ("calcium", "high", "symptoms", ["constipation", "thirst", "urinate_often", "tired", "aches_bone"],
     "calcium-blood-test"),
    ("calcium", "low", "symptoms", ["cramps", "tingle_lips", "irregular_heart"], "calcium-blood-test"),
    ("magnesium", "low", "symptoms", ["cramps", "tired", "numb", "nausea"], "magnesium-blood-test"),
    ("phosphorus", "high", "none", [], "phosphate-in-blood"),
    ("phosphorus", "low", "none", [], "phosphate-in-blood"),
    ("bili_total", "high", "symptoms", ["yellow", "dark_urine", "pale_stool", "belly_pain"], "bilirubin-blood-test"),
    ("bili_direct", "high", "symptoms", ["yellow", "dark_urine", "pale_stool", "belly_pain"], "bilirubin-blood-test"),
    ("bili_indirect", "high", "symptoms", ["yellow", "dark_urine", "belly_pain"], "bilirubin-blood-test"),
    ("alt", "high", "often_none", LIVER, "alt-blood-test"),
    ("ast", "high", "often_none", LIVER, "ast-test"),
    ("alp", "high", "often_none", LIVER + ["bone_pain"], "alkaline-phosphatase"),
    ("ggt", "high", "often_none", LIVER, "gamma-glutamyl-transferase-ggt-test"),
    ("albumin", "low", "symptoms", ["swelling_belly", "tired", "appetite"], "albumin-blood-test"),
    ("protein_total", "low", "symptoms", ["swelling_belly", "tired", "weight_loss"],
     "total-protein-and-albumin-globulin-a-g-ratio"),
    ("tsh", "high", "symptoms", HYPO_THYROID, "tsh-thyroid-stimulating-hormone-test"),
    ("tsh", "low", "symptoms", HYPER_THYROID, "tsh-thyroid-stimulating-hormone-test"),
    ("ft4", "low", "symptoms", HYPO_THYROID, "thyroxine-t4-test"),
    ("ft4", "high", "symptoms", HYPER_THYROID, "thyroxine-t4-test"),
    ("t4", "low", "symptoms", HYPO_THYROID, "thyroxine-t4-test"),
    ("t4", "high", "symptoms", HYPER_THYROID, "thyroxine-t4-test"),
    ("ft3", "high", "symptoms", HYPER_THYROID, "triiodothyronine-t3-tests"),
    ("t3", "high", "symptoms", HYPER_THYROID, "triiodothyronine-t3-tests"),
    ("vitamin_d", "low", "symptoms", ["bone_pain", "muscle_aches"], "vitamin-d-test"),
    ("vitamin_b12", "low", "symptoms", ["tired", "weak", "numb", "memory"], "vitamin-b-test"),
    ("folate", "low", "symptoms", ["tired", "weak", "memory"], "vitamin-b-test"),
    ("iron", "low", "symptoms", LOW_IRON, "iron-tests"),
    ("iron", "high", "symptoms", HIGH_IRON, "iron-tests"),
    ("ferritin", "low", "symptoms", LOW_IRON, "ferritin-blood-test"),
    ("ferritin", "high", "symptoms", HIGH_IRON, "ferritin-blood-test"),
    ("tsat", "low", "symptoms", LOW_IRON, "iron-tests"),
    ("urine_pus", "high", "symptoms", ["painful_urine", "urinate_often", "back_pain"], "blood-in-urine"),
    ("urine_rbc", "high", "symptoms", ["painful_urine", "urinate_often", "back_pain"], "blood-in-urine"),
    ("psa", "high", "often_none", ["painful_urine", "blood_urine", "back_pain"], "prostate-specific-antigen-psa-test"),
]


def main() -> None:
    out = Path(settings.data_dir) / "catalogue" / "symptoms.csv"
    with out.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["test_code", "direction", "kind", "symptoms_en", "symptoms_hi", "symptoms_or", "source"])
        for code, direction, kind, keys, page in ROWS:
            w.writerow([code, direction, kind, *("|".join(V[k][i] for k in keys) for i in range(3)), LAB + page])
    print(f"wrote {len(ROWS)} rows to {out}")


if __name__ == "__main__":
    main()
