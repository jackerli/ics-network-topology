# author Jiang ChangHui
# time 2008/11/27
# for Domain of libvirt
class DomainXml:
    def __init__(self, type, name, uuid):
        self.type = type
        self.name = name
        self.uuid = uuid
        self.memory = -1
        self.currentMemory = -1
        self.vcup = -1
        self.on_poweroff = ""
        self.on_reboot = ""
        self.on_crash = ""
        self.time = ""
        self.memory = -1
        self.currentMemory = -1
        self.vcup = -1
        self.OStype = 0
        self.devices = []
        self.BIOSLoader = {}
        self.DirectKernelBoot = {}
        self.HostBootLoader = {}
        self.features = 0
        self.bootScripts = []
        self.shutdownScripts = []

    def setShutdownScripts(self, scripts):
        self.shutdownScripts = scripts

    def shutdownScriptsToXml(self):
        xml = "<shutdownScript>\n"
        for script in self.shutdownScripts:
            xml += "\t" + script + "\n"
        xml += "</shutdownScript>"
        return xml

    def setBootScripts(self, bootScripts):
        self.bootScripts = bootScripts

    def bootScriptsToXml(self):
        xml = "<bootScript>\n"
        for script in self.bootScripts:
            xml += "\t" + script + "\n"
        xml += "</bootScript>"
        return xml

    def setBIOSBootloader(self, type, loader, dev, arch, machine):
        self.BIOSLoader['type'] = type
        self.BIOSLoader['loader'] = loader
        self.BIOSLoader['dev'] = dev
        self.BIOSLoader['arch'] = arch
        self.BIOSLoader['machine'] = machine
        self.OStype = 1

    def BIOSBootloaderToXml(self):
        try:
            xml = ""
            xml = "<os>"
            xml += "\n\t<type "
            if self.BIOSLoader['arch'] != "":
                xml += "arch='" + self.BIOSLoader['arch'] + "' "
            if self.BIOSLoader['machine'] != "":
                xml += "machine='" + self.BIOSLoader['machine'] + "' "
            xml += ">" + self.BIOSLoader['type'] + "</type>"
            if self.BIOSLoader['loader'] != "":
                xml += "\n\t<loader>" + self.BIOSLoader['loader'] + "</loader>"
            xml += "\n\t<boot dev='" + self.BIOSLoader['dev'] + "'/>"

            xml += "\n\t<boot dev='cdrom'/>"
            xml += "\n\t<bootmenu enable='yes'/>"

            xml += "\n</os>"
            return xml
        except KeyError:
            return ""

    def setHostBootloader(self, bootloader, bootloader_args=""):
        self.HostBootLoader['bootloader'] = bootloader
        self.HostBootLoader['bootloader_args'] = bootloader_args
        self.OStype = 2

    def setFeatures(self):
        self.features = 1

    def hostBootloaderToXml(self):
        try:
            xml = ""
            xml += "<bootloader>" + self.HostBootLoader['bootloader'] + "</bootloader>"
            xml += "\n<bootloader_args>" + self.HostBootLoader['bootloader_args'] + "</bootloader_args>"
            return xml
        except KeyError:
            return ""

    def setDirectKernelBoot(self, type, loader, kernel, initrd, cmdline):
        self.DirectKernelBoot['type'] = type
        self.DirectKernelBoot['loader'] = loader
        self.DirectKernelBoot['kernel'] = kernel
        self.DirectKernelBoot['initrd'] = initrd
        self.DirectKernelBoot['cmdline'] = cmdline
        self.OStype = 3

    def directKernelBootToXml(self):
        try:
            xml = ""
            xml = "<os>"
            xml += "\n\t<type>" + self.DirectKernelBoot['type'] + "</type>"
            xml += "\n\t<loader>" + self.DirectKernelBoot['loader'] + "</loader>"
            xml += "\n\t<kernel>" + self.DirectKernelBoot['kernel'] + "</kernel>"
            xml += "\n\t<initrd>" + self.DirectKernelBoot['initrd'] + "</initrd>"
            xml += "\n\t<cmdline>" + self.DirectKernelBoot['cmdline'] + "</cmdline>"
            xml += "\n</os>"
            return xml
        except KeyError:
            return ""

    def setBasicResources(self, memory, currentMemory, vcup):
        self.memory = memory
        self.currentMemory = currentMemory
        self.vcup = vcup

    def basicResourcesToXml(self):
        xml = ""
        if self.memory != -1:
            xml += "<memory>" + self.memory + "</memory>\n"
        if self.currentMemory != -1:
            xml += "<currentMemory>" + self.currentMemory + "</currentMemory>\n"
        if self.vcup != -1:
            xml += "<vcpu>" + self.vcup + "</vcpu>"
        return xml

    def setLifecycleControl(self, on_poweroff, on_reboot, on_crash):
        self.on_poweroff = on_poweroff
        self.on_reboot = on_reboot
        self.on_crash = on_crash

    def lifecycleControlToXml(self):
        xml = ""
        if self.on_poweroff != "":
            xml += "\n<on_poweroff>" + self.on_poweroff + "</on_poweroff>"
        if self.on_reboot != "":
            xml += "\n<on_reboot>" + self.on_reboot + "</on_reboot>"
        if self.on_crash != "":
            xml += "\n<on_crash>" + self.on_crash + "</on_crash>"
        return xml

    def setTimeKeeping(self, time):
        self.time = time

    def timeKeepingToXml(self):

        if self.time != "":
            return '<clock offset="' + self.time + '"/>'
        else:
            return ""

    def setDevices(self, devices):
        self.devices = devices

    def OSBootToXml(self):

        OSBootingType = self.OStype
        if OSBootingType == 1:
            return self.BIOSBootloaderToXml()
        elif OSBootingType == 2:
            return self.hostBootloaderToXml()
        elif OSBootingType == 3:
            return self.directKernelBootToXml()
        else:
            return ""

    def featuresToXml(self):
        if self.features == 1:
            return "<features><pae/><acpi/><apic/></features>"
        else:
            return ""

    def toXml(self):
        xml = ""
        xml = "<domain type='" + self.type + "'>"
        xml += "\n\t<name>" + self.name + "</name>"
        if self.uuid != "":
            xml += "\n\t<uuid>" + self.uuid + "</uuid>"
        xml += "\n" + self.OSBootToXml()
        xml += "\n" + self.featuresToXml()
        xml += "\n" + self.lifecycleControlToXml()
        xml += "\n" + self.timeKeepingToXml()
        xml += "\n" + self.basicResourcesToXml()
        xml += "\n" + self.bootScriptsToXml()
        xml += "\n" + self.shutdownScriptsToXml()
        xml += "\n<devices>"
        for i in range(len(self.devices)):
            xml += "\n" + self.devices[i].toXml()
        xml += "\n</devices>"
        xml += "\n</domain>"
        return xml


