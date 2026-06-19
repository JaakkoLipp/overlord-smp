# CLAUDE.md

Guidance for agents working on Overlord SMP. Read this before changing anything.
The point of this file is to keep the vision intact across sessions. The systems
here are deliberately constrained, and most of the constraints are load-bearing.
If a change feels like it is fighting one of the invariants below, the invariant
is almost certainly right and the change is wrong.

## What this is

A small-group (under six players) Minecraft 26.2 survival server with an LLM
"overlord" that rules the world. Two processes:

- A **datapack** runs inside the world every tick. It owns all real-time
  mechanics: soul-link damage distribution, death and revival, the altar, and the
  demand clock. It never calls the model.
- A **Python bridge** runs beside the server and is the only thing that talks to
  the model. It polls the world over RCON, wakes the overlord on events, and
  executes the overlord's decisions back into the world over RCON.

No client mods. No player installs. Everything is vanilla plus one datapack plus
one out-of-process brain.

## The non-negotiable invariants

These are the spine. Do not break them without an explicit, recorded decision.

1. **The model never emits raw commands.** It selects from a fixed registry of
   typed tools and fills validated, clamped, allow-listed parameters. The bridge
   constructs the actual command string. Catastrophic commands (`/fill` over huge
   volumes, `/kill @e`, `/stop`, `/op`) are structurally inexpressible because no
   tool can express them. The growth path is *more typed tools*, never rawer
   access. If you ever find yourself adding a `run_command(text)` tool, stop.

2. **One escalator.** The overlord (tribute judgement plus demands) is the only
   system that ratchets pressure up. The survival systems (no-regen, soul-link,
   permadeath) are flat. This is what keeps difficulty controllable instead of
   spiralling into a death loop. Do not add a second independent escalator (a
   shrinking border, standalone mob-scaling, a tech-tree timer). New pressure
   should be expressed *through* the overlord so there is a single hand on the
   dial. The **Wrath meter** is that hand made visible, not a second escalator:
   it is set by the overlord's own tools, it falls when players appease it, and it
   decays toward calm on its own when the overlord is idle. If you ever make wrath
   rise on a clock the overlord does not control, you have built the second
   escalator this invariant forbids.

3. **The altar is the shared channel.** Tribute and demand deliveries both flow
   through the altar marker and the same item-scan logic. Keep new player-to-world
   economic interactions on this channel rather than inventing parallel ones.

4. **Latency is theatre, not lag.** Model inference takes seconds. That delay is
   framed in-world as the presence "deliberating", so it reads as intent. Do not
   try to make the model respond on the tick loop. Anything that must be
   frame-accurate belongs in the datapack.

5. **Verification is tiered and mostly correct-by-construction.** A demand is
   checked one of three ways (see below). The first two are datapack-verified with
   the model out of the loop. The third (freeform) is the only place the model
   judges fulfilment, and it is the only place a demand can be satisfied or failed
   incorrectly. Keep freeform the exception, not the default, and never let a
   freeform verdict trigger anything outside the typed-tool boundary.

6. **Memory persists.** The event log is append-only on disk so grudges survive
   restarts. Do not move it into volatile state, and do not let memory failures
   crash the main loop (they are best-effort by design).

## Architecture map

```
datapack/overlord_smp/data/overlord/function/
  load / tick                  init and per-tick driver
  soullink/                    three switchable modes (pairs / global / proximity)
  death/ revival/              permadeath to spectator, altar revival ritual
  tribute/                     altar item tally, credits favour, bumps seqTribute
  altar_tick                   per-altar tribute + revival logic
  demand/                      proactive demands: clock, phases, verify (score / altar /
                               freeform / survive ordeal / sacrifice), plus the vitals bar
  wrath/                       the shared wrath meter (per-second clock, mob buffs, surge)
  event/                       one function per discrete temporary world event
  favor/                       the communal favor-pool bossbar (shared ledger)
  milestone/                   per-second detectors that wake the overlord (diamond, nether, sleep, dawn, idle)
  prayer/                      a written book on the altar becomes a message to the overlord
  admin/                       live switches (link mode, cancel demand, place altar, wrath_clear)

bridge/
  rcon.py            zero-dependency Source RCON client with reconnect
  config.py          all bounds, allow-lists, intervals (env-driven)
  tools.py           the tool registry = the safety boundary
  events.py          RCON sensing + dual-seq polling + demand-result reader
  overlord.py        persona + entry points (judge / demand / judge_freeform / react_event / consider)
  memory.py          EventLog (JSONL) + Chronicle (model-maintained summary)
  overlord_bridge.py main loop: poll tribute/demand/milestone/prayer, maybe issue demand, pulse
  state/             events.jsonl + chronicle.json (created at runtime)
```

