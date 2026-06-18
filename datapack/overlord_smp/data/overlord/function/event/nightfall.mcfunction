# Drag the world into night. The day cycle carries it back out on its own.
time set night
tellraw @a {"text":"[Overlord] Night falls early, by my will.","color":"dark_blue","italic":true}
playsound minecraft:ambient.cave master @a ~ ~ ~ 1 0.6
