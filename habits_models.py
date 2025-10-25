from datetime import datetime
from datetime import date as _date
from models import db


class Habit(db.Model):
    __tablename__ = 'habits'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self, include_completions=False):
        d = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'created_at': self.created_at.isoformat()
        }
        if include_completions:
            d['completions'] = [c.date.isoformat() for c in self.completions]
            d['completed'] = _date.today().isoformat() in d['completions']
        return d


class HabitCompletion(db.Model):
    __tablename__ = 'habit_completions'
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habits.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)

    # reference the Habit class directly to avoid ambiguous string lookup when
    # multiple modules export a class named `Habit` (prevents SQLAlchemy
    # "Multiple classes found for path 'Habit'" errors).
    habit = db.relationship(Habit, backref=db.backref('completions', cascade='all, delete-orphan', lazy='joined'))


class MonthlyGoal(db.Model):
    __tablename__ = 'monthly_goals'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'deadline': self.deadline.isoformat(),
            'completed': bool(self.completed),
            'created_at': self.created_at.isoformat()
        }
