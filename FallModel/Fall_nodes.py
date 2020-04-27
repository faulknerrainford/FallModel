from SPmodelling.Node import Node
import numpy as np
from random import random
import numpy.random as npr
from FallModel.Fall_agent import Agent
import pickle
from FallModel.Fall_Balancer import parselog
import specification


class FallNode(Node):
    """
    FallNode class extends the Node class from SPmodelling with the perception filtering used by all nodes in the
    FallModel.
    """

    def __init__(self, name, capacity=None, duration=None, queue=None):
        super(FallNode, self).__init__(name, capacity, duration, queue)

    def agentsready(self, tx, intf, agentclass="FallAgent"):
        """
        Finds Agents ready to move and prompts them to do so and runs prediction for agents on arrival at new nodes.

        :param tx: neo4j database write transaction
        :param intf: Interface for database calls
        :param agentclass: Tells the node what type of agents they are handling

        :return: None
        """
        super(FallNode, self).agentsready(tx, intf, agentclass)

    def agentperception(self, tx, agent, intf, dest=None, waittime=None):
        """
        Determine based on the node what an agent can see in terms of options to move. It filters out overloaded nodes
        with no spare capacity, edges which require a referral the agent does not have, edges that do not allow this
        type of agent. If Care is an option it directs agents with 0 mobility to Care by removing all other options.
        If Hospital and GP are in options a fall is checked for based on the agents mobility, see Fall algorithm for
        detection and classification of falls. Severe falls cause the agent to be directed to the Hospital, Moderate
        falls direct to the GP.

        :param tx: neo4j database write transaction.
        :param agent: The agent object returned from the database via the interface
        :param intf: Interface for database calls
        :param dest: (Optional) used for agents whose destination has been predicted, passes the predicted destination
        :param waittime: (Optional) integer, time the agent has been waiting at current node for updating the agent

        :return: view, agents filtered perception of their surroundings
        """
        view = super(FallNode, self).agentperception(tx, agent, intf, dest, waittime)
        if type(view) == list:
            for edge in view:
                if "allowed" in edge.keys():
                    if not agent["referral"] and edge["ref"]:
                        view.remove(edge)
                    else:
                        allowed = edge["allowed"].split(',')
                        if not agent["wellbeing"] in allowed:
                            view.remove(edge)
            destinations = [edge.end_node["name"] for edge in view]
        else:
            destinations = [view.end_node["name"]]
            if "allowed" in view.keys():
                if not agent["referral"]:
                    view = []
                else:
                    allowed = view["allowed"].split(',')
                    if not agent["wellbeing"] in allowed:
                        view = []

        # If Care in options check for zero mobility
        if "Care" in destinations and agent["mob"] <= 0:
            view = [edge for edge in view if edge.end_node["name"] == "Care"]
        # If Hos and GP in options check for fall and return hos or GP,
        #  no prediction just straight check based on  mobility
        elif "Hos" in destinations and "GP" in destinations:
            if (r := random()) < np.exp(-3 * agent["mob"]):
                view = [edge for edge in view if edge.end_node["name"] == "Hos"]
                # Mark a severe fall has happened in agent log
                ag = Agent(agent["id"])
                ag.logging(tx, intf, "Severe Fall, " + str(intf.gettime(tx)))
                intf.updateagent(tx, agent["id"], "wellbeing", "Fallen")
            elif r < np.exp(-3 * (agent["mob"] - 0.1 * agent["mob"])):
                view = [edge for edge in view if edge.end_node["name"] == "GP"]
                # Mark a moderate fall has happened in agent log
                ag = Agent(agent["id"])
                ag.logging(tx, intf, "Moderate Fall, " + str(intf.gettime(tx)))
                intf.updateagent(tx, agent["id"], "wellbeing", "Fallen")
            elif r < np.exp(-3 * (agent["mob"] - 0.3 * agent["mob"])):
                # Mark a mild fall has happened in agent log
                ag = Agent(agent["id"])
                ag.logging(tx, intf, "Mild Fall, " + str(intf.gettime(tx)))
                intf.updateagent(tx, agent["id"], "wellbeing", "Fallen")
        return view

    def agentprediction(self, tx, agent, intf):
        """
        For nodes with queues this function is specialised to add the agents to the queue with a wait time and
        destination. Does nothing in this form.

        :param tx: neo4j database write transaction
        :param agent: Agent node object returned by interface
        :param intf: Interface for database calls

        :return: None
        """
        return super(FallNode, self).agentprediction(tx, agent, intf)
        # Node specific only, no general node prediction assume no queue as default, thus no prediction needed


