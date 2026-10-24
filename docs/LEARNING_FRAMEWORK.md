# LearnBook Learning Framework: Evidence, Design, Audit and Roadmap

*For Sidd. Prepared 24 Oct 2026.*

**How much to trust this document.**

- **Research:** I confirmed titles, venues, years and headline numbers against bibliographic records and abstracts found through web search. I did not read the full papers. Numbers marked (secondary) came from a summary of a paper, not the paper. DOIs marked (verify) came from my memory and were not in the search results, so click-test them before copying them into repo docs.
- **Audit:** Section 6 is based only on the coding agent's technical summary dated 2026-10-23. I have not seen the code. Section 6 lists exactly what to confirm.
- **Effect sizes:** They are averages from mostly short lab and classroom studies with students. They do not promise a size for you.

**Labels used.** Evidence: **Strong**, **Promising**, **Hypothesis**, **Overhyped**. Content type: \[R\] research finding, \[E\] engineering recommendation, \[A\] assumption.

## 1. Executive recommendation

Build a retrieval-first loop that I am calling **the Mastery Loop**. Every source is turned into small concept units with page anchors. Each unit is learned with guidance, then pulled from memory without the source, checked against the source, practised on spaced and varied problems, applied in a real task, and only then marked as mastered, based on evidence collected over weeks.

**The seven conclusions that matter:**

1. **Swap "read and summarize" for "attempt, retrieve, get feedback".** Practice testing and spaced practice are the two best-supported techniques in the major review of study methods, and rereading, highlighting and summarizing rated low. Your current app mostly produces summaries and lessons to read. That is the main gap. \[R\]
2. **Let a scheduler handle spacing.** Use the open-source FSRS algorithm with logged reviews from day one. \[E\]
3. **Guidance first, then fade it.** New procedures start as worked examples, then completion problems, then full problems. Experts get less guidance. \[R\]
4. **Train transfer on purpose.** Transfer from retrieval practice is real but smaller than direct retention, so varied problems and real application tasks are mandatory stages, not extras. \[R\]
5. **Mastery is a pile of evidence, not one quiz score.** A concept counts as mastered only after delayed, unaided, varied and transfer evidence. \[E\]
6. **Use AI narrowly.** AI drafts questions from source passages and grades explanations against a rubric and the source. Plain code handles scheduling, state, search and progress. LLM-written questions are demonstrably flawed often enough that every item needs a verification gate. \[R\] + \[E\]
7. **Pause public-launch work and build the learning loop for one user.** Your repo has a good ingestion core and a working skeleton, but nothing that teaches or tests yet. \[E\]

**Assumptions I am proceeding on** \[A\]: you are the only user; first domain is ML and data engineering material from textbook PDFs and papers; you can give 30 to 45 minutes on most days; spend should stay near zero; stack stays Windows, VS Code, a coding agent, Git. Your earlier plan was a public deployment. Your new brief says personal first, so I treat public launch as a later decision, not a current requirement.

## 2. Research synthesis

### 2.1 The anchor review

Dunlosky, Rawson, Marsh, Nathan and Willingham (2013), "Improving Students' Learning With Effective Learning Techniques: Promising Directions From Cognitive and Educational Psychology," *Psychological Science in the Public Interest*, 14(1), 4-58. DOI 10.1177/1529100612453266. It rated ten techniques. Practice testing and distributed practice came out high utility. Elaborative interrogation, self-explanation and interleaved practice came out moderate. Summarization, highlighting, the keyword mnemonic, imagery for text learning and rereading came out low. The authors say the techniques will not help everyone and mostly help motivated learners who can use them. **Limits:** it reflects evidence up to about 2012, much of it short-delay lab work with students.

### 2.2 Mechanism by mechanism

