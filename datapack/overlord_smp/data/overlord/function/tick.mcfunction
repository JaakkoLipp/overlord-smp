# === Overlord SMP :: tick ===
# Initialise per-player baseline once (damage_taken is a LIFETIME stat; without this
# the first delta would equal a player's entire lifetime damage and one-shot a partner).
execute as @a[tag=!ov_init] run function overlord:soullink/init_player

# Soul-link: dispatch by topology.
#   mode 0 = bonded pairs ; mode 1 = global ; mode 2 = proximity
execute if score #linkMode ovGlobal matches 0 run function overlord:soullink/pairs_all
execute if score #linkMode ovGlobal matches 1.. run function overlord:soullink/dist_all

# Permadeath detection
execute as @a[scores={ovDeaths=1..}] run function overlord:death/handle

# Altar (tribute + revival) for every consecrated altar marker
execute as @e[type=marker,tag=ov_altar] at @s run function overlord:altar_tick

# Demand clock (self-paced; runs its own per-second logic while a demand is active)
execute if score #demandActive ovGlobal matches 1 run function overlord:demand/clock

# Wrath clock (self-paced per-second gate; ambient mob buffs + spawn surges)
function overlord:wrath/clock
