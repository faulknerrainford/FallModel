import SPmodelling.Node
import SPmodelling.Interface as intf
import numpy as np
from random import random
import numpy.random as npr
import pickle
from FallModel.Fall_Balancer import parselog
import specification as specification
from FallModel.Fall_agent import Patient
from FallModel.Fall_agent import logging as ag_logging


def fall_or_al_check(dri, agent, edges):
    """
    Check if agent is directed to assisted living or if they have a fall, in the case of a fall the fall is classified.

    :param dri: neo4j database driver
    :param agent: id, label and type of id for agent to check
    :param edges: list of non-eliminated outgoing edges from the node

    :return: view of available edges, possibly reduced by a fall or redirection to assisted living.
    """
    if type(edges) != list:
        edges = [edges]
    destinations = [edge.end_node for edge in edges]
    mob = intf.get_node_value(dri, agent, "mob")
    view = edges
    # If Care in options check for zero mobility
    if "Care" in destinations and mob <= 0:
        view = [edge for edge in edges if edge.end_node["name"] == "Care"]
    # If Hos and GP in options check for fall and return hos or GP,
    #  no prediction just straight check based on  mobility
    elif "Hos" in destinations and "GP" in destinations:
        if (r := random()) < np.exp(-3 * mob):
            view = [edge for edge in edges if edge.end_node["name"] == "Hos"]
            # Mark a severe fall has happened in agent log
            ag_logging(dri, agent, "Severe Fall, " + str(intf.gettime(dri)))
            intf.update_agent(dri, agent, "wellbeing", "Fallen")
        elif r < np.exp(-3 * (mob - 0.1 * mob)):
            view = [edge for edge in edges if edge.end_node["name"] == "GP"]
            # Mark a moderate fall has happened in agent log
            ag_logging(dri, agent, "Moderate Fall, " + str(intf.gettime(dri)))
            intf.update_agent(dri, agent, "wellbeing", "Fallen")
        elif r < np.exp(-3 * (mob - 0.3 * mob)):
            # Mark a mild fall has happened in agent log
            ag_logging(dri, agent, "Mild Fall, " + str(intf.gettime(dri)))
            intf.updateagent(dri, agent, "wellbeing", "Fallen")
    return view


def duration_update(dri, agent, node, duration):
    """
    Update agent values after staying at a node for multiple time steps.

    :param dri: neo4j database driver
    :param agent: id, label and id type
    :param node: id, label and id type
    :param duration: time spent at node

    :return: None
    """
    mob_change = intf.get_node_value(dri, node, "modm")
    mood_change = intf.get_node_value(dri, node, "modmood")
    recover_rate = intf.get_node_value(dri, node, "resources")
    intf.update_agent(dri, agent, "mob", npr.normal((duration * mob_change), 1, 1))
    intf.update_agent(dri, agent, "mood", npr.normal((duration * mood_change), 1, 1))
    intf.update_agent(dri, agent, "resources", npr.normal((duration * recover_rate), 1, 1))


def predict_fall(dri, agent, mob_change):
    """
    Predicts when the agent will next fall by predicting a next fall and then checking time between for fall
    predictions based on changes to mobility.

    :param dri: neo4j database driver
    :param agent: id, label and id type
    :param mob_change: the amount per time step that mobility changes at that location

    :return: fall_time, fall_type
    """
    mob = intf.get_node_value(dri, agent, "mob")
    (fall_time, fall_type) = next_fall(mob)
    t = 1
    while t < fall_time:
        mob = mob + mob_change
        (n_fall_time, n_fall_type) = next_fall(mob)
        if n_fall_time + t < fall_time:
            (fall_time, fall_type) = (n_fall_time + t, n_fall_type)
        t = t + 1
    return fall_time, fall_type


