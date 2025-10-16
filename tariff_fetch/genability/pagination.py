from typing import TypedDict


class PagingParams(TypedDict, total=False):
    pageStart: int
    pageCount: int


paging_params_converters = {
    "pageStart": str,
    "pageCount": str,
}
