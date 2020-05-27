from SPmodelling.Agent import Agent
import numpy.random as np


class Patient(Agent):
    """
    Agent for modelling the physical movement of patients with declining mobility
    """

    def __init__(self, agent_id):
        super(Patient, self).__init__(agent_id, nuid="name")
        self.mobility = None
        self.energy = None
        self.mood = None
        self.inclination = None
        self.current_energy = None
        self.view = None
        self.log = None
        self.fall = ""
        self.wellbeing = None
        self.referral = None

    def generator(self, tx, intf, params):
        """
        Generates Fall Agents and inserts them into the network at the home node.

        :param self: Agent
        :param tx: neo4j database transaction with write permission
        :param intf: An Interface() object to simplify interactions with the database
        :param params: [mobility, mood, energy, inclination] these are the means for the normal distributions sampled to set parameters

        :return: None
        """
        super(Patient, self).generator(tx, intf, params)
        # generate a random set of parameters based on a distribution with mean set by params
        [mobility, mood, energy, inclination] = params
        self.mobility = np.normal(mobility, 0.05)  # draw from normal distribution centred on given value
        self.energy = np.normal(energy, 0.05)
        self.mood = np.normal(mood, 0.05)
        self.inclination = [np.normal(x) for x in inclination]
        self.inclination = self.inclination / sum(self.inclination)
        self.wellbeing = "'At risk'"
        self.referral = "false"
        # Add agent with params to ind in graph with resources starting at 0
        time = tx.run("MATCH (a:Clock) RETURN a.time").values()[0][0]
        self.log = "(CREATED," + str(time) + ")"
        intf.addagent(tx, {"name": "Home"}, "Agent:Patient",
                      {"mob": self.mobility, "mood": self.mood, "energy": self.energy,
                       "inclination": self.inclination, "wellbeing": self.wellbeing,
                       "log": "'" + self.log + "'", "referral": self.referral}, "name")

    @staticmethod
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

    def perception(self, tx, intf, perc):
        """
        Patient perception function. Filters based on agent having sufficient energy for edge and end node.

        :param tx: neo4j write transaction
        :param intf: Interface instance to simplify database calls
        :param perc: perception recieved from the node

        :return: None
        """
        super(Patient, self).perception(tx, intf, perc)
        if type(self.view) == list:
            edges = self.view
        else:
            edges = [self.view]
        # filter out options requiring too much energy
        valid_edges = []
        self.mobility = intf.getnodevalue(tx, self.id, "mob", "Patient")
        self.energy = intf.getnodevalue(tx, self.id, "energy", "Patient")
        self.current_energy = self.energy
        if len(self.view) > 1:
            for edge in edges:
                if not edge.end_node["name"] in ["Care", "GP", "Hos"]:
                    cost = 0
                    if edge["energy"]:
                        cost = cost + edge["energy"]
                    if edge.end_node["energy"]:
                        cost = cost + edge.end_node["energy"]
                    if self.energy > -cost:
                        valid_edges = valid_edges + [edge]
        else:
            valid_edges = self.view
        self.view = valid_edges

    def choose(self, tx, intf, perc):
        """
        Patients conscious choice from possible edges. This is based on the patients mood exceeds the current threshold
        for that edge. If the agent has the mood for multiple choices the final choice is made as a weighted sampling of
        all possible choices with weights based on the Patients inclination applied to the types of edges.

        :param tx: neo4j database write transaction
        :param intf: Interface for calls to database
        :param perc: perception from node perception function.

        :return: single edge as final choice
        """
        super(Patient, self).choose(tx, intf, perc)
        # filter out options where the agent does not reach the mood threshold
        options = []
        self.mood = intf.getnodevalue(tx, self.id, "mood", "Patient")
        self.inclination = intf.getnodevalue(tx, self.id, "inclination", "Patient")
        self.log = intf.getnodevalue(tx, self.id, "log", "Patient")
        self.wellbeing = intf.getnodevalue(tx, self.id, "wellbeing", "Patient")
        self.referral = intf.getnodevalue(tx, self.id, "referral", "Patient")
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
            types = [edge["type"] for edge in options]
            weights = [self.inclination[label] for label in types]
            weights = [w / sum(weights) for w in weights]
            choice = np.choice(options, 1, p=weights)
        return choice

    def learn(self, tx, intf, choice):
        """
        Agent is changed by node and can change node and edge it arrived by. This can include changes to decision
         making parameters.

        :param tx: neo4j database write transaction
        :param intf: Interface for database interaction
        :param choice: Chosen edge for move

        :return: None
        """
        super(Patient, self).learn(tx, intf, choice)
        # modify mob, conf, res and energy based on new node
        if self.fall and self.fall != "Mild":
            if self.wellbeing != "Fallen":
                self.wellbeing = "Fallen"
                intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                clock = tx.run("MATCH (a:Clock) "
                               "RETURN a.time").values()[0][0]
                self.log = self.log + ", (Fallen, " + str(clock) + ")"
        if "modm" in choice.end_node:
            self.mobility = self.positive(np.normal(choice.end_node["modm"], 0.05) + self.mobility)
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
            self.mood = self.positive(np.normal(choice.end_node["modmood"], 0.05) + self.mood)
            intf.updateagent(tx, self.id, "mood", self.mood)
        if "energy" in choice.end_node:
            self.current_energy = np.normal(choice.end_node["energy"], 0.05) + self.current_energy
            energy_change = self.current_energy - self.energy
            intf.updateagent(tx, self.id, "energy", self.current_energy)
            edge_types = ["social", "fall", "medical", "inactive"]
            for i in range(len(edge_types)):
                if choice["type"] == edge_types[i]:
                    if energy_change < 0:
                        self.inclination[i] = self.inclination[i] + 1
                    elif energy_change > 0:
                        self.inclination[i] = self.positive(self.inclination[i] - 1)
        # change to inclination based on mobility, energy and mood
        if self.current_energy > 0.8:
            self.inclination[0] = self.inclination[0] + 1
        elif self.current_energy < 0.2:
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
        # log going into care
        if choice.end_node["name"] == "Care":
            clock = tx.run("MATCH (a:Clock) "
                           "RETURN a.time").values()[0][0]
            self.log = self.log + ", (Care, " + str(clock) + ")"
        if "cap" in choice.end_node.keys():
            intf.updatenode(tx, choice.end_node["name"], "load", choice.end_node["load"] + 1, "name")
        if self.view[0]["name"] == "Hos" and choice.end_node["name"] != "Hos":
            clock = tx.run("MATCH (a:Clock) "
                           "RETURN a.time").values()[0][0]
            self.log = self.log + ", (Discharged, " + str(clock) + ")"
        intf.updateagent(tx, self.id, "log", str(self.log))

    def payment(self, tx, intf):
        """
        Modifies chosen edge and agent. These include mobility, confidence and energy modifications.

        :param tx: neo4j database write transaction
        :param intf: Interface for databse calls

        :return: None
        """
        super(Patient, self).payment(tx, intf)
        # Deduct energy used on edge
        if "energy" in self.choice.keys():
            self.current_energy = np.normal(self.choice["energy"], 0.05) + self.current_energy
            intf.updateagent(tx, self.id, "energy", self.current_energy)
        # mod variables based on edges
        if "modm" in self.choice:
            self.mobility = self.positive(np.normal(self.choice["modm"], 0.05) + self.mobility)
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
            self.mood = self.positive(np.normal(self.choice["modmood"], 0.05) + self.mood)
            intf.updateagent(tx, self.id, "mood", self.mood)

    def move(self, tx, intf, perc):
        """
        Runs complete agent movement algorithm.

        :param tx: neo4j database write transaction
        :param intf: Interface for database calls
        :param perc: perception provided by the node the agent is currently located at

        :return: Node Agent has moved to
        """
        super(Patient, self).move(tx, intf, perc)

    def logging(self, tx, intf, entry):
        """
        Utility function for adding information to the agents log of its activities

        :param tx: neo4j database write transaction
        :param intf: Interface for database calls
        :param entry: String to be added to the log

        :return: None
        """
        self.log = intf.getnodevalue(tx, self.id, "log", "Agent")
        self.log = self.log + ", (" + entry + ")"
        intf.updateagent(tx, self.id, "log", str(self.log))