| Mechanism | Key evidence | Strength | Main limits | Design decision |
| --- | --- | --- | --- | --- |
| **Cognitive load and prior knowledge** | Sweller (1988), "Cognitive load during problem solving," *Cognitive Science* 12, 257-285 (verify DOI). Kalyuga, Ayres, Chandler, Sweller (2003), "The expertise reversal effect," *Educational Psychologist* 38(1). Kalyuga (2007), *Educational Psychology Review*, DOI 10.1007/s10648-007-9054-3 | **Strong** for novices: worked examples beat unaided problem solving early. Guidance that helps novices can hurt experts | Many studies use subjective load ratings. Lab tasks are small | Short lessons. Worked examples for any new procedure. Fade guidance as accuracy rises. A quick diagnostic sets the starting level |
| **Retrieval practice (testing effect)** | Roediger and Karpicke (2006), *Psychological Science* 17(3), 249-255. Rowland (2014), *Psychological Bulletin* 140(6), 1432-1463: about g = 0.50 over 159 effect sizes from 61 studies (secondary). Adesope, Trevisan, Sundararajan (2017), *Review of Educational Research*: about g = 0.61 (secondary). Yang et al. (2021), *Psychological Bulletin* 147(4), 399-435: classroom quizzing helps | **Strong** | Mostly facts and prose. Effect is larger with feedback (g about 0.73 vs 0.39, secondary) and at delays of a day or more. Bigger in controlled designs | Every learning stage ends in retrieval without the source. Feedback is always shown. Prefer short answer, explain-in-your-words and cloze over multiple choice |
| **Spacing** | Cepeda, Pashler, Vul, Wixted, Rohrer (2006), *Psychological Bulletin* 132(3), 354-380, DOI 10.1037/0033-2909.132.3.354: 839 assessments, 317 experiments, 184 articles; best gap grows with the retention interval. Cepeda et al. (2008), *Psychological Science* 19(11): optimal gap, as a share of the test delay, shrinks as the delay grows | **Strong** | Mostly verbal tasks. Exact optimal gaps vary by material | Scheduler, not self-discipline, decides review timing. Reviews spread across days and weeks, never crammed |
| **Transfer of retrieval practice** | Pan and Rickard (2018), "Transfer of test-enhanced learning: Meta-analytic review and synthesis," *Psychological Bulletin* 144(7), 710-756. Grand mean about d = 0.4, and transfer weaker than direct testing effect (secondary). Higher initial accuracy went with more transfer, and transfer vanished at very low initial accuracy (secondary) | **Strong** for format change, **Promising** for far application | Application and inference questions show smaller gains. Mostly lab | Do not test material you have barely seen. Add varied-format questions and application tasks. Do not assume quiz success means you can apply |
| **Self-explanation** | Chi et al. (1994), *Cognitive Science* 18, 439-477 (verify DOI). Bisra et al. (2018), *Educational Psychology Review* 30, 703-725 (verify; I recall a moderate effect near d = 0.55). Rated moderate by Dunlosky 2013 | **Promising to Strong** | Quality depends on learner's prior knowledge and on checking the explanation | After a lesson and after each worked example, you explain in your own words. The AI grades it against the source and flags errors |
| **Interleaving** | Kornell and Bjork (2008), *Psychological Science* 19, 585-592 (verify DOI). Brunmair and Richter (2019), "Similarity matters," *Psychological Bulletin*, DOI 10.1037/bul0000209: g = 0.42 over 59 studies and 238 effect sizes | **Promising, context-dependent** | Weaker for expository text and words. Stronger when categories look similar to each other and for complex material. Novices may need blocked practice first | Only in the practice stage, only among easily confused methods (for example choosing a metric, a regularizer, or an optimizer), and only after a blocked introduction |
| **Problem-first / productive failure** | Sinha and Kapur (2021), "When problem solving followed by instruction works," *Review of Educational Research*, DOI 10.3102/00346543211019105: 53 studies, 166 comparisons, favoring problem-first for conceptual understanding and transfer. Kirschner, Sweller, Clark (2006), *Educational Psychologist* 41(2), argue against minimal guidance | **Promising** | Needs some prior knowledge. For simple procedures instruction-first does about as well | Optional 3 to 5 minute "attempt first" prime for conceptual topics you partly know. Never for brand-new procedures |
| **Deliberate practice and skill building** | Ericsson, Krampe, Tesch-Romer (1993), *Psychological Review* 100, 363-406. Macnamara, Hambrick, Oswald (2014), *Psychological Science*, DOI 10.1177/0956797614535810: deliberate practice explained 26% of performance variance in games, 21% music, 18% sports, 4% education, under 1% professions | **Promising** for its design features. **Overhyped** as a hours-to-expertise rule | Definitions of deliberate practice are disputed. Correlational. Self-reported practice | Borrow the features: specific goals, immediate feedback, progressive difficulty. Do not promise expertise from hours logged |
| **Automaticity** | Anderson (1982), "Acquisition of cognitive skill," *Psychological Review* 89, 369-406 (verify). Logan (1988), *Psychological Review* 95, 492-527 (verify) | **Promising** (lab skill learning). Thin for professional work | Mostly narrow tasks | Treat "automatic" as an observable standard: correct, fast, no lookup, stable over sessions (Section 3) |
| **Feedback** | Hattie and Timperley (2007), "The power of feedback," *Review of Educational Research* 77(1), 81-112 (verify) | **Strong** that feedback matters. Effects vary a lot by type | Generic praise does little | Feedback names what was right, what was wrong, the source passage, and the next step |
| **Metacognition and calibration** | Bjork, Dunlosky, Kornell (2013), "Self-regulated learning: Beliefs, techniques, and illusions," *Annual Review of Psychology* 64, 417-444 (verify). Kornell and Bjork (2008): learners rated blocked study as better even when interleaving worked better | **Strong** that feeling of fluency misleads | Confidence ratings add friction | Ask confidence before showing the answer. Track calibration. Never let "felt easy" decide scheduling |
| **Concept maps, dual coding, imagery** | Karpicke and Blunt (2011), *Science* 331, 772-775 (verify): retrieval beat concept mapping on later tests. Dunlosky 2013 rated imagery for text learning low | **Hypothesis** for your use | Context-dependent | No mandatory diagram feature. "Draw it from memory" can be an optional retrieval format |
| **Motivation and consistency** | Ryan and Deci (2000), *American Psychologist* 55, 68-78 (verify). Gollwitzer and Sheeran (2006) on implementation intentions, *Advances in Experimental Social Psychology* 38 (verify) | **Promising** in general, **Hypothesis** for this app | Effects depend on the person | One small daily queue at a fixed time. Visible mastery progress. No points or badges |
| **Consolidation and sleep** | Diekelmann and Born (2010), *Nature Reviews Neuroscience* 11, 114-126 (verify) | **Promising**, modest | Mostly lab, mixed task types | No feature beyond spacing across days |

### 2.3 Popular claims checked

- **"Highlighting and rereading are fine."** Rated low utility in Dunlosky 2013. Keep them as cheap actions, but they do not count as learning evidence in this app. \[R\]
- **"Learning styles."** Pashler, McDaniel, Rohrer, Bjork (2008), *Psychological Science in the Public Interest* 9(3), concluded there was no adequate evidence that matching teaching to styles improves outcomes (verify details). **Overhyped.** No styles feature.
- **"10,000 hours."** See Macnamara 2014 above. **Overhyped.**
- **"Gamification keeps you consistent."** I found no strong evidence for your case. **Hypothesis.** Skipped.
- **"An AI tutor beats everything."** Direct, high-quality evidence for LLM tutors improving delayed retention in self-directed adults is thin and young. **Hypothesis.** This is why Section 9 exists.

### 2.4 AI-specific evidence

- **LLM-written questions are often flawed.** A 2025 study of ChatGPT-written practice quizzes for medical students (*Advances in Physiology Education* 49(3), PMID 40516963) found 49% of items had item-writing flaws and 22% had factual or conceptual errors, yet 91% were judged a usable starting point for expert revision. Grevisse, Pavlou, Schneider (2024), *SN Computer Science* 5, found broad items, ambiguous keys and implausible distractors. A 2024 workshop paper (arXiv 2409.00113) found models lose about 55% accuracy on questions with no correct option, which shows how readily they follow a bad answer key. \[R\] **Design implication:** never trust a generated item without a verification pass against the source passage.
- **Grading by LLM is a separate risk.** I did not find a strong study for your exact use, so treat grader accuracy as an assumption to test with your own samples (Section 9). \[A\]

### 2.5 What the evidence cannot tell us

Most studies are short, use students, and measure recall of facts or prose. Evidence for turning knowledge into fluent professional performance is much thinner. Evidence for AI-driven personalization is early. This means the framework is a well-supported hypothesis for your goal, and the experiment in Section 9 is how you find out whether it works for you.

## 3. The recommended framework: the Mastery Loop

### 3.1 Five levels, defined so we do not blur them

| Level | Meaning | Observable test |
| --- | --- | --- |
| **Remember** | Can produce the fact or definition | Cued or free recall, no source, after a delay |
| **Understand** | Has an accurate mental model | Explains the concept in own words, answers "why" and "what if", and a rubric finds no major errors |
| **Apply** | Uses it in a familiar problem type | Solves new instances of a known problem type unaided |
| **Transfer** | Uses it in an unfamiliar situation | Solves a problem with different surface features, or completes a realistic task, without being told which method fits |
| **Automatize** | Performs reliably with little effort | Correct, within a time standard, no lookup, stable across at least three sessions on different days |

A single correct quiz answer evidences at most Remember. Passing an AI quiz does not show Transfer or Automatize.

### 3.2 The stages, with inputs, outputs and exit criteria

I changed your starting sequence in three ways. I added an optional **Prime** stage at the front. I merged **Review** and **Maintain**, since both are the same spaced scheduler. I put **Diagnose** after every retrieval attempt, not once, because feedback is where retrieval gets its benefit.

