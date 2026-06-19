# Self-paced per-second gate (same pattern as the demand clock). Cheap to run
# every tick; the real work in wrath/second only fires when wrath or a surge is active.
scoreboard players add #wrathSec ovGlobal 1
execute if score #wrathSec ovGlobal matches 20.. run scoreboard players set #wrathSec ovGlobal 0
execute if score #wrathSec ovGlobal matches 0 run function overlord:wrath/second
