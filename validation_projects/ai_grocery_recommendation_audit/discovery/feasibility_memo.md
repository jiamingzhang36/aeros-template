# Feasibility Memo

## Recommendation

Proceed to G4 smoke execution only. Do not treat smoke outputs as final empirical evidence.

## Skill-Assisted Data Probes

Useful probes include FoodData Central item matching, retailer price capture policy review, Open Food Facts coverage checks, and repeated AI recommendation parsing. These can be assisted by data-inventory, data-quality, web-testing, and replication-check workflows, but none has yet been validated as production data collection.

## Data Engineering Burden

The burden is moderate to high. The hardest pieces are parsing vague AI grocery text into purchasable baskets, matching items to nutrition records, and obtaining reproducible price estimates for fixed ZIP/store contexts. Smoke execution can proceed without solving these, but final execution cannot.

## Claim Boundary

The project is bounded to descriptive and measurement claims. It cannot support causal effects, legal discrimination claims, consumer purchase effects, health outcomes, or platform-wide generalization without additional design and data.

## Required Next Probes

1. Approve a prompt/persona grid.
2. Test item parsing on a small set of AI outputs.
3. Probe FoodData Central match rates for common recommended items.
4. Review retailer price source rules and reproducibility.
5. Record model, prompt, timestamp, and repetition metadata for every output.

## Feasible Now

- Offline pipeline smoke test.
- Result index and provenance generation.
- Draft measurement claim boundary testing.

## Feasible After Protocol Approval

- AI recommendation collection under a fixed prompt/persona grid.
- Nutrition scoring after FoodData Central matching probe.
- Affordability scoring after retailer/proxy price protocol approval.

## Not Yet Feasible

- Causal claims.
- Claims about real household purchasing behavior.
- Legal discrimination claims.
- Platform-wide generalization beyond sampled models/prompts/time windows.

## Decision

Continue with O1 measurement audit design and keep claim ceiling at measurement.
