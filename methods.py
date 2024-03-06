from typing import NamedTuple
from enum import Enum

class QueryResponse(NamedTuple):
    success: bool = False
    status: str = ''
    error_message: str = ''
    data: str = ''
    response: dict = {}

class Method(Enum):
    GET_NEW_ORDERS = 'get_new_orders'
    GET_ORDERS = 'get_orders'
    GET_INFO = 'get_info'
    CANCEL = 'cancel'
    PRODUCT_CANCEL = 'product_cancel'
    SHIP = 'ship'
    REAL_FBS_SHIP = 'real_fbs_ship'
    REAL_FBS_DELIVERING = 'real_fbs_delivering'
    ACT_CREATE = 'act_create'
    ACT_CHECK_STATUS = 'act_check_status'
    ACT_DIGITAL_CHECK_STATUS = 'act_digital_check_status'
    ACT_GET_POSTINGS = 'act_get_postings'
    GET_FBO_ORDERS = 'get_fbo_orders'
    GET_FBO_INFO = 'get_fbo_info'
    SET_PRICES = 'set_prices'
    SET_STOCKS = 'set_stocks'
    SET_GTD = 'set_gtd'
    SET_COUNTRY = 'set_country'
    

