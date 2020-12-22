import SPmodelling.Agent
import SPmodelling.Agent as SPag
import numpy.random as npr
import SPmodelling.Interface as intf
from neobolt.exceptions import TransientError
import specification


def wellbeing_check(tx, agent, fall=None):
    """
    Checks the agents current wellbeing based on its mobility and fall parameter and updates the wellbeing paramater.

    :param tx: neo4j database write transaction
    :param agent: agent tuple - id, label, id type
    :param fall: string indicating what type of fall the agent has just undergone, if None the agent has not just fallen

    :return: string to be added to agent log
    """
    wellbeing = intf.get_node_value(tx, agent, "wellbeing")
    if fall and fall != "Mild":
        if wellbeing != "Fallen":
            wellbeing = "Fallen"
            intf.update_agent(tx, agent, "wellbeing", wellbeing)
            clock = intf.get_time(tx)
            return ", (Fallen, " + str(clock) + ")"
    else:
        mobility = intf.get_node_value(tx, agent, "mob")
        if mobility == 0:
            if wellbeing != "Fallen":
                wellbeing = "Fallen"
                intf.update_agent(tx, agent, "wellbeing", wellbeing)
                clock = intf.get_time(tx)
                return ", (Fallen, " + str(clock) + ")"
        elif mobility > 1:
            if wellbeing != "Healthy":
                wellbeing = "Healthy"
                intf.update_agent(tx, agent, "wellbeing", wellbeing)
                clock = intf.get_time(tx)
                return ", (Healthy, " + str(clock) + ")"
        elif mobility <= 1:
            if wellbeing == "Healthy":
                wellbeing = "At risk"
                intf.update_agent(tx, agent, "wellbeing", wellbeing)
                clock = intf.get_time(tx)
                return ", (At risk, " + str(clock) + ")"
    return None


def positive(num):
    """
    basic function to floor a number at zero

    :param num: real number

    :return: real number
    """
    if num < 0:
        return 0
    else:
        return num


def logging(tx, agent, entry):
    """
    Utility function for adding information to the agents log of its activities

    :param tx: neo4j database write transaction
    :param entry: String to be added to the log
    :param agent: agent tuple - id, label and id type

    :return: None
    """
    log = intf.get_node_value(tx, agent, "log")
    log = log + ", (" + entry + ")"
    intf.update_agent(tx, agent, "log", str(log))