| Stage | Input | Output | Exit criteria | Signals recorded |
| --- | --- | --- | --- | --- |
| **S0 Map** (import) | PDF, paper, transcript | Concept units with type (concept, fact, procedure, skill), prerequisites, source anchors | You accept or edit the unit list | Extraction quality flags, unit count, edits you made |
| **S1 Prime** (optional) | One unit you partly know | A written attempt at a problem or question | Attempt submitted (3 to 5 min) | Attempt text, confidence |
| **S2 Learn** | Unit plus source passages | Lesson with citations. Worked examples for procedures | Read, then own-words explanation submitted | Time on task, explanation text |
| **S3 Retrieve and explain** | Unit | Free recall plus 2 to 4 short questions, no source open | Attempt done, confidence given | Correctness, confidence, response time |
| **S4 Diagnose** | S3 answers plus source | Per-item verdict, cited passage, error tag (missing, wrong, shallow, confused with X) | You read feedback and restate the correction | Error tags, misconception log |
| **S5 Practise** | Units that passed S3 at roughly 70 to 85% | Spaced, varied problems. Guidance fades. Interleaved among similar methods | Three varied problems solved unaided, on two different days | Accuracy, hints used, time, error types |
| **S6 Apply** | Units with solid S5 | A small real task (implement, analyze, decide) with acceptance criteria | Task meets criteria without the source | Task outcome, time, number of lookups |
| **S7 Maintain** | All learned items | Daily due queue from FSRS | Queue cleared | Review log (rating, interval, time) |
| **S8 Certify** | Ledger of evidence | Unit marked mastered, or the exact missing evidence | See 3.3 | Ledger state |

The percentage thresholds in S5 are starting values to tune \[E\]. They follow the finding that transfer from retrieval is weak when initial accuracy is very low (Pan and Rickard, 2018, secondary).

### 3.3 The mastery ledger (completion standard)

A unit is **mastered for its intended use** only when all of these are true. All numbers are starting defaults \[E\], to be tuned in Phase 4.

- **Delayed recall:** an own-words explanation graded above the rubric threshold on two occasions at least 7 days apart, with no source.
- **Varied application:** at least three problems with different surface features solved unaided, at least one of them after a gap of 14 days or more.
- **Transfer:** one cold task or problem where the method was not named, passed.
- **Calibration:** your confidence ratings on this unit are not systematically too high (for example, you were confident on 5 items and got 2 right means not mastered yet).
- **Automatic (only for procedural skills you need fluently):** the procedure done correctly within your time standard, no lookup, on three separate days.

If any piece is missing, the app says which one, and schedules that exact activity. Procedural skills such as writing a training loop get the Automatic gate. Conceptual units such as bias-variance usually need only the first three bullets.

### 3.4 Why this order

- **Guided before independent:** novices benefit from worked examples, then problems (cognitive load and expertise reversal research above).
- **Retrieval before more reading:** retrieval teaches, so it comes right after first exposure. Rereading would be the weaker substitute.
- **Diagnosis before more practice:** practice on a misunderstanding cements it. Feedback must come first.
- **Spacing across all stages:** the scheduler, not the stage, controls when items return.
- **Application late but before certification:** transfer is the stated goal, so a unit cannot be certified without it.

### 3.5 Limitations and trade-offs

- **Effort:** retrieval feels harder than reading and the app will feel slower. That is the intended cost \[R\], but it threatens consistency. Keep the daily queue capped.
- **Question and grader quality:** the framework is only as good as its items and grading. This is the largest technical risk.
- **Unvalidated thresholds:** the mastery numbers are my engineering judgment, not research constants.
- **Weak domain evidence:** for professional skill fluency the research is thin.
- **Single-learner design:** nothing here generalizes beyond you.

### 3.6 Comparison with alternatives

Criteria, defined: **Evidence quality** = how strong the controlled research is for that approach on delayed outcomes. **Comprehension, Retention, Transfer, Skill** = what the evidence suggests it helps with. **Complexity** = engineering effort to build in this repo. **Fit** = suitability for a one-person, AI-assisted, near-zero-cost tool. These are qualitative judgments, not scores.

| Approach | Evidence quality | Comprehension | Retention | Transfer | Skill building | Complexity | Fit for you |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Read, highlight, summarize (baseline)** | Strong evidence it is weak | Modest | Weak | Weak | Weak | Very low | Poor as the main method |
| **Flashcards plus spaced repetition only** | Strong for retention | Weak to modest | Strong | Weak | Weak | Low | Good component, not enough alone |
| **AI chat tutor (Socratic)** | Early, mixed | Plausible | Unknown unless retrieval is built in | Plausible | Plausible | Low to build, hard to control quality | Risky alone. Useful as an explainer inside the loop |
| **Mastery learning (gate on unit tests)** | Promising to strong in classrooms (not reviewed in depth here) | Good | Good if tests are delayed | Depends on tests | Depends on tests | Medium | Good idea, but one-shot gates are weak. Used here with delayed multi-evidence gates |
| **Project-only / cognitive apprenticeship** | Promising | Good | Uneven | Strong potential | Strong | Medium to high | Essential for skills, inefficient for acquiring concepts alone |
| **Problem-first (productive failure) only** | Promising for concepts | Good | Unknown | Good | Limited | Medium | Useful as the optional Prime step |
| **The Mastery Loop (recommended)** | Built from strong parts, whole is untested | Good | Strong | Moderate to good | Good | Medium | Best fit. Smallest set that covers the full journey |

**Why it wins for you:** flashcards cover retention but not skill, projects cover skill but not efficient concept acquisition, and chat tutors cover neither reliably without retrieval and scheduling underneath. The loop is the smallest combination that covers remember, understand, apply, transfer and maintain, and every part of it is cheap to implement without agents, vector stores or knowledge graphs.

## 4. Detailed learning-system design

### 4.1 Shape of a day

Default 30 to 45 minutes:

1. **Due reviews first (10 to 15 min).** They decay on a clock, so they go before anything new.
2. **One new or in-progress unit through S2 to S4 (15 to 20 min).**
3. **A practice or application block (S5 or S6) on 2 to 3 days a week**, replacing step 2 on those days.

New units pause whenever the due queue is bigger than you can clear in about 15 minutes. \[E\]

### 4.2 What each stage does