class DiskXml:
    def __init__(self, type, device=""):
        self.type = type
        self.driver = {}
        self.source = {}
        self.target = {}
        self.device = device

    def setSource(self, file):
        self.source['file'] = file
        self.source['dev'] = file

    def sourceToXml(self):
        try:
            if self.type == "file":
                return "<source file='" + self.source['file'] + "'/>"
            else:
                return "<source dev='" + self.source['dev'] + "'/>"
        except KeyError:
            return ""

    def setTarget(self, dev, bus=""):
        self.target['dev'] = dev
        self.target['bus'] = bus

    def targetToXml(self):
        try:
            if self.target['bus'] == "":
                return "<target dev='" + self.target['dev'] + "' />"
            else:
                return "<target dev='" + self.target['dev'] + "' bus='" + self.target['bus'] + "'/>"
        except KeyError:
            return ""

    def setDriver(self, name, type=""):
        self.driver['name'] = name
        self.driver['type'] = type

    def driverToXml(self):
        try:
            if (self.driver['type'] == ""):
                return '<driver name="' + self.driver['name'] + '" />'
            else:
                return '<driver name="' + self.driver['name'] + '" type="' + self.driver['type'] + '" />'
        except KeyError:
            return ""

    def toXml(self):
        xml = ""
        xml = "<disk type='" + self.type
        if self.device != "":
            xml += "' device='" + self.device + "'>"
        else:
            xml += "'>"

        xml += "\n\t" + self.driverToXml()
        xml += "\n\t" + self.sourceToXml()
        xml += "\n\t" + self.targetToXml()
        xml += "\n</disk>"
        return xml


class USBXml:
    def __init__(self, mode="subsystem", type="usb"):
        self.mode = mode
        self.type = type
        self.source = {}

    def setSource(self, vendor, product):
        self.source['vendor'] = vendor
        self.source['product'] = product

    def sourceToXml(self):
        try:
            xml = ""
            xml = "<source>"
            xml += "\n\t<vendor id = '" + self.source['vendor'] + "' />"
            xml += "\n\t<product id = '" + self.source['product'] + "' />"
            xml += "\n</source>"
            return xml
        except KeyError:
            return ""

    def toXml(self):
        xml = ""
        xml = "<hostdev mode='" + self.mode + "' type='" + self.type + "'>"
        xml += "\n\t" + self.sourceToXml()
        xml += "\n</disk>"
        ########### may be something error , because </disk> target and <hostdev> target don't match
        return xml


