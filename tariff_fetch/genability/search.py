from typing import Literal, TypedDict

from tariff_fetch.genability.converters import comma_separated


class SearchParams(TypedDict, total=False):
    search: str
    """
    The string of text to search on.
    This can also be a regular expression, in which case you should
    set the isRegex flag to true (see below).
    """
    searchOn: list[str]
    """
    Comma-separated list of fields to query on. When searchOn is specified, the text provided
    in the search string field will be searched within these fields. The list of fields to search on
    depends on the entity being searched for. Read the documentation for the entity for more details
    """
    startsWith: bool
    "When true, the search will only return results that begin with the specified search string."
    endsWith: bool
    "When true, the search will only return results that end with the specified search string."
    isRegex: bool
    """
    When true, the provided search string will be regarded as a regular expression
    and the search will return results matching the regular expression.
    Default is False.
    """
    sortOn: list[str]
    sortOrder: list[Literal["ASC", "DESC"]]
    """
    Comma-separated list of ordering. Possible values are ASC and DESC. Default is ASC.
    If your sortOn contains multiple fields and you would like to order fields individually,
    you can pass in a comma-separated list here
    """


search_params_converters = {
    "searchOn": comma_separated,
    "sortOn": comma_separated,
    "sortOrder": comma_separated,
}
