import unittest

from pyramid import testing
from pyramid.compat import json

from webtest import TestApp

class TestJSONRPCMapper(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid_rpc.jsonrpc import JsonRpcViewMapper
        return JsonRpcViewMapper

    def _makeOne(self, *args, **kwargs):
        return self._getTargetClass()(*args, **kwargs)

    def test_implements(self):
        from pyramid.interfaces import IViewMapperFactory
        from pyramid.interfaces import IViewMapper
        cls  = self._getTargetClass()
        self.assertTrue(IViewMapperFactory.providedBy(cls))
        self.assertTrue(IViewMapper.implementedBy(cls))
        target = cls()
        self.assertTrue(IViewMapper.providedBy(target))

    def test_view_callable_with_list(self):

        target = self._makeOne()
        view_callable = target(dummy_view)
        request = testing.DummyRequest()
        request.rpc_args = [1, 2]
        context = object()
        result = view_callable(context, request)
        self.assertEqual(result, 3)
        
    def test_view_callable_cls_with_list(self):

        target = self._makeOne()
        view_callable = target(DummyView)
        request = testing.DummyRequest()
        params = {'jsonrpc':'2.0', 'method':'dummy_view', 
                  'params':[1, 2], 'id':'test'}
        body = json.dumps(params)
        request.json_body = params
        request.rpc_args = [1, 2]
        context = object()
        result = view_callable(context, request)
        self.assertEqual(result, 3)


    def test_view_callable_with_dict(self):
        target = self._makeOne()
        view_callable = target(dummy_view)
        request = testing.DummyRequest()
        request.rpc_args = dict(a=3, b=4)
        context = object()
        result = view_callable(context, request)
        self.assertEqual(result, 7)

    def test_view_callable_cls_with_dict(self):
        target = self._makeOne()
        view_callable = target(DummyView)
        request = testing.DummyRequest()
        params = {'jsonrpc':'2.0', 'method':'dummy_view', 
                  'params':dict(a=3, b=4), 'id':'test'}
        body = json.dumps(params)
        request.json_body = params
        request.rpc_args = dict(a=3, b=4)
        context = object()
        result = view_callable(context, request)
        self.assertEqual(result, 7)

    def test_view_callable_with_invalid_args(self):
        from pyramid_rpc.jsonrpc import JsonRpcParamsInvalid

        target = self._makeOne()
        view_callable = target(dummy_view)
        request = testing.DummyRequest()
        request.rpc_args = []
        context = object()
        self.assertRaises(JsonRpcParamsInvalid, view_callable, context, request)

    def test_view_callable_cls_with_invalid_args(self):
        from pyramid_rpc.jsonrpc import JsonRpcParamsInvalid

        target = self._makeOne()
        view_callable = target(DummyView)
        request = testing.DummyRequest()
        params = {'jsonrpc':'2.0', 'method':'dummy_view', 
                  'params':[], 'id':'test'}
        body = json.dumps(params)
        request.json_body = params
        request.rpc_args = []
        context = object()
        self.assertRaises(JsonRpcParamsInvalid, view_callable, context, request)


    def test_view_callable_with_invalid_keywords(self):
        from pyramid_rpc.jsonrpc import JsonRpcParamsInvalid

        target = self._makeOne()
        view_callable = target(dummy_view)
        request = testing.DummyRequest()
        request.rpc_args = {}
        context = object()
        self.assertRaises(JsonRpcParamsInvalid, view_callable, context, request)

    def test_view_callable_cls_with_invalid_keywords(self):
        from pyramid_rpc.jsonrpc import JsonRpcParamsInvalid

        target = self._makeOne()
        view_callable = target(DummyView)
        request = testing.DummyRequest()
        params = {'jsonrpc':'2.0', 'method':'dummy_view', 
                  'params':{}, 'id':'test'}
        body = json.dumps(params)
        request.json_body = params
        request.rpc_args = {}
        context = object()
        self.assertRaises(JsonRpcParamsInvalid, view_callable, context, request)


class TestJSONRPCEndPoint(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()
        from pyramid.threadlocal import get_current_registry
        self.registry = get_current_registry()

    def tearDown(self):
        testing.cleanUp()

    def _getTargetClass(self):
        from pyramid_rpc.jsonrpc import jsonrpc_endpoint
        return jsonrpc_endpoint

    def _registerRouteRequest(self, name):
        from pyramid.interfaces import IRouteRequest
        from pyramid.request import route_request_iface
        iface = route_request_iface(name)
        self.registry.registerUtility(iface, IRouteRequest, name=name)
        return iface

    def _registerView(self, app, name, classifier, req_iface, ctx_iface):
        from pyramid.interfaces import IView
        self.registry.registerAdapter(
            app, (classifier, req_iface, ctx_iface), IView, name)
    
    def _makeDummyRequest(self, request_data=None):
        from pyramid.testing import DummyRequest
        request = DummyRequest()
        request.matched_route = DummyRoute('JSON-RPC')
        if request_data is not None:
            request.body = json.dumps(request_data)
            request.content_length = len(request.body)

        return request
    
    def _callFUT(self, *args, **kwargs):
        jsonrpc_endpoint = self._getTargetClass()
        response = jsonrpc_endpoint(*args, **kwargs)
        return response

    def test_jsonrpc_endpoint(self):
        rpc_iface = self._registerRouteRequest('JSON-RPC')
        from pyramid.interfaces import IViewClassifier
        view = DummyView({'name': 'Smith'})
        self._registerView(view, 'echo', IViewClassifier, rpc_iface, None)
        
        request_data = {'jsonrpc': '2.0', 'method': 'echo', 'id': 'echo-rpc', 'params':[13]}
        request = self._makeDummyRequest(request_data)

        response = self._callFUT(request)

        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.body)
        self.assertEqual({"jsonrpc": "2.0", "id": "echo-rpc",
                          "result": {'name': 'Smith'}}, data)

    def test_jsonrpc_endpoint_batch_request(self):
        from pyramid.interfaces import IViewClassifier
        rpc_iface = self._registerRouteRequest('JSON-RPC')
        view1 = DummyView({'name': 'Smith'})
        self._registerView(view1, 'echo1', IViewClassifier, rpc_iface, None)
        view2 = DummyView({'name': 'John Doe'})
        self._registerView(view2, 'echo2', IViewClassifier, rpc_iface, None)
        
        request_data = [
            {'jsonrpc': '2.0', 'method': 'echo1',
             'id': 'echo1-rpc', 'params':[13]},
            {'jsonrpc': '2.0', 'method': 'echo2',
             'id': 'echo2-rpc', 'params':[13]},
        ]
        request = self._makeDummyRequest(request_data)

        response = self._callFUT(request)

        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.body)
        self.assertEqual(len(data), 2)
        res1 = data[0]
        self.assertEqual(res1['id'], 'echo1-rpc')
        self.assertEqual(res1['result'], {'name': 'Smith'})
        res2 = data[1]
        self.assertEqual(res2['id'], 'echo2-rpc')
        self.assertEqual(res2['result'], {'name': 'John Doe'})

    def test_jsonrpc_endpoint_batch_request_with_error(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid_rpc.jsonrpc import JsonRpcInternalError
        rpc_iface = self._registerRouteRequest('JSON-RPC')
        view1 = DummyView({'name': 'Smith'})
        self._registerView(view1, 'echo1', IViewClassifier, rpc_iface, None)
        view2 = DummyView(raise_exception=Exception)
        self._registerView(view2, 'echo2', IViewClassifier, rpc_iface, None)
        
        request_data = [
            {'jsonrpc': '2.0', 'method': 'echo1',
             'id': 'echo1-rpc', 'params':[13]},
            {'jsonrpc': '2.0', 'method': 'echo2',
             'id': 'echo2-rpc', 'params':[13]},
        ]
        request = self._makeDummyRequest(request_data)

        response = self._callFUT(request)

        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.body)
        self.assertEqual(len(data), 2)
        res1 = data[0]
        self.assertEqual('echo1-rpc', res1['id'])
        self.assertEqual({'name': 'Smith'}, res1['result'])
        res2 = data[1]
        self.assertEqual('echo2-rpc', res2['id'])
        self.assertEqual(res2['error']['code'], JsonRpcInternalError.code)



    def test_jsonrpc_notification(self):
        from pyramid.interfaces import IViewClassifier
        view = DummyView({'name': 'Smith'})
        rpc_iface = self._registerRouteRequest('JSON-RPC')
        self._registerView(view, 'echo', IViewClassifier, rpc_iface, None)
        
        request_data = {'jsonrpc': '2.0', 'method': 'echo', 'params':[13]}
        request = self._makeDummyRequest(request_data)
        
        response = self._callFUT(request)

        self.assertEqual('', response.body)
    
    def test_jsonrpc_endpoint_not_found(self):
        from pyramid_rpc.jsonrpc import JsonRpcMethodNotFound

        request_data = {'jsonrpc': '2.0', 'id': 'nothing-rpc',
                        'method': 'nothing', 'params':[13]}
        request = self._makeDummyRequest(request_data)
        response = self._callFUT(request)
       
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcMethodNotFound.code)

    def test_jsonrpc_endpoint_parse_error(self):
        from pyramid_rpc.jsonrpc import JsonRpcParseError
        
        request = self._makeDummyRequest()
        request.body = "]"
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = self._callFUT(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcParseError.code)

    def test_jsonrpc_endpoint_internal_error(self):
        from pyramid_rpc.jsonrpc import JsonRpcInternalError
        from pyramid.interfaces import IViewClassifier
        view = DummyView(raise_exception=Exception)
        rpc_iface = self._registerRouteRequest('JSON-RPC')
        self._registerView(view, 'echo', IViewClassifier, rpc_iface, None)

        request_data = {'jsonrpc': '2.0', 'id': 'echo-rpc',
                        'method': 'echo', 'params':[13]}
        request = self._makeDummyRequest(request_data)
        
        response = self._callFUT(request)

        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcInternalError.code)

    def test_jsonrpc_notification_with_error(self):
        from pyramid.interfaces import IViewClassifier
        view = DummyView(raise_exception=Exception)
        rpc_iface = self._registerRouteRequest('JSON-RPC')
        self._registerView(view, 'echo', IViewClassifier, rpc_iface, None)
        
        request_data = {'jsonrpc': '2.0', 'method': 'echo', 'params':[13]}
        request = self._makeDummyRequest(request_data)
        
        response = self._callFUT(request)

        self.assertEqual('', response.body)


    def test_jsonrpc_endpoint_invalid_response(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid_rpc.jsonrpc import JsonRpcInternalError
        def invalid_view(context, request):
            return object()

        rpc_iface = self._registerRouteRequest('JSON-RPC')
        self._registerView(invalid_view, 'invalid', IViewClassifier,
                           rpc_iface, None)
        request_data = {'jsonrpc': '2.0', 'id': 'invalid-rpc',
                        'method': 'invalid', 'params':[]}
        request = self._makeDummyRequest(request_data)
        response = self._callFUT(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcInternalError.code)

    def test_jsonrpc_endpoint_empty_request(self):
        from pyramid_rpc.jsonrpc import JsonRpcRequestInvalid

        request = self._makeDummyRequest()
        request.body = ""
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = self._callFUT(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcRequestInvalid.code)

    def test_jsonrpc_endpoint_invalid_request(self):
        from pyramid_rpc.jsonrpc import JsonRpcRequestInvalid

        request = self._makeDummyRequest()
        request.body = "10"
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = self._callFUT(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcRequestInvalid.code)

    def test_jsonrpc_endpoint_invalid_version(self):
        from pyramid_rpc.jsonrpc import JsonRpcRequestInvalid
        
        request_data = {'jsonrpc': '1.0'}
        request = self._makeDummyRequest(request_data)

        response = self._callFUT(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcRequestInvalid.code)

    def test_jsonrpc_endpoint_no_method(self):
        from pyramid_rpc.jsonrpc import JsonRpcRequestInvalid

        request_data = {'jsonrpc': '2.0'}
        request = self._makeDummyRequest(request_data)
        
        response = self._callFUT(request)

        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcRequestInvalid.code)

