# -*- coding: utf-8 -*-

from urllib import urlopen

from StringIO import StringIO
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core import Logging
from Utils import string_trim
from ImportedModel import *

logger = Logging.get_logger('hicloud.vsched.Model')
VSCHED_USERID = 0  # FIXME: should use caller's user_id, not scheduler's


def get_Session(connect_string):
    engine = create_engine(connect_string, echo=False)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_ScopedSession(connect_string):
    # return scoped_session(get_Session(connect_string))
    return get_Session(connect_string)


def get_session(connect_string):
    return get_Session(connect_string)()


MapperClasses = []


def __generic_repr(self):
    # try:
    cls = type(self)
    attrs = cls.__dict__.items()
    is_column = lambda x: x[1] == InstrumentedAttribute
    to_key_value = lambda x: (x[0], getattr(self, x[0]))
    key_val = map(to_key_value, filter(is_column, attrs))
    to_kv_str = lambda x: '%s:%s' % (x[0], string_trim(str(x[1])))
    str_val = ', '.join(map(to_kv_str, key_val))
    return '<%s (%s)>' % (type(self).__name__, str_val)
    # except Exception, e:
    #    logger.error('bad type %s' % type(self))
    #    logger.error(e)
    #    return '<%s instance with hash %x >' % (type(self).__name__, hash(self))


def register_generic_repr():
    for attrname, attr in globals().items():
        try:
            if issubclass(attr, Base) and attr != Base:
                MapperClasses.append(attr)
                logger.debug('set %s\'s __repr__ to generic_repr', attrname)
                attr.__repr__ = __generic_repr
        except:
            pass


from xml.dom import minidom
from xml.parsers.expat import ExpatError


class XmlImportError(Exception):
    pass


class XmlReader:
    # 获取一个xml元素
    def get_element_by(self, element, tagname):
        nodes = element.getElementsByTagName(tagname)
        if len(nodes) == 0:
            raise XmlImportError, 'bad format, no tag %s' % tagname
        elif len(nodes) > 1:
            logger.warning('possibly format error, more than one tag %s found', tagname)
        return nodes[0]

    # 获取xml元素的值
    def get_string_value(self, element, tagname):
        n = self.get_element_by(element, tagname)
        return n.firstChild.nodeValue.strip()

    # 转换以字节为单位
    def get_size_value(self, element, tagname):
        strval = self.get_string_value(element, tagname)
        if not strval or not len(strval):
            raise XmlImportError, 'bad size format, null string'

        # 获取最后一个字符的大写
        char = strval[-1].upper()
        if char == 'B':
            # 字节单位
            unit = 1
        elif char == 'K':
            # 千字节单位
            unit = 1024
        elif char == 'M':
            # 1024的平方值，兆字节单位
            unit = pow(1024, 2)
        elif char == 'G':
            # G字节单位
            unit = pow(1024, 3)
        elif char == 'T':
            # T字节单位
            unit = pow(1024, 4)
        else:
            raise XmlImportError, 'bad size format, not size unit (B/K/M/G/T) in str: %s' % strval

        try:
            return int(strval[:-1]) * unit
        except:
            raise XmlImportError, 'bad size format: %s' % strval

    # 获取xml元素的整型值
    def get_int_value(self, element, tagname):
        strval = self.get_string_value(element, tagname)
        try:
            return int(strval)
        except:
            raise XmlImportError, 'bad format, expected int but got %s' % strval

    # 获取一个xml元素的子节点名称
    def get_child_tagnames(self, element):
        filter_tagnode = lambda x: x.nodeType == x.ELEMENT_NODE
        get_tagname = lambda x: x.tagName
        return map(get_tagname, filter(filter_tagnode, element.childNodes))

    # 获取一个xml元素的capabilities属性值
    def get_capabilities(self, element, captag='Capabilities'):
        n = self.get_element_by(element, captag)
        return ','.join(self.get_child_tagnames(n))

    def get_xml(self, element, tagname):
        n = self.get_element_by(element, tagname)
        return n.toxml()

    def get_multi_xml(self, element, tagname):
        nodes = element.getElementsByTagName(tagname)
        if len(nodes) == 0:
            raise XmlImportError, 'bad format, no tag %s' % tagname
        toxml = lambda x: x.toxml()
        return '\n'.join(map(toxml, nodes))


