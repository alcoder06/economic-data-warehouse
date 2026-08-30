# Build log

Tick these off as we go. Each phase ends in a checkpoint worth verifying before
moving on, because a mistake in the model is much cheaper to fix before eleven
visuals are sitting on top of it.

## Phase 1 — Data and model

- [ ] `DataFolder` parameter created, pointing at `data\gold`
- [ ] 5 queries loaded and renamed: `Fact`, `Metric`, `Region`, `Year`, `Convergence`
- [ ] `Price Basis` created via Enter Data (Nominal, Real)
- [ ] `_Measure` created via Enter Data, its column hidden
- [ ] Auto Date/Time turned off
- [ ] 3 relationships built, all single-direction
- [ ] `Convergence` and `Price Basis` left disconnected
- [ ] Every numeric column in `Fact` set to *Do not summarize*
- [ ] Key columns hidden from report view

**Checkpoint:** model view shows one star, two floating tables, three relationships.

## Phase 2 — Measures

- [ ] 31 measures created from `measures.dax`
- [ ] Format strings applied
- [ ] Display folders assigned

**Checkpoint:** a card with `Share of Growth That Is Price` and the Year slicer set
to 2010-2024 reads **91.3%**. If it does, the whole model is wired correctly, because
that number depends on the fact, both dimensions, the deflator column and four
measures agreeing.

## Phase 3 — Page 1, The nominal illusion

- [ ] 4 KPI cards
- [ ] Hero: indexed nominal vs real line
- [ ] Growth rates clustered column
- [ ] Investment correlation scatter + `Price Basis` slicer + correlation card

**Checkpoint:** toggling the slicer moves the correlation card between +0.674 and +0.036.

## Phase 4 — Page 2, The long view

- [ ] Real GDP per capita 1987-2025 with era bands
- [ ] Sector composition stacked area
- [ ] Inflation line
- [ ] Openness and remittances
- [ ] Caption noting regional data starts 2010

## Phase 5 — Page 3, Regional divergence

- [ ] Beta-convergence scatter + period slicer + dynamic title
- [ ] Verdict card with conditional colour
- [ ] Two-Gini line chart
- [ ] Regions ranked by real GDP per capita

**Checkpoint:** switching the period slicer flips the trend line's slope.

## Phase 6 — Detail page and polish

- [ ] Hidden drillthrough page on `Region[region_name]`
- [ ] Theme applied
- [ ] Header consistent across pages
- [ ] Reset-filters bookmark

## Phase 7 — Ship

- [ ] Screenshots to `powerbi/images/`
- [ ] `.pbix` saved to `powerbi/`
- [ ] Published, public link in README
- [ ] Commit and push

---

## Numbers to check against

If the model is right, these fall out. If one is wrong, the note says where to look.

| Where | Reads | If wrong |
|---|---|---|
| `Share of Growth That Is Price`, 2010-2024 | 91.3% | deflator join, or Year slicer range |
| `Nominal Growth Multiple`, 2010-2024 | 17.43x | `is_national` filter missing → doubled |
| `Real Growth Multiple`, 2010-2024 | 2.43x | as above |
| `Price Level Multiple`, 2010-2024 | 7.17x | `MAX` vs `SUM` on the deflator |
| `Corr GDP vs Investment`, Nominal | +0.674 | year bound not 2011 |
| `Corr GDP vs Investment`, Real | +0.036 | as above |
| `Gini (real GDP per capita)`, 2024 | 0.325 | `AVERAGE` vs `SUM` |
| `Gini (nominal GDP levels)`, 2024 | 0.328 | |
| `Beta Coefficient`, Post-float | +0.059 | |
| GDP Real Growth %, 2017 | 4.7% | |
| GDP Nominal Growth %, 2018 | 33.9% | |

A card reading exactly double an expected value is almost always the missing
`is_national` filter: the Republic total being summed alongside the fourteen regions
that compose it.
