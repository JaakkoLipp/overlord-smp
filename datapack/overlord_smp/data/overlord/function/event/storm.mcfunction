# weather takes a duration in seconds and reverts on its own when it elapses.
$weather $(weather) $(duration)
tellraw @a {"text":"[Overlord] The sky turns against you.","color":"dark_aqua","italic":true}
playsound minecraft:entity.lightning_bolt.thunder master @a ~ ~ ~ 1 0.8
