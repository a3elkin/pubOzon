import logging
import ssl
import sys
import os
from typing import Callable, Iterable, Sequence
import requests
import json
import random
import string
from methods import Method, QueryResponse
from time import sleep

unicode_replace = {u"\u2013": "-",u"\u2014": "-",u"\xab": '"',u"\xbb": '"',u"\xf6": 'o',u"\xca": 'e'}

def _unicode_filter(param):
    tmp = str(param)
    for u in unicode_replace:
        if tmp.find(u) != -1:
            tmp = tmp.replace(u, unicode_replace[u])
    return tmp


formatter = logging.Formatter(fmt = '%(asctime)s %(levelname)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S')

def setup_logger(name, log_file, level=logging.INFO):
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

log_info = setup_logger('info_log','ozon.log')
log_error = setup_logger('error_log','ozon.err')

host = "https://api-seller.ozon.ru"

if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context



def post_query(url,json_body,headers) -> QueryResponse:
    log_info.info('URL %s, body %s', url, str(json_body))

    try:
        r = requests.post(url, data = json.dumps(json_body),headers = headers)
    except Exception as ex:
        return QueryResponse(success=False, error_message='Request error. %s' % str(ex))#{'success': False, 'error_message': 'Request error. %s' % str(ex)}

    log_info.info('Status %s', str(r.status_code))

    if r.status_code != 200:
        return QueryResponse(success=False, status=r.status_code, data=r.text)#{'success': False, 'status': r.status_code, 'data': r.text}

    try:
        response = json.loads(r.text)
    except Exception as ex:
        return QueryResponse(success=False, status=200, error_message='JSON error. %s' % str(ex))#{'success': False, 'status': 200, 'error_message': 'JSON error. %s' % str(ex)}

    return QueryResponse(success=True, status=200, response=response)#{'success': True, 'status': 200, 'response': response}

def random_string(length: int) -> str:
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


def _fill_section(xml_data: list, parent: Sequence, section: str, params: tuple, spacing: int=1):
    if isinstance(parent, dict):
        if section in parent:        
            xml_data.append('%s<%s>' % (''.join([' ']*spacing), section))
            if isinstance(parent[section], Iterable):
                for param in params:
                    if param in parent[section] and parent[section][param]:
                        xml_data.append('%s<%s>%s</%s>' % (''.join([' ']*(spacing+1)), param,_unicode_filter(parent[section][param]),param))
            xml_data.append('%s</%s>' % (''.join([' ']*spacing), section))
    elif isinstance(parent, list):
        for element in parent:
            xml_data.append('%s<%s>' % (''.join([' ']*spacing), section)) 
            for param in params:
                if param in element and element[param]:
                    xml_data.append('%s<%s>%s</%s>' % (''.join([' ']*(spacing+1)), param,_unicode_filter(element[param]),param))
            xml_data.append('%s</%s>' % (''.join([' ']*spacing), section))
    

