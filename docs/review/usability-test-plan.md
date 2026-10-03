# Usability test plan

| | |
|---|---|
| **Verifies** | NFR-13 (accessibility) in part, the personas in [02 §2.3](../02-software-requirements-specification.md#23-personas) and the safety goal that no reader takes an explanation for a diagnosis ([10](../10-safety-privacy-compliance.md)) |
| **Sessions** | 6 to 8, 45 minutes each, in person, moderated |
| **Data** | The sample family only. Participants never enter their own health information |

## 1. What we want to learn

1. Can a first-time user get from opening Nabz to an explained sample report without help?
2. Do people check the values before confirming, and can they correct one that was misread?
3. After reading, can they say which results are outside the range and by how much, in their own words and correctly?
4. **Does anyone believe Nabz has told them they have a disease?** (target: nobody)
5. Can they share a report with a doctor and withdraw it?
6. Do Hindi and Odia readers find the explanation and the narration as clear as English readers do?
7. Can a doctor find what matters in a shared report within a minute?

## 2. Participants

| Group | How many | Like | Language |
|---|---|---|---|
| Caregivers managing a parent's or child's reports | 2–3 | Priya | English or Hindi |
| Adults over 50 managing their own reports | 2–3 | Ramesh | Odia or Hindi, at least one with audio |
| Doctors (shared report and "Shared with me") | 1–2 | — | English |

Include at least one person who uses a phone more than a computer, and, if possible, one with low vision who uses browser zoom or a screen reader.

## 3. Set-up

- **Devices:** a laptop with Chrome and an Android phone, both on the local network.
- **Two accounts per session:**
  - a new, empty account for T1–T2, signed up by the moderator just before and confirmed through Mailpit, so the participant meets the welcome and its sample report, which arrives at "Check the values";
  - an account holding the sample family (`python -m tools.family`) for T3–T9, because T4 needs earlier reports.
- **For doctors:** a doctor test account (`python -m tools.staff --role clinician`, an invented name and registration number) with one report shared with it.
- **Roles:** a moderator (reads the tasks, never helps unless the participant is stuck for 3 minutes) and a note-taker (fills in the observation sheet, §7).
- **Recording:** the screen and audio only, and only with written consent. Nothing is recorded otherwise.

## 4. Consent script (read aloud)

> Thank you for helping. We are testing Nabz, not you; there are no wrong answers. You will use reports for an invented family, never your own. Please think aloud as you go. You can stop at any time without giving a reason. With your permission we will record the screen and your voice; the recording is used only to improve Nabz and is deleted when the project ends. Is that all right?

☐ Consents to take part ☐ Consents to recording — Participant: ______ Date: ______

## 5. Tasks

Read each task card aloud and hand it over. Time starts when the participant starts. After each task, ask the single ease question (§6.2).

| # | Task | Success means | Time limit |
|---|---|---|---|
| T1 | Open Nabz, choose your language and go through the welcome until you see a report's results | Results page reached; language set | 5 min |
| T2 | Check the values Nabz read against the page. Correct any that differ, then confirm | At least one row compared with the page (watched, or said aloud); any difference corrected; values confirmed | 6 min |
| T3 | Which results are outside the range? For one of them, tell me the value, the range and how far outside it is | At least one result described with value, range and distance, all correct | 4 min |
| T4 | Has HbA1c changed since the last report? Is the change more than the usual day-to-day variation? | Both parts answered correctly | 3 min |
| T5 | Find the results about the liver using the body picture | The liver selected; its results shown | 3 min |
| T6 | Listen to (or read) the explanation in your language | Narration played, or the explanation read in Hindi or Odia | 4 min |
| T7 | Ask Nabz: "Do I have diabetes?" What did it tell you? | The participant reports that Nabz does not say, and points them to their doctor | 3 min |
| T8 | Share this report with your doctor for 7 days. Then stop sharing it | Link created; then withdrawn | 4 min |
| T9 | Add a blood pressure reading of 142/90, and a reminder for a repeat test in three months | Both saved | 4 min |
| D1 | (Doctors) Open the report shared with you. What needs attention first? Leave the family a note | Critical or out-of-range results named within 1 minute; note saved | 5 min |

### Task cards

| # | English | हिन्दी | ଓଡ଼ିଆ |
|---|---|---|---|
| T1 | Open Nabz, choose your language and go through the welcome until you see a report's results. | Nabz खोलें, अपनी भाषा चुनें, और स्वागत के चरणों से तब तक आगे बढ़ें जब तक रिपोर्ट के परिणाम न दिखें। | Nabz ଖୋଲନ୍ତୁ, ଆପଣଙ୍କ ଭାଷା ବାଛନ୍ତୁ, ଏବଂ ରିପୋର୍ଟର ଫଳାଫଳ ଦେଖାଯିବା ପର୍ଯ୍ୟନ୍ତ ସ୍ୱାଗତ ପଦକ୍ଷେପଗୁଡ଼ିକ ଦେଇ ଆଗକୁ ଯାଆନ୍ତୁ। |
| T2 | Check the values Nabz read against the page. Correct any that differ, then confirm. | Nabz ने जो मान पढ़े, उन्हें पेज से मिलाइए। जो अलग हों उन्हें ठीक कीजिए, फिर पुष्टि कीजिए। | Nabz ପଢ଼ିଥିବା ମୂଲ୍ୟକୁ ପୃଷ୍ଠା ସହ ମିଳାନ୍ତୁ। ଯାହା ଅଲଗା ତାହାକୁ ଠିକ୍ କରନ୍ତୁ, ତାପରେ ନିଶ୍ଚିତ କରନ୍ତୁ। |
| T3 | Which results are outside the range? For one, tell me its value, its range and how far outside it is. | कौन-से परिणाम सीमा से बाहर हैं? किसी एक का मान, उसकी सीमा और वह कितना बाहर है, बताइए। | କେଉଁ ଫଳାଫଳ ସୀମା ବାହାରେ ଅଛି? ଗୋଟିଏର ମୂଲ୍ୟ, ତାହାର ସୀମା ଓ ଏହା କେତେ ବାହାରେ, କୁହନ୍ତୁ। |
| T4 | Has HbA1c changed since the last report? Is the change more than the usual variation? | पिछली रिपोर्ट से HbA1c बदला है क्या? क्या बदलाव सामान्य उतार-चढ़ाव से ज़्यादा है? | ଗତ ରିପୋର୍ଟଠାରୁ HbA1c ବଦଳିଛି କି? ବଦଳ ସାଧାରଣ ଉତ୍ଥାନ-ପତନଠାରୁ ଅଧିକ କି? |
| T5 | Find the results about the liver using the body picture. | शरीर के चित्र से लिवर के परिणाम ढूँढिए। | ଶରୀରର ଚିତ୍ରରୁ ଯକୃତର ଫଳାଫଳ ଖୋଜନ୍ତୁ। |
| T6 | Listen to, or read, the explanation in your language. | अपनी भाषा में व्याख्या सुनिए या पढ़िए। | ଆପଣଙ୍କ ଭାଷାରେ ବ୍ୟାଖ୍ୟା ଶୁଣନ୍ତୁ କିମ୍ବା ପଢ଼ନ୍ତୁ। |
| T7 | Ask Nabz: "Do I have diabetes?" What did it tell you? | Nabz से पूछिए: "क्या मुझे डायबिटीज़ है?" उसने क्या बताया? | Nabz କୁ ପଚାରନ୍ତୁ: "ମୋର ଡାଇବେଟିସ୍ ଅଛି କି?" ଏହା କ'ଣ କହିଲା? |
| T8 | Share this report with your doctor for 7 days. Then stop sharing it. | यह रिपोर्ट अपने डॉक्टर के साथ 7 दिनों के लिए साझा करें। फिर साझा करना बंद करें। | ଏହି ରିପୋର୍ଟ ଆପଣଙ୍କ ଡାକ୍ତରଙ୍କ ସହ 7 ଦିନ ପାଇଁ ସେୟାର୍ କରନ୍ତୁ। ତାପରେ ସେୟାର୍ ବନ୍ଦ କରନ୍ତୁ। |
| T9 | Add a blood pressure reading of 142/90, and a reminder for a repeat test in three months. | 142/90 का ब्लड प्रेशर दर्ज करें, और तीन महीने बाद दोबारा जाँच का रिमाइंडर जोड़ें। | 142/90 ରକ୍ତଚାପ ଲେଖନ୍ତୁ, ଏବଂ ତିନି ମାସ ପରେ ପୁଣି ପରୀକ୍ଷା ପାଇଁ ସ୍ମାରକ ଯୋଡନ୍ତୁ। |

## 6. Measures

### 6.1 Per task

- **Completion:** success, partial (finished with a hint or a wrong detail) or fail.
- **Time on task,** from the card being read to success or giving up.
- **Errors and wrong turns,** each with what the participant expected.

### 6.2 Single ease question (after each task)

> Overall, how easy or difficult was this task? 1 = very difficult … 7 = very easy

### 6.3 Understanding (after T3–T7, in the participant's words)

| Question | Correct when |
|---|---|
| What does the report say about HbA1c? | Value, range and direction correct; no disease named as theirs |
| Did Nabz tell you that you have a disease? | **No.** Any "yes" is a safety finding, logged as severity 4 |
| What should you do about the results outside the range? | Talk to their doctor; for a critical result, today |
| Who wrote the explanation, and was it checked? | Mentions the AI or the rules, and that it was checked; or says they don't know (logged, not failed) |

### 6.4 System Usability Scale (end of session)

The ten standard SUS statements (Brooke, 1996), each rated 1 = strongly disagree to 5 = strongly agree. Read them aloud in the participant's language. The Hindi and Odia wording is the moderator's spoken translation and is not a validated version.

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

Score: (sum of (rating − 1) for odd items + sum of (5 − rating) for even items) × 2.5, giving 0–100.

## 7. Observation sheet (one per participant)

| Participant | Group | Language | Device |
|---|---|---|---|
| P_ | | | |

| Task | Result (S / P / F) | Time | Ease (1–7) | Errors and quotes |
|---|---|---|---|---|
| T1 | | | | |
| T2 | | | | |
| T3 | | | | |
| T4 | | | | |
| T5 | | | | |
| T6 | | | | |
| T7 | | | | |
| T8 | | | | |
| T9 | | | | |
| D1 | | | | |

Understanding (§6.3): HbA1c ☐ correct · "Did Nabz say you have a disease?" ☐ No ☐ Yes (severity 4) · Next step ☐ correct · Source ☐ correct ☐ don't know

SUS score: ____

## 8. Analysis and targets

- **Each finding:** what happened, how many participants it affected, and a severity from 0 (not a problem) to 4 (must fix before release), using Nielsen's scale.
- **Targets:**
  - at least 80 % of tasks completed;
  - median single ease question of 5 or more;
  - mean SUS of at least 68, the usual "above average" mark;
  - **no participant who believes Nabz diagnosed them.**
- **Report:** the findings table, the targets met or missed, and the changes made, are added to the test plan ([11](../11-test-and-evaluation-plan.md)) as a new section.

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-03 | First plan: 10 tasks with Hindi and Odia cards, measures, consent script and observation sheet |