### The event channels

The bridge polls independent sequence numbers mirrored into `storage overlord:bridge`,
one per event class so two events in the same second cannot clobber each other. Do not
collapse them. Each channel: the datapack writes a payload plus bumps its `seq*`; the
bridge polls, builds memory context, and calls an overlord entry point.

- `seqTribute` rises when a player commits tribute at the altar. The bridge reads
  the donor and value and calls `overlord.judge`.
- `seqDemand` rises when an active demand resolves. The bridge reads `demandResult`
  (`met` / `failed` / `judge`) and dispatches the staked reward or punishment, or
  runs freeform judging first.
- `seqMilestone` rises when a per-second detector flags a player (first diamond,
  first Nether entry, sleeping, surviving to dawn, going idle). The bridge scans the
  `ovMilestone` codes, maps them to phrases (`events.MILESTONES`), and reacts.
- `seqPrayer` rises when a written book is left on the altar. The bridge copies the
  book out of `storage overlord:prayer`, extracts the text tolerantly, and reacts.

Milestones and prayers both flow through one reactive entry point, `overlord.react_event`,
which offers the same tribute-judgement tool set: the overlord may answer with a line, a
gift, a punishment, an omen, or silence. Adding a trigger is a new datapack detector that
bumps a `seq*` plus a bridge poller that calls `react_event` (see "Add a new event trigger").
This is the main growth surface for agentic, non-deterministic behaviour: more of the world
the overlord can notice and choose to act on.

### The autonomous pulse (the overlord's own rhythm)