| Stage | You do | The app does | AI needed? | Stores |
| --- | --- | --- | --- | --- |
| **S0 Map** | Upload. Review the unit list: merge, split, delete, mark units you already know | Extracts text, assigns passage IDs with page or timestamp anchors, proposes units with type and prerequisites, flags scanned pages | **Yes** for drafting units and prerequisites. **No** for extraction, hashing, anchors | Source, passages, units, prerequisite edges, your edits |
| **S1 Prime** (optional) | Write a quick attempt before reading | Shows one problem or question for the unit. No grading | Optional, to draft the prompt | Attempt, confidence |
| **S2 Learn** | Read the lesson and worked examples. Write an own-words explanation | Shows a lesson where each claim carries a source tag. Worked examples for procedures | **Yes**, to draft lesson and examples from passages | Lesson version, citations, your explanation |
| **S3 Retrieve** | Free recall with the source closed, then 2 to 4 short questions. Rate confidence before the reveal | Draws items from the unit's verified item bank | **Yes**, once, to generate items. **No** at quiz time | Answers, confidence, response time |
| **S4 Diagnose** | Read feedback. Restate the correction in your words | Grades against rubric and source, shows the passage, tags the error, logs misconceptions, queues a repair item | **Yes** for free text. **No** for cloze, numeric and tests | Verdict, error tag, cited passage, misconception record |
| **S5 Practise** | Solve problems. Ask for hints (each is logged) | Picks variants from the unit pool, adds similar-method items after a blocked set passes, fades guidance | **Yes**, to generate variants (verified). **No** for selection logic | Attempts, hints, time, error types |
| **S6 Apply** | Do a small real task outside the app (code, analysis, a decision memo). Paste the result. Reflect | Gives the task with acceptance criteria. Grades against them, with your override | **Yes**, to draft task and criteria and to grade against criteria | Task, submission, grade, override, reflection |
| **S7 Maintain** | Clear the daily queue | Computes due items with FSRS and records the rating | **No** | Review log |
| **S8 Certify** | See the ledger. Do the missing activity | Applies the ledger rules and shows exactly what is missing | **No** | Ledger events, mastery state |

### 4.3 Principles, signals and adaptation

| Stage | Principle | Next stage triggers when | If you struggle | If you progress fast |
| --- | --- | --- | --- | --- |
| **S0** | Organize knowledge before study | You accept the unit list | Split units smaller, add a prerequisite unit | Mark known units and go straight to S3 as a diagnostic |
| **S1** | Activate prior knowledge (**Promising**) | Attempt submitted | Skip it. It needs some prior knowledge | Keep it |
| **S2** | Limit load, worked examples, self-explanation | Own-words explanation submitted | Shorter chunks, more worked examples, add the prerequisite lesson | Skip worked examples, go to problems |
| **S3** | Retrieval practice | Attempt complete and confidence logged | Under 50% correct: re-read only the cited passages, then retry **next day**, not the same session | Over 90% and fast: jump to S5 |
| **S4** | Corrective feedback | You restated the correction | Same error tag 3 times: generate a contrasting worked example and flag the source passage for rereading | Not applicable |
| **S5** | Deliberate practice, interleaving, fading | Three varied solves, unaided, on two different days | Bring back hints and blocked practice | Drop hints sooner, add harder variants, interleave sooner |
| **S6** | Transfer, apprenticeship-style tasks | Task meets criteria | Smaller task with a scaffold | Larger or unscaffolded task |
| **S7** | Spacing | FSRS due date | Intervals shrink automatically. An item failed 4 or more times is a "leech": rewrite the item or re-teach | Intervals grow automatically |
| **S8** | Evidence standard | All ledger conditions met | Shows the missing evidence and schedules it | Certifies without extra drills |

The app's "success" signals are **process metrics** (did you do the activity). Learning is judged only by **outcome metrics** at delay (Section 9).

### 4.4 Different kinds of knowledge

The types and rubrics are generic. ML appears only in the content, so the same design works for statistics, finance, writing or anything else.

| Type | Typical activities | Item forms | Evidence of success |
| --- | --- | --- | --- |
| **Conceptual** | Explain, predict "what if", compare, repair a misconception | Free response with rubric, prediction questions | Own-words explanation passes at delay. A far-transfer question passes |
| **Factual** | Cloze, term to definition, formula recall | Cloze, short answer | Exact or fuzzy match, FSRS stability growing |
| **Procedural** | Worked example, then completion problem, then full problem | Step ordering, find the bug, fill the missing step | Solves unaided, within a time standard |
| **Practical skill** | Implement from a spec, debug, tune, interpret outputs | Coding exercise or notebook task with tests | Tests pass, no lookup, time within standard |
| **Professional transfer** | Ambiguous scenario, trade-off decision, written recommendation | Case, "which method and why", mini-project at work | Rubric on reasoning plus outcome criteria |

### 4.5 Example: a gradient descent chapter

- **S0** proposes six units: loss function (concept), gradient as steepest-ascent direction (concept), update rule and learning rate (procedure plus fact), effect of a too-large or too-small learning rate (concept), batch vs stochastic vs mini-batch (compare), implement gradient descent for linear regression (skill).
- **S2 to S4 on the update rule:** a worked numeric example on a one-variable function. You explain each step. Free recall of the rule with the source closed. A "what happens when the gradient is zero" question. Misconceptions get logged, for example "learning rate sets the number of iterations" or "gradient descent always finds the global minimum."
- **S5:** diagnose a loss curve that diverges, then later interleave it with momentum and learning-rate decay.
- **S6:** implement it from a blank file in NumPy on a dataset you have not seen, plot the loss, tune the rate, write a five-line interpretation.
- **S7 and S8:** re-derive the rule at about 3, 10 and 30 days, and re-implement under a time budget. The ledger decides when it counts as mastered.

## 5. What AI should and should not do

### 5.1 Capability verdicts for version 1

| Capability | Verdict | Why, and the simpler alternative |
| --- | --- | --- |
| **Document parsing, OCR** | **Necessary** (parsing, already built). OCR postponed | PyMuPDF text extraction exists and scanned files are flagged. Add OCR only when a scanned book actually blocks you |
| **Chunking and semantic organization** | **Necessary**, mostly deterministic | Use headings and pages. The LLM only names and groups units |
| **Source-grounded explanations** | **Necessary** | Passage IDs are mandatory in prompts and output |
| **RAG** | **Necessary in a simple form** | Select passages by the unit's own anchors plus Postgres full-text search. No vector database. Add embeddings only if measured misses justify it |
| **Knowledge graph / dependency graph** | **Optional, minimal** | A prerequisite edge list between units, editable by you. A full graph is unnecessary |
| **Question and exercise generation** | **Necessary**, behind a verification gate | See 5.3 |
| **Answer evaluation, misconception detection** | **Necessary** for free text | Deterministic matching for cloze, numeric answers and code tests |
| **Adaptive review scheduling** | **Necessary**, deterministic | FSRS, not an LLM |
| **Progress tracking, analytics** | **Necessary, small** | Ledger plus a handful of charts |
| **Personalization** | **Necessary, rule-based** | The adaptation rules in 4.3. Learned personalization is unnecessary now |
| **Practical task generation** | **Necessary, small** | Templates plus an LLM draft plus explicit acceptance criteria |
| **Citations and traceability** | **Necessary** | Anchors on every claim and item |
| **Autonomous agents, multi-agent orchestration, fine-tuning, knowledge-graph reasoning** | **Unnecessary** | No requirement in this brief needs them. Revisit only if the experiment shows a specific failure they would fix |

