# Shared low-health bar: the weakest living member's health, so the group watches
# one number. Start high, take the minimum across living players.
scoreboard players set #minHp ovTmp 20
execute as @a[tag=!ov_dead] run function overlord:demand/vitals_one
execute store result bossbar overlord:vitals value run scoreboard players get #minHp ovTmp
