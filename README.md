# Overlord SMP (Minecraft 26.2 "Chaos Cubed")

A small-group survival server with four interlocking systems and an LLM "overlord"
that reacts to player tribute. Built for under six players.

- **No natural regen** — healing is always economic (golden apples, regen potions, mercy from the overlord).
- **Soul-link (three modes)** — a configurable percentage of damage one player takes bleeds to other linked players. Switchable topology: **pairs** (bonded two-by-two), **global** (everyone shares), or **proximity** (only players within a radius). In global/proximity the coefficient is the *total* bled, split evenly among recipients, so total shared damage stays bounded regardless of group size. Individual death is preserved, so it composes with revival.
- **Permadeath + revival** — death sends you to spectator; the living buy you back at the altar with a Totem of Undying plus XP levels.
- **The Overlord** — an LLM that reads world state and a player's tribute, then acts through a fixed set of typed, validated tools. It both *reacts* to tribute and *proactively issues timed demands*. It is the *only* escalating pressure; the three survival systems are flat. (One escalator, by design, so the difficulty multiplies controllably instead of spiralling.)
- **Demands** — occasionally the overlord issues a collective, timed demand enforced by a visible bossbar countdown. Fulfilment is verified one of three ways (a vanilla scoreboard criterion summed across the group, an altar item delivery, or a freeform objective the model judges at the deadline). The clock escalates through phases and ends in a "Reckoning" overtime; success and failure each fire a typed reward or punishment tool.
- **Wrath and world events.** The overlord's mood is a single shared, visible meter on a bossbar. While it is up, hostile mobs near players are empowered and the world darkens for everyone; a met demand soothes it, a failed one stokes it (harder on a failure streak), and it decays toward calm when the overlord is idle. It is the overlord's hand on the dial made legible, *not* a second always-rising curve. Alongside it, the overlord can impose group-wide effects and unleash temporary, self-reverting world events (spawn surges, storms, nightfall, dread, a blood moon), and can invoke owner-vetted rituals from external datapacks. Every one of these is one more typed tool with its own clamps and allow-lists.
- **Shared fate and foreshadowing.** Beyond the basic demand kinds, the overlord can call a **survival ordeal** (keep everyone alive to the deadline; any death fails it, and the world turns massively deadlier as the clock falls), a **sacrifice** (a steep collective tithe of weighted valuables to the altar, or a drawdown of the saved favor pool), and can **foreshadow** (speak an omen now and let a pre-validated blow land minutes later). All tribute also feeds one **communal favor pool** on a shared bossbar, the literal "one number the whole group fills," which the overlord spends for group relief.
- **The overlord notices, answers, and acts on its own.** Beyond tribute and demands, the overlord wakes on what happens in the world: a player's first diamond or first step into the Nether, sleeping, surviving to dawn, or standing idle too long. Players can also speak back: leave a **written book** on the altar and the overlord reads it and responds in character (a line, a gift, wrath, an omen, or pointed silence). And on its own rhythm (every `PULSE_MINUTES`) it takes an **autonomous turn**, surveying the world and choosing to stir or stay silent without being prompted. Every reactive trigger is its own event channel, so this is the main surface for agentic, nondeterministic behavior.
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
- Wrath uses **named attribute modifiers** (resource-location ids, `add_multiplied_base` operation) and a custom **entity-type tag** (`tags/entity_type/overlord:hostiles`), both current at this format. Attribute ids dropped their `generic.` prefix in 1.21.2, so the datapack uses `minecraft:attack_damage` / `minecraft:max_health`. A handful of mobs (creepers) have no attack-damage attribute, so that one modifier simply no-ops for them.

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

The typed-tool boundary (validation, clamping, allow-list refusals, the wrath
coupling) has unit tests that need only `pydantic`:

```bash
python -m pytest bridge/tests        # or: python -m unittest discover bridge/tests
```

## How a tribute flows

1. A player drops items near the altar, then drops a **gold ingot** as the commit token ("ring the bell").
2. The datapack tallies tribute (stack count, with diamonds x3 and netherite x10), credits the donor's `ovFavor`, clears the offering, and bumps `storage overlord:bridge seqTribute`.
3. The bridge polls that seq over RCON, finds the donor by their `ovTribute` score, snapshots the world, and asks the overlord.
4. The overlord returns one to three typed tool calls. Each is validated and clamped, then executed over RCON.

