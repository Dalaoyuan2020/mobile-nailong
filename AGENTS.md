# Project guide

- Read `docs/PRD.md` for product scope, `docs/PDR.md` for design status, and `docs/REVIEW_HANDOFF.md` for review entry points.
- The product is a retrofitted smart suitcase: stable phone control and owner following, with a removable Nailong standee. Following is required, not yet implemented.
- The current assembly is upright; the case sits behind the photo-proportioned flat cutout. Archived horizontal-layout documents are not active constraints.
- Preserve `cad/case26/` source geometry and its design coordinates. `cad/handle/case_pose.py` provides the upright assembly transform.
- Current CAD wheels are passive placeholders. Mount bars are concepts, not manufacturing-ready clamps. Do not describe motors, phone software or following as implemented.
- CAD uses millimetres; `simulation/` uses SI units. Keep diagram and Python assumptions consistent. Distinguish proposed targets, calculations and measured evidence.
- Do not treat 540 mm legacy mounting-hole spacing as the current 210 mm fore-aft support spacing.
- The 0.3 m/s low-speed study does not validate the proposed 0.8 m/s bare-case target.
- `python simulation/simulate.py --output <review-file.json>` runs the numerical checks without replacing committed results.
- CAD reproduction: install `cad/standee/requirements.txt`; use the commands in README. Do not regenerate large CAD exports for document-only edits.
- `simulation/nailong-motion.fragment.html` is editable interactive source; `simulation/nailong-motion.html` is the exported browser review page.
- Update PRD/PDR, FUNCTIONS, BOM and TASKS when scope or acceptance changes. Keep historical material clearly marked.
- Do not buy hardware, merge PRs or claim physical acceptance as part of a read-only review.
