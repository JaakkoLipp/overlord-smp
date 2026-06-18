# A creeping darkness over everyone. The effect expires on its own.
$effect give @a minecraft:darkness $(duration) 0 true
tellraw @a {"text":"[Overlord] A dread settles over you. Something is watching.","color":"dark_gray","italic":true}
playsound minecraft:entity.warden.heartbeat master @a ~ ~ ~ 1 0.5
