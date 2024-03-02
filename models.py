from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from const import Base


class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    user_profile = Column(Integer, nullable=False)
    preference = relationship('PreferencesUsers', back_populates='user')


class PreferencesUsers(Base):
    __tablename__ = 'preferences_users'
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    preference_id = Column(Integer, ForeignKey('preferences.preference_id'),
                           primary_key=True)
    user = relationship('User', back_populates='preference')
    preference = relationship('Preferences', back_populates='user')


class Preferences(Base):
    __tablename__ = 'preferences'
    preference_id = Column(Integer, primary_key=True)
    favourite_profile = Column(Integer)
    black_profile = Column(Integer)
    user = relationship('PreferencesUsers', back_populates='preference')


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