class FallAgent(Agent):
    """
    Agent for modelling patients with declining mobility
    """

    def __init__(self, agent_id):
        super(FallAgent, self).__init__(agent_id, nuid="name")
        self.mobility = None
        self.energy = None
        self.confidence = None
        self.mobility_resources = None
        self.confidence_resources = None
        self.current_energy = None
        self.view = None
        self.log = None
        self.fall = ""
        self.wellbeing = None
        self.referral = None

    def generator(self, tx, intf, params):
        """
        Generates Fall Agents and inserts them into the network at the home node.

        :param self: Agent
        :param tx: neo4j database transaction with write permission
        :param intf: An Interface() object to simplify interactions with the database
        :param params: [mobility, confidence, energy] these are the means for the normal distributions sampled to set parameters

        :return: None
        """
        super(FallAgent, self).generator(tx, intf, params)
        # generate a random set of parameters based on a distribution with mean set by params
        [mobility, confidence, energy] = params
        self.mobility = np.normal(mobility, 0.05)  # draw from normal distribution centred on given value
        self.energy = np.normal(energy, 0.05)
        self.confidence = np.normal(confidence, 0.05)
        self.wellbeing = "'At risk'"
        self.referral = "false"
        # Add agent with params to ind in graph with resources starting at 0
        time = tx.run("MATCH (a:Clock) RETURN a.time").values()[0][0]
        self.log = "(CREATED," + str(time) + ")"
        intf.addagent(tx, {"name": "Home"}, "Agent", {"mob": self.mobility, "conf": self.confidence, "mob_res": 0,
                                                      "conf_res": 0, "energy": self.energy, "wellbeing": self.wellbeing,
                                                      "log": "'" + self.log + "'", "referral": self.referral}, "name")

    @staticmethod
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

    def perception(self, tx, intf, perc):
        """
        Fall agent perception function. Filters based on agent having sufficient energy for edge and end node.

        :param tx: neo4j write transaction
        :param intf: Interface instance to simplify database calls
        :param perc: perception recieved from the node

        :return: None
        """
        super(FallAgent, self).perception(tx, intf, perc)
        if type(self.view) == list:
            edges = self.view
        else:
            edges = [self.view]
        # filter out options requiring too much energy
        valid_edges = []
        self.mobility = intf.getnodevalue(tx, self.id, "mob", "Agent")
        self.energy = intf.getnodevalue(tx, self.id, "energy", "Agent")
        self.current_energy = self.energy
        if len(self.view) > 1:
            for edge in edges:
                if not edge.end_node["name"] in ["Care", "GP", "Hos"]:
                    cost = 0
                    if edge["energy"]:
                        cost = cost + edge["energy"]
                    if edge.end_node["energy"]:
                        cost = cost + edge.end_node["energy"]
                    if self.energy > -cost:
                        valid_edges = valid_edges + [edge]
        else:
            valid_edges = self.view
        self.view = valid_edges

    def choose(self, tx, intf, perc):
        """
        Agents conscious choice from possible edges. This is based on the effort of the agent calculated from the
        combination of agent and edge values. If the agent has the effort for multiple choices the worth of the edge is
        used as a deciding factor.

        :param tx: neo4j database write transaction
        :param intf: Interface for calls to database
        :param perc: perception from node perception function.

        :return: single edge as final choice
        """
        super(FallAgent, self).choose(tx, intf, perc)
        # filter out options where the agent does not reach the effort threshold
        options = []
        self.confidence = intf.getnodevalue(tx, self.id, "conf", "Agent")
        self.mobility_resources = intf.getnodevalue(tx, self.id, "mob_res", "Agent")
        self.confidence_resources = intf.getnodevalue(tx, self.id, "conf_res", "Agent")
        self.log = intf.getnodevalue(tx, self.id, "log", "Agent")
        self.wellbeing = intf.getnodevalue(tx, self.id, "wellbeing", "Agent")
        self.referral = intf.getnodevalue(tx, self.id, "referral", "Agent")
        if len(self.view) < 2:
            if type(self.view) == list and self.view:
                choice = self.view[0]
            else:
                choice = self.view
        else:
            for edge in self.view:
                if edge["effort"] <= edge["mobility"] * (self.mobility + self.confidence * self.mobility_resources) + \
                        edge["confidence"] * (self.confidence + self.mobility * self.confidence_resources):
                    options = options + [edge]
            # choose based on current highest worth edge ignores edges with no worth score, these are not choosable
            # edges, they are primarily edges indicating a fall
            if not options:
                return None
            choice = options[0]
            for edge in options:
                if "worth" in edge and "worth" in choice:
                    if edge["worth"] > choice["worth"]:
                        choice = edge
                elif "worth" in edge:
                    choice = edge
        return choice

    def learn(self, tx, intf, choice):
        """
        Agent is changed by node and can change node and edge it arrived by. This can include changes to decision
         making parameters.

        :param tx: neo4j database write transaction
        :param intf: Interface for database interaction
        :param choice: Chosen edge for move

        :return: None
        """
        super(FallAgent, self).learn(tx, intf, choice)
        # modify mob, conf, res and energy based on new node
        if self.fall and self.fall != "Mild":
            if self.wellbeing != "Fallen":
                self.wellbeing = "Fallen"
                intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                clock = tx.run("MATCH (a:Clock) "
                               "RETURN a.time").values()[0][0]
                self.log = self.log + ", (Fallen, " + str(clock) + ")"
        if "modm" in choice.end_node:
            self.mobility = self.positive(np.normal(choice.end_node["modm"], 0.05) + self.mobility)
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
        if "modc" in choice.end_node:
            self.confidence = self.positive(np.normal(choice.end_node["modc"], 0.05) + self.confidence)
            intf.updateagent(tx, self.id, "conf", self.confidence)
        if "modrc" in choice.end_node:
            self.confidence_resources = self.positive(np.normal(choice.end_node["modrc"], 0.05) +
                                                      self.confidence_resources)
            intf.updateagent(tx, self.id, "conf_res", self.confidence_resources)
        if "modrm" in choice.end_node:
            self.mobility_resources = self.positive(np.normal(choice.end_node["modrm"], 0.05) + self.mobility)
            intf.updateagent(tx, self.id, "mob_res", self.mobility_resources)
        if "energy" in choice.end_node:
            self.current_energy = np.normal(choice.end_node["energy"], 0.05) + self.current_energy
            intf.updateagent(tx, self.id, "energy", self.current_energy)
        # log going into care
        if choice.end_node["name"] == "Care":
            clock = tx.run("MATCH (a:Clock) "
                           "RETURN a.time").values()[0][0]
            self.log = self.log + ", (Care, " + str(clock) + ")"
        if "cap" in choice.end_node.keys():
            intf.updatenode(tx, choice.end_node["name"], "load", choice.end_node["load"] + 1, "name")
        if self.view[0]["name"] == "Hos" and choice.end_node["name"] != "Hos":
            clock = tx.run("MATCH (a:Clock) "
                           "RETURN a.time").values()[0][0]
            self.log = self.log + ", (Discharged, " + str(clock) + ")"
        intf.updateagent(tx, self.id, "log", str(self.log))

    def payment(self, tx, intf):
        """
        Modifies chosen edge and agent. These include mobility, confidence and energy modifications.

        :param tx: neo4j database write transaction
        :param intf: Interface for databse calls

        :return: None
        """
        super(FallAgent, self).payment(tx, intf)
        # Deduct energy used on edge
        if "energy" in self.choice.keys():
            self.current_energy = np.normal(self.choice["energy"], 0.05) + self.current_energy
            intf.updateagent(tx, self.id, "energy", self.current_energy)
        # mod variables based on edges
        if "modm" in self.choice:
            self.mobility = self.positive(np.normal(self.choice["modm"], 0.05) + self.mobility)
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
        if "modc" in self.choice:
            self.confidence = self.positive(np.normal(self.choice["modc"], 0.05) + self.confidence)
            intf.updateagent(tx, self.id, "conf", self.confidence)

    def move(self, tx, intf, perc):
        """
        Runs complete agent movement algorithm.

        :param tx: neo4j database write transaction
        :param intf: Interface for database calls
        :param perc: perception provided by the node the agent is currently located at

        :return: Node Agent has moved to
        """
        super(FallAgent, self).move(tx, intf, perc)

    def logging(self, tx, intf, entry):
        """
        Utility function for adding information to the agents log of its activities

        :param tx: neo4j database write transaction
        :param intf: Interface for database calls
        :param entry: String to be added to the log

        :return: None
        """
        self.log = intf.getnodevalue(tx, self.id, "log", "Agent")
        self.log = self.log + ", (" + entry + ")"
        intf.updateagent(tx, self.id, "log", str(self.log))
