# context: @s = an ov_altar marker. Items dropped within 3 blocks are the offering.
# Revival: a Totem of Undying present + at least one dead player => attempt ritual.
execute if entity @e[type=item,distance=..3,nbt={Item:{id:"minecraft:totem_of_undying"}}] if entity @a[tag=ov_dead] run function overlord:revival/try
# Tribute: a Gold Ingot acts as the commit token ("ring the bell") => tally and send to overlord.
execute if entity @e[type=item,distance=..3,nbt={Item:{id:"minecraft:gold_ingot"}}] run function overlord:tribute/commit
