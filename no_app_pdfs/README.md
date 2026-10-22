# Reference PDFs

These 11 PDFs were imported from the existing `review_no_app_paperscorer/`
reference set. PaperScorer is excluded because it is the draft being evaluated.
Bibliographies are retained. ConvNeXt's interleaved appendix and Deconstructing
Diffusion's appendix sections on page 9 were removed from the imported copies;
the other nine PDFs are unchanged from the existing shortened copies.

`sources.json` records page counts, preparation details, and SHA-256 hashes.
The CLI symlinks these files into each run. Do not edit the symlink targets
inside a run; supply a different set with `--references-dir` if needed.
