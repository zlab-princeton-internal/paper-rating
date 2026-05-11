# Paper Writing Self-Review

AI-based writing quality check for your draft, comparing against a curated set of high-quality reference papers from our group and others.

This evaluates **writing and presentation only** — not impact, novelty, or technical contribution. Run it when your draft is mostly complete, before submission.

## How to use

1. Make a folder, copy your draft PDF in as `my_paper.pdf`, and download **all** reference papers below into the same folder.

   ```bash
   mkdir review && cd review
   cp /path/to/your/draft.pdf my_paper.pdf
   curl -fsSL https://arxiv.org/pdf/2201.03545 -o ConvNeXt.pdf
   curl -fsSL https://arxiv.org/pdf/1608.06993 -o DenseNet.pdf
   curl -fsSL https://arxiv.org/pdf/2503.10622 -o Transformers_without_Normalization.pdf
   curl -fsSL https://arxiv.org/pdf/2306.11695 -o Wanda.pdf
   curl -fsSL https://arxiv.org/pdf/2401.14404 -o Deconstructing_Diffusion.pdf
   curl -fsSL https://arxiv.org/pdf/2403.08632 -o Decades_Battle_Dataset_Bias.pdf
   curl -fsSL https://arxiv.org/pdf/2402.17762 -o Massive_Activations.pdf
   curl -fsSL https://arxiv.org/pdf/2401.06209 -o Eyes_Wide_Shut.pdf
   curl -fsSL https://arxiv.org/pdf/2111.06377 -o MAE.pdf
   curl -fsSL https://arxiv.org/pdf/2412.14171 -o Thinking_in_Space.pdf
   ```

2. Start Claude Code from this folder (`claude`), then paste the prompt below. The AI will score all papers (your draft + the references) together in one comparison table.

3. In the output table, find where your draft lands. Pay attention to **same-type** reference papers — your draft is most directly comparable to method papers if it's a method paper, empirical studies if it's empirical, benchmarks if it's a benchmark. If you are 5+ points below same-type peers, plan a writing revision before submission.

4. AI scoring has variance. Run the prompt 2–3 times and look at the spread, not a single number.

## The prompt

```
Score the writing quality of every PDF in this folder. Writing and presentation only — NOT impact, novelty, or technical merit.

For each paper, read pages 1-15 and rate 0-100 on:
- Overall
- Title
- Abstract
- Experiment design

Anchors: 90+ outstanding, 80s very good, 70s good, <70 weak. Most ML papers fall 65-85. Be calibrated; do not inflate.

Output a comparison table sorted by Overall (highest first). For my_paper.pdf, also give 3 most actionable writing improvements.
```

## Reference papers

| Paper | Type | arXiv |
|-------|------|-------|
| ConvNeXt | Method | https://arxiv.org/abs/2201.03545 |
| DenseNet | Method | https://arxiv.org/abs/1608.06993 |
| Transformers without Normalization | Method | https://arxiv.org/abs/2503.10622 |
| Wanda (LLM pruning) | Method | https://arxiv.org/abs/2306.11695 |
| MAE (Kaiming He) | Method | https://arxiv.org/abs/2111.06377 |
| Deconstructing Denoising Diffusion | Empirical study | https://arxiv.org/abs/2401.14404 |
| A Decade's Battle on Dataset Bias | Empirical study | https://arxiv.org/abs/2403.08632 |
| Massive Activations in LLMs | Empirical study | https://arxiv.org/abs/2402.17762 |
| Eyes Wide Shut | Benchmark | https://arxiv.org/abs/2401.06209 |
| Thinking in Space (Saining Xie) | Benchmark | https://arxiv.org/abs/2412.14171 |
