# Shadow Validation Report

Generated: 2026-07-16T17:38:50.601037+00:00
Source built at: 2026-07-16T17:38:50.554460+00:00

## Dataset Summary

- Videos: 389
- Channels: 79
- Labeled trends: 10

## Scoring Validation Metrics

- Precision@15 (high-value trends in top rank): **60.0%**
- Recall of high-value trends in top 15: **100.0%**
- Multi-channel breakout trends (≥3 channels, ≥50% breakout≥2): **3**
- High-value trends in algorithmic top 10: **6**
- Low-value counter-examples in algorithmic top 10: **2** (target: 0)

## Acceptance Checks

- [PASS] Clear breakout trends rank above median
- [FAIL] Low-value generic/manhwa trends not dominating top 10
- [PASS] At least one multi-channel resonance trend detected
- [PASS] Precision@15 ≥ 50%
- [PASS] BreakoutRatio is populated for all videos

## Top 15 Trends by Algorithm Score

| Rank | Trend | Score | Channels | Median Breakout | Manager Value |
| ---: | --- | ---: | ---: | ---: | --- |
| 1 | One Piece Egghead / Recent Arc | 100.0 | 10 | 8.0 | high |
| 2 | Jujutsu Kaisen Current Arc | 100.0 | 7 | 1.0 | high |
| 3 | Hindi Language Recap (non-target) | 100.0 | 20 | 3.365 | low |
| 4 | Isekai Reincarnation Power Fantasy | 96.0 | 8 | 8.0 | normal |
| 5 | Manhwa/Webtoon Recap Crossover | 80.85 | 4 | 0.545 | low |
| 6 | Solo Leveling Season 2 / Jinwoo Arc | 80.2 | 5 | 1.0 | high |
| 7 | Chainsaw Man Season 2 / Reze Arc | 69.09 | 3 | 1.0 | high |
| 8 | Boruto / Naruto Next Generation | 64.81 | 3 | 1.284 | normal |
| 9 | Dandadan Supernatural Battles | 44.8 | 1 | 0.841 | high |
| 10 | Black Clover Return Hype | 39.84 | 1 | 1.177 | high |

## Top 15 Videos by BreakoutRatio

| Rank | Title | Channel | Views | Breakout | Label | Trend |
| ---: | --- | --- | ---: | ---: | --- | --- |
| 1 | Iruma's Family is NOT Human & The Strongest: Derkila's DEMON | Anime Balls Deep | 340262 | 1554.472 | strong_breakout | Unclustered / Other |
| 2 | (20) Ordinary Boy Accidently Awakens Soul Reaper Powers Insi | Animity | 210181 | 1045.619 | strong_breakout | Isekai Reincarnation Power Fantasy |
| 3 | (19) Ordinary Boy Accidently Awakens Soul Reaper Powers Insi | Animity | 239131 | 824.198 | strong_breakout | Isekai Reincarnation Power Fantasy |
| 4 | Everyone Thought He Was The Weakest But He Is The Most Power | Anime Bench | 2500794 | 756.961 | strong_breakout | Hindi Language Recap (non-target) |
| 5 | He Was Born With the Weakest Villager Class, but Unlocks a L | AniCap | 127598 | 697.926 | strong_breakout | Isekai Reincarnation Power Fantasy |
| 6 | 5 Years by Her Side Meant Nothing After She Got Rich—So I Ch | Anime Recap | 263254 | 642.643 | strong_breakout | Unclustered / Other |
| 7 | (18) Ordinary Boy Accidently Awakens Soul Reaper Powers Insi | Animity | 204994 | 492.787 | strong_breakout | Isekai Reincarnation Power Fantasy |
| 8 | King is Reborn As the Greatest Prodigy And Accidentally Tame | Recap-kun | 147226 | 426.424 | strong_breakout | Isekai Reincarnation Power Fantasy |
| 9 | (16) Ordinary Boy Accidently Awakens Soul Reaper Powers Insi | Animity | 207681 | 373.158 | strong_breakout | Isekai Reincarnation Power Fantasy |
| 10 | Our HORRIFYING EXPERIENCE on SKIN WALKER ISLAND (WE ALMOST Q | HypeMyke | 114233 | 369.684 | strong_breakout | Unclustered / Other |
| 11 | The One Piece Remake Ignored Oda... I'm worried | Totally Not Mark | 174158 | 366.169 | strong_breakout | One Piece Egghead / Recent Arc |
| 12 | (17) Ordinary Boy Accidently Awakens Soul Reaper Powers Insi | Animity | 183513 | 362.603 | strong_breakout | Isekai Reincarnation Power Fantasy |
| 13 | (15) Ordinary Boy Accidently Awakens Soul Reaper Powers Insi | Animity | 242218 | 358.113 | strong_breakout | Isekai Reincarnation Power Fantasy |
| 14 | [Full]Orphan Boy is Actually The Reincarnation of The Strong | Anime Bench | 789399 | 341.947 | strong_breakout | Hindi Language Recap (non-target) |
| 15 | The Goku Black Plot Hole Isn't Real | Totally Not Mark | 194479 | 324.325 | strong_breakout | Unclustered / Other |

## Manager Value Ranking (reference)

1. **One Piece Egghead / Recent Arc** (high) — algo score 100.0
2. **Jujutsu Kaisen Current Arc** (high) — algo score 100.0
3. **Solo Leveling Season 2 / Jinwoo Arc** (high) — algo score 80.2
4. **Chainsaw Man Season 2 / Reze Arc** (high) — algo score 69.09
5. **Dandadan Supernatural Battles** (high) — algo score 44.8
6. **Black Clover Return Hype** (high) — algo score 39.84
7. **Isekai Reincarnation Power Fantasy** (normal) — algo score 96.0
8. **Boruto / Naruto Next Generation** (normal) — algo score 64.81
9. **Hindi Language Recap (non-target)** (low) — algo score 100.0
10. **Manhwa/Webtoon Recap Crossover** (low) — algo score 80.85

## Interpretation

BreakoutRatio compares each video's views/hour against its channel's median for the same age bucket. Trend score weights cross-channel resonance (35%) and relative breakout (25%) so coordinated topics with abnormal per-channel performance rise to the top, while routine uploads from large channels stay muted.