def json_to_xml(method: Method, json_data, xml_data: list):
    if method is Method.GET_NEW_ORDERS:
        for order in json_data:
            xml_data.append(' <order>')
            for param in ('order_id','order_number','posting_number','status','cancel_reason_id','in_process_at','delivering_date','shipment_date','tracking_number'):
                if param in order and order[param]:
                    xml_data.append('  <%s>%s</%s>' % (param, _unicode_filter(order[param]) ,param))

            _fill_section(xml_data, order, 'delivery_method', ['id','warehouse_id','tpl_provider_id'], 2)
            _fill_section(xml_data, order, 'analytics_data', ['region','city','delivery_type','is_premium','payment_type_group_name','is_legal'], 2)
            _fill_section(xml_data, order, 'cancellation', ['cancel_reason','cancel_reason_id','cancellation_type','cancellation_initiator'], 2)
            _fill_section(xml_data, order, 'customer', ['address','customer_email','customer_id','name','phone'], 2)
            
            xml_data.append('  <products>')
            _fill_section(xml_data, order['products'], 'product', ('sku','quantity','offer_id','price'), 3) #name - out
            xml_data.append('  </products>')

            xml_data.append(' </order>')
    elif method is Method.GET_ORDERS:
        for order in json_data:
            xml_data.append(' <order>')
            for param in ('order_id','order_number','posting_number','status','cancel_reason_id','delivering_date','delivery_price','shipment_date','tracking_number','_only_if_status_changes'):
                if param in order and order[param]:
                    xml_data.append('  <%s>%s</%s>' % (param, _unicode_filter(order[param]) ,param))

            _fill_section(xml_data, order, 'delivery_method', ['id','warehouse_id','tpl_provider_id'], 2)
            _fill_section(xml_data, order, 'analytics_data', ['region','city','delivery_type','is_premium','payment_type_group_name','is_legal'], 2)
            _fill_section(xml_data, order, 'cancellation', ['cancel_reason','cancel_reason_id','cancellation_type','cancellation_initiator'], 2)
            _fill_section(xml_data, order, 'courier', ['car_model','car_number','name','phone'], 2)
            _fill_section(xml_data, order, 'customer', ['address','customer_email','customer_id','name','phone'], 2)
            
            xml_data.append('  <products>')
            _fill_section(xml_data, order['products'], 'product', ('sku','quantity','offer_id','price'), 3) #name - out
            xml_data.append('  </products>')

            xml_data.append('  <financial_data>')
            _fill_section(xml_data, order['financial_data']['products'], 'finance', ['product_id','quantity','payout','commission_amount','price'], 3)
            xml_data.append('  </financial_data>')

            xml_data.append(' </order>')
    elif method is Method.GET_INFO:
        for param in ('order_id','order_number','posting_number','status','cancel_reason_id','delivering_date','delivery_price','shipment_date','tracking_number'):
            if param in json_data and json_data[param]:
                xml_data.append('  <%s>%s</%s>' % (param, _unicode_filter(json_data[param]) ,param))

        _fill_section(xml_data, json_data, 'delivery_method', ['id','warehouse_id','tpl_provider_id'], 2)
        _fill_section(xml_data, json_data, 'analytics_data', ['region','city','delivery_type','is_premium','payment_type_group_name','is_legal'], 2)
        _fill_section(xml_data, json_data, 'cancellation', ['cancel_reason','cancel_reason_id','cancellation_type','cancellation_initiator'], 2)
        _fill_section(xml_data, json_data, 'courier', ['car_model','car_number','name','phone'], 2)
        _fill_section(xml_data, json_data, 'customer', ['address','customer_email','customer_id','name','phone'], 2)
        
        xml_data.append('  <products>')
        _fill_section(xml_data, json_data['products'], 'product', ['sku','quantity','offer_id','price'], 3) #name - out
        xml_data.append('  </products>')

        xml_data.append('  <financial_data>')
        _fill_section(xml_data, json_data['financial_data']['products'], 'finance', ['product_id','quantity','payout','commission_amount','price'], 3)
        xml_data.append('  </financial_data>')
    elif method is Method.GET_FBO_INFO:
        for param in ('order_id','order_number','posting_number','status','cancel_reason_id'):
            if param in json_data and json_data[param]:
                xml_data.append('  <%s>%s</%s>' % (param, _unicode_filter(json_data[param]) ,param))

        xml_data.append('  <products>')
        _fill_section(xml_data, json_data['products'], 'product', ['sku','quantity','offer_id','price'], 3) #name - out
        xml_data.append('  </products>')

        xml_data.append('  <financial_data>')
        _fill_section(xml_data, json_data['financial_data']['products'], 'finance', ['product_id','quantity','payout','commission_amount','price'], 3)
        xml_data.append('  </financial_data>')
    elif method is Method.GET_FBO_ORDERS:
        for order in json_data:
            xml_data.append(' <fbo_order>')
            for param in ('order_id','order_number','posting_number','status','cancel_reason_id','in_process_at'):
                if param in order and order[param]:
                    xml_data.append('  <%s>%s</%s>' % (param, _unicode_filter(order[param]) ,param))

            _fill_section(xml_data, order, 'analytics_data', ['region','city','delivery_type','is_premium','payment_type_group_name','is_legal'], 2)
            
            xml_data.append('  <products>')
            _fill_section(xml_data, order['products'], 'product', ('sku','quantity','offer_id','price'), 3) #name - out
            xml_data.append('  </products>')

            xml_data.append('  <financial_data>')
            _fill_section(xml_data, order['financial_data']['products'], 'finance', ['product_id','quantity','payout','commission_amount','price'], 3)
            xml_data.append('  </financial_data>')

            xml_data.append(' </fbo_order>')
    elif method is Method.ACT_CREATE:
        xml_data.append('    <task_id>%s</task_id>' % json_data['id'])
        xml_data.append('    <delivery_method_id>%s</delivery_method_id>' % json_data['delivery_method_id'])
    elif method is Method.ACT_CHECK_STATUS or method is Method.ACT_DIGITAL_CHECK_STATUS:
        if 'added_to_act' in json_data:
            xml_data.append('    <added>')
            for element in json_data['added_to_act']:
                if element:
                    xml_data.append('      <added_to_act>%s</added_to_act>' % element)
            xml_data.append('    </added>')
        if 'removed_from_act' in json_data:
            xml_data.append('    <removed>')
            for element in json_data['removed_from_act']:
                if element:
                    xml_data.append('      <removed_from_act>%s</removed_from_act>' % element)
            xml_data.append('    </removed>')
        if 'status' in json_data:
            xml_data.append('    <status>%s</status>' % _unicode_filter(json_data['status']))
    elif method is Method.ACT_GET_POSTINGS:
        if 'result' in json_data:
            xml_data.append('    <added>')
            for element in json_data['result']:
                if element:
                    xml_data.append('      <added_to_act>%s</added_to_act>' % element['posting_number'])
            xml_data.append('    </added>')
    elif method is Method.SET_PRICES:
        prices_dict = {}
        for offer in json_data['prices_data']:
            prices_dict[offer['offer_id']] = (offer['old_price'],offer['price'])

        for price in json_data['prices_response']:
            xml_data.append('   <price>')
            for param in ('offer_id','updated'):
                if param in price:
                    xml_data.append('    <%s>%s</%s>' % (param, _unicode_filter(price[param]) ,param))
            
            if 'updated' in price and price['updated']:
                xml_data.append('    <old_price>%s</old_price>' % prices_dict[price['offer_id']][0])
                xml_data.append('    <new_price>%s</new_price>' % prices_dict[price['offer_id']][1])
            elif 'errors' in price:            
                _fill_section(xml_data, price['errors'], 'error', ('code','message'), 5)

            xml_data.append('   </price>')
    elif method is Method.SET_STOCKS:
        stocks_dict = {}
        for offer in json_data['stocks_data']:
            stocks_dict[offer['offer_id']] = (offer['warehouse_id'],offer['stock'])

        for stock in json_data['stocks_response']:
            xml_data.append('   <stock>')
            for param in ('offer_id','updated'):
                if param in stock:
                    xml_data.append('    <%s>%s</%s>' % (param, _unicode_filter(stock[param]) ,param))
            
            if 'updated' in stock and stock['updated']:
                xml_data.append('    <warehouse_id>%s</warehouse_id>' % stocks_dict[stock['offer_id']][0])
                xml_data.append('    <qty>%s</qty>' % stocks_dict[stock['offer_id']][1])
            elif 'errors' in stock:            
                _fill_section(xml_data, stock['errors'], 'error', ('code','message'), 5)

            xml_data.append('   </stock>')



