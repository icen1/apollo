from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from models.models import Base, discord_snowflake, user_id


class IgnoredChannel(Base):
    __tablename__ = "ignored_channels"

    channel: Mapped[discord_snowflake] = mapped_column(init=False, primary_key=True)
    user_id: Mapped[user_id]
    added_at: Mapped[datetime] = mapped_column(
        default_factory=datetime.now, insert_default=func.current_timestamp()
    )


class MiniKarmaChannel(Base):
    __tablename__ = "mini_karma_channels"

    channel: Mapped[discord_snowflake] = mapped_column(init=False, primary_key=True)
    user_id: Mapped[user_id]
    added_at: Mapped[datetime] = mapped_column(
        default_factory=datetime.now, insert_default=func.current_timestamp()
    )