def next_fall(mob):
    """
    We predict how many time steps until the next fall of each type based on a poisson distribution with mean for
    severe falls:
    -log(1-mobility)
    moderate falls:
    -log(1-0.9*mobility)
    mild falls:
    -log(1-0.7*mobility)
    We return the earliest fall.

    :param mob: Agents current mobility

    :return: [fall time, fall type] for the fall occurring first
    """
    server_fall_prediction = npr.poisson(-np.log(1 - mob), 1)
    fall_type = "Severe"
    fall_time = server_fall_prediction
    moderate_fall_prediction = npr.poisson(-np.log(1 - (mob - 0.1 * mob)), 1)
    if moderate_fall_prediction < fall_time:
        fall_type = "Moderate"
        fall_time = moderate_fall_prediction
    mild_fall_prediction = npr.poisson(-np.log(1 - (mob - 0.3 * mob)), 1)
    if mild_fall_prediction < fall_time:
        fall_type = "Mild"
        fall_time = mild_fall_prediction
    return fall_time, fall_type


class FallNode(SPmodelling.Node.Node):
    """
    FallNode class extends the Node class from SPmodelling with the perception filtering used by all nodes in the
    FallModel.
    """

    def __init__(self, name, capacity=None, duration=None, queue=None):
        super(FallNode, self).__init__(name, capacity, duration, queue)
        self.servicemodel = "alternate"

    def available_services(self, dri):
        services = super(FallNode, self).available_services(dri)
        serv = []
        for service in services:
            serv_cap = intf.get_node_value(dri, service, "capacity")
            serv_load = intf.get_node_value(dri, service, "load")
            if serv_cap > serv_load:
                serv.append(service)
        return serv

    def agents_ready(self, dri):
        """
        Checks for unqueued agents at a node with a queue and queues them, it also moves agents ready to move.

        :param dri: neo4j database driver

        :return: None
        """
        super(FallNode, self).agents_ready(dri)

    def agent_perception(self, dri, agent, dest=None, wait_time=None):
        """
        Determine based on the node the agent is located at what an agent can see in terms of options to move. It
        filters out overloaded nodes with no spare capacity, edges which require a referral the agent does not have,
        edges that do not allow that type of agent. If Care is an option it directs agents with 0 mobility to Care by
        removing all other options. If Hospital and GP are in options a fall is checked for based on the agents
        mobility, see Fall algorithm for detection and classification of falls. Severe falls cause the agent to be
        directed to the Hospital, Moderate falls direct to the GP.

        :param dri: neo4j database driver.
        :param agent: The agent object returned from the database via the interface
        :param dest: (Optional) used for agents whose destination has been predicted, passes the predicted destination
        :param wait_time: (Optional) integer, time the agent has been waiting at current node for updating the agent

        :return: view, agents filtered perception of their surroundings
        """
        view = super(FallNode, self).agent_perception(dri, agent, dest, wait_time)
        if type(view) == list:
            for edge in view:
                if "allowed" in edge.keys():
                    referral = intf.get_node_value(dri, agent, "referral")
                    if not referral and edge["ref"]:
                        view.remove(edge)
                    else:
                        allowed = edge["allowed"]
                        wellbeing = intf.get_node_value(dri, agent, "wellbeing")
                        if wellbeing not in allowed:
                            view.remove(edge)
        else:
            if "allowed" in view.keys():
                referral = intf.get_node_value(dri, agent, "referral")
                if not referral:
                    view = []
                else:
                    allowed = view["allowed"].split(',')
                    wellbeing = intf.get_node_value(dri, agent, "wellbeing")
                    if wellbeing not in allowed:
                        view = []
        return fall_or_al_check(dri, agent, view)

    def agent_prediction(self, dri, agent):
        """
        For nodes with queues this function is specialised to add the agents to the queue with a wait time and
        destination. Does nothing in this form.

        :param dri: neo4j database driver
        :param agent: Agent node object returned by interface

        :return: None
        """
        return super(FallNode, self).agent_prediction(dri, agent)
        # Node specific only, no general node prediction assume no queue as default, thus no prediction needed