class XmlImporter(XmlReader):
    # 导入模板
    def __import_vnode(self, typ, element):
        vnode = typ()
        vnode.settings = element.toxml()
        vtemp_url = self.get_string_value(element, 'vTemplateRef')
        vnode.vm_temp_id = self.__import_vtemplate_url(vtemp_url)
        self.s.save(vnode)
        logger.debug('saving %s', vnode)
        return vnode

    # 返回模板中uuid对应VmTemp的主键值
    def __import_vtemplate_url(self, url):
        logger.debug('download vTeamplate from %s', url)
        try:
            xml = urlopen(url).read()
            doc = minidom.parseString(xml.encode("utf-8")).documentElement
            xml_type = doc.nodeName
            if xml_type != 'vTemplate':
                raise XmlImportError, 'bad vTemplate format for %s' % url
        except IOError, e:
            logger.exception(e)
            raise XmlImportError, 'error importing referenced vTemplate from %s: %s' % (url, e.message)
        except ExpatError, e:
            logger.exception(e)
            raise XmlImportError, 'bad vTemplate format for %s: %s' % (url, e.message)

        uuid = doc.getAttribute('uuid')
        try:  # find existing boj with same uuid, return its id
            logger.debug('finding vTemplate %s in database', uuid)
            id = self.s.query(VmTemp).filter(VmTemp.uuid == uuid).one().id
            logger.debug('found vTemplate %s in database: id=%d', uuid, id)
            return id
        except:  # not found
            logger.debug('not found vTemplate %s in database, try importing', uuid)

        # 对应的记录不存在，根据模板创建一条新纪录
        obj = VmTemp()
        obj.uuid = uuid
        self.__import_vtemplate_xml(obj, doc)
        self.s.flush()
        return obj.id

    # 根据模板信息初始化VmTemp表记录
    def __import_vtemplate_xml(self, vtemp, element):
        vtemp.name = self.get_string_value(element, 'Name')
        vtemp.description = self.get_string_value(element, 'Description')
        vtemp.repository = self.get_string_value(element, 'Repository')
        vtemp.capabilities = self.get_capabilities(element)

        os = self.get_element_by(element, 'OS')
        vtemp.os_type = self.get_string_value(os, 'Type')
        vtemp.distribution = self.get_string_value(os, 'Distribution')
        vtemp.kernel = self.get_string_value(os, 'Kernel')

        deployinfo = self.get_element_by(element, 'DeployInfo')
        vtemp.deploy_method = self.get_string_value(deployinfo, 'Method')
        vtemp.deploy_url = self.get_string_value(deployinfo, 'URL')
        vtemp.prefer_settings = self.get_xml(deployinfo, 'PreferedSettings')

        self.s.save(vtemp)
        logger.debug('saving %s', vtemp)

    # 验证uuid的唯一性，不存在是创建对应字段
    def __dup_check_create(self, xml_type, uuid):
        if len(uuid) == 0:
            raise XmlImportError, 'no uuid attribute'

        tables = {'vTemplate': VmTemp}
        table = tables[xml_type]  # xml_type checked before

        if self.s.query(table).filter(table.uuid == uuid).count() > 0:
            raise XmlImportError, 'record exists with the same uuid(%s)' % uuid

        obj = table()
        obj.uuid = uuid
        return obj

    def do_import(self, xml, session):
        self.s = session
        try:
            doc = minidom.parseString(xml.encode("utf-8")).documentElement
            xml_type = doc.nodeName
            name = '_XmlImporter__import_%s_xml' % xml_type.lower()
            # 获取初始化对应表的方法
            do_import_xml = getattr(self, name)
        except ExpatError, e:
            raise XmlImportError, 'error in xml: %s' % e.message
        except AttributeError:
            raise XmlImportError, 'bad xml type %s' % xml_type

        # 创建uuid对象
        uuid = doc.getAttribute('uuid')
        obj = self.__dup_check_create(xml_type, uuid)

        try:
            self.s.begin()
            # 根据模板信息初始化对应表记录
            do_import_xml(obj, doc)
            self.s.commit()
            return '%s@%d' % (xml_type, obj.id)
        except XmlImportError, e:
            self.s.rollback()
            # self.s.close()
            # remove_template(obj, self.s, remove_instances = False)
            raise