### 5.2 Four epistemic tags

Every sentence the AI writes in a lesson or feedback carries one tag:

- **SOURCE:** supported by a cited passage ID, shown with page or timestamp.
- **EXPLAINED:** the AI's elaboration or analogy, not in the source.
- **EXTERNAL:** backed by outside research. A link is required.
- **UNVERIFIED:** could not be tied to the source. Shown with a visible marker and excluded from graded items.

This is enforced in code, not by asking nicely. The model returns JSON with claims and passage IDs. Code checks that every cited ID exists and that any quoted span appears verbatim in that passage. Failures become UNVERIFIED or the item is rejected. \[E\]

### 5.3 Failure modes and controls

| Failure | Control |
| --- | --- |
| **Hallucinated facts** | Passage-bounded prompts, required passage IDs, substring check on quoted evidence |
| **Wrong answer key** | A second, independent call sees only the passage and the question and answers blind. A mismatch rejects the item. For numeric items compute the answer in code. For code items run tests |
| **Shallow questions** | Each item declares a level (recall, explain, apply, transfer). A unit must contain a minimum share above recall. Reject items answerable from the question text alone |
| **Unreliable grading** | Explicit rubric. The grader must quote your text and the source passage. Your overrides are logged and used to audit grader accuracy |
| **Inconsistent difficulty** | Difficulty comes from your actual results, not the model's guess |
| **Repetitive exercises** | Store item fingerprints. Variants must change surface features and keep structure. Dedupe check |
| **Contradicting the source** | Claim-to-passage check. Conflicts become UNVERIFIED |
| **Multiple-choice flaws** (longest answer correct, "all of the above") | Prefer non-MCQ formats. Add a small deterministic lint for known item-writing flaws |
| **Over-trust** | You review the first 50 generated items by hand and keep a spot-check habit |

### 5.4 Model choice

Keep Groq behind the existing `provider.py` wrapper so you can switch. Choose the model by measurement, not reputation: key-correctness rate on 30 hand-checked items, and grader agreement with you on 30 of your own answers. I am not stating model names or rate limits because they change. Check Groq's current free-tier limits and data-retention terms, which your agent's summary says are still untested. \[E\]

## 6. Existing-project audit

**Scope warning.** This audit comes from the coding agent's technical summary of 2026-10-23, not from the code. Items below are "reported" unless stated. Where the summary is silent I say "not reported" instead of guessing. 6.2 lists what to confirm in the repo.

### 6.1 Findings

| Area | Reported state | Assessment |
| --- | --- | --- |
| **Architecture and stack** | Next.js on Vercel, FastAPI in Docker for Render, Supabase (Auth, Postgres with RLS, private Storage), Groq called server-side. Python tooling is uv, pytest, ruff. Frontend tests use Vitest and Playwright | Standard and sound. Sized for a multi-user public service, which is more than a one-person tool needs |
| **Frontend and backend roles** | UI uses Supabase JS for auth and sends a JWT. FastAPI verifies it and scopes every query by `user_id`. `learnbook.core` holds pure logic with no UI or storage imports | Good separation. This is the part worth protecting |
| **Import and document processing** | PyMuPDF validation, page-preserving extraction, size and page caps, scanned-PDF detection, SHA-256 hashing, process-isolated parsing with a timeout | Solid for PDFs. **Gaps:** no stable passage-level anchors reported (pages only). No import path reported for transcripts, articles or plain text, which your brief requires. OCR absent, which is fine until you need it |
| **AI provider and orchestration** | Groq, server-side, behind a consent gate and token accounting. Book-map generation runs as resumable chunk-then-merge jobs. **No model key configured**, so no real call has run | Reasonable plumbing. Model names, prompts, output validation and citation behavior are **not reported**. Quality is entirely unverified |
| **Storage and retrieval** | Owner-scoped Postgres rows, one migration file (`202610130001_public_books.sql`), private bucket. Search exists in the Streamlit prototype. No embeddings reported | Fine. Nothing reported for concept units, items, attempts, reviews or mastery |
| **Auth and user data** | Supabase email and password. RLS policies unverified with two real accounts. Account-deletion routes missing | Mostly irrelevant for a single user, apart from turning off public sign-ups |
| **Learning and assessment today** | Book map, deterministic extractive digest, time-based learning path, cached lessons, notes and highlights, status updates | **Read-oriented.** Not reported: quizzes, flashcards, spaced repetition, free-recall exercises, grading, practice problems, application tasks, a mastery view, the implementation journal from your original brief |
| **Performance and reliability** | 81 Python tests and 16 Vitest tests pass, lint and format pass, npm audit shows 0 vulnerabilities. Resumable jobs are single-process, rate pacing is process-local. Docker never built. Cold starts unverified | Healthy offline. Nothing about live behavior is known |
| **Deployment and cost** | Render, Vercel, Supabase free tier, Groq. Nothing deployed. Summary notes the Supabase free tier can pause | Likely near zero cost, but all limits are unverified |
| **Security, privacy, retention** | Private storage, RLS, explicit consent before sending text to Groq. Groq retention terms unknown. Placeholder takedown email in the terms page | The consent gate is sensible. Retention terms matter more for personal books and notes than for public-service features |
| **License** | PyMuPDF is AGPL. Decision between AGPL-3.0 and a permissive library is open | If this stays a private personal tool, this is a non-issue for now. If you ever expose it to other people or publish it, get proper advice. I am not a lawyer |

**Worth retaining:** ingestion core and tests, the `core` package separation, resumable job pattern, deterministic digest as a *ranker* of candidate passages, time-based path packing, lesson caching, the test and lint discipline.

**Unnecessary complexity for a personal tool:** per-user and global AI quotas, the provider consent gate as a product feature, terms and takedown page, multi-tenant RLS verification, distributed rate limiting, account deletion, Render and Vercel deployment, AGPL resolution, and a duplicate Streamlit UI beside the Next.js one.

### 6.2 Questions the coding agent should answer before any change

Ask for a written answer in `docs/AUDIT.md`, **no code changes**:

1. List every table and column in the migration. Is there a passage-level table, or only pages?
2. Print the map and lesson prompts. Do they require citations or page references? Is output validated against a schema? What happens on malformed JSON?
3. Which model names and token limits are configured? Where is the model name set?
4. How is the deterministic digest used, and has its quality been checked against anything?
5. What is the lesson cache key and how is it invalidated?
6. What happens to a map job after a crash or restart?
7. Give a route inventory (path, method, purpose) and which UI pages call each route.
8. Which tests use a fake provider, and are there any live-call tests?
9. Is there any code for quizzes, flashcards or spaced repetition, even unused? List dead code.
10. List dependencies and licenses, and flag unused packages.
11. After you add a key, map one real 300-page PDF once and report wall time and tokens used.