class HomeNode(FallNode):
    """
    HomeNode is a subclass of FallNode and extends it to add a queue for agents, a prediction algorithm for where an
    agent is going next and how long they will be at the home node. As part of this it has a function for predicting
    falls including categorisation.
    """

    def __init__(self, name="Home", mc=-0.015, rr=0.3, moc=-0.02):
        super(HomeNode, self).__init__(name, queue={})
        self.mob_change = mc
        self.recover_rate = rr
        self.mood_change = moc

    def agents_ready(self, dri, agent_class="Patient"):
        """
        If there are agents ready at this time step the node checks the nodes mobility, confidence and resources
        modifiers. It uses those values to update the agent based on the agents duration at the home node. After this
        agents are processed as usual for a fall node.

        :param dri: neo4j database driver
        :param agent_class: (Optional) the class of agents this node expects to find and process.

        :return: None
        """
        # Apply changes from wait_time not dest
        agents = intf.get_node_agents(dri, [self.name, "Node", "name"])
        clock = intf.get_time(dri)
        if clock in self.queue.keys():
            for ag in agents:
                if ag[0] in self.queue[clock].keys() and self.queue[clock][ag[0]][1]:
                    duration_update(dri, ag, [self.name, "Node", "name"],
                                    self.queue[clock][ag[0]][1])
        super(HomeNode, self).agents_ready(dri)

    def agent_perception(self, dri, agent, dest=None, waittime=None):
        return super(HomeNode, self).agent_perception(dri, agent, dest, waittime)

    def agent_prediction(self, dri, agent):
        """
        We check the time it will take the agent to have the recovered the minimum resources required to move to a
        different node other than by a fall. We then predict when and kind of the agents next fall. We compare this with
        the recovery time to see if the agent will fall before they move. If the agent is going to fall we add them to
        the queue at the time step when they will fall and log the fall. In the case of a severe or moderate fall we
        also set a destination as Hospital or GP respectively. We add agents with mild falls or recovery before fall are
        added to the queue with out a destination but with a duration the same as their recovery time in both cases, if
        they have a mild fall we update their wellbeing to "Fallen" as well. It the agent has sufficient resources to
        act immediately then they are added to the top of the queue with no duration or destination.

        :param dri: neo4j database driver
        :param agent: Agent node object returned by interface

        :return: None
        """
        view = intf.perception(dri, agent)[1:]
        min_resources = min(
            [edge["resources"] for edge in view if edge["resources"]] + [edge.end_node["resources"] for edge in view
                                                                         if edge.end_node["resources"]])
        ag_resources = intf.get_node_value(dri, agent, "resources")
        recovery_time = (min_resources - ag_resources) / self.recover_rate
        if ag_resources < min_resources:
            (fall_time, fall_type) = predict_fall(dri, agent, self.mob_change)
            if fall_time < recovery_time and not fall_type == "Mild" and fall_type:
                # Add agent to queue with fall
                queue_time = fall_time + intf.get_time(dri)
                intf.update_agent(dri, agent, "wellbeing", "Fallen")
                if queue_time not in self.queue.keys():
                    self.queue[queue_time] = {}
                if fall_type == "Severe":
                    dest = [edge for edge in view if edge.end_node["name"] == "Hos"]
                else:
                    dest = [edge for edge in view if edge.end_node["name"] == "GP"]
                self.queue[queue_time][agent[0]] = (dest[0], fall_time)
                ag_logging(dri, agent, fall_type + " Fall, " + str(queue_time))
            else:
                # Add agent to queue with recovery
                if fall_type == "Mild":
                    queue_time = fall_time + intf.get_time(dri)
                    ag_logging(dri, agent, fall_type + " Fall, " + str(queue_time))
                    intf.update_agent(dri, agent, "wellbeing", "Fallen")
                if recovery_time + intf.get_time(dri) not in self.queue.keys():
                    self.queue[recovery_time + intf.gettime(dri)] = {}
                self.queue[recovery_time + intf.get_time(dri)][agent[0]] = (None, recovery_time)
        else:
            # Add agent to next time step - no wait_time or dest
            if intf.get_time(dri) + 1 not in self.queue.keys():
                self.queue[intf.get_time(dri) + 1] = {}
            self.queue[intf.get_time(dri) + 1][agent[0]] = (None, None)