class HomeNode(FallNode):
    """
    HomeNode is a subclass of FallNode and extends it to add a queue for agents, a prediction algorithm for where an
    agent is going next and how long they will be at the home node. As part of this is has a function for predicting
    falls including categorication.
    """

    def __init__(self, name="Home", mc=-0.015, rr=0.3, cc=-0.02):
        super(HomeNode, self).__init__(name, queue={})
        self.mobchange = mc
        self.recoverrate = rr
        self.confchange = cc

    def agentsready(self, tx, intf, agentclass="FallAgent"):
        """
        If there are agents ready at this time step the node checks the nodes mobility, confidence and energy modifiers.
        It uses those values to update the agent based on the agents duration at the home node. After this agents are
        processed as usual for a fall node.

        :param tx: neo4j database write transaction
        :param intf:  Interface for database calls
        :param agentclass: the class of agents this node expects to find and process.

        :return: None
        """
        # Apply changes from waittime not dest
        agents = intf.getnodeagents(tx, self.name, "name")
        clock = intf.gettime(tx)
        if clock in self.queue.keys():
            for ag in agents:
                if ag["id"] in self.queue[clock].keys() and self.queue[clock][ag["id"]][1]:
                    self.mobchange = intf.getnodevalue(tx, self.name, "modm", "Node", "name")
                    self.confchange = intf.getnodevalue(tx, self.name, "modc", "Node", "name")
                    self.recoverrate = intf.getnodevalue(tx, self.name, "energy", "Node", "name")
                    intf.updateagent(ag["id"], "mob",
                                     npr.normal((self.queue[clock][ag["id"]][1] * self.mobchange), 1, 1))
                    intf.updateagent(ag["id"], "conf",
                                     npr.normal((self.queue[clock][ag["id"]][1] * self.confchange), 1, 1))
                    intf.updateagent(ag["id"], "energy", self.queue[clock][ag["id"]][1] * self.recoverrate)
        super(HomeNode, self).agentsready(tx, intf)

    def agentperception(self, tx, agent, intf, dest=None, waittime=None):
        return super(HomeNode, self).agentperception(tx, agent, intf, dest, waittime)

    def agentprediction(self, tx, agent, intf):
        """
        We check the time it will take the agent to have the recovered the minimum energy required to move to a
        different node other than by a fall. We then predict when and kind of the agents next fall. We compare this with
        the recovery time to see if the agent will fall before they move. If the agent is going to fall we add them to
        the queue at the time step when they will fall and log the fall. In the case of a severe or moderate fall we
        also set a destination as Hospital or GP respectively. We add agents with mild falls or recovery before fall are
        added to the queue with out a destination but with a duration the same as their recovery time in both cases, if
        they have a mild fall we update their wellbeing to "Fallen" as well. It the agent has sufficient energy to act
        immediately then they are added to the top of the queue with no duration or destination.

        :param tx: neo4j database write transaction
        :param agent: Agent node object returned by interface
        :param intf: Interface for database calls

        :return: None
        """
        view = intf.perception(tx, agent["id"])[1:]
        minenergy = min([edge["energy"] for edge in view if edge["energy"]] + [edge.end_node["energy"] for edge in view
                                                                               if edge.end_node["energy"]])
        recoverytime = (minenergy - agent["energy"]) / self.recoverrate
        if agent["energy"] < minenergy:
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
                queuetime = falltime + intf.gettime(tx)
                intf.updateagent(tx, agent["id"], "wellbeing", "Fallen")
                if queuetime not in self.queue.keys():
                    self.queue[queuetime] = {}
                if falltype == "Severe":
                    dest = [edge for edge in view if edge.end_node["name"] == "Hos"]
                    self.queue[queuetime][agent["id"]] = (dest[0], falltime)
                    ag = Agent(agent["id"])
                    ag.logging(tx, intf, "Severe Fall, " + str(queuetime))
                elif falltype == "Moderate":
                    dest = [edge for edge in view if edge.end_node["name"] == "GP"]
                    self.queue[queuetime][agent["id"]] = (dest[0], falltime)
                    ag = Agent(agent["id"])
                    ag.logging(tx, intf, "Moderate Fall, " + str(queuetime))
            else:
                # Add agent to queue with recovery
                if falltype == "Mild":
                    queuetime = falltime + intf.gettime(tx)
                    ag = Agent(agent["id"])
                    ag.logging(tx, intf, "Mild Fall, " + str(queuetime))
                    intf.updateagent(tx, agent["id"], "wellbeing", "Fallen")
                if recoverytime + intf.gettime(tx) not in self.queue.keys():
                    self.queue[recoverytime + intf.gettime(tx)] = {}
                self.queue[recoverytime + intf.gettime(tx)][agent["id"]] = (None, recoverytime)
        else:
            # Add agent to next time step - no waittime or dest
            if intf.gettime(tx) + 1 not in self.queue.keys():
                self.queue[intf.gettime(tx) + 1] = {}
            self.queue[intf.gettime(tx) + 1][agent["id"]] = (None, None)

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