## 7. Keep / Modify / Remove / Add matrix

Rule applied: do not rewrite working components just to match a preferred design. "Postpone" means leave the code alone and stop investing.

| Item | Decision | What changes and why |
| --- | --- | --- |
| **PDF ingestion core** (PyMuPDF, caps, hashing, scanned detection, isolation) | **Keep** | Works and is tested |
| **Page-preserving extraction** | **Modify** | Add stable passage IDs with page and character or block offsets so every generated item can cite a source span |
| **Transcript, article and plain-text import** | **Add** | Your brief needs them. Start with plain text and `.srt`/`.vtt`-style timestamps. Keep anchors (page or timestamp) uniform across types |
| **Deterministic digest** | **Modify** | Use it to rank candidate passages, not as teaching content. Evaluate it against 20 passages you pick by hand |
| **Groq provider wrapper, token accounting** | **Keep** | Keep the interface. Simplify to one global budget number later |
| **Book-map generation (resumable)** | **Modify** | Output concept units with type, prerequisites and passage anchors, in a validated schema, instead of only summaries |
| **Time-based learning path** | **Modify** | Keep the packing logic. Plan sessions that include due reviews and practice, not reading time alone |
| **Lessons and lesson cache** | **Modify** | Each claim carries an epistemic tag and passage ID. Add worked examples for procedures |
| **Notes and highlights** | **Modify** | Keep (cheap), but demote: highlighting is low utility, so it never counts as progress. Notes become "my explanation" entries tied to a unit |
| **Progress visualization** | **Modify** | Replace read-status with the mastery ledger view |
| **Streamlit prototype** | **Remove from active work** | Freeze it. Two UIs double maintenance. Keep the CLI ingestion shim |
| **Per-user and global quotas, consent-gate extensions, terms page, takedown email, account deletion, distributed limiter** | **Postpone** | Public-service features. Revisit only if you decide to open the app to others |
| **Docker, Render and Vercel deployment** | **Postpone** | Run locally for the experiment first. Deploy only if you want phone access |
| **Supabase auth and RLS** | **Keep, simplify** | Turn off public sign-ups. One real account. Verify once, not as a two-account security exercise |
| **Concept units and prerequisite edges** | **Add** | Core data for S0 |
| **Item bank with verification pipeline** | **Add** | Core. See 5.3 |
| **Attempts, confidence and misconception log** | **Add** | Feeds diagnosis and calibration |
| **FSRS review queue and review log** | **Add** | Core spacing mechanism |
| **Free-recall and self-explanation exercise with rubric grading** | **Add** | The first learning feature to build |
| **Practice sets with fading guidance and interleaving** | **Add** | S5 |
| **Application tasks and implementation journal** | **Add** | S6. Matches your original journal idea |
| **Mastery ledger and gates** | **Add** | S8 |
| **Experiment harness and event log** | **Add** | Needed to answer "does it work for me" |

## 8. Recommended architecture and stack

### 8.1 Component view

```
You (browser, local)
   |
 Next.js UI (existing)  ---  Supabase Auth (one account, sign-ups off)
   |  JWT
 FastAPI (existing, run locally with uv)
   |-- learnbook.core  (pure logic)
   |      ingestion (existing) | units + anchors | item verification
   |      ledger rules | session planner | FSRS wrapper
   |-- provider.py  --> Groq (draft items, lessons, grading)
   |-- Supabase Postgres (existing)
          sources, passages(+full-text index), units, items,
          attempts, reviews, misconceptions, tasks, ledger_events
   |-- Supabase Storage (private PDFs)
```

### 8.2 One recommended stack

| Component | Choice | Why | Cost | Upgrade only when |
| --- | --- | --- | --- | --- |
| **Frontend** | Next.js (existing), run locally | Already built and tested | Free (local) | You want phone access: deploy to Vercel |
| **Backend** | FastAPI (existing), run locally with uv | Already built. Local avoids cold starts and a Docker detour | Free (local) | Same trigger as above: Render, after a Docker build works |
| **Parsing** | PyMuPDF (existing) | Fast, page-preserving | Free | You distribute the app: revisit the AGPL question |
| **Database and files** | Supabase Postgres and Storage (existing) | Rewriting the data layer to SQLite would cost more than it saves | Free tier with limits I have not verified. The free tier can pause when idle | Limits actually bite, or pausing becomes annoying |
| **Retrieval** | Postgres full-text search on passages (tsvector) plus the unit's own anchors | Enough for source-bounded generation. No new service | Free | A measured share of items cannot find their supporting passage: add pgvector, which Supabase supports |
| **LLM** | Groq through `provider.py` (existing) | Already wired. Swappable | Free tier with limits that must be checked | Daily sessions hit rate limits: add a second provider behind the same interface |
| **Scheduling** | FSRS via an open-source Python package (verify the exact package name and version on PyPI before pinning) | Better predicted recall than the older SM-2 in the open community benchmark. Open source, trainable later from your logs | Free | You have a few thousand reviews: fit personal parameters |
| **Background work** | The existing resumable DB-backed jobs. "Due items" are computed on request, so no cron | Fewer moving parts | Free | Never needed for one user |
| **Code exercises** | You run code in your own editor and paste results. The app stores the task, criteria and submission | Avoids building a sandbox | Free | Manual checking becomes the bottleneck: add a local test runner |
| **Backups** | Weekly `pg_dump` plus a JSONL export of reviews, attempts and ledger to a private location | Your learning history is the valuable data. Keeps the move-provider path open | Free | Not applicable |
| **Monitoring** | Existing logging only | One user | Free | Public launch |

Free means different things here, and I am not mixing them: **local software is free with no quota**; **Supabase and Groq are free tiers with limits that can change, pause or end**; nothing in this stack requires a paid service on day one.

### 8.3 New data, kept small

Tables to add: `passages`, `units`, `unit_prereqs`, `items`, `attempts`, `reviews`, `misconceptions`, `tasks`, `ledger_events`. An `items` row holds type, level, prompt, key, rubric, passage IDs, a verified-at stamp and a fingerprint. `reviews` stores the rating, due date and the scheduler's state after every review, from the first day, so parameters can be fitted later. Nothing else is needed for the first version.

## 9. Evaluation strategy

### 9.1 What to measure

| Metric | Kind | How |
| --- | --- | --- |
| **Immediate comprehension** | Outcome | Free recall plus 3 short questions right after study, source closed |
| **Delayed recall** | Outcome | Same skills, new wording, at about 2, 7 and 30 days. Optionally 60 |
| **Calibration** | Outcome (metacognitive) | Average confidence minus accuracy per session. Optionally a Brier score |
| **Explain without the source** | Outcome | Own-words explanation graded blind with a rubric |
| **New-problem performance** | Outcome | Problems with different surface features than anything practised |
| **Implementation quality** | Outcome | Acceptance criteria met, tests passed, lookups used, time taken |
| **Time to standard** | Efficiency | Study minutes until a unit first meets the ledger |
| **Misconception frequency and type** | Diagnostic | Error tags per unit per week, and whether they stop recurring |
| **Effort and latency** | Process | Session minutes, grading delay, tokens per day |
| **Sessions, cards reviewed, streaks** | Process only | Logged, but **never** treated as evidence of learning |

