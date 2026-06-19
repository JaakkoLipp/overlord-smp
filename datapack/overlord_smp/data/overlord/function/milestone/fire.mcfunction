# Bump the milestone channel so the bridge wakes and scans flagged players.
scoreboard players add #seqMilestone ovGlobal 1
execute store result storage overlord:bridge seqMilestone int 1 run scoreboard players get #seqMilestone ovGlobal