class HosNode(FallNode):
    """
    Extends the FallNode class with the addition of prediction of length of hospital stay and modification of agent
    values before leaving node based on duration.
    """

    def __init__(self, name="Hos", mc=-0.1, rr=0.2, moc=-0.05):
        super(HosNode, self).__init__(name, queue={})
        self.mob_change = mc
        self.recover_rate = rr
        self.mood_change = moc

    def agents_ready(self, dri):
        """
        If there are agents ready at this time step the node checks the nodes mobility, confidence and resources
        modifiers. It uses those values to update the agent based on the agents duration at the Hospital node. It also
        updates the agent to give it a referral and logs its discharge from hospital. After this agents are processed
        as usual for a fall node.

        :param dri: neo4j database driver

        :return:None
        """
        # Apply changes from wait_time not dest
        agents = intf.get_node_agents(dri, [self.name, "Node", "name"])
        clock = intf.get_time(dri)
        if clock in self.queue.keys() and agents:
            for ag in agents:
                if ag[0] in self.queue[clock].keys() and self.queue[clock][ag[0]][1]:
                    self.mob_change = intf.get_node_value(dri, [self.name, "Node", "name"], "modm")
                    self.mood_change = intf.get_node_value(dri, [self.name, "Node", "name"], "modmood")
                    self.recover_rate = intf.get_node_value(dri, [self.name, "Node", "name"], "resources")
                    intf.update_agent(dri, ag, "mob",
                                      npr.normal((self.queue[clock][ag[0]][1] * self.mob_change), 1, 1)[0])
                    intf.update_agent(dri, ag, "mood",
                                      npr.normal((self.queue[clock][ag[0]][1] * self.mood_change), 1, 1)[0])
                    intf.update_agent(dri, ag, "resources",
                                      self.queue[clock][ag[0]][1] * self.recover_rate)
                    intf.update_agent(dri, ag, "referral", True)
                    ag_logging(dri, ag, "Hos discharge, " + str(intf.get_time(dri)))
        super(HosNode, self).agents_ready(dri)

    def agent_perception(self, dri, agent, dest=None, wait_time=None):
        return super(HosNode, self).agent_perception(dri, agent, dest, wait_time)

    def agent_prediction(self, dri, agent):
        """
        Logs the agent being admitted to hospital and then calculates mean for poisson distribution to predict the
        duration of the agents stay.
        mean = -9*min(agent_mobility, 1) + 14
        This means a fully healthy agent has a mean stay of 5 days in hospital after a severe fall. The predicted
        duration is drawn from a poisson distribution.
        The agent is added to the queue at t = current_time + predicted_duration
        with destination home.

        :param dri: neo4j database driver
        :param agent: agent database object returned from Interface

        :return: None
        """
        view = super(HosNode, self).agent_prediction(dri, agent)[1:]
        clock = intf.get_time(dri)
        ag_logging(dri, agent, "Hos admitted, " + str(clock))
        mob = intf.get_node_value(dri, agent, "mob")
        mean = -9 * min(mob, 1) + 14
        time = npr.poisson(mean, 1)[0]
        if clock + time not in self.queue.keys():
            self.queue[clock + time] = {}
        dest = [edge for edge in view if edge.end_node["name"] == "Home"]
        self.queue[clock + time][agent[0]] = (dest[0], time)


