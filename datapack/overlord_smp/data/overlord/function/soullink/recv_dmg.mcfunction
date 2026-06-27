# context: @s = recipient ; whole/frac = dealt amount split into HP and tenths.
# Magic damage bypasses armour (the bond is metaphysical). Dealt as a decimal so a
# 0.6 HP share lands as 0.6, not rounded away to 0.
$damage @s $(whole).$(frac) minecraft:magic
