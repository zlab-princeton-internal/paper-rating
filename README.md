# Paper Writing Self-Review

*By [Zhuang Liu](https://liuzhuang13.github.io/)*

**Related**: [Writing Guide](https://github.com/zlab-princeton-internal/writing-guide) · [Figure Guide](https://github.com/zlab-princeton-internal/figure-guide) · [AI Paper Checking](https://github.com/zlab-princeton-internal/ai-paper-checking) · [Peer Review System](https://github.com/zlab-princeton-internal/peer-review)

> This guide is intended for [Zhuang Liu](https://liuzhuang13.github.io/)'s group members. Others are welcome to adopt or adapt it for their own use.

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

2. Start Claude Code from this folder (`claude`) and paste the prompt below. **Use the highest-effort / reasoning mode available** (Claude Opus with extended thinking, GPT-5 / Codex with high reasoning, etc.).

   Alternative: ChatGPT in **Thinking or Pro mode** — upload all the PDFs directly to the chat instead of using a local folder.

## The prompt

```
Score the writing quality of every PDF in this folder. Writing and presentation only, not impact.

Read each paper in full and score each one independently. Rate 0-100 on:
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

- Find your draft in the output table. Pay attention to **same-type** reference papers (method vs method, empirical vs empirical, benchmark vs benchmark). **Aim to bring your draft at least up to the average score of the same-type reference papers.**
- You can keep chatting with the AI to dig into the justifications, ask why a certain dimension scored where it did, or get advice on what to look at first. How to actually improve the paper is up to you.
- **Do not let the AI directly edit your paper and re-score in the same session.** The AI will optimize against its own biases and the score becomes meaningless (overfitting).
- **Every re-scoring must be in a brand-new session** with no access to prior history or previous scores. Fully exit the AI tool and start over from scratch each time.
