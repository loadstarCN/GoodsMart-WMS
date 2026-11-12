"""本地联调：批发站真实 WMSClient → WMS 内存测试应用，不访问网络或生产数据。"""
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from types import ModuleType
from unittest.mock import patch
from urllib.parse import urlsplit

os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['TEST_DATABASE_URL'] = 'sqlite:///:memory:'

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'GoodsMart-WMS-Backend'))
import tests.conftest  # noqa: E402,F401 — 隔离 Redis
from tests.helpers import (  # noqa: E402
    client as client_fixture, db, get_api_key, get_company,
    get_warehouse_admin_user, get_warehouse, get_supplier,
    TEST_API_KEY_PLAIN, warehouse_today,
)
from tests.test_customs import _prepare  # noqa: E402
from warehouse.carrier.file_templates import validate_template, render_rows  # noqa: E402
import requests  # noqa: E402

source = ROOT.parent / 'GoodsMart/GoodsMart-Wholesale-API/app/services/wms_client.py'
# 两个仓库都使用 app 模块名；只装载客户端所需的纯服务，禁止意外启动任一生产 app。
for name, directory in [('app', source.parents[1]), ('app.services', source.parent),
                        ('app.utils', source.parents[1] / 'utils')]:
    package = ModuleType(name)
    package.__path__ = [str(directory)]
    sys.modules[name] = package
