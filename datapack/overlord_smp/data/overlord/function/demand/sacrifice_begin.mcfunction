# context: run once when a sacrifice demand begins. Progress is value delivered
# (altar source) or the standing favor pool (pool source); the per-second measure
# fills it. The bar shows progress via the shared bar_name path.
scoreboard players set #demandProg ovGlobal 0
# Pool source: snapshot the pool now so progress measures FRESH contribution, not the
# standing balance. Without this, a threshold at or below the current pool would win on
# the first tick and hand out the reward for favor the group already had.
execute if score #sacSource ovGlobal matches 1 run scoreboard players operation #favorPoolBase ovGlobal = #favorPool ovGlobal
bossbar set overlord:demand color gold
tellraw @a {"text":"[Overlord] A sacrifice is demanded. Pay the price, or be paid from.","color":"dark_red","bold":true}
playsound minecraft:entity.wither.ambient master @a ~ ~ ~ 1 0.6
