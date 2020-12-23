import SPmodelling.Service
import SPmodelling.Interface as intf


class Care(SPmodelling.Service.Service):

    def __init__(self, dri):
        super(Care, self).__init__("care", "care")
        self.name = "care"
        self.resources = intf.get_node_value(dri, [self.name, "Service", "name"], "resources")
        self.date = intf.get_node_value(dri, [self.name, "Service", "name"], "date")
        self.capacity = intf.get_node_value(dri, [self.name, "Service", "name"], "capacity")
        self.load = intf.get_node_value(dri, [self.name, "Service", "name"], "load")

    def provide_service(self, dri, agent):
        [ag_id, ag_label, ag_uid] = agent
        resources = intf.get_node_value(dri, agent, "resources")
        # add resources to agent
        intf.update_agent(dri, agent, "resources", resources + self.resources)
        # check for day end and reset capacity
        if intf.get_time(dri) != self.date:
            intf.update_node(dri, [self.name, "Service", "name"], "date", intf.get_time(dri))
            intf.update_node(dri, [self.name, "Service", "name"], "load", 0)


class Intervention(SPmodelling.Service.Service):

    def __init__(self, dri):
        super(Intervention, self).__init__("intervention", "intervention")
        self.resources = intf.get_node_value(dri, [self.name, "Service", "name"], "resources")
        self.mobility = intf.get_node_value(dri, [self.name, "Service", "name"], "mobility")
        self.date = intf.get_node_value(dri, [self.name, "Service", "name"], "date")

    def provide_service(self, dri, agent):
        [ag_id, ag_label, ag_uid] = agent
        resources = intf.get_node_value(dri, [ag_id, ag_label, ag_uid], "resources")
        mobility = intf.get_node_value(dri, [ag_id,ag_label, ag_uid], "mob")
        # add resources to agent
        intf.update_agent(dri, [ag_id, ag_label, ag_uid], "resources", resources + self.resources)
        intf.update_agent(dri, [ag_id, ag_label, ag_uid], "mob", mobility + self.mobility)
        # check for day end and reset capacity
        if intf.get_time(dri) != self.date:
            intf.update_node(dri, [self.name, "Service", "name"], "date", intf.get_time(dri))
            intf.update_node(dri, [self.name, "Service", "name"], "load", 0)

