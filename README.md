# Overlord SMP (Minecraft 26.2 "Chaos Cubed")

A small-group survival server with four interlocking systems and an LLM "overlord"
that reacts to player tribute. Built for under six players.

- **No natural regen** — healing is always economic (golden apples, regen potions, mercy from the overlord).
- **Soul-link (three modes)** — a configurable percentage of damage one player takes bleeds to other linked players. Switchable topology: **pairs** (bonded two-by-two), **global** (everyone shares), or **proximity** (only players within a radius). In global/proximity the coefficient is the *total* bled, split evenly among recipients, so total shared damage stays bounded regardless of group size. Individual death is preserved, so it composes with revival.
- **Permadeath + revival** — death sends you to spectator; the living buy you back at the altar with a Totem of Undying plus XP levels.
- **The Overlord** — an LLM that reads world state and a player's tribute, then acts through a fixed set of typed, validated tools. It both *reacts* to tribute and *proactively issues timed demands*. It is the *only* escalating pressure; the three survival systems are flat. (One escalator, by design, so the difficulty multiplies controllably instead of spiralling.)
- **Demands** — occasionally the overlord issues a collective, timed demand enforced by a visible bossbar countdown. Fulfilment is verified one of three ways (a vanilla scoreboard criterion summed across the group, an altar item delivery, or a freeform objective the model judges at the deadline). The clock escalates through phases and ends in a "Reckoning" overtime; success and failure each fire a typed reward or punishment tool.
- **Memory** — the overlord keeps a persistent event library (append-only on disk) plus a model-maintained chronicle, so it remembers tribute, grudges, and past demands across restarts.

Everything above is a set of **dials the overlord can read and turn**: the soul-link coefficient, the revival cost, per-player buffs and curses. The four features are really one system with a god's hands on it.

---

## Layout

```
datapack/overlord_smp/      # drop into <world>/datapacks/
bridge/                     # the Python overlord (runs beside the server, talks RCON)
```

## Minecraft 26.2 specifics (verified against this release, June 16 2026)

- **Pack format is 107.** `pack.mcmeta` uses `min_format`/`max_format` (the `pack_format` field was replaced in 25w31a). If `/datapack list` shows a format-mismatch warning, set both to the exact value the command reports; the pack still loads, the warning is non-fatal.
- **Singular directory names** (`function`, `tags/function`) — correct at this format.
- The **entity-predicate format changed in 26.2** (component-style map, unknown fields now rejected). This datapack deliberately avoids entity predicates and builds on scoreboards, tags, and `/damage`, so it is unaffected.
- `damage_taken` is a **lifetime cumulative stat**, so soul-link initialises a per-player baseline (`ov_init`) on first tick. Without that, a player's first bonded tick would transfer their entire lifetime damage at once.

## Server setup

1. Copy `datapack/overlord_smp/` into `<world>/datapacks/`, then in-game run `/reload` (or `/datapack enable`).
2. Enable RCON in `server.properties`:
   ```
   enable-rcon=true
   rcon.password=change-me
   rcon.port=25575
   ```
3. Consecrate an altar: stand where you want it and run `/function overlord:admin/altar`.
4. Choose a soul-link mode (default is **global**):
   ```
   /function overlord:admin/link_global       # everyone shares damage
   /function overlord:admin/link_proximity    # only players within the radius share
   /function overlord:admin/link_pairs         # classic bonded pairs
   ```
   For **proximity**, set the radius (blocks): `/scoreboard players set #linkRadius ovGlobal 16`
   For **pairs**, bond two players per pair tag (up to three pairs):
   ```
   /tag Alice add ov_pair_1
   /tag Bob   add ov_pair_1
   /tag Carol add ov_pair_2
   /tag Dave  add ov_pair_2
   ```
   In global and proximity modes no tagging is needed; all living players are linked automatically.

## Bridge setup

```bash
cd bridge
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in RCON_PASSWORD and your LiteLLM endpoint
python overlord_bridge.py
```

The bridge points at any OpenAI-compatible endpoint via `LLM_BASE_URL`, so your
LiteLLM gateway in front of the local 3090 works unchanged. Set
`LANGFUSE_ENABLED=true` (and the keys) to trace every divine judgement.

## How a tribute flows

1. A player drops items near the altar, then drops a **gold ingot** as the commit token ("ring the bell").
2. The datapack tallies tribute (stack count, with diamonds x3 and netherite x10), credits the donor's `ovFavor`, clears the offering, and bumps `storage overlord:bridge seqTribute`.
3. The bridge polls that seq over RCON, finds the donor by their `ovTribute` score, snapshots the world, and asks the overlord.
4. The overlord returns one to three typed tool calls. Each is validated and clamped, then executed over RCON.

The inference delay is intentional theatre: players already saw "the presence
deliberates" when the tribute landed.

## How a demand flows

1. The bridge self-triggers occasionally (probabilistic, mean `DEMAND_MEAN_MINUTES`, with a cooldown and a minimum online-player count) and calls the overlord in *demand* mode, where the only offered tool is `issue_demand`.
2. The overlord authors a collective demand: a description in its own voice, a verification `kind` (`score` / `altar` / `freeform`), a threshold, a deadline, and a `{reward, punishment}` pair naming other tools. The bridge validates and clamps all of it.
3. For `score` demands the bridge creates a scoreboard objective with the chosen criterion and baselines it; for `altar` it passes the item id; for `freeform` it stores the text. It writes the demand into `storage overlord:demand` and runs `demand/begin`, which raises the bossbar and announces it.
4. The datapack owns the clock from here: it counts down on the bossbar, measures group progress every second, and crosses phases (orange at half, red and tightened bonds at quarter, the Reckoning overtime at zero).
5. On resolution the datapack writes `met` / `failed` / `judge` to `demandResult` and bumps `seqDemand`. The bridge reads it and fires the staked reward or punishment (for `freeform` it judges fulfilment first), then records the outcome to memory.

