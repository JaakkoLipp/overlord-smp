# Set up a timed, cadence-gated, cap-checked spawn surge from storage overlord:event,
# then fire the first wave immediately. The wrath clock drives the rest.
$scoreboard players set #surgeTimer ovGlobal $(duration)
$scoreboard players set #surgeCadence ovGlobal $(cadence)
$scoreboard players set #surgeCap ovGlobal $(cap)
scoreboard players set #surgeBeat ovGlobal 0
function overlord:wrath/surge
tellraw @a {"text":"[Overlord] The dark teems. They are coming for you.","color":"dark_red","italic":true}
playsound minecraft:entity.enderman.scream master @a ~ ~ ~ 1 0.7
