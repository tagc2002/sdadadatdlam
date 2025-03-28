from typing import List
from typing import Optional

from sqlalchemy import ForeignKey, create_engine
from sqlalchemy import text
from sqlalchemy import Table, Column, Integer, String


from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)

#rollsback unless conn.commit() is called after query
with engine.connect() as conn:
    result = conn.execute(text("select 'hello world'"))
    print(result.all())

    result = conn.execute(text("SELECT x, y FROM some_table"))
    for row in result:
        print(f"x: {row.x}  y: {row.y}")
    for x, y in result:
        print(f"x: {x}  y: {y}")
    for row in result.mappings():
        print(f"{row['x']}")

#autocommits except on error
with engine.begin() as conn:
    conn.execute(text("INSERT INTO table (x, y) VALUES (:x, :y)"), [{"x": 1, "y": 2}])



class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[Optional[str]]

    addresses: Mapped[List["Address"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f'User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})'
    
class Address(Base):
    __tablename__ = "address"

    id: Mapped[int] = mapped_column(primary_key=True)
    email_address: Mapped[str]
    user_id = mapped_column(ForeignKey("user_account.id"))

    user: Mapped[User] = relationship(back_populates="addresses")
    
    def __repr__(self) -> str:
        return f"Address(id={self.id!r}, email_address={self.email_address!r})"
    
DeclarativeBase.metadata.create_all()