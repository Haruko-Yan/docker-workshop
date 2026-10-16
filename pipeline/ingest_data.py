
import click
import pandas as pd
from sqlalchemy import create_engine
from tqdm.auto import tqdm

PREFIX = (
    "https://github.com/DataTalksClub/nyc-tlc-data/"
    "releases/download/yellow/"
)

DTYPE = {
    "VendorID": "Int64",
    "passenger_count": "Int64",
    "trip_distance": "float64",
    "RatecodeID": "Int64",
    "store_and_fwd_flag": "string",
    "PULocationID": "Int64",
    "DOLocationID": "Int64",
    "payment_type": "Int64",
    "fare_amount": "float64",
    "extra": "float64",
    "mta_tax": "float64",
    "tip_amount": "float64",
    "tolls_amount": "float64",
    "improvement_surcharge": "float64",
    "total_amount": "float64",
    "congestion_surcharge": "float64",
}

PARSE_DATES = [
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
]


@click.command()
@click.option("--pg-user", default="root", help="PostgreSQL user")
@click.option("--pg-pass", default="root", help="PostgreSQL password")
@click.option("--pg-host", default="localhost", help="PostgreSQL host")
@click.option("--pg-port", default=5432, type=int, help="PostgreSQL port")
@click.option("--pg-db", default="ny_taxi", help="Database name")
@click.option(
    "--target-table",
    default="yellow_taxi_data",
    help="Target table name",
)
@click.option(
    "--year", default=2021, type=int, help="Taxi data year"
)
@click.option(
    "--month", default=1, type=click.IntRange(1, 12),
    help="Taxi data month (1-12)"
)
@click.option(
    "--chunksize", default=100000, type=int,
    help="Rows per batch"
)
def run(
    pg_user, pg_pass, pg_host, pg_port, pg_db,
    target_table, year, month, chunksize
):
    """Load NYC yellow taxi CSV data into PostgreSQL."""

    if chunksize < 1:
        raise click.BadParameter("Must be at least 1", param_hint="--chunksize")

    url = (
        f"{PREFIX}yellow_tripdata_{year}-{month:02d}.csv.gz"
    )

    # Connect to PostgreSQL
    engine = create_engine(
        f"postgresql+psycopg://{pg_user}:{pg_pass}"
        f"@{pg_host}:{pg_port}/{pg_db}"
    )

    try:
        # Read the CSV in batches
        df_iter = pd.read_csv(
            url,
            dtype=DTYPE,
            parse_dates=PARSE_DATES,
            iterator=True,
            chunksize=chunksize,
        )

        # The first chunk creates the table; subsequent
        # chunks append rows to it.
        first = True

        for df_chunk in tqdm(df_iter, desc="Ingesting data"):
            df_chunk.to_sql(
                name=target_table,
                con=engine,
                if_exists="replace" if first else "append",
                index=False,
            )

            first = False
            click.echo(f"Inserted {len(df_chunk):,} rows")

        if first:
            click.echo("The source file contained no rows.")

        click.echo(f"Finished ingesting {url}")

    finally:
        engine.dispose()


if __name__ == "__main__":
    run()