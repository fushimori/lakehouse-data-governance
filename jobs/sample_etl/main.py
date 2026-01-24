import argparse

from contracts.loader import load_contract
from etl.extract import create_spark_session, read_dataset
from etl.transform import (
    validate_not_null,
    clean_posts,
    add_time_columns
)
from etl.load import write_target


def run(contract_path: str):
    spark = create_spark_session()

    contract = load_contract(contract_path)

    df = read_dataset(spark, contract)

    quality = contract.get("quality", {})
    not_null_fields = quality.get("not_null", [])
    df = validate_not_null(df, not_null_fields)

    if contract["dataset"]["name"] == "reddit_posts":
        df = clean_posts(df)

    df = add_time_columns(df)

    write_target(df, contract)

    spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()

    run(args.contract)
