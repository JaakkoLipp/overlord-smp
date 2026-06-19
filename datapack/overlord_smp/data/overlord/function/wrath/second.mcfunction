# Nothing to do while calm and no surge is running.
execute if score #wrath ovGlobal matches ..0 if score #surgeTimer ovGlobal matches ..0 run return 0
# Reflect the current wrath on the shared bossbar.
execute if score #wrath ovGlobal matches 1.. run function overlord:wrath/show_bar
# Empower newly seen hostiles near players. Bounded by radius; ov_buffed is never re-scanned.
execute if score #wrath ovGlobal matches 1.. as @a at @s run function overlord:wrath/buff_near with storage overlord:wrath
# Drive an active spawn surge (cadence-gated, cap-checked).
execute if score #surgeTimer ovGlobal matches 1.. run function overlord:wrath/surge_tick
