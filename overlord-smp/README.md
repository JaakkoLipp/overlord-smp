# Overlord SMP (Minecraft 26.2 "Chaos Cubed")

A small-group survival server with four interlocking systems and an LLM "overlord"
that reacts to player tribute. Built for under six players.

- **No natural regen** — healing is always economic (golden apples, regen potions, mercy from the overlord).
- **Soul-link (bonded pairs)** — a configurable percentage of damage one bonded player takes bleeds to their partner. Individual death is preserved, so it composes with revival.
- **Permadeath + revival** — death sends you to spectator; the living buy you back at the altar with a Totem of Undying plus XP levels.
- **The Overlord** — an LLM that reads world state and a player's tribute, then acts through a fixed set of typed, validated tools. It is the *only* escalating pressure; the three survival systems are flat. (One escalator, by design, so the difficulty multiplies controllably instead of spiralling.)

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
4. Bond your pairs with tags (two players per pair, up to three pairs):
   ```
   /tag Alice add ov_pair_1
   /tag Bob   add ov_pair_1
   /tag Carol add ov_pair_2
   /tag Dave  add ov_pair_2
   ```
   Unbonded players simply take no soul-link damage.

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
2. The datapack tallies tribute (stack count, with diamonds x3 and netherite x10), credits the donor's `ovFavor`, clears the offering, and bumps `storage overlord:bridge seq`.
3. The bridge polls that seq over RCON, finds the donor by their `ovTribute` score, snapshots the world, and asks the overlord.
4. The overlord returns one to three typed tool calls. Each is validated and clamped, then executed over RCON.

The inference delay is intentional theatre: players already saw "the presence
deliberates" when the tribute landed.

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

1. **Soul-link distribution.** Bond two players, have one take fall/mob damage, confirm the partner takes roughly `coefficient%` of it and that there is **no ping-pong** (the magic-damage bleed must not itself bleed back). The anti-feedback compensation in `soullink/apply.mcfunction` pre-advances the partner's baseline; if you see oscillation, that is the line to inspect. Note the MVP works at integer-HP granularity (sub-half-heart bleed is dropped); move to a macro-passed decimal if you want finer resolution.
2. **Altar attribution.** Tribute is credited to the *nearest* player within 12 blocks. With several players clustered on the altar this can misattribute; widen or tighten the radius, or gate on a per-player commit, if it matters for your group.
3. **Revival selection.** Currently revives an arbitrary single dead player. Add a queue (oldest-death-first) or a chooser if you want deterministic order.

## Upgrade paths (when the MVP proves the loop is fun)

- **Transport:** 26.x ships the **Minecraft Server Management Protocol v3.0.0** (JSON-RPC). It is a cleaner push-based event channel than RCON polling and the right next step for the bridge. RCON is used here only because it is universal and zero-dependency.
- **Skill-library promotion (Voyager pattern):** when you add a freeform-generation tool later, promote any generated intervention that validates and runs clean into the typed registry. The overlord should get *more* templated and safer the longer it runs, not more feral.
- **More dials:** expose escalating-difficulty as overlord tools (global mob attribute buffs, threat waves) so rising pressure stays reactive instead of becoming a second always-on curve.

## Tuning quick reference

| Dial | Where | Default |
|---|---|---|
| Soul-link bleed % | `#coeff ovGlobal` (or `set_soullink_coefficient` tool) | 30 |
| Revival cost (levels) | `#revivalXp ovGlobal` (or `set_revival_cost` tool) | 30 |
| Tribute commit token | `tribute/commit.mcfunction` (gold ingot) | gold_ingot |
| Effect/mob allow-lists, bounds | `bridge/.env` / `config.py` | see file |