def get_new_orders(xml: list, data) -> bool:
    if 'debug_data' in data:
        json_to_xml(Method.GET_NEW_ORDERS, data['debug_data'], xml)
        return True
    url = host + '/v3/posting/fbs/list'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','<orders>'))
    offset = 0
    body = {'with':{'analytics_data': True, 'financial_data': False},'translit':True, 'limit': 100, 'offset': 0, 'filter': {'status': 'awaiting_packaging', 'since': data['since'], 'to': data['to']}}     
    strings_exist = False
    while True:
        result = post_query(url, body, headers)
        if not result.success:
            if result.data:
                log_error.error('Status: %s. Error: %s',result.status,result.data)
            else:
                log_error.error('%s%s',('Status: ' + result.status +'. ') if result.status else '',result.error_message)
            return False

        try:
            if result.response['result']['postings']:
                json_to_xml(Method.GET_NEW_ORDERS, result.response['result']['postings'], xml)
                strings_exist = True
        except Exception as ex:
            log_error.error('%s', str(ex))
            return False

        if result.response['result']['has_next']:
            offset += 100
            body['offset'] = offset
        else:
            break

    xml.append('</orders>')

    return strings_exist

def get_orders(xml: list, data) -> bool:
    if 'debug_data' in data:
        json_to_xml(Method.GET_ORDERS, data['debug_data'], xml)
        return True
    url = host + '/v3/posting/fbs/list'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','<orders>'))
    offset = 0
    body = {'with':{'analytics_data': True, 'financial_data': True},'translit':True, 'limit': 100, 'offset': 0, 'filter': {'since': data['since'], 'to': data['to']}}     
    strings_exist = False
    skipped_statuses = ('awaiting_registration','awaiting_approve')
    while True:
        result = post_query(url, body, headers)
        if not result.success:
            if result.data:
                log_error.error('Status: %s. Error: %s',result.status,result.data)
            else:
                log_error.error('%s%s',('Status: ' + result.status +'. ') if result.status else '',result.error_message)
            return False

        try:
            if 'postings' in result.response['result']:
                postings = [posting for posting in result.response['result']['postings'] if 'status' in posting and posting['status'] not in skipped_statuses]
            else:
                postings = []
            if 'params' in data:
                for param in dict(data['params']).keys():                    
                    for posting in postings:
                        posting['_%s' % str(param)] = data['params'][param]

            if postings:
                json_to_xml(Method.GET_ORDERS, postings, xml)
                strings_exist = True
        except Exception as ex:
            log_error.error('%s', str(ex))
            return False

        if 'has_next' in result.response['result'] and result.response['result']['has_next']:
            offset += 100
            body['offset'] = offset
        else:
            break

    xml.append('</orders>')

    return strings_exist

