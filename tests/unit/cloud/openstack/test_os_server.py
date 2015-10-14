from bunch import Bunch
import pytest
import yaml
import inspect

from cloud.openstack import os_server

def params_from_doc(self):
    '''This function extracts the docstring from the calling function,
    parses it as a YAML document, and returns parameters for the os_server
    module.'''

    outer = inspect.currentframe().f_back
    name = outer.f_code.co_name
    doc = inspect.getdoc(getattr(self, name))
    cfg = yaml.load(doc)

    # This enforces the "everything is a list" rule for the 'nics'
    # parameter.
    try:
        nics = cfg[0]['os_server']['nics']
        if type(nics) == str:
            cfg[0]['os_server']['nics'] = [nics]
    except KeyError:
        pass

    return cfg[0]['os_server']

class FakeCloud (object):
    ports = [
        {'name': 'port1', 'id': '1234'},
        {'name': 'port2', 'id': '4321'},
    ]

    networks = [
        {'name': 'network1', 'id': '5678'},
        {'name': 'network2', 'id': '8765'},
    ]

    def get_port(self, name):
        for port in self.ports:
            if port['name'] == name:
                return port
        else:
            raise KeyError(name)

    def get_network(self, name):
        for network in self.networks:
            if network['name'] == name:
                return network
        else:
            raise KeyError(name)

class TestNetworkArgs(object):
    '''This class exercises the _network_args function of the
    os_server module.  For each test, we parse the YAML document
    contained in the docstring to retrieve the module parameters for the
    test.'''

    def setup_method(self, method):
        self.cloud = FakeCloud()

    def test_nics_string_net_id(self):
        '''
        - os_server:
            nics: net-id=1234
        '''
        _module = Bunch(params=params_from_doc(self))
        args = os_server._network_args(_module, self.cloud)
        assert(args[0]['net-id'] == '1234')

    def test_nics_string_net_id_list(self):
        '''
        - os_server:
            nics: net-id=1234,net-id=4321
        '''
        _module = Bunch(params=params_from_doc(self))
        args = os_server._network_args(_module, self.cloud)
        assert(args[0]['net-id'] == '1234')
        assert(args[1]['net-id'] == '4321')

    def test_nics_string_port_id(self):
        '''
        - os_server:
            nics: port-id=1234
        '''
        _module = Bunch(params=params_from_doc(self))
        args = os_server._network_args(_module, self.cloud)
        assert(args[0]['port-id'] == '1234')

    def test_nics_string_net_name(self):
        '''
        - os_server:
            nics: net-name=network1
        '''
        _module = Bunch(params=params_from_doc(self))
        args = os_server._network_args(_module, self.cloud)
        assert(args[0]['net-id'] == '5678')

    def test_nics_string_port_name(self):
        '''
        - os_server:
            nics: port-name=port1
        '''
        _module = Bunch(params=params_from_doc(self))
        args = os_server._network_args(_module, self.cloud)
        assert(args[0]['port-id'] == '1234')

    def test_nics_structured_net_id(self):
        '''
        - os_server:
            nics:
                - net-id: '1234'
        '''
        _module = Bunch(params=params_from_doc(self))
        args = os_server._network_args(_module, self.cloud)
        assert(args[0]['net-id'] == '1234')

    def test_nics_structured_mixed(self):
        '''
        - os_server:
            nics:
                - net-id: '1234'
                - port-name: port1
                - 'net-name=network1,port-id=4321'
        '''
        _module = Bunch(params=params_from_doc(self))
        args = os_server._network_args(_module, self.cloud)
        assert(args[0]['net-id'] == '1234')
        assert(args[1]['port-id'] == '1234')
        assert(args[2]['net-id'] == '5678')
        assert(args[3]['port-id'] == '4321')
