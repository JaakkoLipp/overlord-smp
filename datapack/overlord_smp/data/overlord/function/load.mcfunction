# === Overlord SMP :: load ===
# Objectives
scoreboard objectives add ovDmgTaken minecraft.custom:minecraft.damage_taken
scoreboard objectives add ovDmgPrev dummy
scoreboard objectives add ovDeaths deathCount
scoreboard objectives add ovTribute dummy
scoreboard objectives add ovFavor dummy
scoreboard objectives add ovGlobal dummy
scoreboard objectives add ovTmp dummy
scoreboard objectives add ovDemandBase dummy
# Reactive event triggers (milestones + prayers)
scoreboard objectives add ovMilestone dummy
scoreboard objectives add ovDiamond minecraft.picked_up:minecraft.diamond
scoreboard objectives add ovSleep minecraft.custom:minecraft.sleep_in_bed
scoreboard objectives add ovSleepPrev dummy
scoreboard objectives add ovIdle dummy
scoreboard objectives add ovPosXp dummy
scoreboard objectives add ovPosZp dummy
scoreboard objectives add ovPrayer dummy

# Constants
scoreboard players set #ten ovGlobal 10
scoreboard players set #hundred ovGlobal 100
scoreboard players set #three ovGlobal 3
scoreboard players set #two ovGlobal 2
scoreboard players set #four ovGlobal 4

# Dials (overlord-tunable via RCON). Preserve across reload if already set.
execute unless score #coeff ovGlobal matches -2147483648.. run scoreboard players set #coeff ovGlobal 30
execute unless score #revivalXp ovGlobal matches -2147483648.. run scoreboard players set #revivalXp ovGlobal 30
# Soul-link topology: 0 = bonded pairs, 1 = global (all players), 2 = proximity (within radius)
execute unless score #linkMode ovGlobal matches -2147483648.. run scoreboard players set #linkMode ovGlobal 1
execute unless score #linkRadius ovGlobal matches -2147483648.. run scoreboard players set #linkRadius ovGlobal 16
# Demand state
scoreboard players set #demandActive ovGlobal 0
scoreboard players set #demandPhase ovGlobal 0
scoreboard players add #secCounter ovGlobal 0
execute unless score #failStreak ovGlobal matches -2147483648.. run scoreboard players set #failStreak ovGlobal 0
scoreboard players add #seqTribute ovGlobal 0
scoreboard players add #seqDemand ovGlobal 0

# Bridge event channels (mirrored to storage for the Python bridge to poll over RCON)
execute store result storage overlord:bridge seqTribute int 1 run scoreboard players get #seqTribute ovGlobal
execute store result storage overlord:bridge seqDemand int 1 run scoreboard players get #seqDemand ovGlobal

# Reactive channels: milestones (the overlord notices the world) and prayers (players speak to it)
scoreboard players add #seqMilestone ovGlobal 0
scoreboard players add #seqPrayer ovGlobal 0
scoreboard players set #mSec ovGlobal 0
scoreboard players set #wasNight ovGlobal 0
execute unless score #idleThreshold ovGlobal matches -2147483648.. run scoreboard players set #idleThreshold ovGlobal 180
execute store result storage overlord:bridge seqMilestone int 1 run scoreboard players get #seqMilestone ovGlobal
execute store result storage overlord:bridge seqPrayer int 1 run scoreboard players get #seqPrayer ovGlobal
data modify storage overlord:prayer set value {book:{}}
bossbar remove overlord:demand

# Wrath: the overlord's disposition, made shared + visible. Persist the level across
# reload; the bridge re-pushes fractions + bar on startup. NOT a second escalator
# (it falls on appeasement and decays when the overlord is idle).
scoreboard players add #wrathSec ovGlobal 0
execute unless score #wrath ovGlobal matches -2147483648.. run scoreboard players set #wrath ovGlobal 0
scoreboard players set #wrathMax ovGlobal 5
scoreboard players set #surgeTimer ovGlobal 0
scoreboard players set #surgeBeat ovGlobal 0
scoreboard players set #surgeCadence ovGlobal 6
execute unless score #surgeCap ovGlobal matches -2147483648.. run scoreboard players set #surgeCap ovGlobal 12
# Defaults so the buff scan + surge have data even before the bridge pushes any.
data modify storage overlord:wrath set value {level:0,dmg:"0",hp:"0",radius:48,color:"white",label:"Dormant"}
data modify storage overlord:event set value {event:"none",magnitude:1,duration:0,cadence:6,cap:12,surge_mob:"zombie",weather:"thunder"}
bossbar remove overlord:wrath
bossbar add overlord:wrath {"text":"Wrath"}
bossbar set overlord:wrath color white
bossbar set overlord:wrath style notched_10
bossbar set overlord:wrath visible false

# Communal favor pool: one shared ledger the whole group fills with tribute and the
# overlord spends for relief. Persist the pool across reload; the bridge re-syncs the
# scale on startup. Always visible: it is the shared common-goal number.
execute unless score #favorPool ovGlobal matches -2147483648.. run scoreboard players set #favorPool ovGlobal 0
scoreboard players set #favorMax ovGlobal 1000
# Monotonic death tally (survive ordeals baseline against it) and survive scratch.
scoreboard players add #deathTally ovGlobal 0
scoreboard players add #surviveBaseDeaths ovGlobal 0
bossbar remove overlord:favor
bossbar add overlord:favor [{"text":"Favor of the Realm","color":"green"}]
bossbar set overlord:favor color green
bossbar set overlord:favor style notched_10
bossbar set overlord:favor players @a
bossbar set overlord:favor visible true
execute store result bossbar overlord:favor max run scoreboard players get #favorMax ovGlobal
execute store result bossbar overlord:favor value run scoreboard players get #favorPool ovGlobal

# Group vitals bar: shown only during a survive ordeal (the weakest member's health).
bossbar remove overlord:vitals
bossbar add overlord:vitals [{"text":"♥ Group Vitals","color":"red"}]
bossbar set overlord:vitals color red
bossbar set overlord:vitals max 20
bossbar set overlord:vitals style notched_10
bossbar set overlord:vitals visible false

# Lethal world; deaths are handled by us, not vanilla respawn.
gamerule naturalRegeneration false
gamerule doImmediateRespawn true

tellraw @a {"text":"[Overlord] Systems online. The world is watching.","color":"dark_purple","italic":true}