def get_fbo_orders(xml: list, data) -> bool:
    if 'debug_data' in data:
        json_to_xml(Method.GET_FBO_ORDERS, data['debug_data'], xml)
        return True
    url = host + '/v2/posting/fbo/list'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','<fbo_orders>'))
    offset = 0
    body = {'with':{'analytics_data': True, 'financial_data': True},'translit':True, 'limit': 1000, 'offset': 0, 'filter': {'since': data['since'], 'to': data['to']}}     
    strings_exist = False
    only_statuses = ('delivered','cancelled')
    while True:
        result = post_query(url, body, headers)
        if not result.success:
            if result.data:
                log_error.error('Status: %s. Error: %s',result.status,result.data)
            else:
                log_error.error('%s%s',('Status: ' + result.status +'. ') if result.status else '',result.error_message)
            return False

        try:
            if 'result' in result.response:
                postings = [posting for posting in result.response['result'] if 'status' in posting and posting['status'] in only_statuses]
            else:
                postings = []

            if 'params' in data:
                for param in dict(data['params']).keys():                    
                    for posting in postings:
                        posting['_%s' % str(param)] = data['params'][param]                

            if postings:
                json_to_xml(Method.GET_FBO_ORDERS, postings, xml)
                strings_exist = True
        except Exception as ex:
            log_error.error('%s', str(ex))
            return False

        if 'has_next' in result.response['result'] and result.response['result']['has_next']:
            offset += 100
            body['offset'] = offset
        else:
            break

    xml.append('</fbo_orders>')

    return strings_exist

