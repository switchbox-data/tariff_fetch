from enum import Enum
from typing import NamedTuple


class Provider(str, Enum):
    GENABILITY = "Genability"
    OPENEI = "OpenEI"
    RATEACUITY = "RateAcuity"
    PUDL = "PUDL"


class StateCode(str, Enum):
    AL = "al"
    AK = "ak"
    AZ = "az"
    AR = "ar"
    CA = "ca"
    CO = "co"
    CT = "ct"
    DE = "de"
    FL = "fl"
    GA = "ga"
    HI = "hi"
    ID = "id"
    IL = "il"
    IN = "in"
    IA = "ia"
    KS = "ks"
    KY = "ky"
    LA = "la"
    ME = "me"
    MD = "md"
    MA = "ma"
    MI = "mi"
    MN = "mn"
    MS = "ms"
    MO = "mo"
    MT = "mt"
    NE = "ne"
    NV = "nv"
    NH = "nh"
    NJ = "nj"
    NM = "nm"
    NY = "ny"
    NC = "nc"
    ND = "nd"
    OH = "oh"
    OK = "ok"
    OR = "or"
    PA = "pa"
    RI = "ri"
    SC = "sc"
    SD = "sd"
    TN = "tn"
    TX = "tx"
    UT = "ut"
    VT = "vt"
    VA = "va"
    WA = "wa"
    WV = "wv"
    WI = "wi"
    WY = "wy"
    DC = "dc"


class Utility(NamedTuple):
    eia_id: int
    name: str