class XmlExportError(Exception):
    pass


# 构造xml模板
class XmlWriter:
    def __init__(self, iob):
        # io对象
        self.iob = iob
        # xml文件缩进，默认四个空格
        self.indent = 0

    # 添加缩进
    def print_line(self, line):
        space = '    ' * self.indent
        self.iob.write(space + line.strip())

    # 头部信息
    def print_xml_version(self):
        self.print_line('<?xml version="1.0"?>')

    # 添加xml格式
    def print_tag(self, tagname, value):
        if not value:
            self.print_line('<%s/>' % tagname)
        else:
            self.print_line('<%s>%s</%s>' % (tagname, value, tagname))

    # 转换为字符串
    def print_int_tag(self, tagname, value):
        self.print_tag(tagname, str(value))

    # 添加存储简写形式
    def print_size_tag(self, tagname, value):
        units = ['B', 'K', 'M', 'G', 'T']
        unit_idx = 0
        while value % 1024 == 0:
            value /= 1024
            unit_idx += 1
        self.print_tag(tagname, '%d%s' % (value, units[unit_idx]))

    # 添加带有属性值的xml节点前部
    def print_tag_open(self, tagname, attributes=None):
        if attributes:
            kv_fmt = lambda x: '%s="%s"' % (x[0], x[1])
            strattr = ' ' + ' '.join(map(kv_fmt, attributes.items()))
        else:
            strattr = ''
        self.print_line('<%s%s>' % (tagname, strattr))
        self.indent += 1

    # 添加xml节点尾部
    def print_tag_close(self, tagname):
        self.indent -= 1
        self.print_line('</%s>' % tagname)

    # 添加capabilities值
    def print_capabilities(self, capabilities):
        if not capabilities:
            return
        caps = capabilities.split(',')
        if len(caps) == 1 and caps[0] == '':
            self.print_line('<Capabilities/>')
            return

        self.print_tag_open('Capabilities')
        for cap in caps:
            self.print_tag(cap, None)
        self.print_tag_close('Capabilities')

    # 使用递归生成xml模板
    def print_dom_tree(self, root):
        filter_node = lambda x: x.nodeType == x.ELEMENT_NODE
        for node in filter(filter_node, root.childNodes):
            if len(node.childNodes) == 1 and node.firstChild.nodeType == node.TEXT_NODE:
                self.print_tag(node.tagName, node.firstChild.nodeValue.strip())
            else:
                self.print_tag_open(node.tagName, node._get_attributes())
                self.print_dom_tree(node)
                self.print_tag_close(node.tagName)

    # 添加根目录
    def print_xml(self, xml):
        if not xml:
            return
        xml = '<dummy>%s</dummy>' % xml
        try:
            doc = minidom.parseString(xml.encode("utf-8"))
        except:
            logger.errror('bad xml format: %s', trip(xml))
        self.print_dom_tree(doc.documentElement)
        # for l in xml.splitlines():
        #    self.print_line(l)


