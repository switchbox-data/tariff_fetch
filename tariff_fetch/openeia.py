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


class Core_PUDL_ASSN_EIA_PUDL_UTILITIES:
    """Association table providing connections between EIA utility IDs and manually assigned PUDL utility IDs."""

    https = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/core_pudl__assn_eia_pudl_utilities.parquet"
    s3 = "s3://pudl.catalyst.coop/nightly/core_pudl__assn_eia_pudl_utilities.parquet"

    class Columns:
        utility_id_eia = "utility_id_eia"
        "integer, primary key, The EIA Utility Identification number."
        utility_id_pudl = "utility_id_pudl"
        "integer, A manually assigned PUDL utility ID. May not be stable over time."
        utility_name_eia = "utility_name_eia"
        "string, The name of the utility."
