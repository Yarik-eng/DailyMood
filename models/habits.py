"""
Compatibility shim for habit models.

To avoid duplicate SQLAlchemy mapper registrations we centralize the real
model definitions in `habits_models.py`. This module re-exports those
classes so existing imports referencing `models.habits` still work.
"""

from habits_models import Habit, HabitCompletion, MonthlyGoal  # re-export

__all__ = ['Habit', 'HabitCompletion', 'MonthlyGoal']