class Patient(SPmodelling.Agent.MobileAgent, SPmodelling.Agent.CommunicativeAgent):
    """
    Agent for modelling the physical movement of patients with declining mobility
    """

    def __init__(self, agent_id):
        """
        :param agent_id: integer id number for patient
        """
        super(Patient, self).__init__(agent_id, nuid="name")
        self.mobility = None
        self.resources = None
        self.mood = None
        self.inclination = None
        self.current_resources = None
        self.view = None
        self.log = None
        self.fall = ""
        self.wellbeing = None
        self.referral = None
        self.friendliness = 6
        self.colocated = None
        self.contacts = None
        self.new_contacts = None
        self.carers = None
        self.id = agent_id

    def generator(self, tx, params):
        """
        Generates Fall Agents and inserts them into the network at the home node.

        :param self: Agent
        :param tx: neo4j database transaction with write permission
        :param params: [mobility, mood, resources, inclination] these are the means for the normal distributions
        sampled to set parameters

        :return: None
        """
        super(Patient, self).generator(tx, params)
        # generate a random set of parameters based on a distribution with mean set by params
        mobility, mood, resources, inclination, min_friendliness, max_friendliness = tuple(params)
        self.mobility = npr.normal(mobility, 0.05)  # draw from normal distribution centred on given value
        self.resources = npr.normal(resources, 0.05)
        self.mood = npr.normal(mood, 0.05)
        self.inclination = [npr.normal(x) for x in inclination]
        self.inclination = [inc / sum(self.inclination) for inc in self.inclination]
        self.wellbeing = "'At risk'"
        self.referral = "false"
        self.friendliness = npr.choice(range(min_friendliness, max_friendliness + 1), 1)[0]
        # Add agent with params to ind in graph with resources starting at 0
        time = intf.get_time(tx)
        self.log = "(CREATED," + str(time) + ")"
        intf.add_agent(tx, ["Home", "Node", "name"], "Agent:Patient",
                       {"mob": self.mobility, "mood": self.mood, "resources": self.resources,
                        "inclination": self.inclination, "wellbeing": self.wellbeing,
                        "log": "'" + self.log + "'", "referral": self.referral, "friendliness": self.friendliness,
                        "opinion": 0})

    def move_perception(self, tx, perception):
        """
        Patient perception function. Filters based on agent having sufficient resources for edge and end node.

        :param tx: neo4j write transaction
        :param perception: perception received from the node

        :return: None
        """
        super(Patient, self).move_perception(tx, perception)
        if type(self.view) == list:
            edges = self.view
        else:
            edges = [self.view]
        # filter out options requiring too much resources
        self.mobility = intf.get_node_value(tx, [self.id, "Patient", "id"], "mob")
        self.resources = intf.get_node_value(tx, [self.id, "Patient", "id"], "resources")
        self.current_resources = self.resources
        if len(edges) > 1:
            valid_edges = SPag.filter_resource(tx, [self.id, "Patient", "id"], edges, "resources", "resources")
            self.view = valid_edges

    def move_choose(self, tx, perception):
        """
        Patients conscious choice from possible edges. This is based on the patients mood exceeds the current threshold
        for that edge. If the agent has the mood for multiple choices the final choice is made as a weighted sampling of
        all possible choices with weights based on the Patients inclination applied to the types of edges.

        :param tx: neo4j database write transaction
        :param perception: perception from node perception function.

        :return: single edge as final choice
        """
        super(Patient, self).move_choose(tx, perception)
        # filter out options where the agent does not reach the mood threshold
        self.mood = intf.get_node_value(tx, [self.id, "Patient", "id"], "mood")
        self.inclination = intf.get_node_value(tx, [self.id, "Patient", "id"], "inclination")
        self.log = intf.get_node_value(tx, [self.id, "Patient", "id"], "log")
        self.wellbeing = intf.get_node_value(tx, [self.id, "Patient", "id"], "wellbeing")
        self.referral = intf.get_node_value(tx, [self.id, "Patient", "id"], "referral")
        self.view = SPag.filter_threshold(tx, [self.id, "Patient", "id"], self.view, "mood", "mood")
        if len(self.view) <= 1:
            return None
        options = self.view
        if type(options) != list:
            options = [options]
        choice = options[0]
        # Assign weights based on edge types
        types = [edge["type"] for edge in options]
        soc_nodes = [i for i, x in enumerate(types) if x == "social"]
        soc_paths = [intf.shortest_social_path(tx, [options[soc_node].end_node["name"], "Node", "name"],
                                               [self.id, "Agent", "id"]) for soc_node in soc_nodes]
        soc_paths = [path for path in soc_paths if path]
        edge_types = ["social", "fall", "medical", "inactive", "immobility"]
        types = [edge_types.index(label) for label in types]
        weights = [positive(self.inclination[label]) for label in types]
        if len(soc_paths) > 1:
            rank_length = min(soc_paths)
            check_rank = max(soc_paths)
            adjustment = 1
            while min(soc_paths) < check_rank:
                temp = soc_paths.index(min(soc_paths))
                weights[soc_nodes[temp]] * adjustment
                soc_paths[temp] = check_rank + 1
                if not min(soc_paths) == rank_length:
                    adjustment = adjustment - 0.2
                    rank_length = min(soc_paths)
            if sum(weights):
                weights = [w / sum(weights) for w in weights]
                sample = npr.choice(range(len(options)), 1, p=weights)
            else:
                sample = npr.choice(range(len(options)), 1)
            choice = options[sample[0]]
        return choice

    def move_learn(self, tx, choice, service=None):
        """
        Agent is changed by node and can change node and edge it arrived by. This can include changes to decision
         making parameters.

        :param tx: neo4j database write transaction
        :param choice: Chosen edge for move
        :param service: provided by node, defines how the node and services interact at the agents new node

        :return: None
        """
        super(Patient, self).move_learn(tx, choice, service)
        # modify mob, conf, res and resources based on new node
        if not self.current_resources:
            self.current_resources = self.resources
        wellbeing_change = wellbeing_check(tx, [self.id, "Patient", "id"], self.fall)
        if wellbeing_change:
            self.log = self.log + wellbeing_change
        # switch for type of node and service choice, call service function if service chosen
        if service and not choice.end_node["servicemodel"] == "core":
            serv_class = specification.ServiceClasses[service[0]]
            serv = serv_class(tx)
            serv.provide_service(tx, [self.id, "Agent", "id"])
        if choice.end_node["servicemodel"] in ["core", "additional"] or not service:
            if "modm" in choice.end_node:
                self.mobility = positive(npr.normal(choice.end_node["modm"], 0.05) + self.mobility)
                intf.update_agent(tx, [self.id, "Patient", "id"], "mob", self.mobility)
                # check for updates to wellbeing and log any changes
                wellbeing_change = wellbeing_check(tx, [self.id, "Patient", "id"], self.fall)
                if wellbeing_change:
                    self.log = self.log + wellbeing_change
            if "modmood" in choice.end_node:
                self.mood = positive(npr.normal(choice.end_node["modmood"], 0.05) + self.mood)
                intf.update_agent(tx, [self.id, "Patient", "id"], "mood", self.mood)
            if "resources" in choice.end_node:
                self.current_resources = npr.normal(choice.end_node["resources"], 0.05) + self.current_resources
                resources_change = self.current_resources - self.resources
                intf.update_agent(tx, [self.id, "Patient", "id"], "resources", self.current_resources)
                # Update inclination to different edge types based on resource profit/loss of move
                edge_types = ["social", "fall", "medical", "inactive"]
                for i in range(len(edge_types)):
                    if choice["type"] == edge_types[i]:
                        if resources_change < 0:
                            self.inclination[i] = self.inclination[i] + 1
                        elif resources_change > 0:
                            self.inclination[i] = positive(self.inclination[i] - 1)
        # change to inclination based on mobility, resources and mood
        if self.current_resources > 0.8:
            self.inclination[0] = self.inclination[0] + 1
        elif self.current_resources < 0.2:
            self.inclination[3] = self.inclination[3] + 1
        if self.mood > 0.8:
            self.inclination[0] = self.inclination[0] - 1
            self.inclination[3] = self.inclination[3] + 1
        elif self.mood < 0.2:
            self.inclination[0] = self.inclination[0] + 1
            self.inclination[3] = self.inclination[3] - 1
        if self.mobility < 0.4:
            self.inclination[2] = self.inclination[2] + 1
            self.inclination[3] = self.inclination[3] + 1
        elif self.mobility > 0.8:
            self.inclination[3] = self.inclination[3] - 1
        agent = [self.id, "Patient", "id"]
        intf.update_agent(tx, agent, "inclination", self.inclination)
        # Update opinion
        if choice["type"] == "medical":
            if self.mobility > 0.8:
                opinion = 1
            elif self.mobility < 0.5:
                opinion = -1
            else:
                opinion = 0
        else:
            if self.mobility < 0.5:
                opinion = -1
            else:
                opinion = 0
        clusters = [[clust, "Cluster", "id"] for clust in intf.check_groupings(tx, agent)]
        total_strength = 0
        # check the cluster opinion for each cluster and create weighted average based on strength of connection
        if clusters:
            for cluster in clusters:
                op = intf.get_node_value(tx, cluster, "opinion")
                if opinion * op > 0:
                    strength = intf.get_edge_value(tx, [agent, cluster], "connectedness")
                    total_strength = total_strength + strength
            if total_strength:
                group_influenced_opinion = opinion * total_strength
            else:
                group_influenced_opinion = opinion
        else:
            group_influenced_opinion = opinion
        scaled_opinion = opinion * (0.07 * abs(opinion * group_influenced_opinion) - 0.06)
        intf.update_agent(tx, agent, "opinion", scaled_opinion)
        # log going into care
        if choice.end_node["name"] == "Care":
            clock = intf.get_time(tx)
            self.log = self.log + ", (Care, " + str(clock) + ")"
        if "cap" in choice.end_node.keys():
            intf.update_node(tx, [choice.end_node["name"], "Node", "name"], "load", choice.end_node["load"] + 1)
        if intf.locate_agent(tx,[self.id, "Patient", "id"])["name"] == "Hos" and choice.end_node["name"] != "Hos":
            clock = intf.get_time(tx)
            self.log = self.log + ", (Discharged, " + str(clock) + ")"
        intf.update_agent(tx, [self.id, "Patient", "id"], "log", str(self.log))

    def move_payment(self, tx):
        """
        Modifies chosen edge and agent. These include mobility, confidence and resources modifications.

        :param tx: neo4j database write transaction

        :return: None
        """
        super(Patient, self).move_payment(tx)
        # Deduct resources used on edge
        if "resources" in self.choice.keys():
            if "resources" in self.choice.end_node.keys():
                if not self.current_resources:
                    self.current_resources = self.resources
                if specification.carers and self.choice["resources"] + \
                        self.choice.end_node["resources"] > self.current_resources:
                    # Check for carers
                    carers = intf.agent_contacts(tx, [self.id, "Patient", "id"], "Carer")
                    # Check for sufficient resources (in
                    if carers:
                        carers = [carer for carer in carers if carer.end_node["resources"]]
                        for carer in carers:
                            if carer.end_node["resources"] >= self.choice["resources"]:
                                intf.update_node(tx, [carer.end_node["id"], "Patient", "id"], "resources",
                                                 carer.end_node["resources"] - self.choice["resources"], label='Carer')
                                self.current_resources = self.current_resources + self.choice["resources"]
                                intf.update_agent(tx, [self.id, "Patient", "id"], "resources", self.current_resources)
                                intf.update_contact_edge(tx, [self.id, "Patient", "id"],
                                                         [carer.end_node["id"], "Carer", "id"], "utilization",
                                                         intf.gettime(tx))
                                break
                        else:
                            return False
                elif self.choice["resources"] + self.choice.end_node["resources"] > self.current_resources:
                    return False
            self.current_resources = npr.normal(self.choice["resources"], 0.05) + self.current_resources
            intf.update_agent(tx, [self.id, "Patient", "id"], "resources", self.current_resources)
        # mod variables based on edges
        if "modm" in self.choice:
            self.mobility = positive(npr.normal(self.choice["modm"], 0.05) + self.mobility)
            intf.update_agent(tx, [self.id, "Patient", "id"], "mob", self.mobility)
            wellbeing_change = wellbeing_check(tx, [self.id, "Patient", "id"], self.fall)
            if wellbeing_change:
                self.log = self.log + wellbeing_change
        if "modmood" in self.choice:
            self.mood = positive(npr.normal(self.choice["modmood"], 0.05) + self.mood)
            intf.update_agent(tx, [self.id, "Patient", "id"], "mood", self.mood)
        intf.update_agent(tx, [self.id, "Patient", "id"], "log", str(self.log))
        return True

    def move_services(self, tx):
        """
        Gathers a list of services available to the agent and selects if they wish to use one.

        :param tx: neo4j database read or write transaction

        :return: A list of services the agent wishes to use
        """
        services = super(Patient, self).move_services(tx)
        if not services:
            return None
        elif "intervention" in [serv[0] for serv in services]:
            if self.mobility < 0.9:
                return [serv for serv in services if serv[0] == "intervention"][0]
        elif "care" in [serv[0] for serv in services]:
            if self.resources < 1:
                return [serv for serv in services if serv[0] == "care"][0]
        else:
            return None

    def move(self, tx, perc):
        """
        Runs complete agent movement algorithm.

        :param tx: neo4j database write transaction
        :param perc: perception provided by the node the agent is currently located at

        :return: Node Agent has moved to
        """
        super(Patient, self).move(tx, perc)

    def logging(self, tx, entry):
        """
        Utility function for adding information to the agents log of its activities

        :param tx: neo4j database write transaction
        :param entry: String to be added to the log

        :return: None
        """
        self.log = intf.get_node_value(tx, [self.id, "Patient", "id"], "log")
        self.log = self.log + ", (" + entry + ")"
        intf.update_agent(tx, [self.id, "Patient", "id"], "log", str(self.log))

    def social_perception(self, tx):
        """
        If not at home, find co-located agents

        :param tx: neo4j database write transaction

        :return: None
        """
        super(Patient, self).social_perception(tx)
        # If not at home, find co-located agents
        try:
            if intf.locate_agent(tx, [self.id, "Patient", "id"])["name"] != "Home":
                self.colocated = intf.co_located(tx, [self.id, "Patient", "id"])
            self.friendliness = intf.get_node_value(tx, [self.id, "Patient", "id"], "friendliness")
        except IndexError:
            return True

    def social_update(self, tx):
        """
        Check agent contacts compare list with co-located agents and update co-located contacts with new last usage

        :param tx: neo4j database write transaction

        :return: None
        """
        super(Patient, self).social_update(tx)
        # Update existing com links with latest co-location
        self.contacts = intf.agent_contacts(tx, [self.id, "Patient", "id"], "Patient")
        if self.contacts and self.colocated:
            update = [contact for contact in self.contacts if contact[1] in self.colocated]
            for contact in update:
                intf.update_contact_edge(tx, [contact[1], "Agent", "id"], [self.id, "Patient", "id"],
                                         "last_usage", intf.get_time(tx))
            self.new_contacts = [contact for contact in self.colocated if contact not in [rel[1]
                                                                                          for rel in update]]

    def social_talk(self, tx):
        """
        Determine if agent forms a new social link with random co-located agent based on their social values and
        shortest social path

        :param tx: neo4j write transaction

        :return: None
        """
        super(Patient, self).social_talk(tx)
        if self.colocated and self.new_contacts:
            self.new_contacts = [nc for nc in self.new_contacts if nc != self.id]
            if self.new_contacts:
                if len(new_contacts) > 1:
                    new_friend = self.new_contacts[npr.choice(range(len(self.new_contacts)))]
                else:
                    new_friend = self.new_contacts[0]
                # Based on relative social values and length of shortest path set probability for forming link with a
                #  randomly sampled co-located unknown agent. social from 2-8 per agent, combined from 4-16.
                #  So combined -4 over 24 gives value between 0 and 0.5 plus the if minimum path greater than 6 nothing,
                #  else from m=2-6 then 1/(2m-2) gives 0.1-0.5 (m=1 or 0 means itself or already connected).
                prob1 = (intf.get_node_value(tx, [new_friend, "Agent", "id"], "friendliness")
                         + self.friendliness - 4) / 24
                while True:
                    try:
                        sp = intf.shortest_path(tx, [self.id, "Patient", "id"],
                                                [new_friend, "Agent", "id"], 'SOCIAL')
                        break
                    except TransientError:
                        pass
                if not sp:
                    sp = float("inf")
                if sp < 2:
                    prob2 = 0
                elif sp > 6:
                    prob2 = 0
                else:
                    prob2 = 1 / (2 * sp - 2)
                if npr.random(1) <= (prob1 + prob2):
                    try:
                        if intf.locate_agent(tx, [self.id, "Patient", "id"])["name"] not in \
                                ["Home", "Social", "SocialLunch", "SocialWalk", "SocialCraft"]:
                            if npr.random(1) < 0.25:
                                ag_type = "professional"
                            else:
                                ag_type = "friend"
                        else:
                            ag_type = "friend"
                        intf.create_edge(tx, [self.id, "Patient", "id"], [new_friend, "Agent", "id"], 'SOCIAL',
                                         parameters='created: ' + str(intf.get_time(tx)) + ', utilization: '
                                                    + str(intf.get_time(tx)) + ', colocation: ' + str(intf.get_time(tx))
                                                    + ", carer: False, type: '" + ag_type + "'")
                    except IndexError:
                        return None
                    self.contacts = new_friend
                else:
                    self.contacts = None
            else:
                self.contacts = None
        else:
            self.contacts = None

    def social_listen(self, tx):
        """
        If the agent has a new social link check if the new friend has a link to a carer if they do for a random carer
        they form a link with a .5 chance.

        :param tx: neo4j write transaction

        :return: None
        """
        super(Patient, self).social_listen(tx)
        if specification.carers and self.contacts and not isinstance(self.contacts, list):
            carers = intf.agent_contacts(tx, [self.contacts["id"], "Patient", "id"], "Carer")
            if carers:
                carer = carers[npr.choice(range(len(carers)))]
                if npr.random(1) < 0.5:
                    if (carer.end_node["id"] or carer.end_node["id"] == 0) and carer.end_node["id"] != self.id:
                        carer_id = carer.end_node["id"]
                    elif carer.end_node["id"] == self.id and not carer.start_node["id"]:
                        carer_id = carer.end_node["id"]
                    else:
                        carer_id = carer.start_node["id"]
                    intf.create_edge(tx, [self.id, "Patient", "id"], [carer_id, "Carer", "id"], 'SOCIAL', 'created: '
                                     + str(intf.gettime(tx)) + ', colocation: ' + str(intf.gettime(tx))
                                     + ', utilization: ' + str(intf.gettime(tx))
                                     + ', carer: True, type: "professional"')

    def social_react(self, tx):
        """
        If the agent now has more social bonds than they can manage we drop new non carer friends then those not used
        recently and finally reduce the carers from most recent.

        :param tx: neo4j write transaction

        :return: None
        """
        super(Patient, self).social_react(tx)
        self.contacts = intf.agent_contacts(tx, [self.id, "Patient", "id"], "SOCIAL")
        # age out social contacts
        for contact in self.contacts:
            if contact[0]["type"] == "professional" and intf.get_time(tx) - contact[0]["colocation"] > 60:
                intf.delete_contact(tx, [self.id, "Patient", "id"], [contact[1], "Agent", "id"])
            elif contact[0]["type"] == "friend" and intf.get_time(tx) - contact[0]["colocation"] > 120:
                intf.delete_contact(tx, [self.id, "Patient", "id"], [contact[1], "Agent", "id"])
            elif contact[0]["type"] == "family" and intf.get_time(tx) - contact[0]["colocation"] > 240:
                intf.delete_contact(tx, [self.id, "Patient", "id"], [contact[1], "Agent", "id"])
        self.contacts = intf.agent_contacts(tx, [self.id, "Patient", "id"], "SOCIAL")
        if self.contacts:
            while len(self.contacts) > self.friendliness:
                for contact in self.contacts:
                    if intf.get_time(tx) - contact[0]['created'] < 5:
                        intf.delete_contact(tx, [self.id, "Patient", "id"], [contact[1], "Agent", "id"])
                    self.contacts = intf.agent_contacts(tx, [self.id, "Patient", "id"], "SOCIAL")
        oldest_usage = 0
        contact_drop = None
        while len(self.contacts) > self.friendliness:
            for contact in self.contacts:
                if intf.get_time(tx) - contact[0]["usage"] > oldest_usage:
                    contact_drop = contact
                    oldest_usage = intf.get_time(tx) - contact["usage"]
            if contact_drop:
                intf.delete_contact(tx, [self.id, "Patient", "id"], [contact_drop[1], "Agent", "id"])