class GPNode(FallNode):
    """
    GPNode is a subclass of Fall node which extends the Fall node by filtering the agents perception to redirect the
    agent home or to the hospital. It also gives the agent a referral if they have lower mobility.
    """

    def __init__(self, name="GP"):
        super(FallNode, self).__init__(name)

    def agents_ready(self, dri):
        super(FallNode, self).agents_ready(dri)

    def agent_perception(self, dri, agent, dest=None, wait_time=None):
        """
        Add additional filters to direct the agent to Hospital if mobility below 0.6 and home otherwise. If the agent
        is sent home but have mobility below 0.85 they are given a referral.

        :param dri: neo4j database driver
        :param agent: agent database object returned by interface
        :param dest: (Optional) Not used here
        :param wait_time: (Optional) Not used here

        :return: perception with either Home or Hospital as the only destination
        """
        view = super(GPNode, self).agent_perception(dri, agent, dest, wait_time)
        mob = intf.get_node_value(dri, agent, "mob")
        if mob < 0.6:
            view = [edge for edge in view if edge.end_node["name"] == "Hos"]
        else:
            view = [edge for edge in view if edge.end_node["name"] == "Home"]
            if mob < 0.85:
                intf.update_agent(dri, agent, "referral", True)
        return view

    def agent_prediction(self, dri, agent):
        return None
        # No queue so prediction not needed


class SocialNode(FallNode):
    """
    Currently a generic FallNode with name "Social"
    """

    def __init__(self, name="Social"):
        super(FallNode, self).__init__(name)

    def agents_ready(self, dri):
        super(FallNode, self).agents_ready(dri)

    def agent_perception(self, dri, agent, dest=None, wait_time=None):
        view = super(SocialNode, self).agent_perception(dri, agent, dest, wait_time)
        return view

    def agent_prediction(self, dri, agent):
        return None
        # No queue so prediction not needed


class InterventionNode(FallNode):
    """
    Extends the Fall Node to manage the capacity limit changes to Intervention nodes and manages the referrals for
    agents
    """

    def __init__(self, name="Intervention"):
        super(FallNode, self).__init__(name)

    def agents_ready(self, dri):
        """
        Extends normal Fall node by updating the load value after processing agents.

        :param dri: neo4j database driver

        :return: None
        """
        super(FallNode, self).agents_ready(dri)
        load = len(intf.get_node_agents(dri, [self.name, "Node", "name"]))
        intf.update_node(dri, [self.name, "Node", "name"], "load", load)

    def agent_perception(self, dri, agent, dest=None, wait_time=None):
        """
        Extends normal Fall Node function by logging the agents attendance at the intervention. It checks if the agent
        has mobility below 0.6, if they do the agent is given a referral (if they didn't have one) else if they have a
        referral is removed.

        :param dri: neo4j database driver
        :param agent: agent database object returned from Interface
        :param dest: (Optional) Not used here
        :param wait_time: (Optional) Not used here

        :return: view from Fall Node agent_perception
        """
        view = super(InterventionNode, self).agent_perception(dri, agent, dest, wait_time)
        ag_logging(dri, agent, self.name + ", " + str(intf.get_time(dri)))
        mob = intf.get_node_value(dri, agent, "mob")
        if mob > 0.6:
            intf.update_agent(dri, agent, "referral", "False")
        else:
            intf.update_agent(dri, agent, "referral", "True")
        return view

    def agent_prediction(self, dri, agent):
        return None
        # No queue so prediction not needed