class HosNode(FallNode):
    """
    Extends the FallNode class with the addition of prediction of length of hospital stay and modification of agent
    values before leaving node based on duration.
    """

    def __init__(self, name="Hos", mc=-0.1, rr=0.2, cc=-0.05):
        super(HosNode, self).__init__(name, queue={})
        self.mobchange = mc
        self.recoverrate = rr
        self.confchange = cc

    def agentsready(self, tx, intf, agentclass="FallAgent"):
        """
        If there are agents ready at this time step the node checks the nodes mobility, confidence and energy modifiers.
        It uses those values to update the agent based on the agents duration at the Hospital node. It also updates the
        agent to give it a referral and logs its discharge from hospital. After this agents are processed as usual for a
        fall node.

        :param tx: neo4j database write transaction
        :param intf: Interface for database calls
        :param agentclass: class of agent the node will be processing

        :return:None
        """
        # Apply changes from waittime not dest
        agents = intf.getnodeagents(tx, self.name)
        clock = intf.gettime(tx)
        if clock in self.queue.keys() and agents:
            for ag in agents:
                if ag["id"] in self.queue[clock].keys() and self.queue[clock][ag["id"]][1]:
                    self.mobchange = intf.getnodevalue(tx, self.name, "modm", "Node", "name")
                    self.confchange = intf.getnodevalue(tx, self.name, "modc", "Node", "name")
                    self.recoverrate = intf.getnodevalue(tx, self.name, "energy", "Node", "name")
                    intf.updateagent(tx, ag["id"], "mob",
                                     npr.normal((self.queue[clock][ag["id"]][1] * self.mobchange), 1, 1)[0])
                    intf.updateagent(tx, ag["id"], "conf",
                                     npr.normal((self.queue[clock][ag["id"]][1] * self.confchange), 1, 1)[0])
                    intf.updateagent(tx, ag["id"], "energy", self.queue[clock][ag["id"]][1] * self.recoverrate)
                    intf.updateagent(tx, ag["id"], "referral", True)
                    agent = Agent(ag["id"])
                    agent.logging(tx, intf, "Hos discharge, " + str(intf.gettime(tx)))
        super(HosNode, self).agentsready(tx, intf)

    def agentperception(self, tx, agent, intf, dest=None, waittime=None):
        return super(HosNode, self).agentperception(tx, agent, intf, dest, waittime)

    def agentprediction(self, tx, agent, intf):
        """
        Logs the agent being admitted to hospital and then calculates mean for poisson distribution to predict the
        duration of the agents stay.
        mean = min(-9*min(agent_mobility, 1) + 14, -9*(min(agent_confidence_resources, 1) +
        min(agent_mobility_resources, 1)) + 14
        This means a fully healthy agent has a mean stay of 5 days in hospital after a severe fall. The predicted
        duration is drawn from a poisson distribution.
        The agent is added to the queue at t = current_time + predicted_duration
        with destination home.

        :param tx: neo4j database write transaction
        :param agent: agent database object returned from Interface
        :param intf: Interface for database calls

        :return: None
        """
        view = super(HosNode, self).agentprediction(tx, agent, intf)[1:]
        clock = intf.gettime(tx)
        ag = Agent(agent["id"])
        ag.logging(tx, intf, "Hos admitted, " + str(clock))
        mean = min(-9 * min(agent["mob"], 1) + 14, -9 * (min(agent["conf_res"], 1) + min(agent["mob_res"], 1)) + 14)
        time = npr.poisson(mean, 1)[0]
        if clock + time not in self.queue.keys():
            self.queue[clock + time] = {}
        dest = [edge for edge in view if edge.end_node["name"] == "Home"]
        self.queue[clock + time][agent["id"]] = (dest[0], time)


class GPNode(FallNode):
    """
    GPNode is a subclass of Fall node which extends the Fall node by filtering the agents perception to redirect the
    agent home or to the hospital. It also gives the agent a referral if they have lower mobility.
    """

    def __init__(self, name="GP"):
        super(FallNode, self).__init__(name)

    def agentsready(self, tx, intf, agentclass="FallAgent"):
        super(FallNode, self).agentsready(tx, intf, agentclass)

    def agentperception(self, tx, agent, intf, dest=None, waittime=None):
        """
        Add aditional filter to direct the agent to Hospital if mobility below 0.6 and home otherwise. If the agent
        is sent home but have mobility below 0.85 they are given a referral.

        :param tx: neo4j database write transaction
        :param agent: agent database object returned by interface
        :param intf: Interface for database calls
        :param dest: Not used here
        :param waittime: Not used here

        :return: perception with either Home or Hospital as the only destination
        """
        view = super(GPNode, self).agentperception(tx, agent, intf, dest, waittime)
        if agent["mob"] < 0.6:
            view = [edge for edge in view if edge.end_node["name"] == "Hos"]
        else:
            view = [edge for edge in view if edge.end_node["name"] == "Home"]
            if agent["mob"] < 0.85:
                intf.updateagent(tx, agent["id"], "referral", True)
        return view

    def agentprediction(self, tx, agent, intf):
        return None
        # No queue so prediction not needed


