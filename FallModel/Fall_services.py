import SPmodelling.Service
import SPmodelling.Interface as intf


class Care(SPmodelling.Service):

    def __init__(self, tx):
        super(Care, self).__init__("care")
        self.name = "care"
        self.resources = intf.getnodevalue(tx, self.name, "resources", "Service", "name")
        self.date = intf.getnodevalue(tx, self.name, "date", "Service", "name")
        self.capacity = intf.getnodevalue(tx, self.name, "capacity", "Service", "name")
        self.load = intf.getnodevalue(tx, self.name, "load", "Service", "name")

    @staticmethod
    def provide_service(self, tx, agent):
        [ag_id, ag_label, ag_uid] = agent
        resources = intf.getnodevalue(tx, ag_id, "resources", ag_label, ag_uid)
        # add resources to agent
        intf.updateagent(tx, ag_id, "resources", resources+self.resources)
        # check for day end and reset capacity
        if intf.gettime(tx) != self.date:
            intf.updatenode(tx, self.name, "date", intf.gettime(tx), "name", "Serivce")
            intf.updatenode(tx, self.name, "load", 0, "name", "Serivce")


class Intervention(SPmodelling.Service):

    def __init__(self, tx):
        super(Intervention, self).__init__()
        self.resources = intf.getnodevalue(tx, self.name, "resources", "Service", "name")
        self.mobility = intf.getnodevalue(tx, self.name, "mobility", "Service", "name")

    @staticmethod
    def provide_service(self, tx, agent):
        [ag_id, ag_label, ag_uid] = agent
        resources = intf.getnodevalue(tx, ag_id, "resources", ag_label, ag_uid)
        mobility = intf.getnodevalue(tx, ag_id, "mob", ag_label, ag_uid)
        # add resources to agent
        intf.updateagent(tx, ag_id, "resources", resources+self.resources)
        intf.updateagent(tx, ag_id, "mob", mobility+self.mobility)
        # check for day end and reset capacity
        if intf.gettime(tx) != self.date:
            intf.updatenode(tx, self.name, "date", intf.gettime(tx), "name", "Serivce")
            intf.updatenode(tx, self.name, "load", 0, "name", "Serivce")