def get_info(xml: list, data: dict) -> bool:
    url = host + '/v3/posting/fbs/get'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    body = {'posting_number': data['posting_number'],'with':{'analytics_data': True, 'financial_data': True, 'translit':False, 'barcodes': False}}
    result = post_query(url, body, headers)
    if not result.success:
        if result.data:
            log_error.error('Status: %s. Error: %s',result.status,result.data)
        else:
            log_error.error(('%s%s'),('Status: %s. ' % result.status) if result.status else '',result.error_message)
        return False

    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','<orders>',' <order>'))
    json_to_xml(Method.GET_INFO, result.response['result'], xml)
    xml.extend((' </order>','</orders>'))
    return True

def get_fbo_info(xml: list, data: dict) -> bool:
    url = host + '/v2/posting/fbo/get'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    body = {'posting_number': data['posting_number'],'with':{'analytics_data': False, 'financial_data': True, 'translit':False, 'barcodes': False}}
    result = post_query(url, body, headers)
    if not result.success:
        if result.data:
            log_error.error('Status: %s. Error: %s',result.status,result.data)
        else:
            log_error.error(('%s%s'),('Status: %s. ' % result.status) if result.status else '',result.error_message)
        return False

    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','<fbo_orders>',' <fbo_order>'))
    json_to_xml(Method.GET_FBO_INFO, result.response['result'], xml)
    xml.extend((' </fbo_order>','</fbo_orders>'))
    return True

def act_create(xml: list, data: dict) -> bool:
    url = host + '/v2/posting/fbs/act/create'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    body = {'delivery_method_id': data['delivery_method_id'],'departure_date': data['departure_date']}
    result = post_query(url, body, headers)
    if not result.success:
        if result.data:
            log_error.error('Status: %s. Error: %s',result.status,result.data)
        else:
            log_error.error(('%s%s'),('Status: %s. ' % result.status) if result.status else '',result.error_message)
        return False

    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','  <act-tn>','    <date>%s</date>' % data['departure_date']))
    json_to_xml(Method.ACT_CREATE, {'id':result.response['result']['id'],'delivery_method_id': data['delivery_method_id']}, xml)
    xml.append('  </act-tn>')
    return True

def act_check_status(xml: list, data: dict) -> bool:
    url = host + '/v2/posting/fbs/act/check-status'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    body = {'id': data['task_id']}
    result = post_query(url, body, headers)
    if not result.success:
        if result.data:
            log_error.error('Status: %s. Error: %s',result.status,result.data)
        else:
            log_error.error(('%s%s'),('Status: %s. ' % result.status) if result.status else '',result.error_message)
        return False

    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','  <act-tn>','    <task_id>%s</task_id>' % data['task_id']))
    json_to_xml(Method.ACT_CHECK_STATUS, result.response['result'], xml)
    xml.append('  </act-tn>')
    return True

def act_digital_check_status(xml: list, data: dict) -> bool:
    url = host + '/v2/posting/fbs/digital/act/check-status'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    body = {'id': data['task_id']}
    result = post_query(url, body, headers)
    if not result.success:
        if result.data:
            log_error.error('Status: %s. Error: %s',result.status,result.data)
        else:
            log_error.error(('%s%s'),('Status: %s. ' % result.status) if result.status else '',result.error_message)
        return False

    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','  <act-tn>','    <task_id>%s</task_id>' % data['task_id']))
    json_to_xml(Method.ACT_DIGITAL_CHECK_STATUS, result.response, xml)
    xml.append('  </act-tn>')
    return True

def act_get_postings(xml: list, data: dict) -> bool:
    url = host + '/v2/posting/fbs/act/get-postings'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    body = {'id': data['task_id']}
    result = post_query(url, body, headers)
    if not result.success:
        if result.data:
            log_error.error('Status: %s. Error: %s',result.status,result.data)
        else:
            log_error.error(('%s%s'),('Status: %s. ' % result.status) if result.status else '',result.error_message)
        return False

    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','  <act-tn>','    <task_id>%s</task_id>' % data['task_id']))
    json_to_xml(Method.ACT_GET_POSTINGS, result.response, xml)
    xml.append('  </act-tn>')
    return True

