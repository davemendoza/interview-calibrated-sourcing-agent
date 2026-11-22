# Known Limits and Roadmap

This page lists what the agent does not do well yet, why it matters, and what fixes it. It is here so nobody learns these limits the hard way in a client pilot. Items marked **Done** have shipped; the rest are planned.

## 1. Learned weights only reorder leads inside a tier

**What happens.** `icsa recalibrate` changes signal weights, but tiers come from evidence channels and commit counts. The final sort is tier first, signal score second. So learning can move a lead up or down within Tier 2, but it cannot move anyone across a tier line.

**Why it matters.** Someone reading "the agent learns from interviews" will expect outcomes to change who lands in Tier 1. Today they mostly change the order inside a tier.

**Fix.** Let the weighted signal score contribute to the tier decision itself, behind a setting so the fail-closed rules stay the default. Publish before and after tier movement on a held-out set so the effect is measurable.

## 2. Interview outcome labels are noisy

**What happens.** An outcome row records advanced or not, plus signals credited. It does not record who interviewed, how senior the stage was, or how strong the decision was. Evidence can repeat across stage rows for one person, and outcomes match people by name.

**Why it matters.** Recalibration treats a rejection from a rushed screen the same as one from a final panel, and one candidate with many stage rows can outweigh several others. A name match can attach an outcome to the wrong person.

**Fix.**
* Add `interviewer` and `stage_weight` columns, and weight later stages higher.
* Count each person once per signal per stage.
* Match outcomes on a stable candidate id, not a name.
* Add a minimum interviewer count before any weight moves.

## 3. Corroboration by metro area is weak

**What happens.** Two records can count as the same person when both sit in the same metro and neither names an employer. That is thin support for a large metro.

**Why it matters.** The identity gate is the main protection against attaching one person's work to another. A weak rule here shows up as a wrong-person lead.

**Fix.** Require metro plus one stronger signal (shared link, email, or employer), or treat metro as a tie-breaker only. Add a test with two same-name engineers in one metro.

## 4. No compliance layer yet

**What happens.** The agent collects public evidence and stores it locally. It does not yet produce the paperwork a regulated hiring team needs.

**Missing pieces.**
* A candidate notice for GDPR Article 14 (data collected from a public source rather than from the person).
* A retention setting that deletes evidence after a set period.
* An erase-person command that removes one person's evidence, scores and cached AI judgments.
* An audit export showing what was collected, from where, when, and why a person was ranked.
* A plain statement that, with `--judge`, public evidence text is sent to the Anthropic API. Teams with a no-third-party rule should leave the judge off.

**Fix.** Add `icsa notice`, `icsa erase`, `icsa audit` and a `retention_days` setting. Until then, run it only with your counsel's agreement on lawful basis and notice.

## 5. No repeat-run consistency test

**What happens.** The test gate checks accuracy against your ratings once. It does not run the same role several times and measure whether the results agree.

**Why it matters.** Harvest sources change and the AI judge can vary. A talent team needs to know how stable a Tier 1 list is from run to run before trusting it.

**Fix.** Add `icsa repeat --runs 5` that scores the same evidence repeatedly and reports how often each lead keeps its tier. Publish the number with every pilot.

## 6. Hidden or instructing text in evidence

**Done.** See [Hidden-text guard](HIDDEN_TEXT_GUARD.md). Resumes, PDFs, Word files and harvested pages are checked for white or tiny text, text off the page, invisible characters, metadata and sentences aimed at an AI. Flagged evidence is held back from scoring and the AI judge, and listed for a person to review.

**Still open.** Scanned images of text, text inside embedded images, and font tricks that remap letters are not inspected yet. The guard lowers the risk; it does not replace a person reading a finalist's resume.
