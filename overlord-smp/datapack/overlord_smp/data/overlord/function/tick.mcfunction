# === Overlord SMP :: tick ===
# Initialise per-player baseline once (damage_taken is a LIFETIME stat; without this
# the first delta would equal a player's entire lifetime damage and one-shot a partner).
execute as @a[tag=!ov_init] run function overlord:soullink/init_player

# Soul-link: process each bonded pair (up to 3 pairs => 6 players).
function overlord:soullink/pair {pair:"ov_pair_1"}
function overlord:soullink/pair {pair:"ov_pair_2"}
function overlord:soullink/pair {pair:"ov_pair_3"}

# Permadeath detection
execute as @a[scores={ovDeaths=1..}] run function overlord:death/handle

# Altar (tribute + revival) for every consecrated altar marker
execute as @e[type=marker,tag=ov_altar] at @s run function overlord:altar_tick