class TestJSONRPCIntegration(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_add_jsonrpc_method_with_no_endpoint(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        self.assertRaises(ConfigurationError,
                          config.add_jsonrpc_method,
                          lambda r: None, method='dummy')

    def test_add_jsonrpc_method_with_no_method(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        self.assertRaises(ConfigurationError,
                          config.add_jsonrpc_method,
                          lambda r: None, endpoint='rpc')

    def test_it(self):
        def view(request):
            return request.rpc_args[0]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                          params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['result'], 2)

    def test_it_with_multiple_methods(self):
        def view(request):
            return request.rpc_args[0]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        config.add_jsonrpc_method(lambda r: 'fail',
                                  endpoint='rpc', method='dummy2')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['result'], 2)

    def test_it_with_no_version(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'method': 'dummy', 'id': 5, 'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                          params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['error']['code'], -32600)

    def test_it_with_no_method(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'id': 5, 'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                          params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['error']['code'], -32600)

    def test_it_with_no_id(self):
        def view(request):
            return request.rpc_args[0]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                          params=json.dumps(params))
        self.assertEqual(resp.status_int, 204)
        self.assertEqual(resp.body, '')

    def test_it_with_no_params(self):
        def view(request):
            self.assertEqual(request.rpc_args, [])
            return 'no params'
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'id': 5, 'method': 'dummy'}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                          params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['result'], 'no params')

    def test_it_with_invalid_method(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'id': 5, 'method': 'foo', 'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                          params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['error']['code'], -32601)

    def test_it_with_invalid_body(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = app.post('/api/jsonrpc', content_type='application/json',
                          params='{')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['error']['code'], -32700)

    def test_it_with_general_exception(self):
        def view(request):
            raise Exception()
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                          params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['error']['code'], -32603)

