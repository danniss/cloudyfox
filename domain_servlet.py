import logging, json, os, random, sys, uuid, stat
from twisted.web import http
import libvirt, libxml2, guestfs

import config, servlet, util

class DomainServlet(servlet.Servlet):
    DOMAIN_ERROR_CODE_OK = 0
    """
    Ok result
    """
    DOMAIN_ERROR_CODE_BAD_PARAMETER = 101
    """
    Bad domain parameter
    """

    DOMAIN_ERROR_CODE_NAME_DUPLICATED = 102
    """
    Domain name already exists
    """

    DOMAIN_ERROR_CODE_INADEQUATE_MEMORY = 103
    """
    Not enough memory
    """

    DOMAIN_ERROR_CODE_NO_POOL = 104
    """
    No pool found
    """

    DOMAIN_ERROR_CODE_POOL_ERROR = 105
    """
    Error code for pool
    """

    DOMAIN_ERROR_CODE_INTERFACE_ERROR = 106
    """
    Error code for interface
    """

    DOMAIN_ERROR_CODE_NOT_FOUND = 107
    """
    Error code for domain not found
    """

    DOMAIN_ERROR_CODE_NO_DISK = 108
    """
    Disk file not found
    """

    DOMAIN_ERROR_CODE_SYS_ERROR = 1002
    """
    System error
    """
    def request(self, req):
        segments = req.path.split('/')
        if len(segments) != 4:
            req.setResponseCode(http.BAD_REQUEST)
            req.finish()
            return
        op = segments[3]
        if op == 'list':
            return self.listDomains(req)
        elif op == 'get':
            return self.queryDomain(req)
        elif op == 'info':
            return self.domainInfo(req)
        elif op == 'create':
            return self.createDomain(req)
        elif op == 'reset':
            return self.resetDomain(req)
        elif op == 'reboot':
            return self.rebootDomain(req)
        elif op == 'pause':
            return self.pauseDomain(req)
        elif op == 'resume':
            return self.resumeDomain(req)
        elif op == 'shutdown':
            return self.shutdownDomain(req)
        elif op == 'destroy':
            return self.destroyDomain(req)
        elif op == 'start':
            return self.startDomain(req)
        elif op == 'purge':
            return self.purgeDomain(req)
        elif op == 'newnet':
            return self.newNet(req)
        elif op == 'newmem':
            return self.newMemory(req)
        elif op == 'newvol':
            vol = self.newVol(req)
            ret = dict()
            if vol == None:
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
            else:
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
                ret['prefix'] = vol['prefix']
                ret['path']  = vol['path']
                ret['size'] = vol['size']
            req.write(json.dumps(ret))
            req.finish()
            return
        elif op == 'attach_disk':
            return self.attachDisk(req)
        elif op == 'copy_debian_template':
            return self.copyDebianTemplate(req)
        req.setResponseCode(http.NOT_FOUND)
        req.finish()

    def listDomains(self, req):
        conn = util.getConnection('R')
        try:
            domainNames = conn.listDefinedDomains()
            domains = list()
            for name in domainNames:
                domain = conn.lookupByName(name)
                domains.append(domain)
            domainIDs = conn.listDomainsID()
            for id in domainIDs:
                domain = conn.lookupByID(id)
                domains.append(domain)

            domainList = list()
            for domain in domains:
                d = dict()
                d["id"] = domain.ID()
                d["name"] = domain.name()
                d["uuid"] = domain.UUIDString()
                d["state"] = domain.state(0)
                domainList.append(d)
        finally:
            conn.close()
        req.write(json.dumps(domainList))
        req.finish()

    def getDomain(self, req, conn):
        domain = None
        if req.args.has_key('name') and len(req.args['name']) > 0 :
            try:
                domain = conn.lookupByName(req.args['name'][0])
            except:
                pass
        if domain == None and req.args.has_key('id') and len(req.args['id']) > 0:
            try:
                domain = conn.lookupByID(int(req.args['id'][0]))
            except:
                pass
        if domain == None and req.args.has_key('uuid') and len(req.args['uuid']) > 0:
            try:
                domain = conn.lookupByUUIDString(req.args['uuid'][0])
            except:
                pass
        return domain


    def queryDomain(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        domainList = list()
        if domain != None:
            d = dict()
            d["id"] = domain.ID()
            d["name"] = domain.name()
            d["uuid"] = domain.UUIDString()
            d["state"] = domain.state(0)
            domainList.append(d)
        conn.close()
        req.write(json.dumps(domainList))
        req.finish()

    def domainInfo(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        else:
            info = domain.info()
            ret['state'] = info[0]
            ret['max_memory'] = info[1]
            ret['memory'] = info[2]
            ret['vcpus'] = info[3]
            if info[0] == libvirt.VIR_DOMAIN_RUNNING:
                cpus = dict()
                cpus = domain.getCPUStats(1,0)[0]
                cpus['cpus'] = [i['cpu_time'] for i in  domain.getCPUStats(0,0)]
                ret['cpus'] = cpus
                
            doc = libxml2.parseDoc(domain.XMLDesc(0))
            xml_disks = doc.xpathEval('//disk')
            disks = list()
            for xml_disk in xml_disks:
                if not xml_disk.hasProp('device'):
                    continue
                if xml_disk.prop('device') == 'cdrom':
                    cdrom = dict()
                    cdrom['type'] = xml_disk.prop('type')
                    sub_ele = xml_disk.firstElementChild()
                    while sub_ele:
                        if sub_ele.name == 'source':
                            cdrom['path'] = sub_ele.prop('file') if xml_disk.prop('type') == 'file' else sub_ele.prop('dev')
                            break
                        sub_ele = sub_ele.nextElementSibling()
                    
                    ret['cdrom'] = cdrom
                else:
                    disk = dict()                                    
                    sub_ele = xml_disk.firstElementChild()
                    while sub_ele:
                        if sub_ele.name == 'source':
                            path = sub_ele.prop('file') if xml_disk.prop('type') == 'file' else sub_ele.prop('dev')
                            try:
                                vol = conn.storageVolLookupByPath(path)
                                disk['name'] = vol.name()
                                disk['size'] = vol.info()[1]
                                disk['pool'] = vol.storagePoolLookupByVolume().name()
                            except:
                                pass
                        elif sub_ele.name == 'target':
                            disk['target'] = sub_ele.prop('dev')
                        sub_ele = sub_ele.nextElementSibling()
                    disks.append(disk)
            ret['disks'] = disks
            xml_nets = doc.xpathEval("//interface")
            nets = list()
            for xml_net in xml_nets:
                if xml_net.prop("type") != 'network':
                    continue
                net = dict()
                sub_ele = xml_net.firstElementChild()
                while sub_ele:
                    if sub_ele.name == 'mac':
                        net['mac'] = sub_ele.prop('address')
                    elif sub_ele.name == 'source':
                        net['source'] = sub_ele.prop('network')
                    elif sub_ele.name == 'alias':
                        net['serial'] = sub_ele.prop('name')[-1:]
                    elif sub_ele.name == 'target':
                        try:
                            net_stat = domain.interfaceStats(sub_ele.prop('dev'))
                            stat_names = ('rx_bytes', 'rx_packets', 'rx_errs', 'rx_drop',
                                          'tx_bytes', 'tx_packets', 'tx_errs', 'tx_drop')
                            net['stat'] = dict()
                            for i in xrange(len(net_stat)):
                                net['stat'][stat_names[i]] = net_stat[i]
                        except:
                            pass
                    sub_ele =  sub_ele.nextElementSibling()
                nets.append(net)
            ret['net'] = nets
            req.write(json.dumps(ret))
            req.finish()
            conn.close()

    def purgeDomain(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        else:
            doc = libxml2.parseDoc(domain.XMLDesc(0))
            xml_disks = doc.xpathEval('//disk')
            if domain.state(0)[0] == libvirt.VIR_DOMAIN_RUNNING:
                domain.destroy()
            domain.undefine()
            for xml_disk in xml_disks:
                if not xml_disk.hasProp('device'):
                    continue
                if xml_disk.prop('device') == 'cdrom':
                    continue
                sub_ele = xml_disk.firstElementChild()
                path = None
                while sub_ele:
                    if sub_ele.name == 'source':
                        path = sub_ele.prop('file') if xml_disk.prop('type') == 'file' else sub_ele.prop('dev')
                        break
                    sub_ele = sub_ele.nextElementSibling()
                if path != None:
                    try:
                        vol = conn.storageVolLookupByPath(path)
                        vol.delete(0)
                    except:
                        pass
        req.write(json.dumps(ret))
        req.finish()

    def newNet(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        else:
            if not req.args.has_key('source'):
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_BAD_PARAMETER
            else:
                doc = libxml2.parseDoc("<interface type='network'></interface>")
                root = doc.getRootElement()
                node = libxml2.newNode('mac')
                mac = req.args['mac'][0] if req.args.has_key('mac') else self.generateMAC()
                node.newProp('address', mac)
                root.addChild(node)
                try:
                    source = req.args['source'][0]
                    conn.networkLookupByName(source)
                    node = libxml2.newNode('source')
                    node.newProp('network', source)
                    root.addChild(node)
                    flag = libvirt.VIR_DOMAIN_AFFECT_CONFIG
                    if domain.state(0)[0] == libvirt.VIR_DOMAIN_RUNNING:
                        flag |= libvirt.VIR_DOMAIN_AFFECT_LIVE
                    if domain.attachDeviceFlags(root.serialize(), flag) > 0:
#libvirt.VIR_DOMAIN_AFFECT_CURRENT) > 0:
                        raise BaseException()
                    ret['source'] = source
                    ret['mac'] = mac
                except:
                    ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
        conn.close()
        req.write(json.dumps(ret))
        req.finish()

    def newVol(self, req):
        conn = util.getConnection()
        ret = dict()
        try:
            if not req.args.has_key('source'):
                raise BaseException()
            pool = conn.storagePoolLookupByName(req.args['source'][0])
            doc = libxml2.parseDoc(pool.XMLDesc(0))
            root = doc.getRootElement()
            pool_type = root.prop('type')
            poolInfo = pool.info()
            disk_size = int(req.args['size'][0])
            if disk_size * 1024 * 1024 * 1024 > poolInfo[3]:
                raise BaseException()
            disk_prefix = None
            if req.args.has_key('prefix'):
                disk_prefix = req.args['prefix'][0]
            else:
                disk_prefix = str(uuid.uuid4())
            disk_idx = 1
            disk_name = disk_prefix + '-' + str(disk_idx)
            while True:
                try:
                    pool.storageVolLookupByName(disk_name)
                    disk_idx = disk_idx + 1
                    disk_name = disk_prefix + '-' + str(disk_idx)
                    continue
                except:
                    break
            volDoc = libxml2.parseDoc('<volume/>')
            volRoot = volDoc.getRootElement()
            node = libxml2.newNode('name')
            node.setContent(disk_name)
            volRoot.addChild(node)
            node = libxml2.newNode('capacity')
            node.newProp('unit', 'G')
            node.setContent(str(disk_size))
            volRoot.addChild(node)
            if pool_type == 'dir':
                node = libxml2.newNode('allocation')
                node.newProp('unit', 'G')
                node.setContent('0')
                volRoot.addChild(node)
            vol = pool.createXML(volRoot.serialize(), 0)
            ret['prefix'] = disk_prefix
            ret['path'] = vol.path()
            ret['size'] = vol.info()[1]
        except:
            pass
        finally:
            conn.close()
        return ret

    def attachDisk(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        else:
            try:
                diskDoc = libxml2.parseDoc("<disk/>")
                diskRoot = diskDoc.getRootElement()
                node = libxml2.newNode('driver')
                node.newProp('name', 'qemu')
                node.newProp('type', 'raw')
                diskRoot.addChild(node)
                target_path = None
                if req.args.has_key('cdrom'):
                    if not os.path.exists(req.args['cdrom'][0]):
                        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
                        raise BaseException()
                    diskRoot.newProp('type', 'file')
                    diskRoot.newProp('device', 'cdrom')
                    node = libxml2.newNode('source')
                    node.newProp('file', req.args['cdrom'][0])
                    diskRoot.addChild(node)
                    node = libxml2.newNode('target')
                    node.newProp('dev', 'hdc')
                    node.newProp('tray', 'closed')
                    diskRoot.addChild(node)
                    node = libxml2.newNode('readonly')
                    diskRoot.addChild(node)
                    target_path = 'hdc'
                elif not req.args.has_key('disk'):
                    ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
                    raise BaseException()
                else:
                    if domain.info()[0] == libvirt.VIR_DOMAIN_RUNNING:
                        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
                        raise BaseException()
                    domainDoc = libxml2.parseDoc(domain.XMLDesc(0))
                    xml_disks = domainDoc.xpathEval('//disk')
                    disk_idx = 1
                    for xml_disk in xml_disks:
                        if not xml_disk.hasProp('device'):
                            continue
                        if xml_disk.prop('device') == 'cdrom':
                            continue
                        disk_idx = disk_idx +  1
                    target_path = 'vd' + chr(ord('a') + (disk_idx - 1))
                    disk_name = req.args['disk'][0]
                    if not os.path.exists(disk_name):
                        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_BAD_PARAMETER
                        raise BaseException()
                    vol = conn.storageVolLookupByPath(disk_name)
                    ret['size'] = vol.info()[1]
                    st = os.stat(disk_name)
                    if stat.S_ISBLK(st.st_mode):
                        diskRoot.newProp('type', 'block')
                    else:
                        diskRoot.newProp('type', 'file')
                    diskRoot.newProp('device', 'disk')
                    node = libxml2.newNode('source')
                    if stat.S_ISBLK(st.st_mode):
                        node.newProp('dev', disk_name)
                    else:
                        node.newProp('file', disk_name)
                    diskRoot.addChild(node)
                    node = libxml2.newNode('target')
                    node.newProp('dev', target_path)
                    node.newProp('bus', 'virtio')
                    diskRoot.addChild(node)
                if domain.attachDeviceFlags(diskRoot.serialize(), libvirt.VIR_DOMAIN_AFFECT_CURRENT) > 0:
                    raise BaseException()
                ret['target'] = target_path
            except:
                pass
        conn.close()
        req.write(json.dumps(ret))
        req.finish()

    def resetDomain(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        elif domain.state(0)[0] == libvirt.VIR_DOMAIN_RUNNING:
            try:
                domain.reset(0)
            except:
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
            ret['state'] = domain.state(0)[0]
        else:
            ret['state'] = domain.state(0)[0]
        conn.close()
        req.write(json.dumps(ret))
        req.finish()

    def newMemory(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        elif not req.args.has_key('value'):
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_BAD_PARAMETER
        elif domain.state(0)[0] == libvirt.VIR_DOMAIN_RUNNING:
            domain.setMemory(int(req.args['value'][0]))
            ret['value'] = int(req.args['value'][0])
        else:
            ret['value'] = domain.info()[2]
        conn.close()
        req.write(json.dumps(ret))
        req.finish()


    def rebootDomain(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        elif domain.state(0)[0] == libvirt.VIR_DOMAIN_RUNNING:
            try:
                domain.reboot(0)
            except:
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
            ret['state'] = domain.state(0)[0]
        else:
            ret['state'] = domain.state(0)[0]
        conn.close()
        req.write(json.dumps(ret))
        req.finish()

    def pauseDomain(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        elif domain.state(0)[0] == libvirt.VIR_DOMAIN_RUNNING:
            try:
                domain.suspend()
            except:
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
            ret['state'] = domain.state(0)[0]
        else:
            ret['state'] = domain.state(0)[0]
        conn.close()
        req.write(json.dumps(ret))
        req.finish()

    def resumeDomain(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        elif domain.state(0)[0] == libvirt.VIR_DOMAIN_PAUSED:
            try:
                domain.resume()
            except:
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
            ret['state'] = domain.state(0)[0]
        else:
            ret['state'] = domain.state(0)[0]
        conn.close()
        req.write(json.dumps(ret))
        req.finish()
        

    def shutdownDomain(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        elif domain.state(0)[0] == libvirt.VIR_DOMAIN_RUNNING:
            try:
                domain.shutdown()
            except:
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
            ret['state'] = domain.state(0)[0]
        else:
            ret['state'] = domain.state(0)[0]
        conn.close()
        req.write(json.dumps(ret))
        req.finish()

    def destroyDomain(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        elif domain.state(0)[0] == libvirt.VIR_DOMAIN_RUNNING:
            try:
                domain.destroy()
            except:
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
            ret['state'] = domain.state(0)[0]
        else:
            ret['state'] = domain.state(0)[0]
        conn.close()
        req.write(json.dumps(ret))
        req.finish()

    def startDomain(self, req):
        conn = util.getConnection()
        domain = self.getDomain(req, conn)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        if domain == None:
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
        elif domain.state(0)[0] == libvirt.VIR_DOMAIN_SHUTOFF or domain.state(0)[0] == libvirt.VIR_DOMAIN_CRASHED:
            try:
                domain.create()
            except:
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
            ret['state'] = domain.state(0)[0]
        else:
            ret['state'] = domain.state(0)[0]
        conn.close()
        req.write(json.dumps(ret))
        req.finish()

    def createDomain(self, req):
        obj = json.load(req.content)
        xmlDef = self.parseDefinition(obj, req)
        if xmlDef != None:
            try:
                conn = util.getConnection()
                dom = conn.defineXML(xmlDef)
#                dom.create()
                res = dict()
                res['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
                res['name'] = dom.name()
                res['uuid'] = dom.UUIDString()
                res['state'] = dom.state(0)
                req.write(json.dumps(res))
                req.finish()
                return
            finally:
                conn.close()

    def parseDefinition(self, obj, req):
        name = obj.get('name')
        UUID = obj.get('uuid')
        if UUID == None or len(UUID) == 0:
            UUID = str(uuid.uuid4())
        if name == None or len(name) == 0:
            name = UUID
        memory = obj.get('memory')
        if memory == None:
            return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_BAD_PARAMETER,
                                "Memory value invalid")
        else:
            try:
                memory = int(memory)
            except:
                return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_BAD_PARAMETER,
                                    "Memory value invalid")

        maxMemory = obj.get('maxMemory')
        if maxMemory == None:
            maxMemory = memory
        else:
            try:
                maxMemory = int(maxMemory)
            except:
                return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_BAD_PARAMETER,
                                    "Max memory value invalid")

        vcpus = obj.get('vcpu')
        if vcpus == None:
            vcpus = 1
        else:
            try:
                vcpus = int(vcpus)
            except:
                return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_BAD_PARAMETER,
                                    "vcpu value invalid")

        disks = obj.get('disks')
        if disks != None:
            if not isinstance(disks, list):
                return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_BAD_PARAMETER,
                                    "Invalid disk parameter")
        cdrom = obj.get('cdrom')
        interfaces = obj.get('interfaces')
        if interfaces != None:
            if not isinstance(interfaces, list):
                return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_BAD_PARAMETER,
                                    "Invalid interface parameter")
        try:
            conn = util.getConnection()
            domain = None
            try:
                domain = conn.lookupByName(str(name))
            except:
                pass
            if domain != None:
                return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_NAME_DUPLICATED, "Domain name dulicated")
            nodeInfo = conn.getInfo()
            if vcpus > nodeInfo[2]:
                vcpus = nodeInfo[2]
            if memory > nodeInfo[1] * 1024:
                return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_INADEQUATE_MEMORY, "Not enough memory")

            doc = libxml2.parseFile('/etc/cloudyfox/template.xml')
            root = doc.getRootElement()
            node = libxml2.newNode('name')
            node.setContent(name)
            root.addChild(node)
            node = libxml2.newNode("uuid")
            node.setContent(UUID)
            root.addChild(node)
            node = libxml2.newNode('memory')
            node.newProp("unit", "KiB")
            node.setContent(str(maxMemory))
            root.addChild(node)
            node = libxml2.newNode("currentMemory")
            node.newProp("unit", "KiB")
            node.setContent(str(memory))
            root.addChild(node)
            node = libxml2.newNode("vcpu")
            node.newProp("placement", "static")
            node.setContent(str(vcpus))
            root.addChild(node)
            result = doc.xpathEval("//devices")
            devices = result[0]
            if disks != None:
                diskIdx = 1
                for disk in disks:
                    if not os.path.exists(disk):
                        return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_NO_DISK, "Unable to find disk")
                    diskNode = libxml2.newNode('disk')
                    st = os.stat(disk)
                    diskType = 'block' if stat.S_ISBLK(st.st_mode) else 'file'
                    diskNode.newProp('type', diskType)
                    diskNode.newProp('device', 'disk')
                    node = libxml2.newNode('source')
                    if diskType == 'block':
                        node.newProp('dev', disk)
                    else:
                        node.newProp('file', disk)
                    diskNode.addChild(node)
                    node = libxml2.newNode('target')
                    node.newProp('bus', 'virtio')
                    node.newProp('dev', 'vd' + chr(ord('a') + (diskIdx - 1)))
                    diskNode.addChild(node)
                    devices.addChild(diskNode)
                    diskIdx = diskIdx + 1

            cdromNode = libxml2.newNode('disk')
            cdromNode.newProp('type', 'file')
            cdromNode.newProp('device', 'cdrom')
            if cdrom != None and os.path.isfile(cdrom):
                node = libxml2.newNode('source')
                node.newProp('file', cdrom)
                cdromNode.addChild(node)
            node = libxml2.newNode('target')
            node.newProp('dev', 'hdc')
            node.newProp('bus', 'ide')
            cdromNode.addChild(node)
            devices.addChild(cdromNode)

            if interfaces != None:
                networks = conn.listNetworks()
                if len(networks) == 0:
                    return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_INTERFACE_ERROR,
                                        "No network defined")
                for interface in interfaces:
                    if not isinstance(interface, dict) or not interface.has_key('source'):
                        return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_INTERFACE_ERROR,
                                            "No eth defined")
                    netName = interface['source']
                    if not netName in networks:
                        return self.respond(req, self.__class__.DOMAIN_ERROR_CODE_INTERFACE_ERROR,
                                       "No such eth")
                    mac = interface.get('mac')
                    if mac == None:
                        mac = self.generateMAC()
                    netNode = libxml2.newNode('interface')
                    netNode.newProp('type', 'network')
                    node = libxml2.newNode('source')
                    node.newProp('network', netName)
                    netNode.addChild(node)
                    node = libxml2.newNode('mac')
                    node.newProp('address', mac)
                    netNode.addChild(node)
                    node = libxml2.newNode('model')
                    node.newProp('type', 'virtio')
                    netNode.addChild(node)
                    devices.addChild(netNode)
            xmlData = root.serialize()
            doc.freeDoc()
            return xmlData
        finally:
            conn.close()

    def deployDisk(self, src, to, swap_size, obj):
        from_file = open(src, 'rb')
        to_file = open(to, 'wb')
        while True:
            data = from_file.read(1024)
            if len(data) == 0:
                break
            to_file.write(data)
        from_file.close()
        to_file.close()
#        gfs = guestfs.GuestFS()
#        gfs.add_drive_opts(src, readonly=1)
#        gfs.add_drive_opts(to, readonly=0)
#        gfs.launch()
#        devices = gfs.list_devices()
#        gfs.copy_device_to_device(devices[0], devices[1])
#        gfs.close()
        gfs = guestfs.GuestFS()
        gfs.add_drive_opts(to, readonly=0)
        gfs.launch()
        devices = gfs.list_devices()
        parts = gfs.part_list(devices[0])
        gfs.part_del(devices[0], parts[1]['part_num'])
        gfs.part_add(devices[0], 'p', parts[1]['part_start'] / 512, -swap_size * 2)
        parts = gfs.part_list(devices[0])
        gfs.part_add(devices[0], 'p', parts[1]['part_end'] / 512 + 1, -1)
        partitions = gfs.list_partitions()
        gfs.mkswap(partitions[2])
        gfs.e2fsck_f(partitions[1])
        gfs.resize2fs(partitions[1])
        blkid = gfs.blkid(partitions[2])
        UUID = None
        for x in blkid:
            if x[0] == 'UUID':
                UUID = x[1]
                break
        gfs.mkmountpoint('/tmp')
        gfs.mount(partitions[1], '/tmp')
        if UUID != None:
            gfs.write_append('/tmp/etc/fstab',
                             "\nUUID=" + UUID + "\tswap\tswap\tdefaults\t0\t0\n")
        if obj.has_key('hostname'):
            gfs.write('/tmp/etc/hostname', obj.get('hostname'))
        interfaces = obj.get('interfaces')
        if interfaces != None and isinstance(interfaces, list):
            idx = 0
            content = ""
            for interface in interfaces:
                content += "auto eth" + str(idx) + "\niface eth" + str(idx) + " inet static\n"
                if interface.has_key('address'):
                    content += "\taddress " + interface['address'] + "\n"
                if interface.has_key('netmask'):
                    content += "\tnetmask " + interface['netmask'] + "\n"
                if interface.has_key('gateway'):
                    content += "\tgateway " + interface['gateway'] + "\n\n\n"
                idx = idx + 1
            gfs.write_append('/tmp/etc/network/interfaces', content)
        gfs.umount('/tmp')
        gfs.close()

    def copyDebianTemplate(self, req):
        obj = json.load(req.content)
        ret = dict()
        ret['code'] = self.__class__.DOMAIN_ERROR_CODE_SYS_ERROR
        try:
            template = obj['template']
            to = obj['disk']
            swap = obj['swap']
            swap_size = 0
            if swap != None:
                swap_size = int(swap)
            if template == None or to == None or swap_size <= 0:
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_BAD_PARAMETER
                ret['desc'] = 'Invalid parameter'
                raise BaseException()
            else:
                template = config.SHARED_POOL_PATH + "/templates/" + template
            if not os.path.exists(template) or not os.path.exists(to):
                ret['code'] = self.__class__.DOMAIN_ERROR_CODE_NOT_FOUND
                ret['desc'] = "Device invalid"
                raise BaseException()
            from_file = open(template, 'rb')
            try:
                to_file = open(to, 'r+b')
            except:
                to_file = open(to, 'wb')
            while True:
                data = from_file.read(1024)
                if len(data) == 0:
                    break
                to_file.write(data)
            from_file.close()
            to_file.close()
            gfs = guestfs.GuestFS()
            gfs.add_drive_opts(to, readonly=0)
            gfs.launch()
            devices = gfs.list_devices()
            parts = gfs.part_list(devices[0])
            gfs.part_del(devices[0], parts[1]['part_num'])
            gfs.part_add(devices[0], 'p', parts[1]['part_start'] / 512, -swap_size * 2)
            parts = gfs.part_list(devices[0])
            gfs.part_add(devices[0], 'p', parts[1]['part_end'] / 512 + 1, -1)
            partitions = gfs.list_partitions()
            gfs.mkswap(partitions[2])
            gfs.e2fsck_f(partitions[1])
            gfs.resize2fs(partitions[1])
            blkid = gfs.blkid(partitions[2])
            UUID = None
            for x in blkid:
                if x[0] == 'UUID':
                    UUID = x[1]
                    break
            gfs.mkmountpoint('/tmp')
            gfs.mount(partitions[1], '/tmp')
            if UUID != None:
                gfs.write_append('/tmp/etc/fstab',
                                 "\nUUID=" + UUID + "\tswap\tswap\tdefaults\t0\t0\n")
            if obj.has_key('hostname'):
                gfs.write('/tmp/etc/hostname', obj['hostname'])
            interfaces = obj.get('interfaces')
            if interfaces != None and isinstance(interfaces, list):
                idx = 0
                content = ""
                for interface in interfaces:
                    if not interface.has_key('address'):
                        idx = idx + 1
                        continue
                    content += "auto eth" + str(idx) + "\niface eth" + str(idx) + " inet static\n"
                    content += "\taddress " + interface['address'] + "\n"
                    if interface.has_key('netmask'):
                        content += "\tnetmask " + interface['netmask'] + "\n"
                    if interface.has_key('gateway'):
                        content += "\tgateway " + interface['gateway'] + "\n\n\n"
                    idx = idx + 1
                if len(content) > 0:
                    gfs.write_append('/tmp/etc/network/interfaces', content)
            gfs.umount('/tmp')
            gfs.close()
            ret['code'] = self.__class__.DOMAIN_ERROR_CODE_OK
        except:
            raise
        req.write(json.dumps(ret))
        req.finish()

    def respond(self, req, code, desc = ''):
        obj = {"code" : code, "desc" : desc}
        req.write(json.dumps(obj))
        req.finish()
        return None

    def generateMAC(self):
        mac = [0x00, 0x16, 0x3e, random.randint(0x00, 0x7f),
               random.randint(0x00, 0xff), random.randint(0x00, 0xff)]
        return ':'.join(map(lambda x:"%02x" % x, mac))
