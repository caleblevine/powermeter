import sqlalchemy as sa

engine = sa.create_engine("sqlite:///test.db")
metadata = sa.MetaData(bind=engine)

readings = sa.Table('readings', metadata,
    sa.Column('timestamp', sa.types.DateTime, primary_key=True),
    sa.Column('amperage', sa.types.Float),
    sa.Column('wattage', sa.types.Float)
)