Beyond reacting, the overlord takes an unprompted turn every `pulse_minutes` (`_maybe_pulse`
to `overlord.consider`): it surveys world state plus memory and chooses to act through its
reactive tools or to watch in silence. This is what makes it read as a presence with its own
will rather than a vending machine that only responds when poked. It is deliberately NOT a
second escalator: the pulse ratchets nothing by itself, every action is a typed tool the
model selected, an active demand suppresses it (the demand is the overlord's current focus),
and wrath still decays on its own. The pulse offers the reactive tool set but not
`issue_demand` (demands keep their own dedicated clock); wiring the pulse to author demands
at a moment of the model's choosing is a sane future step. Set `pulse_minutes` to 0 to
disable. It costs one model call per pulse, so keep the interval sane for a local model.

### The demand lifecycle (the interesting clock)

The clock is not binary. It crosses phases that ratchet visible dread, all of it
bounded and reversible, using the soul-link coefficient as the instrument:

- Above half time: just the bossbar countdown.
- At half time: bar turns orange, the overlord murmurs.
- At quarter time: bar turns red, the soul-link coefficient spikes (saved first,
  restored on resolve) so shared pain tightens exactly when players are scrambling.
- At zero, unmet: the **Reckoning**, an overtime window (`demand_overtime_s`) with
  the coefficient maxed and a dramatic title/sound. A clutch delivery during
  overtime still wins.
- Overtime expires: true failure. `failStreak` increments, and consecutive
  failures escalate the next demand. Success resets the streak and relaxes bonds.

The datapack owns every part of this. The bridge only sets it up and handles the
two outcomes. The reward and punishment are each a deferred, typed `{tool, args}`
call validated against the registry, so the safety boundary holds even on failure.

Five verification kinds now ride this one clock. `score`, `altar`, and `freeform`
are the originals. Two more were added for shared-fate play, both reusing the same
lifecycle, bossbar, phases, and staked outcomes:

- `survive`: an ordeal. The win is reaching the deadline with nobody dead; any death
  fails it instantly (detected against a monotonic `#deathTally` so revival cannot
  mask it). It inverts the deadline (reaching zero is success, not a Reckoning) and
  is correct-by-construction. As the clock falls it ramps both instruments together
  by phase: the soul-link coefficient climbs and the spawn surge tightens, so staying
  alive gets massively harder near the end. A shared `overlord:vitals` bossbar shows
  the weakest living member's health for the duration. The survive ramp owns the
  coefficient (saved at begin, restored on resolve), so `enter_quarter` skips its
  standard spike for this kind.
- `sacrifice`: a steep collective tithe. `source=altar` tallies and consumes weighted
  valuables delivered to the altar (rarer items count for more, summed into progress);
  `source=pool` measures the communal favor pool and spends `threshold` from it on
  success. Both are progress-based and resolve through the normal success / Reckoning
  paths. The bridge picks the form the model chose.

### The communal favor pool (one shared number the group feeds)

Every tribute also adds its value to `#favorPool ovGlobal`, shown to everyone on the
always-visible `overlord:favor` bossbar: the literal common-goal number. The overlord
alone spends it through the `spend_favor` tool, which reads the pool over RCON, refuses
if it cannot afford the flat cost, then deducts and grants a group boon (`mercy`,
`feast`, `reprieve`, or `calm`, which lowers wrath one level via the shared `push_wrath`
helper). The pool persists across reload; the bridge re-syncs the bar scale on startup.

### Foreshadowing (the dungeon-master lever)

`foreshadow` speaks an omen now and optionally schedules one pre-validated `{tool, args}`
action to strike after a clamped delay. The omen is pure theatre (and is logged to
memory); the deferred payload is held in the bridge's `pending_omens` and fired by
`_fire_due_omens` through the same `_fire_stake` path a demand stake uses, so it stays
inside the typed boundary. It is not a second escalator: it is one delayed expression of
the overlord's own will. `foreshadow` is stake-forbidden so a resolution cannot schedule
another deferral, and `issue_demand` payloads are refused (no nested clocks). Pending
omens are in-memory, so a bridge restart drops them (like an active demand).

### The wrath meter (the overlord's disposition, made shared and visible)

Wrath is one global level (`#wrath ovGlobal`, 0..`#wrathMax`) shown to everyone on
a bossbar. It is the overlord's mood made mechanical: while it is above zero, the
`wrath/` per-second clock empowers hostile mobs near players (removable named
attribute modifiers, scaled by per-level fraction tables) and reddens the bar.

The split of responsibility mirrors the demand clock. The **bridge** owns the
level-to-fraction math (in `tools.py`, fully testable and clamped): the `set_wrath`
tool computes the mob-buff fractions and bar appearance, pushes them into
`storage overlord:wrath`, and writes `#wrath` / `#wrathMax`. The **datapack** just
reflects that storage. Coupling to demands lives in `overlord_bridge`: a met demand
lowers wrath by `wrath_on_success`, a failed one raises it by `wrath_on_fail` scaled
by `failStreak` (so a bad streak escalates the world for the whole group), and at
peak wrath a failure erupts into a blood moon. Idle decay drops one level every
`wrath_decay_minutes` of calm. On startup the bridge re-pushes fractions from the
persisted `#wrath` so storage, scoreboard, and bar stay consistent across restarts.

World events are the open-ended flavour channel beside the meter. `world_event`
picks a registered event (`spawn_surge`, `storm`, `nightfall`, `dread`,
`blood_moon`), the bridge clamps magnitude and duration and chooses an allow-listed
themed surge mob, pushes `storage overlord:event`, and runs `overlord:event/<name>`.
Spawn surges are timed, cadence-gated, and capped at `#surgeCap` concurrent
`ov_surge` mobs. Everything auto-reverts; `admin/wrath_clear` is the hard reset
(zero the meter, strip all modifiers off `ov_buffed` mobs, kill surge mobs, hide
the bar).

## Conventions

- Datapack format **107**. `pack.mcmeta` uses `min_format`/`max_format`. Singular
  directory names (`function`, `tags/function`).
- Avoid entity predicates (their format changed in 26.2 and rejects unknown
  fields). Build on scoreboards, tags, and `/damage`.
- Item NBT is lowercase post-1.20.5: `{Item:{id:"...",count:N}}`.
- Dynamic values (item ids, demand text) reach functions via macros
  (`function ... with storage overlord:demand`). Keep the `$`-prefixed macro lines
  minimal and read scalars into scoreboards early.
- Global state lives on the `ovGlobal` fake-player namespace (`#demandTimer
  ovGlobal`, etc.). Scratch goes on `ovTmp`.
- Python: production-quality baseline. Validation before side effects, logging on
  every tool execution, best-effort memory that never raises into the loop.
- **No em dashes in any prose or docs in this repo.**

## How to extend

### Add a new overlord tool

1. Subclass `Tool` in `tools.py`. Define a pydantic `Params` with validators that
   clamp ranges, enforce allow-lists, and sanitise any player name (reject command
   separators). Implement `run(self, rcon, params)` to build and send the command.
2. Add it to `build_registry`. If it should be offered when judging tribute, add
   its name to `JUDGMENT_TOOLS`. It is automatically eligible as a demand stake
   unless you add it to `_STAKE_FORBIDDEN`.
3. That is the whole safety story: a new capability is a new typed tool with its
   own clamps. Never widen an existing tool to accept freer input as a shortcut.

### Add a demand verification kind

The kinds are `score` (vanilla scoreboard criterion, datapack-summed), `altar` (item
delivery), `freeform` (model-judged), `survive` (an ordeal: nobody dies before the
deadline), and `sacrifice` (a weighted-valuables or favor-pool tithe). To add another:

1. Extend `IssueDemand.Params.kind` and the `kind_n` mapping in `validate_full`,
   with validation for any new fields (see how `sacrifice` validates `source`).
2. Add a `measure_*` function in `demand/` and dispatch to it from `demand/second`
   on the new `#demandKind` value. Decide the deadline semantics: most kinds fall
   into a Reckoning at zero, but `survive` inverts it (reaching zero is the win), so
   route the new value explicitly in `demand/deadline`. If the kind has no running
   progress counter (like `survive`), exclude it from the progress-success line in
   `demand/second` and from the per-second `bar_name` in `demand/update_bar`.
3. Prefer correct-by-construction. If the new kind needs the model to judge it,
   you are really adding another freeform variant, so reuse the `judge` result
   path rather than inventing a second model-in-the-loop mechanism.

### Add a new event trigger

Tribute and demand-resolution both work by bumping a dedicated `seq*` in storage
and having the bridge poll it. To react to something else (a death, a milestone):
have the datapack detect it, write a payload plus bump a new `seq*`, and add a
poller in the bridge that builds memory context and calls the appropriate overlord
entry point. Keep one channel per event class.

### Add a world event

The `world_event` enum is meant to grow. To add one named `meteor`:

1. Add `meteor` to the `WORLD_EVENTS` config list (and `.env.example`).
2. Create `event/meteor.mcfunction`. If it needs parameters, read them from
   `storage overlord:event` via macros (`$(duration)`, `$(magnitude)`, etc.); the
   tool already pushes that storage and invokes the function `with` it. Make the
   effect temporary and self-reverting (a duration-bounded effect, a timed surge,
   weather with a duration), so nothing has to be cleaned up by hand.
3. If it spawns mobs, reuse the surge plumbing (`#surgeTimer` / `#surgeCadence` /
   `#surgeCap` and `wrath/surge`) so the concurrent cap and `ov_surge` tagging
   (and therefore `admin/wrath_clear`) apply for free. Never let the model name the
   mob: the tool draws it from the `surge_mobs` allow-list.

### Fold in an external datapack (invoke_ritual)

`invoke_ritual` is the sanctioned way to expand the palette with premade packs
without ever letting the model name a raw function. The server owner registers an
allow-list of friendly-name to function-id pairs in `EXTERNAL_RITUALS`
(`name=ns:path,...`). The model may only pick a registered friendly name; the
bridge maps it to the vetted function id and runs it. An empty allow-list means the
tool reports nothing available. Do not replace this with anything that accepts a
function id from the model directly.

## Do not

- Add a tool that takes raw command text, or that lets the model name an arbitrary
  command, effect, or mob outside an allow-list.
- Let a freeform verdict do anything except select between the two pre-validated
  stakes.
- Add a second escalating system outside the overlord.
- Move tribute or demand delivery off the altar channel.
- Make the model part of any tick-rate loop.
- Persist secrets, raw RCON passwords, or player PII into the event log.
- Use em dashes.

## Known sharp edges (carry these forward)

- Soul-link distribution is the highest-variance subsystem. Test every mode for
  damage ping-pong. It runs at integer-HP granularity, so tiny chip damage rounds
  to zero, worse with larger groups.
- Altar attribution credits the nearest player within range, so a tight cluster
  can misattribute tribute.
- Revival currently returns an arbitrary dead player (no queue).
- Score demands baseline per-player stats shortly after creating the objective; a
  player who joins mid-demand can miscount.
- Global soul-link has no death floor, so one creeper can cascade a group wipe.
  A chain-death floor (link cannot take a recipient below one heart) is a planned
  option, not yet built.
- Freeform demands can be judged incorrectly and default to mercy if judging
  fails. This is the deliberate cost of supporting "anything".
- The wrath buff scan plus surge spawning is the highest-performance-risk piece in
  the build. It is bounded to hostiles within `wrath_buff_radius` of a player (a
  near-players scan, not world-wide) and the surge is capped, but keep the radius
  bounded and the cap low on large or busy worlds.
- Surge spawn positioning is heuristic: a few blocks ahead of each player with a
  basic air-here / solid-below check. It can still place mobs in awkward spots, and
  a player looking sharply up or down skews the point.
- Mob buffs linger. A mob is buffed once (then tagged `ov_buffed` so it is never
  re-scanned), so dropping wrath does not weaken mobs already buffed; they keep the
  modifier until they die or `admin/wrath_clear` strips it. A few mobs (creepers)
  have no attack-damage attribute, so that one modifier no-ops for them.
- The survive ordeal is deliberately brutal at the end: the coefficient reaches 80
  in the last quarter, and in global soul-link (the default) there is no death floor,
  so a single hard hit can chain-wipe and fail the ordeal. That is the intended stakes,
  but it is the knob to soften (lower the phase values in `demand/survive_ramp`, or run
  proximity link so spreading out helps). Death detection has up to one second of
  latency (the per-second clock), which is fine as theatre.
- The favor bossbar is always visible (it is the shared goal). With the wrath and
  demand bars that can be three bars at once on a busy moment; acceptable for a small
  group, but note it. Sacrifice (`source=altar`) consumes the offered valuables (they
  are destroyed, not added to the pool); `source=pool` spends the saved pool on success.
- Foreshadowed payloads live only in bridge memory, so a restart between the omen and
  its delivery drops the pending action (the spoken omen is still logged to memory).
- Prayer reading is the most version-fragile piece: a written book is copied to
  `storage overlord:prayer` and `events.read_prayer_text` parses the SNBT tolerantly
  (pull quoted text, unwrap `{"text":...}`, drop `minecraft:` tokens). Book NBT paths
  can shift between versions; if prayers come back blank, that parser is the place to
  look, and the Server Management Protocol is the clean long-term replacement for it.
- Milestones can be chatty. The datapack rate-limits each detector (tags for one-time
  events, deltas for sleep, a per-day flag for dawn), and the bridge adds a
  `milestone_cooldown_s` so a flurry (everyone sleeps at once) yields one reaction;
  events inside the cooldown are dropped, not queued. Idle detection is heuristic
  (block X/Z unchanged for `#idleThreshold` seconds; jumping in place still reads as
  idle), and a lone written book on the altar is treated as a prayer, so combining a
  book with a gold-ingot tribute makes the book count as tribute instead.

## Roadmap (open, not yet built)

- Optional chain-death floor for global soul-link.
- Persona tuning toward a structured "dungeon master" (arcs, foreshadowing,
  continuity) instead of a pure mood generator.
- More event triggers (react to deaths and milestones, not just tribute/demand).
- Revival queue instead of arbitrary single revive.
