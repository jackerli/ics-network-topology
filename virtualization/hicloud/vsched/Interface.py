class Interface:

    def importTemplate(self, xml):
        '''import XML into Portal's database'''
        raise NotImplementedError

    def listTemplate(self):
        '''list template'''
        raise NotImplementedError

    def listTemplateByType(self, typ):
        '''list template by `type`, `type` can be: vLab, vCluster, vTemplate'''
        raise NotImplementedError

    def showTemplate(self, uuid):
        '''show template info by UUID'''
        raise NotImplementedError

    def showTemplateByKey(self, key):
        '''show template info by `key`, `key` can be: vLab@<int>, vCluster@<int>, vTemplate@<int>'''
        raise NotImplementedError

    def removeTemplate(self, uuid):
        '''remove template according to specified uuid, also remove related instances'''
        raise NotImplementedError

    def removeTemplates(self, uuid):
        '''remove multiple template according to partial uuid, also remove related instances'''
        raise NotImplementedError

    def removeTemplateByKey(self, key):
        '''remove template according to specified key, also remove related instances'''
        raise NotImplementedError

    def deployV(self, template_uuid, param):
        '''deploy phase 1: generate VM and VSwitch instances in database'''
        raise NotImplementedError

    def startV(self, template_uuid):
        '''startV phase 1: generate job to start vLab/vCluster'''
        raise NotImplementedError

    def stopV(self, template_uuid):
        '''stopV phase 1: generate job to stop vLab/vCluster'''
        raise NotImplementedError

    def undeployV(self, template_uuid):
        '''undeploy phase 1: generate job to undeploy vLab/vCluster'''
        raise NotImplementedError
