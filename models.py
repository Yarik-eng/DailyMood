from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()

class MoodEntry(db.Model):
    """Модель для зберігання записів настрою."""
    
    VALID_MOODS = ['happy', 'neutral', 'sad']
    
    __tablename__ = 'mood_entries'
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(32), nullable=False)
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    activities = db.Column(db.String(500), nullable=True)  # Зберігаємо як comma-separated string
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, mood, date, title, content=None, activities=None):
        if mood not in self.VALID_MOODS:
            raise ValueError(f'Недійсне значення настрою. Допустимі значення: {", ".join(self.VALID_MOODS)}')
        self.mood = mood
        self.date = date
        self.title = title
        self.content = content
        self.activities = activities

    def to_dict(self):
        """Конвертує запис в словник для JSON відповіді."""
        return {
            'id': self.id,
            'mood': self.mood,
            'date': self.date.isoformat(),
            'title': self.title,
            'content': self.content,
            'activities': self.activities.split(',') if self.activities else [],
            'created_at': self.created_at.isoformat(),
            'mood_emoji': self.get_mood_emoji()
        }
    
    def get_mood_emoji(self):
        """Повертає емодзі для відповідного настрою."""
        emoji_map = {
            'happy': '😊',
            'neutral': '😐',
            'sad': '😢'
        }
        return emoji_map.get(self.mood, '❓')