class FunctionalTest(unittest.TestCase):

    def test_it(self):
        try:
            # Pyramid 1.1
            from pyramid.renderers import null_renderer
            renderer = null_renderer
        except ImportError:
            # Pyramid 1.0
            renderer = None
        from pyramid.config import Configurator
        from pyramid_rpc.jsonrpc import jsonrpc_endpoint
        from pyramid_rpc.jsonrpc import JsonRpcViewMapper
        config = Configurator()
        config.add_route('JSON-RPC', 'apis/rpc')
        config.add_view(jsonrpc_endpoint, route_name='JSON-RPC')
        def dummy_rpc(request, a, b):
            return a + b
        config.add_view(route_name='JSON-RPC', name='dummy_rpc',
                        view=dummy_rpc, mapper=JsonRpcViewMapper,
                        renderer=renderer)
        app = config.make_wsgi_app()
        import webtest
        app = webtest.TestApp(app)
        params = {'jsonrpc': '2.0', 'method': 'dummy_rpc',
                  'params': [2, 3], 'id': 'test'}
        body = json.dumps(params)
        res = app.post('/apis/rpc', params=body,
                       content_type='application/json')
        data = json.loads(res.body)
        self.assertEqual(data['id'], 'test')
        self.assertEqual(data['jsonrpc'], '2.0')
        self.assertEqual(data['result'], 5)


class DummyRoute:
    def __init__(self, route_name):
        self.name = route_name

def dummy_view(request, a, b):
    return a + b

class DummyView:
    def __init__(self, response=None, raise_exception=None, request=None):
        self.response = response
        self.raise_exception = raise_exception
        self.request = request

    def __call__(self, context, request):
        if self.raise_exception is not None:
            raise self.raise_exception
        self.context = context
        self.request = request
        return self.response
    
    def dummy_view(self, request, a, b):
        return a + b

