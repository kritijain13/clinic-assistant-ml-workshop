from datetime import date

from sqlalchemy import Column, Integer, Float, Date, UniqueConstraint

from mcp_layer.database.connection import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, nullable=False)

    usage_date = Column(Date, default=date.today, nullable=False)

    input_tokens = Column(Integer, default=0, nullable=False)

    output_tokens = Column(Integer, default=0, nullable=False)

    total_tokens = Column(Integer, default=0, nullable=False)

    cost = Column(Float, default=0.0, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "usage_date",
            name="unique_user_daily_usage"
        ),
    )