import ConfigParser, os
HTTP_SERVER_ADDRESS = ""
HTTP_PORT = 8000
VNC_SERVER_ADDRESS = ""
VNC_SERVER_PORT = 9001
SHARED_POOL_PATH = "/spool"

CONFIG_FILE_NAME = "/etc/cloudyfox/cloudyfox.conf"

if os.path.isfile(CONFIG_FILE_NAME):
    cfg = ConfigParser.ConfigParser()
    cfg.read(CONFIG_FILE_NAME)
    if cfg.has_option('http', 'address'):
        HTTP_SERVER_ADDRESS = cfg.get('http', 'address')
    if cfg.has_option('http', 'port'):
        HTTP_PORT = cfg.getint('http', 'port')
    if cfg.has_option('vnc', 'address'):
        VNC_SERVER_ADDRESS = cfg.get('vnc', 'address')
    if cfg.has_option('vnc', 'port'):
        VNC_SERVER_PORT = cfg.getint('vnc', 'port')
    if cfg.has_option('system', 'spool'):
        SHARED_POOL_PATH = cfg.get('system', 'spool')