### 9.2 The personal experiment

**Question.** For the same study time, does the Mastery Loop beat "read the source and write your own summary" on delayed recall and on transfer?

**Design (within-subject, matched material).**

1. **Pick material.** One or two chapters you do not know well, split into at least 12 independent units. Independent means one unit does not teach another.
2. **Write the tests first.** For every unit, create 6 or more items before studying: recall, explain and application. Hand-verify them. Freeze them. Use a different item set at each delay so a test does not act as extra practice on the same item.
3. **Randomly assign units** to **A (baseline):** read the source, write a summary, rereading allowed. **B (Mastery Loop):** S2 to S5. Use a script for assignment, not your preference.
4. **Match time.** Use a timer. Each unit gets the same total study minutes in both conditions.
5. **Test** at day 0, 7 and 30. At day 30 add one transfer problem per unit that neither condition practised.
6. **Grade blind.** A script strips condition labels. The LLM grades with the rubric, and you grade a random 20% blind to check agreement.
7. **Pre-register.** Write the hypothesis, metrics, assignment rule and decision threshold into `docs/EXPERIMENT.md` before study starts.
8. **Cross over** on a second source if you can, swapping which kinds of units get which condition.

**Decision threshold.** Set it before you see data, at a gap you would genuinely care about. A starting suggestion is that B is at least 10 to 15 percentage points higher on day-30 accuracy without costing more study time. \[A\]

**Analysis.** With about 12 units you cannot do convincing significance testing. Report per-unit differences, the average difference with a bootstrap range, and the raw table. Keep claims modest.

### 9.3 Confounders and limits

- **Unit difficulty:** reduced by random assignment, not removed.
- **Test as practice:** delayed tests also exercise retrieval for both conditions, so use separate items per delay.
- **Teaching to the test:** B practises question styles similar to the tests. The unpractised transfer problems and blind grading limit this.
- **Expectation and motivation:** you know B is the new method. Blind grading helps, nothing fully fixes it.
- **Carryover between units:** limited by choosing independent units.
- **Grader error:** measured through your 20% blind check.
- **One learner, small sample:** the result tells you about you, on this material. It cannot establish that the method works in general.

### 9.4 Automatic performance

The system cannot promise automaticity. Pick two or three procedural skills you actually need, for example writing a training loop or a SQL window-function query. Re-do each from a blank file on different days under a time standard you set. Treat the skill as approaching reliable when the last three runs are correct, have zero lookups, and are within about 20% of each other in time. \[E\]

### 9.5 System quality targets (starting values)

- **Item key accuracy:** at least 95% on 30 to 50 hand-checked items after the verification gate. \[E\]
- **Grader agreement with you:** at least 85% on pass or fail across 30 of your own answers. \[E\]
- **Daily load:** a normal session stays under 45 minutes. \[E\]

Miss a target and the fix goes in before more features.

## 10. Phased implementation roadmap

Each task is sized for one coding-agent session, with tests and lint passing. Nothing is built before Phase 2 is done.

### Phase 1: Research and decisions

- **Deliverables:** this document saved as `docs/LEARNING_FRAMEWORK.md`. Entries added to `docs/TECH_DECISIONS.md`: retrieval-first loop, FSRS, no vector database, public launch paused.
- **Files:** docs only.
- **Acceptance:** you have read and edited the document and confirmed or changed the assumptions in Section 1 and Section 11.

### Phase 2: Audit and baseline

- **Deliverables:** `docs/AUDIT.md` answering all 11 questions in 6.2. A baseline: one real 300-page PDF mapped once, with wall time and tokens recorded.
- **Files:** docs, optionally `scripts/benchmark_map.py`.
- **Prerequisites:** a Groq key set locally, one Supabase account, sign-ups off.
- **Acceptance:** every question answered with file paths, baseline numbers recorded, the matrix in Section 7 corrected where the code disagrees with the summary.

### Phase 3: Minimum viable learning system

First, do **one manual dry run** of the loop for a single unit using your current app and a chat window, to see where it hurts, before writing code. Then:

| Task | Scope | Acceptance |
| --- | --- | --- |
| **T9 Anchors and units** | Passage IDs, `passages` and `units` tables, validated map schema with prerequisites | The sample PDF yields units that each cite at least one passage. Malformed model output is rejected, with tests |
| **T10 Item bank and verification** | Generate items for one unit. Blind second-pass key check. Quote-in-passage check. Reject log | Reported key accuracy on 30 hand-checked items. Failure fixtures covered by tests |
| **T11 Retrieve and diagnose (S3, S4)** | Free recall plus short questions, confidence before reveal, rubric grading with quoted evidence, misconception log, UI | One unit works end to end locally. Grader agreement measured on 30 answers |
| **T12 FSRS queue (S7)** | `reviews` table, due query, rating, daily queue page, JSONL export | Unit tests with a fixed clock. Export restores a queue |
| **T13 Practise (S5)** | Variant generation, hint logging, fading and interleaving rules | Rule tests: interleave only after a blocked pass, fade after set accuracy |
| **T14 Apply and ledger (S6, S8)** | Task template, submission, criteria grading with override, ledger evaluation, mastery view | Ledger tests cover every gate combination |
| **T15 Experiment harness** | Random assignment, blind grading export, event log, `docs/EXPERIMENT.md` | A dry run exports a label-free grading sheet |

- **Dependencies:** T9 first, then T10, then T11 and T12 in either order, then T13, T14, T15.
- **Files likely to change:** `src/learnbook/core/*` (new modules), `src/learnbook/api/*` (routes, `provider.py`, `schemas.py`, `summary.py`, `lessons.py`), `supabase/migrations/*`, `web/src/app/*`, `tests/*`.

### Phase 4: Validation

- **Deliverables:** the experiment run, `docs/RESULTS.md`, measured latency, tokens and cost, a list of observed failure modes.
- **Acceptance:** pre-registered metrics reported honestly, quality targets in 9.5 met or a documented fix in progress, normal sessions under 45 minutes.

### Phase 5: Iterate on evidence

Pick work from the results, not from this list. Likely candidates, each gated by a measured trigger: pgvector if retrieval misses, FSRS parameter fitting once you have enough reviews, a second LLM provider if limits block daily sessions, a local test runner for code tasks, a podcast and transcript pipeline, and only then deployment or public-launch work.

## 11. Immediate next action

**Save this document into the repo as `docs/LEARNING_FRAMEWORK.md`, then give your coding agent the audit prompt below.** The audit is the cheapest step that removes the biggest uncertainty, because everything in Sections 6 and 7 rests on a summary rather than on code.

