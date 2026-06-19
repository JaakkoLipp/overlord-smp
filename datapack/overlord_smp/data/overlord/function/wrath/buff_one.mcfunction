# context: @s = a hostile. Apply removable named modifiers scaled by the wrath
# fractions, tag it so it is never re-buffed, then heal it to its new max.
# (attack_damage may not exist on a few mobs e.g. creepers; that line no-ops for them.)
$attribute @s minecraft:attack_damage modifier add overlord:wrath_dmg $(dmg) add_multiplied_base
$attribute @s minecraft:max_health modifier add overlord:wrath_hp $(hp) add_multiplied_base
tag @s add ov_buffed
execute store result entity @s Health float 1 run attribute @s minecraft:max_health get
