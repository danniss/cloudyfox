import logging, json, os, random, sys, uuid
from twisted.web import http
import libvirt, libxml2, guestfs

import servlet, util

class NodeServlet(servlet.Servlet):
    def request(self, req):
        segments = req.path.split('/')
        if len(segments) != 4:
            req.setResponseCode(http.BAD_REQUEST)
            req.finish()
            return
        op = segments[3]
        if op == 'info':
            return self.info(req)
        elif op == 'newpool':
            return self.newPool(req)
        elif op == 'listvol':
            return self.listVol(req)
        req.setResponseCode(http.NOT_FOUND)
        req.finish()

    def info(self, req):
        conn = util.getConnection()
        res = dict()
        info = conn.getInfo()
        res['arch'] = info[0]
        res['cpus'] = info[2]
        res['freq'] = info[3]
        f = file('/proc/uptime')
        with f:
            data = f.read()
            arr = data.split(' ')
            res['uptime'] = int(float(arr[0]))
        res['memory'] = conn.getMemoryStats(-1, 0)
        ifaces = util.listInterfaces()
        res['ifaces'] = list()
        for iface in ifaces:
            if iface[0] == 'lo':
                continue
            res['ifaces'].append(iface)
        res['net'] = self.listNet(conn)
        res['pool'] = self.listPool(conn)
        req.write(json.dumps(res))
        req.finish()

    def newPool(self, req):
        ret = dict()
        ret['code'] = 0
        try:
            if not req.args.has_key('type'):
                ret['code'] = 1001
                ret['desc'] = "No type parameter"
                raise BaseException()
            pool_type = req.args['type'][0]
            if not req.args.has_key('name'):
                ret['code'] = 1001
                ret['desc'] = "No name parameter"
                raise BaseException()
            name = req.args['name'][0]
            doc = libxml2.parseDoc("<pool/>")
            root = doc.getRootElement()
            if pool_type == 'logical':
                root.newProp('type', 'logical')
                node = libxml2.newNode('name')
                node.setContent(name)
                root.addChild(node)
                node = libxml2.newNode('target')
                if not req.args.has_key('dev'):
                    ret['code'] = 1003
                    ret['desc'] = "Parameter dev invalid"
                    raise BaseException()
                dev = req.args['dev'][0]
                if not os.path.exists(dev):
                    ret['code'] = 1003
                    ret['desc'] = 'Parameter dev invalid'
                    raise BaseException()
                path = libxml2.newNode('path')
                path.setContent(dev)
                node.addChild(path)
                root.addChild(node)
            elif pool_type == 'dir':
                root.newProp('type', 'dir')
                node = libxml2.newNode('name')
                node.setContent(name)
                root.addChild(node)
                node = libxml2.newNode('target')
                path = libxml2.newNode('path')
                if not req.args.has_key('dev') or len(req.args['dev'][0]) == 0:
                    ret['code'] = 1003
                    ret['desc'] = "Parameter path invalid"
                    raise BaseException()
                dev = req.args['dev'][0]
                if not os.path.isdir(dev):
                    ret['code'] = 1003
                    ret['desc'] = "Path doesn't exists"
                    raise BaseException()
                path.setContent(dev)
                node.addChild(path)
                root.addChild(node)
            elif pool_type == 'netfs' or pool_type == 'iscsi':
                root.newProp('type', pool_type)
                node = libxml2.newNode('name')
                node.setContent(name)
                root.addChild(node)
                node = libxml2.newNode('source')
                if not req.args.has_key('host'):
                    ret['code'] = 1004
                    ret['desc'] = 'Parameter host invalid'
                    raise BaseException()
                subNode = libxml2.newNode('host')
                subNode.newProp('name', req.args['host'][0])
                node.addChild(subNode)
                if pool_type == 'netfs':
                    if not req.args.has_key('src_path'):
                        ret['code'] = 1004
                        ret['desc'] = 'Parameter src_path invalid'
                        raise BaseException()
                    subNode = libxml2.newNode('dir')
                    subNode.newProp('path', req.args['src_path'][0])
                    node.addChild(subNode)
                else:
                    if not req.args.has_key('device'):
                        ret['code'] = 1004
                        ret['desc'] = 'Parameter device invalid'
                        raise BaseException()
                    subNode = libxml2.newNode('device')
                    subNode.newProp('path', req.args['device'][0])
                    node.addChild(subNode)
                                
                root.addChild(node)
                if not req.args.has_key('target_path') or not os.path.isdir(req.args['target_path'][0]):
                    ret['code'] = '1004'
                    ret['desc'] = "Parameter target path invalid"
                    raise BaseException()
                
                node = libxml2.newNode('target')
                subNode = libxml2.newNode('path')
                subNode.setContent(req.args['target_path'][0])
                node.addChild(subNode)
                permission = libxml2.newNode('permissions')
                subNode = libxml2.newNode('owner')
                subNode.setContent('-1')
                permission.addChild(subNode)
                subNode = libxml2.newNode('group')
                subNode.setContent('-1')
                permission.addChild(subNode)
                subNode = libxml2.newNode('mode')
                subNode.setContent('0700')
                permission.addChild(subNode)
                node.addChild(permission)
                root.addChild(node)
            else:
                ret['code'] = 1002
                ret['desc'] = "Invalid storage type"
                raise BaseException()
            conn = util.getConnection()
            pool = None
            try:
                pool = conn.storagePoolDefineXML(root.serialize(), 0)
                if int(req.args['auto_start'][0]) != 0:
                    pool.setAutostart(True)
                    pool.create(0)
            except:
                ret['code'] = 10000
                ret['desc'] = 'Unable to create poool'
                if pool != None:
                    pool.undefine()
                conn.close()
                raise
            ret['name'] = name
            ret['type'] = pool_type
            doc = libxml2.parseDoc(pool.XMLDesc(0))
            nodes = doc.xpathEval('//uuid')
            if len(nodes) > 0:
                ret['uuid'] = nodes[0].getContent()
            nodes = doc.xpathEval('//capacity')
            if len(nodes) > 0:
                ret['capacity'] = nodes[0].getContent()
            nodes = doc.xpathEval('//allocation')
            if len(nodes) > 0:
                ret['allocation'] = nodes[0].getContent()
            nodes = doc.xpathEval('//available')
            if len(nodes) > 0:
                ret['available'] = nodes[0].getContent()
            conn.close()
        except:
            pass
        req.write(json.dumps(ret))
        req.finish()

    def listNet(self, conn):
        network_names = conn.listNetworks()
        network_names.sort()
        networks = list()
        try:
            for network_name in network_names:
                network = conn.networkLookupByName(network_name)
                doc = libxml2.parseDoc(network.XMLDesc(0))
                nodes = doc.xpathEval('//name')
                n = dict()
                if len(nodes) > 0:
                    n['name'] = nodes[0].getContent()
                nodes = doc.xpathEval('//uuid')
                if len(nodes) > 0:
                    n['uuid'] = nodes[0].getContent()
                nodes = doc.xpathEval('//bridge')
                if len(nodes) > 0:
                    if nodes[0].hasProp('name'):
                        n['bridge'] = dict()
                        n['bridge']['name'] = nodes[0].prop('name')
                nodes = doc.xpathEval('//forward')
                if len(nodes) > 0:
                    if nodes[0].hasProp('mode'):
                        n['forward'] = dict()
                        n['forward']['mode'] = nodes[0].prop('mode')
                    if nodes[0].hasProp('dev'):
                        if not n.has_key('forward'):
                            n['forward'] = dict()
                            n['forward']['dev'] = nodes[0].prop('dev')
                nodes = doc.xpathEval('//mac')
                if len(nodes) > 0 and nodes[0].hasProp('address'):
                    n['mac'] = nodes[0].prop('address')
                nodes = doc.xpathEval('//ip')
                if len(nodes) > 0:
                    node = nodes[0]
                    n['ip'] = dict()
                    n['ip']['address'] = node.prop('address')
                    n['ip']['netmask'] = node.prop('netmask')
                    if node.firstElementChild():
                        node = node.firstElementChild();
                        if node.firstElementChild():
                            node = node.firstElementChild()
                            if node.hasProp('start'):
                                n['ip']['start'] = node.prop('start')
                            if node.hasProp('end'):
                                n['ip']['end'] = node.prop('end')
                networks.append(n)
        finally:
            pass
        return networks

    def listPool(self, conn):
        pools = list()
        try:
            pool_names = conn.listStoragePools()
            for pool_name in pool_names:
                pool = conn.storagePoolLookupByName(pool_name)
                pool.refresh(0)
                doc = libxml2.parseDoc(pool.XMLDesc(0))
                p = dict()
                if doc.getRootElement().hasProp('type'):
                    p['type'] = doc.getRootElement().prop('type')
                nodes = doc.xpathEval('//name')
                if len(nodes) > 0:
                    p['name'] = nodes[0].getContent()
                nodes = doc.xpathEval('//uuid')
                if len(nodes) > 0:
                    p['uuid'] = nodes[0].getContent()
                nodes = doc.xpathEval('//capacity')
                if len(nodes) > 0:
                    p['capacity'] = nodes[0].getContent()
                nodes = doc.xpathEval('//allocation')
                if len(nodes) > 0:
                    p['allocation'] = nodes[0].getContent()
                nodes = doc.xpathEval('//available')
                if len(nodes) > 0:
                    p['available'] = nodes[0].getContent()
                pools.append(p)
        finally:
            pass
        return pools

    def listVol(self, req):
        vols = list()
        conn = util.getConnection()
        try:
            if not req.args.has_key('pool'):
                raise BaseException()
            pool = conn.storagePoolLookupByName(req.args['pool'][0])
            vol_names = pool.listVolumes()
            for vol_name in vol_names:
                vol = pool.storageVolLookupByName(vol_name)
                d = dict()
                d['name'] = vol.name()
                d['path'] = vol.path()
                d['size'] = vol.info()[1]
                vols.append(d)
        except:
            pass
        finally:
            conn.close()
        req.write(json.dumps(vols))
        req.finish()

            