class CareNode(SPmodelling.Node.Node):
    """
    This node is not a true node. It is a sink node which only processes agents on arrival. As such it only has an
    agents_ready function which processes the agents out of the system to save database space.
    """

    def __init__(self, name=None):
        """
        Sets up node name and data storage for monitor and analysis of system.
        """
        self.name = "Care"
        self.run_name = None
        self.agents = 0
        self.interval = 0
        self.mild = 0
        self.moderate = 0
        self.severe = 0

    def agents_ready(self, dri):
        """
        Saves out the log strings of all agents at the Care Node using the runname acquired from the database. Updates
        its own track of average number of falls and length of interval using information in agent logs. Also updates
        the total number of agents that have left the system. It then deletes the agents at the Care node.

        :param dri: neo4j database driver

        :return: None
        """
        agents = intf.get_node_agents(dri, ["Care", "Node", "name"])
        if not self.run_name:
            self.run_name = intf.get_run_name(dri)
        file = open(specification.savedirectory + "AgentLogscareag_" + self.run_name + ".p", 'ab')
        for agent in agents:
            log = intf.get_node_value(dri, agent, "log")
            agl = parselog(log)
            agint = agl[-1][1] - agl[0][1]
            self.interval = (self.interval * self.agents + agint) / (self.agents + 1)
            for entry in agl:
                if entry[0] == "Mild Fall":
                    self.mild = self.mild + 1
                if entry[0] == "Moderate Fall":
                    self.moderate = self.moderate + 1
                if entry[0] == "Severe Fall":
                    self.severe = self.severe + 1
            self.agents = self.agents + 1
            intf.update_node(dri, ["Care", "Node", "name"], "interval", self.interval)
            intf.update_node(dri, ["Care", "Node", "name"], "mild", self.mild)
            intf.update_node(dri, ["Care", "Node", "name"], "moderate", self.moderate)
            intf.update_node(dri, ["Care", "Node", "name"], "severe", self.severe)
            intf.update_node(dri, ["Care", "Node", "name"], "agents", self.agents)
            aglog = "Agent " + str(agent[0]) + ": " + log
            pickle.dump(aglog, file)
            intf.delete_agent(dri, agent)
        # file.close()
        return None

    def agent_perception(self, dri, agent, dest=None, wait_time=None):
        pass

    def agent_prediction(self, dri, agent):
        pass

    # While Care is not actually a node it does have an agents_ready function which is triggered on arrival.
    # This causes the agents log to be saved to file.


