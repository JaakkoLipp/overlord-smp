# context: run once when a sacrifice demand begins. Progress is value delivered
# (altar source) or the standing favor pool (pool source); the per-second measure
# fills it. The bar shows progress via the shared bar_name path.
scoreboard players set #demandProg ovGlobal 0
bossbar set overlord:demand color gold
tellraw @a {"text":"[Overlord] A sacrifice is demanded. Pay the price, or be paid from.","color":"dark_red","bold":true}
playsound minecraft:entity.wither.ambient master @a ~ ~ ~ 1 0.6
