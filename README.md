# Paper Writing Self-Review

AI-based writing quality check for your draft, comparing against a set of reference papers.

This evaluates **writing and presentation only** — not impact, novelty, or technical contribution. Run it when your draft is mostly complete, before submission.

## How to use

1. Make a folder, copy your draft PDF into it, and download all reference papers below into the same folder.

   ```bash
   mkdir review && cd review
   cp /path/to/your/draft.pdf .
   curl -fsSL https://arxiv.org/pdf/2201.03545 -o ConvNeXt.pdf
   curl -fsSL https://arxiv.org/pdf/1608.06993 -o DenseNet.pdf
   curl -fsSL https://arxiv.org/pdf/2503.10622 -o Transformers_without_Normalization.pdf
   curl -fsSL https://arxiv.org/pdf/2306.11695 -o Wanda.pdf
   curl -fsSL https://arxiv.org/pdf/2111.06377 -o MAE.pdf
   curl -fsSL https://arxiv.org/pdf/2401.14404 -o Deconstructing_Diffusion.pdf
   curl -fsSL https://arxiv.org/pdf/2403.08632 -o Decades_Battle_Dataset_Bias.pdf
   curl -fsSL https://arxiv.org/pdf/2402.17762 -o Massive_Activations.pdf
   curl -fsSL https://arxiv.org/pdf/2401.06209 -o Eyes_Wide_Shut.pdf
   curl -fsSL https://arxiv.org/pdf/2412.14171 -o Thinking_in_Space.pdf
   ```

2. Start Claude Code from this folder (`claude`) and paste the prompt below.

## The prompt

```
Score the writing quality of every PDF in this folder. Writing and presentation only, not impact.

Read pages 1-15 of each. Rate 0-100 on:
- Overall
- Title
- Abstract
- Experiment design

Output a comparison table sorted by Overall (highest first).
```

## Reference papers

| Paper | Type | arXiv |
|-------|------|-------|
| ConvNeXt | Method | https://arxiv.org/abs/2201.03545 |
| DenseNet | Method | https://arxiv.org/abs/1608.06993 |
| Transformers without Normalization | Method | https://arxiv.org/abs/2503.10622 |
| Wanda | Method | https://arxiv.org/abs/2306.11695 |
| MAE | Method | https://arxiv.org/abs/2111.06377 |
| Deconstructing Denoising Diffusion | Empirical study | https://arxiv.org/abs/2401.14404 |
| A Decade's Battle on Dataset Bias | Empirical study | https://arxiv.org/abs/2403.08632 |
| Massive Activations in LLMs | Empirical study | https://arxiv.org/abs/2402.17762 |
| Eyes Wide Shut | Benchmark | https://arxiv.org/abs/2401.06209 |
| Thinking in Space | Benchmark | https://arxiv.org/abs/2412.14171 |

## After scoring

- Find your draft in the output table. Pay attention to **same-type** reference papers (method vs method, empirical vs empirical, benchmark vs benchmark).
- You can keep chatting with Claude afterward — discuss the table, ask about specific dimensions. How to improve your paper is up to you.
- If you revise your draft and want to re-score, **start a fresh Claude Code session.** Prior scores in history will bias the new run.