The inference delay is intentional theatre: players already saw "the presence
deliberates" when the tribute landed.

## How a demand flows

1. The bridge self-triggers occasionally (probabilistic, mean `DEMAND_MEAN_MINUTES`, with a cooldown and a minimum online-player count) and calls the overlord in *demand* mode, where the only offered tool is `issue_demand`.
2. The overlord authors a collective demand: a description in its own voice, a verification `kind` (`score` / `altar` / `freeform` / `survive` / `sacrifice`), a threshold, a deadline, and a `{reward, punishment}` pair naming other tools. The bridge validates and clamps all of it.
3. For `score` demands the bridge creates a scoreboard objective with the chosen criterion and baselines it; for `altar` it passes the item id; for `freeform` it stores the text; for `survive` it pushes a surge profile for the ordeal's escalating hordes; for `sacrifice` it records the source (fresh altar valuables or a draw from the saved favor pool). It writes the demand into `storage overlord:demand` and runs `demand/begin`, which raises the bossbar and announces it.
4. The datapack owns the clock from here: it counts down on the bossbar, measures group progress every second, and crosses phases (orange at half, red and tightened bonds at quarter, the Reckoning overtime at zero). A `survive` ordeal instead ramps the soul-link coefficient and spawn surges together as the clock falls, fails instantly on any death, and wins by reaching the deadline with everyone alive (a shared low-health vitals bar tracks the weakest member).
5. On resolution the datapack writes `met` / `failed` / `judge` to `demandResult` and bumps `seqDemand`. The bridge reads it and fires the staked reward or punishment (for `freeform` it judges fulfilment first), then records the outcome to memory.

## How wrath flows

1. The overlord sets its wrath with the `set_wrath` tool (or it shifts automatically: a met demand lowers it, a failed demand raises it, scaled by the failure streak). The bridge owns the level-to-fraction math, pushes the mob-buff fractions and bar appearance into `storage overlord:wrath`, and writes `#wrath` / `#wrathMax`.
2. The datapack's `wrath/` per-second clock reflects the meter on a shared bossbar and, while wrath is above zero, empowers hostile mobs within `WRATH_BUFF_RADIUS` of any player using removable named attribute modifiers (each mob is buffed once, then tagged `ov_buffed`).
3. `world_event` unleashes a temporary event: the bridge clamps magnitude and duration, picks an allow-listed themed mob for any spawn surge, writes `storage overlord:event`, and runs `overlord:event/<name>`. Surges are timed, cadence-gated, and capped at `EVENT_SPAWN_CAP` concurrent `ov_surge` mobs; storms and effects expire on their own.
4. Wrath decays one level every `WRATH_DECAY_MINUTES` of idle calm, and the bridge re-pushes fractions from the persisted level on startup. To hard-reset everything (zero the meter, strip all mob buffs, kill surge mobs, hide the bar) run `/function overlord:admin/wrath_clear`.

## How the overlord reacts (milestones and prayers)

1. A `milestone/` per-second detector flags a player on `ovMilestone` (first diamond via the `picked_up:diamond` stat, first Nether via `if dimension`, sleeping via a stat delta, surviving to dawn via the day/night transition, or going idle via unchanged block position) and bumps `seqMilestone`.
2. A player who leaves a **written book** on the altar triggers `prayer/commit`, which copies the book into `storage overlord:prayer`, marks the supplicant, and bumps `seqPrayer`.
3. The bridge polls both channels (each with its own cooldown so the overlord stays un-chatty), assembles memory context, and calls one shared `react_event` turn. The overlord answers with the normal tool set: a line, a boon, a punishment, an omen, or silence. For a prayer met with silence it still posts a brief acknowledgement so the player knows it was heard.

This is the agentic surface: adding a new thing for the overlord to notice is a datapack detector that bumps a `seq*` plus a bridge poller that calls `react_event`. (Reading player text from a book over RCON is the version-fragile part; the Server Management Protocol is the clean upgrade path.)

