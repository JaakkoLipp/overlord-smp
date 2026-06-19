# Self-paced per-second gate (cheap to run every tick). Detectors live in second.
scoreboard players add #mSec ovGlobal 1
execute if score #mSec ovGlobal matches 20.. run scoreboard players set #mSec ovGlobal 0
execute if score #mSec ovGlobal matches 0 run function overlord:milestone/second