def set_prices(xml: list, data: dict) -> bool:
    url = host + '/v1/product/import/prices'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    body = {'prices': data['prices']}
    result = post_query(url, body, headers)
    if not result.success:
        if result.data:
            log_error.error('Status: %s. Error: %s',result.status,result.data)
        else:
            log_error.error(('%s%s'),('Status: %s. ' % result.status) if result.status else '',result.error_message)
        return False

    prices = {'prices_response': result.response['result'] if 'result' in result.response else [], 'prices_data': data['prices']}
    
    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','  <set-prices>'))
    json_to_xml(Method.SET_PRICES, prices, xml)
    xml.append('  </set-prices>')
    return True

def set_stocks(xml: list, data: dict) -> bool:
    url = host + '/v2/products/stocks'
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    body = {'stocks': data['stocks']}
    result = post_query(url, body, headers)
    if not result.success:
        if result.data:
            log_error.error('Status: %s. Error: %s',result.status,result.data)
        else:
            log_error.error(('%s%s'),('Status: %s. ' % result.status) if result.status else '',result.error_message)
        return False

    stocks = {'stocks_response': result.response['result'] if 'result' in result.response else [], 'stocks_data': data['stocks']}
    
    xml.extend(('<?xml version="1.0" encoding="windows-1251"?>','  <set-stocks>'))
    json_to_xml(Method.SET_STOCKS, stocks, xml)
    xml.append('  </set-stocks>')
    return True

def _post_without_xml(url:str, data: dict) -> bool:
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'Client-Id': CLIENT_ID, 'Api-Key': API_KEY}
    body = data
    result = post_query(url, body, headers)
    if not result.success:
        if result.data:
            log_error.error('Status: %s. Error: %s',result.status,result.data)
        else:
            log_error.error(('%s%s'),('Status: %s. ' % result.status) if result.status else '',result.error_message)
        return False

    return True

def cancel(xml, data: dict) -> bool:
    return _post_without_xml(host + '/v2/posting/fbs/cancel', data)

def product_cancel(xml, data: dict) -> bool:
    return _post_without_xml(host + '/v2/posting/fbs/product/cancel', data)

def ship(xml, data: dict) -> bool:
    return _post_without_xml(host + '/v4/posting/fbs/ship', data)

def real_fbs_ship(xml, data: dict) -> bool:
    return _post_without_xml(host + '/v4/posting/fbs/ship', data)

def real_fbs_delivering(xml, data: dict) -> bool:
    return _post_without_xml(host + '/v2/fbs/posting/delivering', data)

def set_country(xml, data: dict) -> bool:
    return _post_without_xml(host + '/v2/posting/fbs/product/country/set', data)

def set_gtd(xml, data: dict) -> bool:
    return _post_without_xml(host + '/v4/fbs/posting/product/exemplar/set', data)

functions = {
    Method.GET_NEW_ORDERS: (get_new_orders, 'oznw_'),
    Method.GET_ORDERS: (get_orders, 'ozgi_'),
    Method.GET_INFO: (get_info,'ozgi_'), 
    Method.CANCEL: (cancel, None), 
    Method.PRODUCT_CANCEL: (product_cancel, None),
    Method.SHIP: (ship, None),
    Method.REAL_FBS_SHIP: (real_fbs_ship, None),
    Method.REAL_FBS_DELIVERING: (real_fbs_delivering, None),
    Method.ACT_CREATE: (act_create, 'ozac_'),
    Method.ACT_CHECK_STATUS: (act_check_status, 'ozac_'),
    Method.ACT_DIGITAL_CHECK_STATUS: (act_digital_check_status, 'ozac_'),
    Method.ACT_GET_POSTINGS: (act_get_postings, 'ozac_'),
    Method.GET_FBO_ORDERS: (get_fbo_orders, 'ozfbo_'),
    Method.GET_FBO_INFO: (get_fbo_info,'ozfbo_'), 
    Method.SET_PRICES: (set_prices, 'ozspr_'),
    Method.SET_STOCKS: (set_stocks, 'ozsst_'),
    Method.SET_COUNTRY: (set_country, None),
    Method.SET_GTD: (set_gtd, None)
    }