Beyond reacting, the overlord also takes an **autonomous turn every `PULSE_MINUTES`**: it surveys world state and memory and chooses, on its own rhythm, to act through its tools (speak, bless or curse, shift wrath, unleash an event, spend favor, foreshadow) or to watch in silence. This is what makes it feel like a presence with its own will rather than something that only responds when poked. It is not a second escalator: the pulse ratchets nothing by itself, an active demand suppresses it, and wrath still decays on its own. Set `PULSE_MINUTES=0` to turn it off.

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
6. **Wrath buffs and surges.** Raise wrath (`set_wrath`) and confirm nearby hostiles gain the `overlord:wrath_dmg` / `overlord:wrath_hp` modifiers and that their health rescales to the new max; then confirm `/function overlord:admin/wrath_clear` strips the modifiers, kills `ov_surge` mobs, and hides the bar. Trigger a `spawn_surge` world event and confirm it respects `EVENT_SPAWN_CAP` and that the spawn positions are sane (the heuristic placement can be awkward). The buff scan is near-players-only and bounded by `WRATH_BUFF_RADIUS`; watch it on large or busy worlds.
7. **Survival ordeal and sacrifice.** Issue a `survive` demand and confirm the vitals bar appears, the coefficient and surges ramp by phase, a single death fails it instantly, and reaching the deadline alive wins. For `sacrifice`, confirm `source=altar` consumes weighted valuables into progress (rarer items count for more) and `source=pool` reads and then spends the favor pool on success. Confirm tribute raises the `overlord:favor` bar and that `spend_favor` refuses when the pool cannot afford the cost. Note the ordeal is tuned brutal at the end (coefficient 80 in global soul-link has no death floor); soften it in `demand/survive_ramp` if it is too punishing for your group.

## Upgrade paths (when the MVP proves the loop is fun)

- **Transport:** 26.x ships the **Minecraft Server Management Protocol v3.0.0** (JSON-RPC). It is a cleaner push-based event channel than RCON polling and the right next step for the bridge. RCON is used here only because it is universal and zero-dependency.
- **Skill-library promotion (Voyager pattern):** when you add a freeform-generation tool later, promote any generated intervention that validates and runs clean into the typed registry. The overlord should get *more* templated and safer the longer it runs, not more feral.
- **More dials:** the wrath meter and world events already expose global mob attribute buffs and threat waves as reactive overlord tools (rising pressure stays the overlord's choice, not a second always-on curve). Extend the same way: add a `world_event` entry plus one datapack function, or register an external pack through `invoke_ritual`. Never widen a tool to take raw input as a shortcut.

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
| Wrath max level | `WRATH_MAX` | 5 |
| Wrath mob buff fractions | `WRATH_MOB_DMG` / `WRATH_MOB_HP` | see config |
| Wrath buff radius (near players) | `WRATH_BUFF_RADIUS` | 48 |
| Wrath idle decay (min/level) | `WRATH_DECAY_MINUTES` | 25 |
| Wrath shift per demand | `WRATH_ON_FAIL` / `WRATH_ON_SUCCESS` | 1 / 1 |
| Registered world events | `WORLD_EVENTS` | spawn_surge,storm,nightfall,dread,blood_moon |
| World event max duration (s) | `EVENT_MAX_DURATION_S` | 300 |
| Surge concurrent cap | `EVENT_SPAWN_CAP` | 12 |
| Surge mob allow-list | `SURGE_MOBS` | see config |
| Group-effect allow-list | `MASS_EFFECTS` | see config |
| External ritual allow-list | `EXTERNAL_RITUALS` | empty |
| Favor pool bar scale | `FAVOR_POOL_MAX` | 1000 |
| Favor spend cost / boon length | `FAVOR_SPEND_COST` / `FAVOR_BOON_DURATION` | 150 / 40 |
| Favor boon allow-list | `FAVOR_BOONS` | mercy,feast,reprieve,calm |
| Foreshadow delay bounds (s) | `FORESHADOW_MIN_S` / `FORESHADOW_MAX_S` | 10 / 1800 |
| Survive ordeal ramp | `demand/survive_ramp.mcfunction` | coeff 40/60/80 by phase |
| Milestone / prayer cooldowns (s) | `MILESTONE_COOLDOWN_S` / `PRAYER_COOLDOWN_S` | 45 / 12 |
| Idle detection threshold (s) | `#idleThreshold ovGlobal` | 180 |
| Prayer medium | written book left on the altar | written_book |
| Autonomous pulse interval (min) | `PULSE_MINUTES` (0 disables) | 10 |
| Pulse minimum players | `PULSE_MIN_PLAYERS` | 1 |
| Chronicle fold cadence | `CHRONICLE_EVERY` | 4 |
| State dir (events + chronicle) | `STATE_DIR` | state |
| Effect/mob allow-lists, bounds | `bridge/.env` / `config.py` | see file |
