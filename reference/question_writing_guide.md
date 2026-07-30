# Question Writing: Knowledge Checks, Assessments, Qualification Exams

Working copy of the Confluence page "Question Writing (KCs, Assessments, Qualification Exams)".
Live source: https://celonis.atlassian.net/wiki/spaces/CA/pages/70942740/Question+Writing+KCs+Assessments+Qualification+Exams
Re-fetch the live page if a detail seems outdated  -  this is a working copy, not the source of truth.

Use this when a task involves writing quiz questions, knowledge checks, or exam items for a
course. Follow the three steps below in order  -  objective and cognitive level come before any
question gets drafted.

## 1. Start from the learning objective

Well-written objectives (audience, behavior, condition) are the foundation  -  they define what
competency is being tested and drive what the question should ask. If there's no clear objective
for a topic yet, that has to be settled first (see
`instructional_design_foundations.md` for how to phrase an outcome-based objective).

## 2. Match the question to Bloom's cognitive level of the objective

Verify what cognitive level the objective sits at, then write the question to match  -  not above
or below it. Getting this wrong causes real problems in an exam context:

- **Too hard for the objective** -> a competent learner fails even though they can actually do the
  task (false negative)  -  this hurts morale and can create legal/compliance exposure.
- **Too easy for the objective** -> an unprepared learner passes anyway (false positive)  -  this
  puts someone in a role they can't perform and can affect Celonis' reputation.

## 3. Write the question in the right format

**Multiple choice** (one correct answer)
- Phrase the stem as a question ("What is...?"), never as a fill-in-the-blank completion  - 
  completion form breaks in some languages during localization.
- Use exactly 3 answer choices unless there's a specific reason for more.
- Keep answer choices similar in length (so the correct one isn't always the longest) and
  parallel in structure (all noun phrases, all full sentences, etc.)  -  unless the choices mirror
  something concrete in the software (e.g. actual drop-down items), where varying length is fine.
- No "All of the above" / "None of the above."
- No complex combined answers like "D: A and B"  -  use multiple response instead.
- Distractors should reflect real learner mistakes, use familiar-but-wrong phrasing, or be true
  statements that don't answer the question  -  never a "gotcha" or intentionally tricky twist.
- Don't make distractors visually/phonetically confusable with the correct answer (e.g. EPR vs.
  ERP).

**Multiple response** (2+ correct answers)
- Also phrase as a question, and explicitly say "Select TWO" (etc.) in capitals. Match the number
  of distractors to the number of correct answers (2 correct -> 2 distractors). Avoid "Select
  THREE" outside technical exams  -  it's unnecessarily hard.
- Base choices on real, plausible options (e.g. only include roles that are genuinely
  plausible in the scenario).
- Same rules as multiple choice for length/parallel structure/no "all-none of the above"/no gotcha
  distractors.
- Keep multiple-response questions to 15-20% of a question set at most.
- **Qualification exams only use multiple choice and multiple response**  -  other formats create
  fairness issues or a 50% guess rate. Teaching statements are also banned from qualification
  exams, since they can leak the answer to another question.

**Fill-in-the-blank**  -  avoid. Localization problems. Use multiple choice instead, even in
regular course quizzes (not just exams).

**Hotspot** (mark a point on an image)  -  not used in qualification exams. If used elsewhere, give
explicit instructions on how to answer, or consider converting it into a lettered-marker multiple
choice question instead (usually easier for the learner).

**True/False or Yes/No**  -  not used in qualification exams. If used elsewhere: phrase the
statement positively (a negatively-worded false statement is confusing), test exactly one fact,
and when the answer is False, reinforce the actual true fact in the feedback (a "False" answer
alone doesn't confirm the learner knows what's actually true).

**Matching / drag-and-drop**  -  not used in qualification exams. If used elsewhere, it's fine for
the option list to have more entries than correct matches, but don't overload it.

## General rules for every question, regardless of format

- Test content that reflects real on-the-job decisions and tasks  -  not trivia. No joke/obviously
  wrong answer choices; they can come across as wasting the learner's time.
- One objective, one answer per question. Avoid double-barreled questions that bundle two issues
  into one question with only one answer slot.
- Word the stem positively. If a negative (NOT, EXCEPT) is unavoidable, use it sparingly and
  always capitalize it. Never stack a negative stem with a negative answer choice (double
  negative).
- Use direct, unambiguous language. Watch out for vague qualifiers that different people read
  differently: could, can, should, may, might, sometimes, generally, some, few, never, only, all,
  always.

## Accessibility

Follow the team's exam accessibility guidance when finalizing question items (see the live
Confluence page linked at the top for the specific accessibility page  -  re-fetch if needed).
