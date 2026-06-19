# context: @s = a player, position + rotation = @s. Cap-checked per spawn so the
# wave cannot exceed #surgeCap concurrent surge mobs. Positioning is heuristic:
# a few blocks ahead of the player, with a basic air-here / solid-below check.
execute store result score #surgeCount ovTmp if entity @e[tag=ov_surge]
execute if score #surgeCount ovTmp < #surgeCap ovGlobal positioned ^ ^ ^5 if block ~ ~ ~ minecraft:air if block ~ ~1 ~ minecraft:air unless block ~ ~-1 ~ minecraft:air run function overlord:wrath/surge_summon with storage overlord:event