class NetworkInterfaceXml:
    def __init__(self, type):
        self.type = type
        self.target = {}
        self.mac = {}
        self.source = {}
        self.model = {}
        self.script = {}
        self.uuid = ""

    def setTarget(self, dev):
        self.target['dev'] = dev

    def setUUID(self, uuid):
        self.uuid = uuid

    def targetToXml(self):
        try:
            return "<target dev = '" + self.target['dev'] + "'/>"
        except KeyError:
            return ""

    def setMac(self, address):
        self.mac['address'] = address

    def macToXml(self):
        try:
            return '<mac address="' + self.mac['address'] + '"/>'
        except KeyError:
            return ""

    def setSource(self, network="", bridge="", address="", port=""):
        self.source['network'] = network
        self.source['bridge'] = bridge
        self.source['address'] = address
        self.source['port'] = port

    def sourceToXml(self):
        type = self.type
        try:
            if type == "network":
                return "<source network='" + self.source['network'] + "'/>"
            elif type == "bridge":
                return "<source bridge='" + self.source['bridge'] + "'/>"
            else:
                return "<source address='" + self.source['address'] + "' port='" + self.source['port'] + "'/>"
        except KeyError:
            return ""

    def setModel(self, type):
        self.model['type'] = type

    def modelToXml(self):
        try:
            return "<model type='" + self.model['type'] + "'/>"
        except KeyError:
            return ""

    def setScript(self, path):
        self.script['path'] = path

    def scriptToXml(self):
        try:
            return "<script path='" + self.script['path'] + "'/>"
        except KeyError:
            return ""

    def uuidToXml(self):
        if self.uuid != "":
            return "<uuid>" + self.uuid + "</uuid>"
        else:
            return ""

    def toXml(self):
        xml = ""
        xml = "<interface type='" + self.type + "'>"
        xml += "\n\t" + self.sourceToXml()
        xml += "\n\t" + self.uuidToXml()
        xml += "\n\t" + self.targetToXml()
        xml += "\n\t" + self.macToXml()
        xml += "\n\t" + self.modelToXml()
        xml += "\n\t" + self.scriptToXml()
        xml += "\n</interface>"
        return xml


class InputDevice:
    def __init__(self, type, bus=""):
        self.type = type
        self.bus = bus

    def toXml(self):
        if self.bus == "":
            return "<input type='" + self.type + "' />"
        else:
            return "<input type='" + self.type + "' bus='" + self.bus + "'/>"


class GraphicalFramebuffer:
    def __init__(self, type):
        self.type = type
        self.autoport = 0
        self.port = ""
        self.listen = ""
        self.password = ""

    def setAutoport(self):
        self.autoport = 1

    def setPort(self, port):
        self.port = port

    def setListen(self, listen):
        self.listen = listen

    def setPassword(self, password):
        self.password = password

    def toXml(self):
        xml = ""
        xml = "<graphics type='" + self.type + "' "
        if self.autoport == 1:
            xml += " autoport "
        elif self.port != "":
            xml += " port='" + self.port + "' "
        if self.listen != "":
            xml += " listen='" + self.listen + "' "
        if self.password != "":
            xml += " passwd='" + self.password + "' "
        xml += " />"
        return xml


class CharacterDevice:
    def __init__(self, deviceType, type):
        self.deviceType = deviceType
        self.type = type

    def setTarget(self, port):
        self.target['port'] = port

    def setSource(self, path):
        self.source['path'] = path

    def targetToXml(self):
        try:
            return "<target port='" + self.target['port'] + "' />"
        except KeyError:
            return ""

    def sourceToXml(self):
        try:
            return "<source path='" + self.source['path'] + "' />"
        except KeyError:
            return ""

    def toXml(self):
        xml = "<" + self.deviceType + " type='" + self.type + "' >"
        xml += "\n\t" + self.sourceToXml()
        xml += "\n\t" + self.targetToXml()
        xml += "\n " + self.deviceType + ">"
        return xml


class DevicesXml:
    def __init__(self):
        self.devices = []

    def addDevice(self, device):
        self.devices.append(device)

    def toXml(self):
        xml = ""
        for i in range(len(self.devices)):
            xml += self.devices[i].toXml + "\n"

        return xml


class EmulatorXml:
    def __init__(self, path):
        self.path = path

    def toXml(self):
        xml = ""
        xml = "<emulator>" + self.path + "</emulator>"
        return xml