class XmlExporter:

    def __export_vlab_id(self, id):
        vtemp = self.s.query(VlabTemp).get(id)
        self.__export_vlab_obj(vtemp)

    # 写入VlabTemp数据
    def __export_vlab_obj(self, vtemp):
        id = vtemp.id
        self.xmlwriter.print_xml_version()
        self.xmlwriter.print_tag_open('vLab')
        self.xmlwriter.print_tag('Id', vtemp.id)
        self.xmlwriter.print_tag('Name', vtemp.name)
        self.xmlwriter.print_tag('Description', vtemp.description)
        self.xmlwriter.print_tag('User_id', vtemp.user_id)
        self.xmlwriter.print_tag('Uuid', vtemp.uuid)
        for vnode in self.s.query(VlabTempsVmTemp).filter(VlabTempsVmTemp.vlab_temp_id == id):
            self.xmlwriter.print_xml(vnode.settings)
        self.xmlwriter.print_xml(vtemp.vswitch_config)
        self.xmlwriter.print_tag_close('vLab')

    # 写入VlabInstance信息
    def __export_vli_obj(self, vli):
        id = vli.id
        self.xmlwriter.print_xml_version()
        self.xmlwriter.print_tag_open('vli')
        self.xmlwriter.print_tag('Id', vli.id)
        self.xmlwriter.print_tag('Vlab_temp_id', vli.vlab_temp_id)
        self.xmlwriter.print_tag('Created_at', vli.created_at)
        self.xmlwriter.print_tag('User_id', vli.user_id)
        self.xmlwriter.print_tag('Status', vli.status)
        self.xmlwriter.print_tag('Uuid', vli.uuid)
        self.xmlwriter.print_tag('Name', vli.name)
        self.xmlwriter.print_tag('Description', vli.description)
        self.xmlwriter.print_tag('Deployment', vli.deployment)
        self.xmlwriter.print_tag_close('vli')

    # 写入VirtualClusterInstance信息
    def __export_vci_obj(self, vci):
        id = vci.id
        self.xmlwriter.print_xml_version()
        self.xmlwriter.print_tag_open('vci')
        self.xmlwriter.print_tag('Id', vci.id)
        self.xmlwriter.print_tag('Vcluster_temp_id', vci.vcluster_temp_id)
        self.xmlwriter.print_tag('Created_at', vci.created_at)
        self.xmlwriter.print_tag('User_id', vci.user_id)
        self.xmlwriter.print_tag('Status', vci.status)
        self.xmlwriter.print_tag('Uuid', vci.uuid)
        self.xmlwriter.print_tag('Name', vci.name)
        self.xmlwriter.print_tag('Description', vci.description)
        self.xmlwriter.print_tag('Deployment', vci.deployment)
        self.xmlwriter.print_tag('Worknode_count', vci.worknode_count)
        self.xmlwriter.print_tag_close('vci')

    def __export_vcluster_id(self, id):
        vtemp = self.s.query(VclusterTemp).get(id)
        self.__export_vcluster_obj(vtemp)

    # 写入VclusterTemp模板信息
    def __export_vcluster_obj(self, vtemp):
        id = vtemp.id
        self.xmlwriter.print_xml_version()
        self.xmlwriter.print_tag_open('vCluster')
        self.xmlwriter.print_tag('Name', vtemp.name)
        self.xmlwriter.print_tag('Description', vtemp.description)
        self.xmlwriter.print_capabilities(vtemp.capabilities)

        self.xmlwriter.print_tag_open('HeadInfo')
        try:
            vnode = self.s.query(VclusterTempsVmTemp).filter(VclusterTempsVmTemp.vcluster_temp_id == id).filter(
                VclusterTempsVmTemp.ref_type == 'headnode').one()
            self.xmlwriter.print_xml(vnode.settings)
        except:
            logger.error('no head node info')
        self.xmlwriter.print_tag_close('HeadInfo')

        self.xmlwriter.print_tag_open('WorkInfo')
        try:
            vnode = self.s.query(VclusterTempsVmTemp).filter(VclusterTempsVmTemp.vcluster_temp_id == id).filter(
                VclusterTempsVmTemp.ref_type == 'worknode').one()
            self.xmlwriter.print_int_tag('Count', vnode.count)
            self.xmlwriter.print_xml(vnode.settings)
        except:
            logger.error('no work node info')
        self.xmlwriter.print_tag_close('WorkInfo')

        self.xmlwriter.print_tag_open('SharedStorage')
        self.xmlwriter.print_size_tag('Size', vtemp.sharedstorage_size)
        self.xmlwriter.print_tag('LocalMountDir', vtemp.sharedstorage_local)
        self.xmlwriter.print_tag_close('SharedStorage')

        self.xmlwriter.print_tag_close('vCluster')

    def __export_vtemplate_id(self, id):
        vtemp = self.s.query(VmTemp).get(id)
        self.__export_vtemplate_obj(vtemp)

    # 写入VmTemp信息
    def __export_vtemplate_obj(self, vtemp):
        id = vtemp.id
        self.xmlwriter.print_xml_version()
        self.xmlwriter.print_tag_open('vTemplate')
        self.xmlwriter.print_tag('Name', vtemp.name)
        self.xmlwriter.print_tag('Description', vtemp.description)
        self.xmlwriter.print_capabilities(vtemp.capabilities)
        self.xmlwriter.print_tag_open('OS')
        self.xmlwriter.print_tag('Type', vtemp.os_type)
        self.xmlwriter.print_tag('Distribution', vtemp.distribution)
        self.xmlwriter.print_tag('Kernel', vtemp.kernel)
        self.xmlwriter.print_tag_close('OS')
        self.xmlwriter.print_tag('Repository', vtemp.repository)
        self.xmlwriter.print_tag_open('DeployInfo')
        self.xmlwriter.print_tag('URL', vtemp.deploy_url)
        self.xmlwriter.print_tag('Method', vtemp.deploy_method)
        self.xmlwriter.print_xml(vtemp.prefer_settings)
        self.xmlwriter.print_tag_close('DeployInfo')
        self.xmlwriter.print_tag_close('vTemplate')

    def generate_vnode(self, vmt):
        iob = StringIO()
        xmlwriter = XmlWriter(iob)
        xmlwriter.print_xml_version()
        xmlwriter.print_tag_open('vNode')
        xmlwriter.print_tag('vTemplateRef', vmt.url)
        xmlwriter.print_tag('Hostname', 'mu')
        xmldoc = minidom.parseString(vmt.prefer_settings.encode("utf-8"))
        mem = xmldoc.getElementsByTagName("Mem")[0].firstChild.data
        disksize = xmldoc.getElementsByTagName("DiskSize")[0].firstChild.data
        xmlwriter.print_tag('Mem', mem)
        xmlwriter.print_tag('DiskSize', disksize)
        xmlwriter.print_tag_close('vNode')
        return iob.getvalue()

    # 通过对象判断导出数据的对应方法
    def do_export(self, obj, session):
        self.s = session
        iob = StringIO()
        self.xmlwriter = XmlWriter(iob)

        functions = {
            VlabTemp: self.__export_vlab_obj,
            VclusterTemp: self.__export_vcluster_obj,
            VmTemp: self.__export_vtemplate_obj,
            VlabInstance: self.__export_vli_obj,
            VirtualClusterInstance: self.__export_vci_obj,
        }

        try:
            do_export_obj = functions[type(obj)]
        except KeyError:
            raise XmlExportError, 'bad object type %s' % type(obj)

        do_export_obj(obj)
        return iob.getvalue()

    # 获取导出模板的对应方法
    def do_export_id(self, key, session):
        self.s = session
        iob = StringIO()
        self.xmlwriter = XmlWriter(iob)

        xml_type, strid = key.split('@')
        try:
            id = int(strid)
        except:
            raise XmlExportError, 'bad id value %s' % strid

        try:
            name = '_XmlExporter__export_%s_id' % xml_type.lower()
            do_export_xml = getattr(self, name)
        except:
            raise XmlExportError, 'bad xml document type %s' % xml_type

        do_export_xml(id)
        return iob.getvalue()