## Memory

The bridge keeps two persistent files under `bridge/state/`:

- `events.jsonl` — an append-only event library (tribute, demands issued/met/failed, memories the overlord chose to record). It survives restarts, so grudges persist.
- `chronicle.json` — a compact, model-maintained first-person summary plus per-player standing, folded forward every `CHRONICLE_EVERY` resolved events so context stays bounded.

Before every decision the bridge assembles a context block from the chronicle, the recent events, and (for tribute) the donor's own history. The overlord can curate its own memory with the `record_memory` tool.

## The safety model (read this before widening the overlord)

The model **never emits a command string.** It selects a tool and fills typed,
clamped, allow-listed parameters; the tool body builds the RCON command from
those validated fields in `tools.py`. This makes commands correct-by-construction
and makes the catastrophic class (`/fill` a million blocks, `/kill @e`, `/stop`)
simply unexpressible. A valid-but-mean call (cursing the wrong player) is allowed
on purpose: that is a capricious god, not a bug.

Growth path is **more typed tools, never rawer access.** If you ever need a raw
escape hatch, add it disabled-by-default and allow-list-filtered, as a rare power
rather than the default loop.

## Test this first (highest-variance pieces)

1. **Soul-link distribution.** Switch to your chosen mode, have one player take fall/mob damage, and confirm the others take roughly `coefficient%` of it *in total* (split among recipients), with **no ping-pong** (the magic-damage bleed must not re-bleed). The anti-feedback compensation in `soullink/dist_apply.mcfunction` (and `apply.mcfunction` for pairs) pre-advances each recipient's baseline; if you see oscillation, that is the code to inspect. In proximity mode, confirm that spreading out past the radius drops a player from the link. Note the MVP works at integer-HP granularity (sub-half-heart bleed is dropped), which is most visible with small hits or large groups; move to macro-passed decimals if you want finer resolution.
2. **Altar attribution.** Tribute is credited to the *nearest* player within 12 blocks. With several players clustered on the altar this can misattribute; widen or tighten the radius, or gate on a per-player commit, if it matters for your group.
3. **Revival selection.** Currently revives an arbitrary single dead player. Add a queue (oldest-death-first) or a chooser if you want deterministic order.
4. **Demand verification.** For a `score` demand, confirm the bridge's 0.4s pause after creating `ovDemand` is enough for the statistic to populate before baselining (a player joining mid-demand can miscount). For `altar`, confirm `count_one` sums item *counts* not stacks. For `freeform`, remember it defaults to mercy if the model fails to judge.
5. **Global shared-pain floor.** Global soul-link has no death floor, so during a Reckoning (coefficient maxed) a single creeper can cascade a group wipe. Add the optional chain-death floor if that is too punishing for your group.

## Upgrade paths (when the MVP proves the loop is fun)

- **Transport:** 26.x ships the **Minecraft Server Management Protocol v3.0.0** (JSON-RPC). It is a cleaner push-based event channel than RCON polling and the right next step for the bridge. RCON is used here only because it is universal and zero-dependency.
- **Skill-library promotion (Voyager pattern):** when you add a freeform-generation tool later, promote any generated intervention that validates and runs clean into the typed registry. The overlord should get *more* templated and safer the longer it runs, not more feral.
- **More dials:** expose escalating-difficulty as overlord tools (global mob attribute buffs, threat waves) so rising pressure stays reactive instead of becoming a second always-on curve.

## Tuning quick reference

| Dial | Where | Default |
|---|---|---|
| Soul-link mode (0/1/2) | `#linkMode ovGlobal` (or `admin/link_*`) | 1 (global) |
| Soul-link bleed % | `#coeff ovGlobal` (or `set_soullink_coefficient` tool) | 30 |
| Proximity radius (blocks) | `#linkRadius ovGlobal` (or `set_soullink_radius` tool) | 16 |
| Revival cost (levels) | `#revivalXp ovGlobal` (or `set_revival_cost` tool) | 30 |
| Tribute commit token | `tribute/commit.mcfunction` (gold ingot) | gold_ingot |
| Demand frequency (mean min) | `DEMAND_MEAN_MINUTES` | 60 |
| Demand cooldown (min) | `DEMAND_COOLDOWN_MINUTES` | 15 |
| Demand min players online | `DEMAND_MIN_PLAYERS` | 2 |
| Demand deadline bounds (min) | `DEMAND_DEADLINE_MIN` / `_MAX` | 3 / 30 |
| Demand threshold cap | `DEMAND_THRESHOLD_MAX` | 2000 |
| Reckoning overtime (s) | `DEMAND_OVERTIME_S` | 45 |
| Allowed demand criteria | `DEMAND_CRITERIA` | see config |
| Chronicle fold cadence | `CHRONICLE_EVERY` | 4 |
| State dir (events + chronicle) | `STATE_DIR` | state |
| Effect/mob allow-lists, bounds | `bridge/.env` / `config.py` | see file |
