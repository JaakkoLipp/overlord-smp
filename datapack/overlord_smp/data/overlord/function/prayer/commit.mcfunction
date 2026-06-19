# context: @s = an ov_altar marker. A written book left on the altar is a prayer.
# Copy its contents out for the bridge to read, mark the nearest player as the
# supplicant, consume the book, and wake the overlord on the prayer channel.
data modify storage overlord:prayer book set from entity @e[type=item,distance=..3,nbt={Item:{id:"minecraft:written_book"}},limit=1] Item
execute as @p[distance=..12] run scoreboard players set @s ovPrayer 1
kill @e[type=item,distance=..3,nbt={Item:{id:"minecraft:written_book"}},limit=1]
scoreboard players add #seqPrayer ovGlobal 1
execute store result storage overlord:bridge seqPrayer int 1 run scoreboard players get #seqPrayer ovGlobal
tellraw @a {"text":"[Overlord] A prayer rises to the presence...","color":"dark_purple","italic":true}
