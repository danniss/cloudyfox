import logging

import libvirt

import fcntl
import array
import struct
import socket
import platform

def getConnection(type = 'RW'):
    try:
        return libvirt.openReadOnly("qemu:///system") if type == 'R' else libvirt.open("qemu:///system")
    except:
        logging.error('Unable to open connection to kvm')
        raise


def listInterfaces():
    SIOCGIFCONF = 0x8912
    MAXBYTES = 8096
    arch = platform.architecture()[0]
    var1 = -1
    var2 = -1
    if arch == '32bit':
        var1 = 32
        var2 = 32
    elif arch == '64bit':
        var1 = 16
        var2 = 40
    else:
        raise OSError("Unknown architecture: %s" % arch)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', '\0' * MAXBYTES)
    outbytes = struct.unpack('iL', fcntl.ioctl(sock.fileno(), SIOCGIFCONF,
                                               struct.pack('iL', MAXBYTES,
                                                           names.buffer_info()[0])))[0]
    namestr = names.tostring()
    return [(namestr[i:i+var1].split('\0', 1)[0],
             socket.inet_ntoa(namestr[i+20 : i+24])) for i in xrange(0, outbytes, var2)]
