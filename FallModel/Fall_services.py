import SPmodelling.Service
import SPmodelling.Interface as intf


class Care(SPmodelling.Service.Service):
    """
    Provision modelling the service of care provided in various contexts
    """

    def __init__(self, tx):
        """
        Identify the parameters of the service

        :param tx: neo4j database read transaction
        """
        super(Care, self).__init__("care", "care")
        self.name = "care"
        self.resources = intf.get_node_value(tx, [self.name, "Service", "name"], "resources")
        self.date = intf.get_node_value(tx, [self.name, "Service", "name"], "date")
        self.capacity = intf.get_node_value(tx, [self.name, "Service", "name"], "capacity")
        self.load = intf.get_node_value(tx, [self.name, "Service", "name"], "load")

    def provide_service(self, tx, agent):
        """
        Gives a set amount of 'resources' to the agent from the service node.
        Then checks if the time step has changed since the last check, if it has it will clear the load on the service.

        :param tx: neo4j database write transaction
        :param agent: agent tuple - id, label, id type

        :return: None
        """
        [ag_id, ag_label, ag_uid] = agent
        resources = intf.get_node_value(tx, agent, "resources")
        # add resources to agent
        intf.update_agent(tx, agent, "resources", resources + self.resources)
        # check for day end and reset capacity
        if intf.get_time(tx) != self.date:
            intf.update_node(tx, [self.name, "Service", "name"], "date", intf.get_time(tx))
            intf.update_node(tx, [self.name, "Service", "name"], "load", 0)


class Intervention(SPmodelling.Service.Service):
    """
    Provision modelling the service of medical intervention (eg. physio therapy, occupational therapy, ...) provided in
    various contexts.
    """

    def __init__(self, tx):
        """
        Identify the parameters of the service

        :param tx: neo4j database read transaction
        """
        super(Intervention, self).__init__("intervention", "intervention")
        self.resources = intf.get_node_value(tx, [self.name, "Service", "name"], "resources")
        self.mobility = intf.get_node_value(tx, [self.name, "Service", "name"], "mobility")
        self.date = intf.get_node_value(tx, [self.name, "Service", "name"], "date")

    def provide_service(self, tx, agent):
        """
        Takes resources from the agent in return for improved mobility. Checks timestep and updates the load on the
        service.

        :param tx: neo4j database write transaction
        :param agent: agent tuple - id, label, id type

        :return: None
        """
        [ag_id, ag_label, ag_uid] = agent
        resources = intf.get_node_value(tx, [ag_id, ag_label, ag_uid], "resources")
        mobility = intf.get_node_value(tx, [ag_id,ag_label, ag_uid], "mob")
        # add resources to agent
        intf.update_agent(tx, [ag_id, ag_label, ag_uid], "resources", resources + self.resources)
        intf.update_agent(tx, [ag_id, ag_label, ag_uid], "mob", mobility + self.mobility)
        # check for day end and reset capacity
        if intf.get_time(tx) != self.date:
            intf.update_node(tx, [self.name, "Service", "name"], "date", intf.get_time(tx))
            intf.update_node(tx, [self.name, "Service", "name"], "load", 0)

