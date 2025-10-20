class CoreEIA861_ASSN_UTILITY:
    https = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/core_eia861__assn_utility.parquet"
    s3 = "s3://pudl.catalyst.coop/nightly/core_eia861__assn_utility.parquet"
    s3_region = "us-west-2"

    class Columns:
        report_date = "report_date"
        "date, Date reported."
        state = "state"
        "string, Two letter US state abbreviation."
        utility_id_eia = "utility_id_eia"
        "integer, The EIA Utility Identification number."
