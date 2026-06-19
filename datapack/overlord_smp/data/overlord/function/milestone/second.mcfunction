# Baseline new players so their stats/positions do not fire spuriously on join.
execute as @a[tag=!ov_minit] run function overlord:milestone/init_player
# Dawn (group milestone): fire once on each night-to-day transition.
execute store result score #daytime ovTmp run time query daytime
execute if score #daytime ovTmp matches 13000.. run scoreboard players set #wasNight ovGlobal 1
execute if score #daytime ovTmp matches 0..1000 if score #wasNight ovGlobal matches 1 run function overlord:milestone/dawn
# Per-player detectors (living players only).
execute as @a[tag=!ov_dead] run function overlord:milestone/player
