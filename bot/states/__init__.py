"""FSM holatlari: suhbatning har bir qadami — alohida holat."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Survey(StatesGroup):
    greeting = State()        # 1. "Albatta" tugmasini kutish
    name = State()            # 2. Ism-familiya (matn)
    workplace = State()       # 3. Ish joyi (tugma)
    employee = State()        # 4. Xodim (tugma)
    function = State()        # 5. Funksiya (tugma)
    function_other = State()  # 5a. "Va boshqa" — erkin matn
    timing_score = State()    # 6. Muddat bahosi (tugma)
    timing_reason = State()   # 6a. Muddat bahosi sababi (matn)
    quality_score = State()   # 7. Sifat bahosi (tugma)
    quality_reason = State()  # 7a. Sifat bahosi sababi (matn)
    suggestions = State()     # 8. Takliflar (matn yoki o'tkazib yuborish)


class AdminStates(StatesGroup):
    add_employee = State()


__all__ = ["AdminStates", "Survey"]