api_extensions = ModuleType('app.extensions')
api_extensions.db = None  # 客户端传入 LocalGoods，联调不查询批发数据库。
sys.modules['app.extensions'] = api_extensions
from app.services import wms_goods_sync as goods_sync
spec = importlib.util.spec_from_file_location('wholesale_client_contract', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

fixture = client_fixture.__wrapped__()
client = next(fixture)
transport = client.application.test_client()
calls = []

def request(method, url, **kwargs):
    path = urlsplit(url).path.removeprefix('/warehouse')
    with client.application.app_context():
        response = transport.open(path, method=method, headers=kwargs.get('headers'),
                               query_string=kwargs.get('params'), json=kwargs.get('json'))
    result = requests.Response()
    result.status_code = response.status_code
    result._content = response.data
    result.headers.update(response.headers)
    result.url = url
    calls.append((method, path, result.status_code))
    if result.status_code >= 400:
        print('HTTP_RESULT', method, path, result.status_code, result.text)
    return result

try:
    _prepare(client)
    template_source = (ROOT / 'GoodsMart-WMS-Web/app/utils/apiKeyTemplates.ts').read_text(encoding='utf-8')
    section = template_source.split("key: 'order-integration'", 1)[1].split('],', 1)[0]
    permissions = re.findall(r"'([a-z_]+)'", section)
    with client.application.app_context():
        key = get_api_key()
        key.user_id = get_warehouse_admin_user().id
        key.company_id = get_company().id
        key.permissions = permissions
        wid, supplier_id = get_warehouse().id, get_supplier().id
        db.session.commit()
        client.application.config.update(WMS_API_URL='https://contract.invalid',
                                         WMS_API_KEY=TEST_API_KEY_PLAIN, WMS_WAREHOUSE_ID=wid,
                                         WMS_GOODS_IMAGE_HEAD_CHECK=False)

    # 只替换客户端的日期辅助模块；显式传日期，业务 HTTP 全部进入真实 WMS 路由。
    jst = ModuleType('app.utils.jst')
    jst.today_jst = warehouse_today
    with client.application.app_context(), patch.dict(sys.modules, {'app.utils.jst': jst}), \
            patch.object(module.requests, 'get', side_effect=lambda u, **k: request('GET', u, **k)), \
            patch.object(module.requests, 'post', side_effect=lambda u, **k: request('POST', u, **k)), \
            patch.object(module.requests, 'put', side_effect=lambda u, **k: request('PUT', u, **k)):
        wms = module.WMSClient()
        image_args = {'image_url': 'https://example.invalid/a.png', 'thumbnail_url': 'https://example.invalid/a.png'}
        image_args['local'] = goods_sync.LocalGoods(goods_id='contract', jan='contract', name='Contract goods')
        similar_id = wms.ensure_goods('PREFIX4580590129474', 'Similar JAN', **image_args)
        exact_id = wms.ensure_goods('4580590129474', 'Exact JAN', **image_args)
        assert exact_id != similar_id
        assert wms.ensure_goods('4580590129474', 'Exact JAN', **image_args) == exact_id
        address = {'name': 'Buyer', 'country': 'JP', 'postal_code': '5300001',
                   'phone': '0600000000', 'admin_area': '\u5927\u962a\u5e9c', 'locality': '\u5927\u962a\u5e02',
                   'address_line1': '\u6885\u75301-1-1', 'address_line2': None,
                   'organization': None, 'latin': None}
        recipient_id = wms.ensure_recipient('contract-address', 'Osaka Umeda 1-1-1', recipient=address)
        items = [{'jan': 'G001', 'quantity': 1, 'goods_name': 'Test goods'}]
        asn = wms.create_asn('CONTRACT-ASN', supplier_id, items, check_existing=True)
        assert wms.get_asn(asn['id'])['id'] == asn['id']
        assert wms.create_asn('CONTRACT-ASN', supplier_id, items, check_existing=True)['id'] == asn['id']
        assert wms.cancel_asn(asn['id'])['status'] == 'closed'
        replacement = wms.create_asn('CONTRACT-ASN', supplier_id, items, check_existing=True)
        assert replacement['id'] != asn['id']
        assert wms.create_asn('CONTRACT-ASN', supplier_id, items, check_existing=True)['id'] == replacement['id']
        dn = wms.create_dn('CONTRACT-DN', recipient_id, 'Osaka Umeda 1-1-1', items,
                           expected_shipping_date=warehouse_today(), ship_to=address, check_existing=True)
        detail = wms.get_dn(dn['id'])
        assert wms.get_dn_carrier_shipment(dn['id'])['shipment'] is None
        assert isinstance(wms.find_delivery_tasks(dn['id']), list)
        for field in ('admin_area', 'locality', 'address_line1'):
            assert detail['ship_to'][field] == address[field], detail
        carrier_template = validate_template(json.loads((ROOT / 'GoodsMart-WMS-Backend/warehouse/carrier/presets/jp/sagawa_ehiden3.json').read_text(encoding='utf-8')))
        row = render_rows(carrier_template, [{'ship_to': detail['ship_to_effective']}])[0]
        assert not [p for p in row['problems'] if p['column_index'] in (5, 6, 7)], row['problems']
        goods_id, goods = wms.update_goods_origin_country('G001', 'Test goods', 'JP',
                                                         image_url='https://example.invalid/a.png',
                                                         thumbnail_url='https://example.invalid/a.png',
                                                         local=image_args['local'])
        assert goods['origin_country'] == 'JP'
        assert any(row['id'] == goods_id for row in wms.list_goods_by_codes(['G001']))
        assert wms.update_goods(goods_id, {'name': 'Test goods'})['id'] == goods_id
        try:
            wms.refresh_dn_tracking(dn['id'])
        except requests.HTTPError as exc:
            # 未创建运单：应通过权限检查后返回业务冲突，而不是 403。
            assert exc.response.status_code == 409 and exc.response.json()['code'] == 16134
        else:
            raise AssertionError('DN without a waybill must reject tracking')
        assert wms.cancel_dn(dn['id'])['status'] == 'closed'
        replacement_dn = wms.create_dn('CONTRACT-DN', recipient_id, 'Osaka Umeda 1-1-1', items,
            expected_shipping_date=warehouse_today(), ship_to=address, check_existing=True)
        assert replacement_dn['id'] != dn['id']
        print(json.dumps({'result': 'PASS', 'requests': calls}, ensure_ascii=True))
finally:
    fixture.close()