def _execute_method(func_method: Callable, xml_prefix: str, func_data: dict) -> bool:
    response_xml = []
    write_xml = False

    try:
        write_xml = func_method(response_xml, func_data)
    except Exception as e:
        log_error.error('Method error: %s', str(e))
        return False

    if write_xml:
        if xml_prefix:
            out_file = os.path.join(file_path, xml_prefix + random_string(8-len(xml_prefix)) + '.xml')
            try:
                with open(out_file, "wb") as result_xml:
                    result_xml.write('\n'.join(response_xml).encode('cp1251', errors='ignore'))
            except Exception as e:
                log_error.error('Write error: %s', str(e))
                return False
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        log_error.error('Illegal arguments count!')
        sys.exit(10)

    function_data = []
    not_delete = False
    delete_anyway = False
    delete_before_execution = False
    command_line = False
    if str(sys.argv[1]).startswith('--'):
        command_line = True
        method,CLIENT_ID,API_KEY = str(sys.argv[1][2:]).split('|')
        file_path = sys.argv[2] if len(sys.argv) == 3 else os.path.dirname(sys.argv[0])
    else:
        file_path = sys.argv[2] if len(sys.argv) == 3 else os.path.dirname(sys.argv[1])
        try:
            try:
                config = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
            except Exception:
                config = json.load(open(sys.argv[1], 'r', encoding='cp1251'))
                
            CLIENT_ID = config['client_id']
            API_KEY = config['api_key']
            not_delete = config['not_delete'] if 'not_delete' in config else False
            delete_anyway = config['delete_anyway'] if 'delete_anyway' in config else False
            delete_before_execution = config['delete_before_execution'] if 'delete_before_execution' in config else False

            if 'xml_path' in config and config['xml_path']:
                file_path = config['xml_path']

            execute_requests = []
            if not isinstance(config['request'], list):
                execute_requests.append(config['request'])
            else:
                execute_requests = config['request']
        except Exception as e:
            log_error.error('Read config error: ' + str(e))
            sys.exit(20)

    if command_line:
        execute_result =_execute_method(*functions[Method(method)], function_data)
    else:
        if delete_before_execution:
            if os.path.exists(sys.argv[1]):
                os.remove(sys.argv[1])
        execute_result = True
        is_not_required = False
        pause_before = 0

        for single_request in execute_requests:
            if not execute_result and not is_not_required: #цепочка запросов до 1-й ошибки в обязательном запросе
                break
            method = single_request['method']
            is_not_required = True if 'is_not_required' in single_request and single_request['is_not_required']==1 else False
            pause_before = int(single_request['pause_before']) if 'pause_before' in single_request and str(single_request['pause_before']).isdigit() else 0

            if 'debug_data' in single_request:
                function_data = {'debug_data': single_request['debug_data']}
            else:
                function_data = single_request['data'] if 'data' in single_request else []

            if pause_before > 0:
                if pause_before > 180:
                    pause_before = 180
                print(f"Pause {pause_before} seconds")
                sleep(pause_before)
        
            execute_result =_execute_method(*functions[Method(method)], function_data)

    if not delete_before_execution and delete_anyway:
        if os.path.exists(sys.argv[1]):
            os.remove(sys.argv[1])

    if not execute_result:
        sys.exit(30)

    if not delete_before_execution and not delete_anyway and not not_delete: #если уже точно не удалено, то удалять, если нет особых указаний
        if os.path.exists(sys.argv[1]):
            os.remove(sys.argv[1])