class ObjectRemoverError(Exception):
    pass


class ObjectRemover:
    def __remove(self, obj):
        logger.debug('deleting %s', obj)
        self.s.delete(obj)

    def __remove_vnode(self, obj):
        self.__remove(obj)

    def __remove_vm_instance(self, obj):
        self.__remove(obj)

    def __remove_vm_temp(self, obj):
        if self.remove_instances:
            for i in self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.vm_temp_id == obj.id):
                self.__remove_vm_instance(i)
        self.__remove(obj)

    def do_remove_template(self, obj, session, remove_instances=True):
        if not obj or not obj.id:
            return

        table = type(obj)
        obj = session.query(table).get(obj.id)
        if not obj:
            return

        functions = {
            VmTemp: self.__remove_vm_temp
        }
        try:
            do_remove_obj = functions[table]
        except KeyError:
            raise ObjectRemoverError, 'bad object type %s' % table

        self.s = session
        self.remove_instances = remove_instances
        do_remove_obj(obj)
        session.flush()

    def do_remove_instance(self, obj, session):
        if not obj or not obj.id:
            return

        table = type(obj)
        obj = session.query(table).get(obj.id)
        if not obj:
            return

        functions = {
            VirtualMachineInstance: self.__remove_vm_instance,
        }
        try:
            do_remove_obj = functions[table]
        except KeyError:
            raise ObjectRemoverError, 'bad object type %s' % table

        self.s = session
        do_remove_obj(obj)
        session.flush()


import_xml = XmlImporter().do_import
export_xml_id = XmlExporter().do_export_id
export_xml = XmlExporter().do_export
remove_template = ObjectRemover().do_remove_template
remove_instance = ObjectRemover().do_remove_instance
generate_vnode = XmlExporter().generate_vnode