# noinspection DuplicatedCode
class HomeNodeV0(FallNode):
    """
    HomeNode is a subclass of FallNode and extends it to add a queue for agents, a prediction algorithm for where an
    agent is going next and how long they will be at the home node. As part of this is has a function for predicting
    falls including categorication.
    """

    def __init__(self, name="Home", mc=-0.015, rr=0.3, cc=-0.02):
        super(HomeNodeV0, self).__init__(name, queue={})
        self.mobchange = mc
        self.recoverrate = rr
        self.confchange = cc

    def agents_ready(self, dri):
        """
        If there are agents ready at this time step the node checks the nodes mobility, confidence and resources
        modifiers. It uses those values to update the agent based on the agents duration at the home node. After this
        agents are processed as usual for a fall node.

        :param dri: neo4j database driver

        :return: None
        """
        # Apply changes from waittime not dest
        agents = intf.getnodeagents(dri, self.name, "name")
        clock = intf.gettime(dri)
        if clock in self.queue.keys():
            for ag in agents:
                if ag["id"] in self.queue[clock].keys() and self.queue[clock][ag["id"]][1]:
                    self.mobchange = intf.getnodevalue(dri, self.name, "modm", "Node", "name")
                    self.confchange = intf.getnodevalue(dri, self.name, "modc", "Node", "name")
                    self.recoverrate = intf.getnodevalue(dri, self.name, "resources", "Node", "name")
                    intf.updateagent(ag["id"], "mob",
                                     npr.normal((self.queue[clock][ag["id"]][1] * self.mobchange), 1, 1))
                    intf.updateagent(ag["id"], "conf",
                                     npr.normal((self.queue[clock][ag["id"]][1] * self.confchange), 1, 1))
                    intf.updateagent(ag["id"], "resources", self.queue[clock][ag["id"]][1] * self.recoverrate)
        super(HomeNodeV0, self).agents_ready(dri, intf)

    def agentperception(self, dri, agent, dest=None, waittime=None):
        return super(HomeNodeV0, self).agentperception(dri, agent, dest, waittime)

    def agentprediction(self, dri, agent):
        """
        We check the time it will take the agent to have the recovered the minimum resources required to move to a
        different node other than by a fall. We then predict when and kind of the agents next fall. We compare this with
        the recovery time to see if the agent will fall before they move. If the agent is going to fall we add them to
        the queue at the time step when they will fall and log the fall. In the case of a severe or moderate fall we
        also set a destination as Hospital or GP respectively. We add agents with mild falls or recovery before fall are
        added to the queue with out a destination but with a duration the same as their recovery time in both cases, if
        they have a mild fall we update their wellbeing to "Fallen" as well. It the agent has sufficient resources to
        act immediately then they are added to the top of the queue with no duration or destination.

        :param dri: neo4j database driver
        :param agent: Agent node object returned by interface

        :return: None
        """
        view = intf.perception(dri, agent["id"])[1:]
        minresources = min([edge.end_node["resources"] for edge in view if edge.end_node["resources"]])
        recoverytime = (minresources - agent["resources"]) / self.recoverrate
        if agent["resources"] < minresources:
            (falltime, falltype) = self.predictfall(agent["mob"])
            t = 1
            mob = agent["mob"]
            while t < falltime:
                mob = mob + self.mobchange
                (nfalltime, nfalltype) = self.predictfall(mob)
                if nfalltime + t < falltime:
                    (falltime, falltype) = (nfalltime + t, nfalltype)
                t = t + 1
            if falltime < recoverytime and not falltype == "Mild":
                # Add agent to queue with fall
                queuetime = falltime + intf.gettime(dri)
                intf.updateagent(dri, agent["id"], "wellbeing", "Fallen")
                if queuetime not in self.queue.keys():
                    self.queue[queuetime] = {}
                if falltype == "Severe":
                    dest = [edge for edge in view if edge.end_node["name"] == "Hos"]
                    self.queue[queuetime][agent["id"]] = (dest[0], falltime)
                    ag = Patient(agent["id"])
                    ag.logging(dri, "Severe Fall, " + str(queuetime))
                elif falltype == "Moderate":
                    dest = [edge for edge in view if edge.end_node["name"] == "GP"]
                    self.queue[queuetime][agent["id"]] = (dest[0], falltime)
                    ag = Patient(agent["id"])
                    ag.logging(dri, "Moderate Fall, " + str(queuetime))
            else:
                # Add agent to queue with recovery
                if falltype == "Mild":
                    queuetime = falltime + intf.gettime(dri)
                    ag = Patient(agent["id"])
                    ag.logging(dri, "Mild Fall, " + str(queuetime))
                    intf.updateagent(dri, agent["id"], "wellbeing", "Fallen")
                if recoverytime + intf.gettime(dri) not in self.queue.keys():
                    self.queue[recoverytime + intf.gettime(dri)] = {}
                self.queue[recoverytime + intf.gettime(dri)][agent["id"]] = (None, recoverytime)
        else:
            # Add agent to next time step - no waittime or dest
            if intf.gettime(dri) + 1 not in self.queue.keys():
                self.queue[intf.gettime(dri) + 1] = {}
            self.queue[intf.gettime(dri) + 1][agent["id"]] = (None, None)

    @staticmethod
    def predictfall(mobility):
        """
        We predict how many time steps until the next fall of each type based on a poisson distribution with mean for
        severe falls:
        -log(1-mobility)
        moderate falls:
        -log(1-0.9*mobility)
        mild falls:
        -log(1-0.7*mobility)
        We return the earliest fall.

        :param mobility: Agents current mobility
        :return: [fall time, fall type] for the fall occurring first
        """
        serverfallprediction = npr.poisson(-np.log(1 - mobility), 1)
        falltype = "Sever"
        falltime = serverfallprediction
        moderatefallprediction = npr.poisson(-np.log(1 - (mobility - 0.1 * mobility)), 1)
        if moderatefallprediction < falltime:
            falltype = "Moderate"
            falltime = moderatefallprediction
        mildfallprediction = npr.poisson(-np.log(1 - (mobility - 0.3 * mobility)), 1)
        if mildfallprediction < falltime:
            falltype = "Mild"
            falltime = mildfallprediction
        return falltime, falltype


