# A group milestone: the living endured the night. Flag everyone alive at daybreak.
scoreboard players set #wasNight ovGlobal 0
execute as @a[tag=!ov_dead] run scoreboard players set @s ovMilestone 4
function overlord:milestone/fire