class Carer(SPmodelling.Agent.MobileAgent, SPmodelling.Agent.CommunicativeAgent):
    """
    Physical and mobile agent mimics an individual who may not have declining mobility but helps
    those who do.
    """

    def __init__(self, agent_id):
        """
        :param agent_id: unique integer id for carer
        """
        self.resources = None
        self.mobility = None
        self.current_resources = None
        self.friendliness = 6
        self.colocated = None
        self.contacts = None
        self.carers = None
        self.view = None
        self.log = None
        self.id = agent_id
        self.mood = None
        self.inclination = None
        self.wellbeing = None
        self.referral = None
        self.fall = None
        self.social = None

    def generator(self, tx, params):
        """
        Generates Carer agents and adds them to the system.

        :param tx: neo4j database write transaction
        :param params: mean values for parameters of the carer agent

        :return: None
        """
        super(Carer, self).generator(tx, params)
        # generate a random set of parameters based on a distribution with mean set by params
        [mobility, mood, resources, inclination, min_social, max_social] = params
        self.mobility = npr.normal(mobility, 0.05)  # draw from normal distribution centred on given value
        self.resources = npr.normal(resources, 0.05)
        self.mood = npr.normal(mood, 0.05)
        self.inclination = [npr.normal(x) for x in inclination]
        self.inclination = [inc / sum(self.inclination) for inc in self.inclination]
        self.wellbeing = "'Healthy'"
        self.referral = "false"
        self.social = npr.choice(range(min_social, max_social + 1), 1)[0]
        # Add agent with params to ind in graph with resources starting at 0
        time = tx.run("MATCH (a:Clock) RETURN a.time").values()[0][0]
        self.log = "(CREATED," + str(time) + ")"
        intf.addagent(tx, {"name": "Home"}, "Agent:Carer",
                      {"mob": self.mobility, "mood": self.mood, "resources": self.resources,
                       "inclination": self.inclination, "wellbeing": self.wellbeing,
                       "log": "'" + self.log + "'", "referral": self.referral, "social": self.social}, "name")

    def perception(self, tx, perc):
        """
        Carer perception function. Filters based on agent having sufficient resources for edge and end node.

        :param tx: neo4j write transaction
        :param perc: perception received from the node

        :return: None
        """
        super(Carer, self).perception(tx, perc)
        if type(self.view) == list:
            edges = self.view
        else:
            edges = [self.view]
        # filter out options requiring too much resources
        valid_edges = []
        self.mobility = intf.getnodevalue(tx, self.id, "mob", "Carer", "id")
        self.resources = intf.getnodevalue(tx, self.id, "resources", "Carer", "id")
        self.current_resources = self.resources
        if len(self.view) > 1:
            for edge in edges:
                if not edge.end_node["name"] in ["Care", "GP", "Hos"]:
                    cost = 0
                    if edge.end_node["resources"]:
                        cost = cost + edge.end_node["resources"]
                    if self.resources > -cost:
                        valid_edges = valid_edges + [edge]
        else:
            valid_edges = self.view
        self.view = valid_edges

    def choose(self, tx, perc):
        """
        Carer conscious choice from possible edges. This is based on the patients mood exceeds the current threshold
        for that edge. If the agent has the mood for multiple choices the final choice is made as a weighted sampling of
        all possible choices with weights based on the Carer inclination applied to the types of edges.

        :param tx: neo4j database write transaction
        :param perc: perception from node perception function.

        :return: single edge as final choice
        """
        super(Carer, self).choose(tx, perc)
        # filter out options where the agent does not reach the mood threshold
        options = []
        self.mood = intf.getnodevalue(tx, self.id, "mood", "Carer")
        self.inclination = intf.getnodevalue(tx, self.id, "inclination", "Carer")
        self.log = intf.getnodevalue(tx, self.id, "log", "Carer")
        self.wellbeing = intf.getnodevalue(tx, self.id, "wellbeing", "Carer")
        if len(self.view) < 2:
            if type(self.view) == list and self.view:
                choice = self.view[0]
            else:
                choice = self.view
        else:
            for edge in self.view:
                if edge["mood"] <= self.mood:
                    options = options + [edge]
            # choose based on random sample bias by patients inclination
            if not options:
                return None
            elif not [i for i in options if not i.end_node["name"] in ["Hos", "GP", "Intervention",
                                                                       "InterventionOpen", "Care"]]:
                return None
            types = [edge["type"] for edge in options]
            soc_nodes = [i for i, x in enumerate(types) if x == "social"]
            soc_paths = [intf.shortestsocialpath(tx, options[soc_node].end_node["name"], self.id) for soc_node in
                         soc_nodes]

            edge_types = ["social", "fall", "medical", "inactive"]
            types = [edge_types.index(label) for label in types]
            weights = [positive(self.inclination[label]) for label in types]
            rank_length = min(soc_paths)
            check_rank = max(soc_paths)
            adjustment = 1
            while min(soc_paths) < check_rank:
                temp = soc_paths.index(min(soc_paths))
                weights[soc_nodes[temp]] * adjustment
                soc_paths[temp] = check_rank + 1
                if not min(soc_paths) == rank_length:
                    adjustment = adjustment - 0.2
                    rank_length = min(soc_paths)
            if sum(weights):
                weights = [w / sum(weights) for w in weights]
                sample = npr.choice(range(len(options)), 1, p=weights)
            else:
                sample = npr.choice(range(len(options)), 1)

            choice = options[sample[0]]
        return choice

    def learn(self, tx, choice):
        """
        Agent is changed by node and can change node and edge it arrived by. This can include changes to decision
         making parameters.

        :param tx: neo4j database write transaction
        :param choice: Chosen edge for move

        :return: None
        """
        super(Carer, self).learn(tx, choice)
        # modify mob, conf, res and resources based on new node
        if self.fall:
            intf.addagentlabel(tx, self.id, "Patient")
        if self.fall and self.fall != "Mild":
            if self.wellbeing != "Fallen":
                self.wellbeing = "Fallen"
                intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                clock = tx.run("MATCH (a:Clock) "
                               "RETURN a.time").values()[0][0]
                self.log = self.log + ", (Fallen, " + str(clock) + ")"
        if "modm" in choice.end_node and choice.end_node["name"] != "Home":
            self.mobility = positive(npr.normal(choice.end_node["modm"], 0.05) + self.mobility)
            intf.updateagent(tx, self.id, "mob", self.mobility)
            # check for updates to wellbeing and log any changes
            if self.mobility == 0:
                if self.wellbeing != "Fallen":
                    self.wellbeing = "Fallen"
                    intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                    clock = tx.run("MATCH (a:Clock) "
                                   "RETURN a.time").values()[0][0]
                    self.log = self.log + ", (Fallen, " + str(clock) + ")"
            elif self.mobility > 1:
                if self.wellbeing != "Healthy":
                    self.wellbeing = "Healthy"
                    intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                    clock = tx.run("MATCH (a:Clock) "
                                   "RETURN a.time").values()[0][0]
                    self.log = self.log + ", (Healthy, " + str(clock) + ")"
            elif self.mobility <= 1:
                if self.wellbeing == "Healthy":
                    self.wellbeing = "At risk"
                    intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                    clock = tx.run("MATCH (a:Clock) "
                                   "RETURN a.time").values()[0][0]
                    self.log = self.log + ", (At risk, " + str(clock) + ")"
        if "modmood" in choice.end_node:
            self.mood = positive(npr.normal(choice.end_node["modmood"], 0.05) + self.mood)
            intf.updateagent(tx, self.id, "mood", self.mood)
        if "resources" in choice.end_node:
            self.current_resources = npr.normal(choice.end_node["resources"], 0.05) + self.current_resources
            resources_change = self.current_resources - self.resources
            intf.updateagent(tx, self.id, "resources", self.current_resources)
            edge_types = ["social", "fall", "medical", "inactive"]
            for i in range(len(edge_types)):
                if choice["type"] == edge_types[i]:
                    if resources_change < 0:
                        self.inclination[i] = self.inclination[i] + 1
                    elif resources_change > 0:
                        self.inclination[i] = positive(self.inclination[i] - 1)
        # change to inclination based on mobility, resources and mood
        if self.current_resources > 0.8:
            self.inclination[0] = self.inclination[0] + 1
        elif self.current_resources < 0.2:
            self.inclination[3] = self.inclination[3] + 1
        if self.mood > 0.8:
            self.inclination[0] = self.inclination[0] - 1
            self.inclination[3] = self.inclination[3] + 1
        elif self.mood < 0.2:
            self.inclination[0] = self.inclination[0] + 1
            self.inclination[3] = self.inclination[3] - 1
        if self.mobility < 0.4:
            self.inclination[2] = self.inclination[2] + 1
            self.inclination[3] = self.inclination[3] + 1
        elif self.mobility > 0.8:
            self.inclination[3] = self.inclination[3] - 1
        intf.updateagent(tx, self.id, "inclination", self.inclination)
        if "cap" in choice.end_node.keys():
            intf.updatenode(tx, choice.end_node["name"], "load", choice.end_node["load"] + 1, "name")
        intf.updateagent(tx, self.id, "log", str(self.log))

    def payment(self, tx):
        """
        Modifies chosen edge and agent. These include mobility, confidence and resources modifications. For
        Carers mobility only changes in the case of a fall.

        :param tx: neo4j database write transaction

        :return: None
        """
        super(Carer, self).payment(tx)
        # Deduct resources used on edge
        if "resources" in self.choice.keys():
            self.current_resources = npr.normal(self.choice["resources"], 0.05) + self.current_resources
            intf.updateagent(tx, self.id, "resources", self.current_resources)
        # mod variables based on edges
        if "modm" in self.choice and self.fall:
            self.mobility = positive(npr.normal(self.choice["modm"], 0.05) + self.mobility)
            intf.updateagent(tx, self.id, "mob", self.mobility)
            if self.mobility == 0:
                if self.wellbeing != "Fallen":
                    self.wellbeing = "Fallen"
                    intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                    clock = tx.run("MATCH (a:Clock) "
                                   "RETURN a.time").values()[0][0]
                    self.log = self.log + ", (Fallen, " + str(clock) + ")"
            elif self.mobility > 1:
                if self.wellbeing != "Healthy":
                    self.wellbeing = "Healthy"
                    intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                    clock = tx.run("MATCH (a:Clock) "
                                   "RETURN a.time").values()[0][0]
                    self.log = self.log + ", (Healthy, " + str(clock) + ")"
            elif self.mobility <= 1:
                if self.wellbeing == "Healthy":
                    self.wellbeing = "At risk"
                    intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                    clock = tx.run("MATCH (a:Clock) "
                                   "RETURN a.time").values()[0][0]
                    self.log = self.log + ", (At risk, " + str(clock) + ")"
        if "modmood" in self.choice:
            self.mood = positive(npr.normal(self.choice["modmood"], 0.05) + self.mood)
            intf.updateagent(tx, self.id, "mood", self.mood)
        return True

    def move(self, tx, perc):
        """
        Runs complete agent movement algorithm.

        :param tx: neo4j database write transaction
        :param perc: perception provided by the node the agent is currently located at

        :return: Node Agent has moved to
        """
        # check if node has patient label as well as carer
        if "Patient" not in intf.checknodelabel(tx, self.id, "id") and "Carer" in intf.checknodelabel(tx, self.id,
                                                                                                      "id"):
            super(Carer, self).move(tx, perc)

    def logging(self, tx, entry):
        """
        Utility function for adding information to the agents log of its activities

        :param tx: neo4j database write transaction
        :param entry: String to be added to the log

        :return: None
        """
        self.log = intf.getnodevalue(tx, self.id, "log", "Agent")
        self.log = self.log + ", (" + entry + ")"
        intf.updateagent(tx, self.id, "log", str(self.log))

    def look(self, tx):
        """
        If not at home, find co-located agents

        :param tx: neo4j database write transaction

        :return: None
        """
        "Carer Looking"
        super(Carer, self).look(tx)
        # If not at home, find co-located agents
        try:
            if intf.locateagent(tx, self.id)["name"] != "Home":
                self.colocated = intf.colocated(tx, self.id)
        except IndexError:
            return True
        self.social = intf.getnodevalue(tx, self.id, "social", "Agent")

    def update(self, tx):
        """
        Check agent contacts compare list with co-located agents and update co-located contacts with new last usage

        :param tx: neo4j database write transaction

        :return: None
        """
        super(Carer, self).update(tx)
        # Update existing com links with latest co-location
        self.contacts = intf.agentcontacts(tx, self.id, "Agent")
        if self.contacts and self.colocated:
            update = [contact for contact in self.contacts if contact.end_node in self.colocated]
            for contact in update:
                intf.updatecontactedge(tx, contact.end_node["id"], self.id, "colocation", intf.gettime(tx))

    def talk(self, tx):
        """
        Determine if agent forms a new social link with random co-located agent based on their social values and
        shortest social path

        :param tx: neo4j write transaction

        :return: None
        """
        super(Carer, self).talk(tx)
        if self.colocated:
            newcontacts = [nc for nc in self.colocated if nc not in self.contacts]
            if newcontacts:
                if len(newcontacts) > 1:
                    newfriend = newcontacts[npr.choice(range(len(newcontacts)))]
                else:
                    newfriend = newcontacts[0]
                # Based on relative social values and length of shortest path set probability for forming link with a
                #  randomly sampled co-located unknown agent. social from 2-8 per agent, combined from 4-16.
                #  So combined -4 over 24 gives value between 0 and 0.5 plus the if minimum path greater than 6 nothing,
                #  else from m=2-6 then 1/(2m-2) gives 0.1-0.5 (m=1 or 0 means itself or already connected).
                prob1 = (newfriend["social"] + self.social - 4) / 24
                sp = intf.shortestpath(tx, self.id, newfriend["id"], 'Agent', 'SOCIAL')
                if sp < 2:
                    prob2 = 0
                elif sp > 6:
                    prob2 = 0
                else:
                    prob2 = 1 / (2 * sp - 2)
                if npr.random(1) <= (prob1 + prob2):
                    try:
                        if intf.locateagent(tx, self.id)["name"] not in ["Home", "Social", "SocialLunch", "SocialWalk",
                                                                         "SocialCraft"]:
                            if npr.random(1) < 0.25:
                                agtype = '"professional"'
                            else:
                                agtype = '"friend"'
                        else:
                            agtype = '"friend"'
                        intf.createedge(tx, self.id, newfriend["id"], 'Agent', 'Agent', 'SOCIAL', 'created: '
                                        + str(intf.gettime(tx)) + ', utilization: ' + str(intf.gettime(tx))
                                        + ', colocation: ' + str(intf.gettime(tx))
                                        + ", carer: False, type: '" + agtype + "'")
                    except IndexError:
                        return None
                    self.contacts = newfriend
                else:
                    self.contacts = None
            else:
                self.contacts = None
        else:
            self.contacts = None

    def listen(self, tx):
        """
        If carers are being used:
        If the agent has a new social link check if the new friend has a link to a carer if they do for a random carer
        they form a social link with a .5 chance.
        Else nothing

        :param tx: neo4j write transaction

        :return: None
        """
        super(Carer, self).listen(tx)
        if self.contacts and not isinstance(self.contacts, list):
            if specification.carers:
                carers = intf.agentcontacts(tx, self.contacts["id"], "Agent", "Carer")
                if carers:
                    carer = carers[npr.choice(range(len(carers)))]
                    if npr.random(1) < 0.5:
                        if (carer.end_node["id"] or carer.end_node["id"] == 0) and carer.end_node["id"] != self.id:
                            carer_id = carer.end_node["id"]
                        elif carer.end_node["id"] == self.id and not carer.start_node["id"]:
                            carer_id = carer.end_node["id"]
                        else:
                            carer_id = carer.start_node["id"]
                        intf.createedge(tx, self.id, carer_id, 'Carer', 'Carer', 'SOCIAL', 'created: '
                                        + str(intf.gettime(tx)) + ', utilization: ' + str(intf.gettime(tx))
                                        + ', colocation: ' + str(intf.gettime(tx))
                                        + ', carer: True, type: "professional"')

    def react(self, tx):
        """
        If the agent now has more social bonds than they can manage we drop new non carer friends then those not used
        recently and finally reduce the carers from most recent.

        :param tx: neo4j write transaction

        :return: None
        """
        super(Carer, self).react(tx)
        self.contacts = intf.agentcontacts(tx, self.id, "Agent", "SOCIAL")
        # age out social contacts
        for contact in self.contacts:
            if (contact.end_node["id"] or contact.end_node["id"] == 0) and contact.end_node["id"] != self.id:
                contact_id = contact.end_node["id"]
            elif contact.end_node["id"] == self.id and not contact.start_node["id"]:
                contact_id = contact.end_node["id"]
            else:
                contact_id = contact.start_node["id"]
            if contact["type"] == "professional" and intf.gettime(tx) - contact["colocation"] > 60:
                intf.deletecontact(tx, self.id, contact_id, "Agent", "Agent")
            elif contact["type"] == "friend" and intf.gettime(tx) - contact["colocation"] > 120:
                intf.deletecontact(tx, self.id, contact_id, "Agent", "Agent")
            elif contact["type"] == "family" and intf.gettime(tx) - contact["colocation"] > 240:
                intf.deletecontact(tx, self.id, contact_id, "Agent", "Agent")
        self.contacts = intf.agentcontacts(tx, self.id, "Agent", "SOCIAL")
        while len(self.contacts) > self.social:
            for contact in self.contacts:
                if intf.gettime(tx) - contact['created'] < 5:
                    intf.deletecontact(tx, self.id, contact.end_node["id"], "Agent", "Agent")
                self.contacts = intf.agentcontacts(tx, self.id, "Agent", "SOCIAL")
        oldest_usage = 0
        contact_drop = None
        while len(self.contacts) > self.social:
            for contact in self.contacts:
                if intf.gettime(tx) - contact["utilization"] > oldest_usage:
                    contact_drop = contact
                    oldest_usage = intf.gettime(tx) - contact["utilization"]
            if contact_drop:
                intf.deletecontact(tx, self.id, contact_drop.end_node["id"], "Agent", "Agent")

    def socialise(self, tx):
        """
        Check if carer is also a patient to prevent double processing of agents. If not then the agent socialises as a
        carer

        :param tx: neo4j database write transaction

        :return: None
        """
        if "Patient" not in intf.checknodelabel(tx, self.id, "id"):
            super(Carer, self).socialise(tx)