class HosNodeV0(FallNode):
    """
    Extends the FallNode class with the addition of prediction of length of hospital stay and modification of agent
    values before leaving node based on duration.
    """

    def __init__(self, name="Hos", mc=-0.1, rr=0.2, cc=-0.05):
        super(HosNodeV0, self).__init__(name, queue={})
        self.mobchange = mc
        self.recoverrate = rr
        self.confchange = cc

    def agents_ready(self, dri):
        """
        If there are agents ready at this time step the node checks the nodes mobility, confidence and resources
        modifiers. It uses those values to update the agent based on the agents duration at the Hospital node. It also
        updates the agent to give it a referral and logs its discharge from hospital. After this agents are processed
        as usual for a fall node.

        :param dri: neo4j database driver

        :return:None
        """
        # Apply changes from waittime not dest
        agents = intf.getnodeagents(dri, self.name)
        clock = intf.gettime(dri)
        if clock in self.queue.keys() and agents:
            for ag in agents:
                if ag["id"] in self.queue[clock].keys() and self.queue[clock][ag["id"]][1]:
                    self.mobchange = intf.getnodevalue(dri, self.name, "modm", "Node", "name")
                    self.confchange = intf.getnodevalue(dri, self.name, "modc", "Node", "name")
                    self.recoverrate = intf.getnodevalue(dri, self.name, "resources", "Node", "name")
                    intf.updateagent(dri, ag["id"], "mob",
                                     npr.normal((self.queue[clock][ag["id"]][1] * self.mobchange), 1, 1)[0])
                    intf.updateagent(dri, ag["id"], "conf",
                                     npr.normal((self.queue[clock][ag["id"]][1] * self.confchange), 1, 1)[0])
                    intf.updateagent(dri, ag["id"], "resources", self.queue[clock][ag["id"]][1] * self.recoverrate)
                    intf.updateagent(dri, ag["id"], "referral", True)
                    agent = Patient(ag["id"])
                    agent.logging(dri, "Hos discharge, " + str(intf.gettime(dri)))
        super(HosNodeV0, self).agents_ready(dri, intf)

    def agentperception(self, dri, agent, dest=None, waittime=None):
        return super(HosNodeV0, self).agentperception(dri, agent, dest, waittime)

    def agentprediction(self, dri, agent):
        """
        Logs the agent being admitted to hospital and then calculates mean for poisson distribution to predict the
        duration of the agents stay.
        mean = min(-9*min(agent_mobility, 1) + 14, -9*(min(agent_confidence_resources, 1) +
        min(agent_mobility_resources, 1)) + 14
        This means a fully healthy agent has a mean stay of 5 days in hospital after a severe fall. The predicted
        duration is drawn from a poisson distribution.
        The agent is added to the queue at t = current_time + predicted_duration
        with destination home.

        :param dri: neo4j database driver
        :param agent: agent database object returned from Interface

        :return: None
        """
        view = super(HosNodeV0, self).agentprediction(dri, agent)[1:]
        clock = intf.gettime(dri)
        ag = Patient(agent["id"])
        ag.logging(dri, "Hos admitted, " + str(clock))
        mean = min(-9 * min(agent["mob"], 1) + 14, -9 * (min(agent["conf_res"], 1) + min(agent["mob_res"], 1)) + 14)
        time = npr.poisson(mean, 1)[0]
        if clock + time not in self.queue.keys():
            self.queue[clock + time] = {}
        dest = [edge for edge in view if edge.end_node["name"] == "Home"]
        self.queue[clock + time][agent["id"]] = (dest[0], time)
