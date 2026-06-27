# Deliver #per (0.1HP) to the bonded partner via the shared receive path. Excludes the
# source (ov_self) and any dead partner (ov_dead) so a fallen partner is never targeted.
$execute as @a[tag=$(pair),tag=!ov_self,tag=!ov_dead] run function overlord:soullink/recv
