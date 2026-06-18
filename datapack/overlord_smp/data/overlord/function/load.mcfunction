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
bossbar remove overlord:demand

# Lethal world; deaths are handled by us, not vanilla respawn.
gamerule naturalRegeneration false
gamerule doImmediateRespawn true

tellraw @a {"text":"[Overlord] Systems online. The world is watching.","color":"dark_purple","italic":true}
