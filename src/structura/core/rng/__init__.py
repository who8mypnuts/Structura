"""Random number generation: legacy-exact MT19937 streams (docs/05 §7, docs/06 §9)."""

from .mt19937 import MT_STATE_SIZE, mt_get_double, mt_get_int, mt_get_int_n, mt_new, mt_seed

__all__ = ["MT_STATE_SIZE", "mt_get_double", "mt_get_int", "mt_get_int_n", "mt_new", "mt_seed"]