# noinspection
# class FallAgent(SPmodelling.Agent.MobileAgent):
#     """
#     Agent for modelling patients with declining mobility
#     """
#
#     def __init__(self, agent_id):
#         super(FallAgent, self).__init__(agent_id, nuid="name")
#         self.mobility = None
#         self.resources = None
#         self.confidence = None
#         self.mobility_resources = None
#         self.confidence_resources = None
#         self.current_resources = None
#         self.view = None
#         self.log = None
#         self.fall = ""
#         self.wellbeing = None
#         self.referral = None
#
#     def generator(self, tx, params):
#         """
#         Generates Fall Agents and inserts them into the network at the home node.
#
#         :param self: Agent
#         :param tx: neo4j database transaction with write permission
#         :param params: [mobility, confidence, resources] these are the means for the normal distributions sampled to
#         set parameters
#
#         :return: None
#         """
#         super(FallAgent, self).generator(tx, params)
#         # generate a random set of parameters based on a distribution with mean set by params
#         [mobility, confidence, resources] = params
#         self.mobility = npr.normal(mobility, 0.05)  # draw from normal distribution centred on given value
#         self.resources = npr.normal(resources, 0.05)
#         self.confidence = npr.normal(confidence, 0.05)
#         self.wellbeing = "'At risk'"
#         self.referral = "false"
#         # Add agent with params to ind in graph with resources starting at 0
#         time = tx.run("MATCH (a:Clock) RETURN a.time").values()[0][0]
#         self.log = "(CREATED," + str(time) + ")"
#         intf.addagent(tx, {"name": "Home"}, "Agent", {"mob": self.mobility, "conf": self.confidence, "mob_res": 0,
#                                                       "conf_res": 0, "resources": self.resources,
#                                                       "wellbeing": self.wellbeing,
#                                                       "log": "'" + self.log + "'", "referral": self.referral}, "name")
#
#     def perception(self, tx, perc):
#         """
#         Fall agent perception function. Filters based on agent having sufficient resources for edge and end node.
#
#         :param tx: neo4j write transaction
#         :param perc: perception recieved from the node
#
#         :return: None
#         """
#         super(FallAgent, self).perception(tx, perc)
#         if type(self.view) == list:
#             edges = self.view
#         else:
#             edges = [self.view]
#         # filter out options requiring too much resources
#         valid_edges = []
#         self.mobility = intf.getnodevalue(tx, self.id, "mob", "Agent")
#         self.resources = intf.getnodevalue(tx, self.id, "resources", "Agent")
#         self.current_resources = self.resources
#         if len(self.view) > 1:
#             for edge in edges:
#                 if not edge.end_node["name"] in ["Care", "GP", "Hos"]:
#                     cost = 0
#                     if edge["resources"]:
#                         cost = cost + edge["resources"]
#                     if edge.end_node["resources"]:
#                         cost = cost + edge.end_node["resources"]
#                     if self.resources > -cost:
#                         valid_edges = valid_edges + [edge]
#         else:
#             valid_edges = self.view
#         self.view = valid_edges
#
#     def choose(self, tx, perc):
#         """
#         Agents conscious choice from possible edges. This is based on the effort of the agent calculated from the
#         combination of agent and edge values. If the agent has the effort for multiple choices the worth of the edge
#         is used as a deciding factor.
#
#         :param tx: neo4j database write transaction
#         :param perc: perception from node perception function.
#
#         :return: single edge as final choice
#         """
#         super(FallAgent, self).choose(tx, perc)
#         # filter out options where the agent does not reach the effort threshold
#         options = []
#         self.confidence = intf.getnodevalue(tx, self.id, "conf", "Agent")
#         self.mobility_resources = intf.getnodevalue(tx, self.id, "mob_res", "Agent")
#         self.confidence_resources = intf.getnodevalue(tx, self.id, "conf_res", "Agent")
#         self.log = intf.getnodevalue(tx, self.id, "log", "Agent")
#         self.wellbeing = intf.getnodevalue(tx, self.id, "wellbeing", "Agent")
#         self.referral = intf.getnodevalue(tx, self.id, "referral", "Agent")
#         if len(self.view) < 2:
#             if type(self.view) == list and self.view:
#                 choice = self.view[0]
#             else:
#                 choice = self.view
#         else:
#             for edge in self.view:
#                 if edge["effort"] <= edge["mobility"] * (self.mobility + self.confidence * self.mobility_resources)
#                 + edge["confidence"] * (self.confidence + self.mobility * self.confidence_resources):
#                     options = options + [edge]
#             # choose based on current highest worth edge ignores edges with no worth score, these are not choosable
#             # edges, they are primarily edges indicating a fall
#             if not options:
#                 return None
#             choice = options[0]
#             for edge in options:
#                 if "worth" in edge and "worth" in choice:
#                     if edge["worth"] > choice["worth"]:
#                         choice = edge
#                 elif "worth" in edge:
#                     choice = edge
#         return choice
#
#     def learn(self, tx, choice):
#         """
#         Agent is changed by node and can change node and edge it arrived by. This can include changes to decision
#          making parameters.
#
#         :param tx: neo4j database write transaction
#         :param choice: Chosen edge for move
#
#         :return: None
#         """
#         super(FallAgent, self).learn(tx, choice)
#         # modify mob, conf, res and resources based on new node
#         if self.fall and self.fall != "Mild":
#             if self.wellbeing != "Fallen":
#                 self.wellbeing = "Fallen"
#                 intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
#                 clock = tx.run("MATCH (a:Clock) "
#                                "RETURN a.time").values()[0][0]
#                 self.log = self.log + ", (Fallen, " + str(clock) + ")"
#         if "modm" in choice.end_node:
#             self.mobility = positive(npr.normal(choice.end_node["modm"], 0.05) + self.mobility)
#             intf.updateagent(tx, self.id, "mob", self.mobility)
#             # check for updates to wellbeing and log any changes
#             if self.mobility == 0:
#                 if self.wellbeing != "Fallen":
#                     self.wellbeing = "Fallen"
#                     intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
#                     clock = tx.run("MATCH (a:Clock) "
#                                    "RETURN a.time").values()[0][0]
#                     self.log = self.log + ", (Fallen, " + str(clock) + ")"
#             elif self.mobility > 1:
#                 if self.wellbeing != "Healthy":
#                     self.wellbeing = "Healthy"
#                     intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
#                     clock = tx.run("MATCH (a:Clock) "
#                                    "RETURN a.time").values()[0][0]
#                     self.log = self.log + ", (Healthy, " + str(clock) + ")"
#             elif self.mobility <= 1:
#                 if self.wellbeing == "Healthy":
#                     self.wellbeing = "At risk"
#                     intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
#                     clock = tx.run("MATCH (a:Clock) "
#                                    "RETURN a.time").values()[0][0]
#                     self.log = self.log + ", (At risk, " + str(clock) + ")"
#         if "modc" in choice.end_node:
#             self.confidence = positive(npr.normal(choice.end_node["modc"], 0.05) + self.confidence)
#             intf.updateagent(tx, self.id, "conf", self.confidence)
#         if "modrc" in choice.end_node:
#             self.confidence_resources = positive(npr.normal(choice.end_node["modrc"], 0.05) +
#                                                  self.confidence_resources)
#             intf.updateagent(tx, self.id, "conf_res", self.confidence_resources)
#         if "modrm" in choice.end_node:
#             self.mobility_resources = positive(npr.normal(choice.end_node["modrm"], 0.05) + self.mobility)
#             intf.updateagent(tx, self.id, "mob_res", self.mobility_resources)
#         if "resources" in choice.end_node:
#             self.current_resources = npr.normal(choice.end_node["resources"], 0.05) + self.current_resources
#             intf.updateagent(tx, self.id, "resources", self.current_resources)
#         # log going into care
#         if choice.end_node["name"] == "Care":
#             clock = tx.run("MATCH (a:Clock) "
#                            "RETURN a.time").values()[0][0]
#             self.log = self.log + ", (Care, " + str(clock) + ")"
#         if "cap" in choice.end_node.keys():
#             intf.updatenode(tx, choice.end_node["name"], "load", choice.end_node["load"] + 1, "name")
#         if self.view[0]["name"] == "Hos" and choice.end_node["name"] != "Hos":
#             clock = tx.run("MATCH (a:Clock) "
#                            "RETURN a.time").values()[0][0]
#             self.log = self.log + ", (Discharged, " + str(clock) + ")"
#         intf.updateagent(tx, self.id, "log", str(self.log))
#
#     def payment(self, tx):
#         """
#         Modifies chosen edge and agent. These include mobility, confidence and resources modifications.
#
#         :param tx: neo4j database write transaction
#
#         :return: None
#         """
#         super(FallAgent, self).payment(tx)
#         # Deduct resources used on edge
#         if "resources" in self.choice.keys():
#             self.current_resources = npr.normal(self.choice["resources"], 0.05) + self.current_resources
#             intf.updateagent(tx, self.id, "resources", self.current_resources)
#         # mod variables based on edges
#         if "modm" in self.choice:
#             self.mobility = positive(npr.normal(self.choice["modm"], 0.05) + self.mobility)
#             intf.updateagent(tx, self.id, "mob", self.mobility)
#             if self.mobility == 0:
#                 if self.wellbeing != "Fallen":
#                     self.wellbeing = "Fallen"
#                     intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
#                     clock = tx.run("MATCH (a:Clock) "
#                                    "RETURN a.time").values()[0][0]
#                     self.log = self.log + ", (Fallen, " + str(clock) + ")"
#             elif self.mobility > 1:
#                 if self.wellbeing != "Healthy":
#                     self.wellbeing = "Healthy"
#                     intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
#                     clock = tx.run("MATCH (a:Clock) "
#                                    "RETURN a.time").values()[0][0]
#                     self.log = self.log + ", (Healthy, " + str(clock) + ")"
#             elif self.mobility <= 1:
#                 if self.wellbeing == "Healthy":
#                     self.wellbeing = "At risk"
#                     intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
#                     clock = tx.run("MATCH (a:Clock) "
#                                    "RETURN a.time").values()[0][0]
#                     self.log = self.log + ", (At risk, " + str(clock) + ")"
#         if "modc" in self.choice:
#             self.confidence = positive(npr.normal(self.choice["modc"], 0.05) + self.confidence)
#             intf.updateagent(tx, self.id, "conf", self.confidence)
#
#     def move(self, tx, perc):
#         """
#         Runs complete agent movement algorithm.
#
#         :param tx: neo4j database write transaction
#         :param perc: perception provided by the node the agent is currently located at
#
#         :return: Node Agent has moved to
#         """
#         super(FallAgent, self).move(tx, perc)
#
#     def logging(self, tx, entry):
#         """
#         Utility function for adding information to the agents log of its activities
#
#         :param tx: neo4j database write transaction
#         :param entry: String to be added to the log
#
#         :return: None
#         """
#         self.log = intf.getnodevalue(tx, self.id, "log", "Agent")
#         self.log = self.log + ", (" + entry + ")"
#         intf.updateagent(tx, self.id, "log", str(self.log))