class SocialNode(FallNode):
    """
    Currently a generic FallNode with name "Social"
    """

    def __init__(self, name="Social"):
        super(FallNode, self).__init__(name)

    def agentsready(self, tx, intf, agentclass="FallAgent"):
        super(FallNode, self).agentsready(tx, intf, agentclass)

    def agentperception(self, tx, agent, intf, dest=None, waittime=None):
        view = super(SocialNode, self).agentperception(tx, agent, intf, dest, waittime)
        return view

    def agentprediction(self, tx, agent, intf):
        return None
        # No queue so prediction not needed


class InterventionNode(FallNode):
    """
    Extends the Fall Node to manage the capacity limit changes to Intervention nodes and manages the referrals for
    agents
    """

    def __init__(self, name="Intervention"):
        super(FallNode, self).__init__(name)

    def agentsready(self, tx, intf, agentclass="FallAgent"):
        """
        Extends normal Fall node by updating the load value after processing agents.

        :param tx: neo4j database write transaction
        :param intf: Interface for database calls
        :param agentclass: Class to use for agents at this location

        :return: None
        """
        super(FallNode, self).agentsready(tx, intf, agentclass)
        load = len(intf.getnodeagents(tx, self.name))
        intf.updatenode(tx, self.name, "load", load, "name")

    def agentperception(self, tx, agent, intf, dest=None, waittime=None):
        """
        Extends normal Fall Node function by logging the agents attendance at the intervention. It checks if the agent
        has mobility below 0.6, if they do the agent is given a referral (if they didn't have one) else if they have a
        referral is removed.

        :param tx: neo4j database write transaction
        :param agent: agent database object returned from Interface
        :param intf: Interface for calls to database
        :param dest: Not used here
        :param waittime: Not used here

        :return: view from Fall Node agentperception
        """
        view = super(InterventionNode, self).agentperception(tx, agent, intf, dest, waittime)
        ag = Agent(agent["id"])
        ag.logging(tx, intf, self.name + ", " + str(intf.gettime(tx)))
        if agent["mob"] > 0.6:
            intf.updateagent(tx, agent["id"], "referral", "False", "name")
        else:
            intf.updateagent(tx, agent["id"], "referral", "True", "name")
        return view

    def agentprediction(self, tx, agent, intf):
        return None
        # No queue so prediction not needed


class CareNode:
    """
    This node is not a true node. It is a sink node which only processes agents on arrival. As such it only has an
    agentsready function which processes the agents out of the system to save database space.
    """

    def __init__(self):
        """
        Sets up node name and data storage for monitor and analysis of system.
        """
        self.name = "Care"
        self.runname = None
        self.agents = 0
        self.interval = 0
        self.mild = 0
        self.moderate = 0
        self.severe = 0

    def agentsready(self, tx, intf):
        """
        Saves out the log strings of all agents at the Care Node using the runname aquired from the database. Updates
        its own track of average number of falls and length of interval using information in agent logs. Also updates
        the total number of agents that have left the system. It then deletes the agents at the Care node.

        :param tx: neo4j database write transaction
        :param intf: Interface for database calls

        :return: None
        """
        agents = intf.getnodeagents(tx, "Care", "name")
        if not self.runname:
            self.runname = intf.getrunname(tx)
        file = open(specification.savedirectory + "AgentLogscareag_" + self.runname + ".p", 'ab')
        for agent in agents:
            agl = parselog(agent["log"])
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
            intf.updatenode(tx, "Care", "interval", self.interval, "name")
            intf.updatenode(tx, "Care", "mild", self.mild, "name")
            intf.updatenode(tx, "Care", "moderate", self.moderate, "name")
            intf.updatenode(tx, "Care", "severe", self.severe, "name")
            intf.updatenode(tx, "Care", "agents", self.agents, "name")
            aglog = "Agent " + str(agent["id"]) + ": " + agent["log"]
            pickle.dump(aglog, file)
            intf.deleteagent(tx, agent, "id")
        # file.close()
        return None

    # While Care is not actually a node it does have an agentready function which is triggered on arrival.
    # This causes the agents log to be saved to file.