> Read-only audit. Make no code changes. Create `docs/AUDIT.md` answering the 11 questions in Section 6.2 of `docs/LEARNING_FRAMEWORK.md`. For each answer, cite file paths and line ranges. Where something does not exist, say "does not exist" instead of inferring. End with a table of anything in the repo that contradicts Section 7 of that document.

**Three inputs I assumed and you can change.** (1) Personal-only for now, public launch paused. (2) Your first pilot source is an ML or data engineering chapter you will really use at work. (3) You can give about 30 to 45 minutes a day. If any is wrong, tell me and I will adjust the plan.

## 12. References

**Confirmed in this session's search results (record, venue, year, headline figures).**

- Dunlosky, Rawson, Marsh, Nathan, Willingham (2013). Improving students' learning with effective learning techniques. *Psychological Science in the Public Interest* 14(1), 4-58. DOI 10.1177/1529100612453266
- Cepeda, Pashler, Vul, Wixted, Rohrer (2006). Distributed practice in verbal recall tasks. *Psychological Bulletin* 132(3), 354-380. DOI 10.1037/0033-2909.132.3.354
- Brunmair and Richter (2019). Similarity matters: A meta-analysis of interleaved learning and its moderators. *Psychological Bulletin*. DOI 10.1037/bul0000209
- Macnamara, Hambrick, Oswald (2014). Deliberate practice and performance in music, games, sports, education, and professions. *Psychological Science*. DOI 10.1177/0956797614535810
- Sinha and Kapur (2021). When problem solving followed by instruction works: Evidence for productive failure. *Review of Educational Research*. DOI 10.3102/00346543211019105
- Kalyuga (2007). Expertise reversal effect and its implications for learner-tailored instruction. *Educational Psychology Review*. DOI 10.1007/s10648-007-9054-3
- Rowland (2014). The effect of testing versus restudy on retention. *Psychological Bulletin* 140(6), 1432-1463. (Effect sizes via secondary summary. DOI 10.1037/a0037559, verify)
- Pan and Rickard (2018). Transfer of test-enhanced learning. *Psychological Bulletin* 144(7), 710-756. (Figures via secondary summary. DOI 10.1037/bul0000151, verify)
- Adesope, Trevisan, Sundararajan (2017). Rethinking the use of tests. *Review of Educational Research* 87(3). (DOI 10.3102/0034654316689306, verify)
- Yang, Luo, Vadillo, Yu, Shanks (2021). Testing (quizzing) boosts classroom learning. *Psychological Bulletin* 147(4), 399-435. (DOI 10.1037/bul0000309, verify)
- Roediger and Karpicke (2006). Test-enhanced learning. *Psychological Science* 17(3), 249-255. (DOI 10.1111/j.1467-9280.2006.01693.x, verify)
- LLM-generated practice quizzes for pre-clinical medical students. *Advances in Physiology Education* 49(3), 2025. PMID 40516963
- Grevisse, Pavlou, Schneider (2024). Docimological quality analysis of LLM-generated multiple choice questions in computer science and medicine. *SN Computer Science* 5
- When all options are wrong: Evaluating LLM robustness with incorrect multiple-choice options (2024). arXiv:2409.00113
- FSRS and benchmark: github.com/open-spaced-repetition/srs-benchmark, and the Anki manual page on its scheduling algorithms (docs.ankiweb.net, "What spaced repetition algorithm does Anki use?"). The benchmark compares prediction of recall on Anki review data. It does not show better learning outcomes by itself.

**From my own knowledge, not seen in this session's results. Click-test each DOI before relying on it.**

- Cepeda, Vul, Rohrer, Wixted, Pashler (2008). Spacing effects in learning: A temporal ridgeline of optimal retention. *Psychological Science* 19(11), 1095-1102. DOI 10.1111/j.1467-9280.2008.02209.x
- Kornell and Bjork (2008). Learning concepts and categories: Is spacing the enemy of induction? *Psychological Science* 19(6), 585-592. DOI 10.1111/j.1467-9280.2008.02127.x
- Sweller (1988). Cognitive load during problem solving: Effects on learning. *Cognitive Science* 12(2), 257-285. DOI 10.1207/s15516709cog1202\_4
- Kalyuga, Ayres, Chandler, Sweller (2003). The expertise reversal effect. *Educational Psychologist* 38(1), 23-31. DOI 10.1207/S15326985EP3801\_4
- Kirschner, Sweller, Clark (2006). Why minimal guidance during instruction does not work. *Educational Psychologist* 41(2), 75-86. DOI 10.1207/s15326985ep4102\_1
- Chi, Leeuw, Chiu, LaVancher (1994). Eliciting self-explanations improves understanding. *Cognitive Science* 18(3), 439-477. DOI 10.1207/s15516709cog1803\_3
- Bisra, Liu, Nesbit, Salimi, Winne (2018). Inducing self-explanation: A meta-analysis. *Educational Psychology Review* 30, 703-725. DOI 10.1007/s10648-018-9434-x
- Ericsson, Krampe, Tesch-Romer (1993). The role of deliberate practice in the acquisition of expert performance. *Psychological Review* 100(3), 363-406. DOI 10.1037/0033-295X.100.3.363
- Anderson (1982). Acquisition of cognitive skill. *Psychological Review* 89(4), 369-406. DOI 10.1037/0033-295X.89.4.369
- Logan (1988). Toward an instance theory of automatization. *Psychological Review* 95(4), 492-527. DOI 10.1037/0033-295X.95.4.492
- Hattie and Timperley (2007). The power of feedback. *Review of Educational Research* 77(1), 81-112. DOI 10.3102/003465430298487
- Bjork, Dunlosky, Kornell (2013). Self-regulated learning: Beliefs, techniques, and illusions. *Annual Review of Psychology* 64, 417-444. DOI 10.1146/annurev-psych-113011-143823
- Karpicke and Blunt (2011). Retrieval practice produces more learning than elaborative studying with concept mapping. *Science* 331, 772-775. DOI 10.1126/science.1199327
- Ryan and Deci (2000). Self-determination theory and the facilitation of intrinsic motivation. *American Psychologist* 55(1), 68-78. DOI 10.1037/0003-066X.55.1.68
- Gollwitzer and Sheeran (2006). Implementation intentions and goal achievement: A meta-analysis. *Advances in Experimental Social Psychology* 38, 69-119. DOI 10.1016/S0065-2601(06)38002-1
- Diekelmann and Born (2010). The memory function of sleep. *Nature Reviews Neuroscience* 11, 114-126. DOI 10.1038/nrn2762
- Pashler, McDaniel, Rohrer, Bjork (2008). Learning styles: Concepts and evidence. *Psychological Science in the Public Interest* 9(3), 105-119. DOI 10.1111/j.1539-6053.2009.01038.x
