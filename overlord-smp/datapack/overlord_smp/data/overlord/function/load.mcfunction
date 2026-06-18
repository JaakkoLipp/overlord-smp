# === Overlord SMP :: load ===
# Objectives
scoreboard objectives add ovDmgTaken minecraft.custom:minecraft.damage_taken
scoreboard objectives add ovDmgPrev dummy
scoreboard objectives add ovDeaths deathCount
scoreboard objectives add ovTribute dummy
scoreboard objectives add ovFavor dummy
scoreboard objectives add ovGlobal dummy
scoreboard objectives add ovTmp dummy

# Constants
scoreboard players set #ten ovGlobal 10
scoreboard players set #hundred ovGlobal 100
scoreboard players set #three ovGlobal 3

# Dials (overlord-tunable via RCON). Preserve across reload if already set.
execute unless score #coeff ovGlobal matches -2147483648.. run scoreboard players set #coeff ovGlobal 30
execute unless score #revivalXp ovGlobal matches -2147483648.. run scoreboard players set #revivalXp ovGlobal 30
scoreboard players add #seq ovGlobal 0

# Bridge event channel (seq is mirrored to storage for the Python bridge to poll over RCON)
execute store result storage overlord:bridge seq int 1 run scoreboard players get #seq ovGlobal

# Lethal world; deaths are handled by us, not vanilla respawn.
gamerule naturalRegeneration false
gamerule doImmediateRespawn true

tellraw @a {"text":"[Overlord] Systems online. The world is watching.","color":"dark_purple","italic":true}
