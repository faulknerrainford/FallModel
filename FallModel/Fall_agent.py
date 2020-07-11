from SPmodelling.Agent import MobileAgent, CommunicativeAgent
import numpy.random as npr
import SPmodelling.Interface as intf


class Patient(MobileAgent, CommunicativeAgent):
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
        self.social = 6
        self.colocated = None
        self.contacts = None

    def generator(self, tx, params):
        """
        Generates Fall Agents and inserts them into the network at the home node.

        :param self: Agent
        :param tx: neo4j database transaction with write permission
        :param params: [mobility, mood, energy, inclination] these are the means for the normal distributions sampled to set parameters

        :return: None
        """
        super(Patient, self).generator(tx, params)
        # generate a random set of parameters based on a distribution with mean set by params
        [mobility, mood, energy, inclination, min_social, max_social] = params
        self.mobility = npr.normal(mobility, 0.05)  # draw from normal distribution centred on given value
        self.energy = npr.normal(energy, 0.05)
        self.mood = npr.normal(mood, 0.05)
        self.inclination = [npr.normal(x) for x in inclination]
        self.inclination = [inc/sum(self.inclination) for inc in self.inclination]
        self.wellbeing = "'At risk'"
        self.referral = "false"
        self.social = npr.choice(range(min_social, max_social+1), 1)[0]
        print(self.social)
        # Add agent with params to ind in graph with resources starting at 0
        time = tx.run("MATCH (a:Clock) RETURN a.time").values()[0][0]
        self.log = "(CREATED," + str(time) + ")"
        intf.addagent(tx, {"name": "Home"}, "Agent:Patient",
                      {"mob": self.mobility, "mood": self.mood, "energy": self.energy,
                       "inclination": self.inclination, "wellbeing": self.wellbeing,
                       "log": "'" + self.log + "'", "referral": self.referral, "social":self.social}, "name")

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

    def perception(self, tx, perc):
        """
        Patient perception function. Filters based on agent having sufficient energy for edge and end node.

        :param tx: neo4j write transaction
        :param perc: perception recieved from the node

        :return: None
        """
        super(Patient, self).perception(tx, perc)
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
                    if edge.end_node["energy"]:
                        cost = cost + edge.end_node["energy"]
                    if self.energy > -cost:
                        valid_edges = valid_edges + [edge]
        else:
            valid_edges = self.view
        self.view = valid_edges

    def choose(self, tx, perc):
        """
        Patients conscious choice from possible edges. This is based on the patients mood exceeds the current threshold
        for that edge. If the agent has the mood for multiple choices the final choice is made as a weighted sampling of
        all possible choices with weights based on the Patients inclination applied to the types of edges.

        :param tx: neo4j database write transaction
        :param perc: perception from node perception function.

        :return: single edge as final choice
        """
        super(Patient, self).choose(tx, perc)
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
            edge_types = ["social", "fall", "medical", "inactive"]
            types = [edge_types.index(lable) for lable in types]
            weights = [self.positive(self.inclination[label]) for label in types]
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
        super(Patient, self).learn(tx, choice)
        # modify mob, conf, res and energy based on new node
        if self.fall and self.fall != "Mild":
            if self.wellbeing != "Fallen":
                self.wellbeing = "Fallen"
                intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                clock = tx.run("MATCH (a:Clock) "
                               "RETURN a.time").values()[0][0]
                self.log = self.log + ", (Fallen, " + str(clock) + ")"
        if "modm" in choice.end_node:
            self.mobility = self.positive(npr.normal(choice.end_node["modm"], 0.05) + self.mobility)
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
            self.mood = self.positive(npr.normal(choice.end_node["modmood"], 0.05) + self.mood)
            intf.updateagent(tx, self.id, "mood", self.mood)
        if "energy" in choice.end_node:
            self.current_energy = npr.normal(choice.end_node["energy"], 0.05) + self.current_energy
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

    def payment(self, tx):
        """
        Modifies chosen edge and agent. These include mobility, confidence and energy modifications.

        :param tx: neo4j database write transaction

        :return: None
        """
        super(Patient, self).payment(tx)
        # Deduct energy used on edge
        if "energy" in self.choice.keys():
            if "energy" in self.choice.end_node.keys():
                if self.choice["energy"]+self.choice.end_node["energy"] > self.current_energy:
                    # Check for carers
                    carers = intf.agentcontacts(tx, self.id, "Agent", "Carer")
                    # Check for sufficient energy
                    for carer in carers:
                        print(carer)
                        if carer.end_node["energy"] >= self.choice["energy"]:
                            intf.updatenode(tx, carer.end_node["id"], "energy", carer.end_node["energy"]
                                            - self.choice["energy"], label='Carer')
                            self.current_energy = self.current_energy+self.choice["energy"]
                            intf.updateagent(tx, self.id, "energy", self.current_energy)
                            intf.updatecontactedge(tx, self.id, carer.end_node["id"], "usage", intf.gettime(tx), "Agent",
                                                   "Carer")
                            break
                    else:
                        return False
            self.current_energy = npr.normal(self.choice["energy"], 0.05) + self.current_energy
            intf.updateagent(tx, self.id, "energy", self.current_energy)
        # mod variables based on edges
        if "modm" in self.choice:
            self.mobility = self.positive(npr.normal(self.choice["modm"], 0.05) + self.mobility)
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
            self.mood = self.positive(npr.normal(self.choice["modmood"], 0.05) + self.mood)
            intf.updateagent(tx, self.id, "mood", self.mood)
        return True

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
        self.log = intf.getnodevalue(tx, self.id, "log", "Agent")
        self.log = self.log + ", (" + entry + ")"
        intf.updateagent(tx, self.id, "log", str(self.log))

    def look(self, tx):
        """
        If not at home, find co-located agents

        :param tx: neo4j database write transaction

        :return: None
        """
        super(Patient, self).look(tx)
        self.id = self.id[0]
        # If not at home, find co-located agents
        if intf.locateagent(tx, self.id)["name"] != "Home":
            self.colocated = intf.colocated(tx, self.id)
        self.social = intf.getnodevalue(tx, self.id, "social", "Agent")

    def update(self, tx):
        """
        Check agent contacts compare list with co-located agents and update co-located contacts with new last usage

        :param tx: neo4j database write transaction

        :return: None
        """
        super(Patient, self).update(tx)
        # Update existing com links with latest co-location
        self.contacts = intf.agentcontacts(tx, self.id, "Patient")
        if self.contacts and self.colocated:
            update = [contact for contact in self.contacts if contact in self.colocated]
            for contact in update:
                intf.updatecontactedge(tx, contact.end_node["id"], self.id, "last_usage", intf.gettime())

    def talk(self, tx):
        """
        Determine if agent forms a new social link with random co-located agent based on their social values and
        shortest social path

        :param tx: neo4j write transaction

        :return: None
        """
        super(Patient , self).talk(tx)
        if self.colocated:
            newcontacts = [nc for nc in self.colocated if nc not in self.contacts]
            if newcontacts:
                if len(newcontacts) > 1:
                    newfriend = npr.sample(newcontacts)
                else:
                    newfriend = newcontacts
                # Based on relative social values and length of shortest path set probability for forming link with a
                #  randomly sampled co-located unknown agent. social from 2-8 per agent, combined from 4-16. So combined -4
                #  over 24 gives value between 0 and 0.5 plus the if minimum path greater than 6 nothing, else from m=2-6
                #  then 1/(2m-2) gives 0.1-0.5 (m=1 or 0 means itself or already connected).
                prob1 = (newfriend.end_node["social"]+self.social-4)/24
                sp = intf.shortestpath(tx, self.id, newfriend.end_node["id"], 'Agent', 'Social')
                if sp < 2:
                    prob2 = 0
                elif sp > 6:
                    prob2 = 0
                else:
                    prob2 = 1/(2*sp-2)
                if npr.random(1) <= (prob1 + prob2):
                # form friend link
                    intf.createedge(self.id, newfriend.end_node["id"], 'Agent', 'Agent', 'SOCIAL:FRIEND', 'created: '
                                  + intf.gettime() + ', usage: ' + intf.gettime() + ', carer: False')
                    self.contacts = newfriend
                else: self.contacts = None
            else:
                self.contacts = None
        else: self.contacts = None

    def listen(self, tx):
        """
        If the agent has a new social link check if the new friend has a link to a carer if they do for a random carer
        they form a link with a .5 chance.

        :param tx: neo4j write transaction

        :return: None
        """
        super(Patient, self).listen(tx)
        if self.contacts:
            carers = intf.agentcontacts(tx, self.contacts.end_node["id"], "Agent", "Carer")
            carers = [carer for carer in carers if carer["carer"]]
            carer = npr.sample(carers)
            if npr.random(1) < 0.5:
                intf.createedge(self.id, carer.end_node["id"], 'Patient', 'Carer', 'SOCIAL:FRIEND', 'created: '
                                + intf.gettime() + ', usage: ' + intf.gettime() + ', carer: True')

    def react(self, tx):
        """
        If the agent now has more social bonds than they can manage we drop new non carer friends then those not used
        recently and finally reduce the carers from most recent.

        :param tx: neo4j write transaction

        :return: None
        """
        super(Patient, self).react(tx)
        self.contacts = intf.agentcontacts(tx, self.id, "Agent")
        carers = self.contacts + intf.agentcontacts(tx, self.id, "Agent", "Carer")
        if len(self.contacts) > self.social:
            while len(carers) > self.social:
                carer_drop = None
                latest_time = 0
                for carer in carers:
                    if carer["created"] > latest_time:
                        carer_drop = carer
                        latest_time = carer["created"]
                intf.deletecontact(tx, self.id, carer_drop.end_node["id"], "Agent", "Carer")
            if len(carers) == self.social:
                for contact in contacts:
                    intf.deletecontact(tx, self.id, contact.end_node["id"], "Agent", "Agent")
            if len(carers)+len(contacts) > self.social:
                for contact in contacts:
                    if len(carers)+len(contacts) > self.social:
                        if intf.gettime() - contact['created'] < 5:
                            intf.deletecontact(tx, self.id, contact.end_node["id"], "Agent", "Agent")
            oldest_usage = 0
            contact_drop = None
            while len(carers)+len(contacts) > self.social:
                for contact in contacts:
                    if intf.gettime() - contact["usage"] > oldest_usage:
                        contact_drop = contact
                        oldest_usage = intf.gettime() - contact["usage"]
                intf.deletecontact(tx, self.id, contact_drop.end_node["id"], "Agent", "Agent")


class FallAgent(MobileAgent):
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

    def generator(self, tx, params):
        """
        Generates Fall Agents and inserts them into the network at the home node.

        :param self: Agent
        :param tx: neo4j database transaction with write permission
        :param params: [mobility, confidence, energy] these are the means for the normal distributions sampled to set parameters

        :return: None
        """
        super(FallAgent, self).generator(tx, params)
        # generate a random set of parameters based on a distribution with mean set by params
        [mobility, confidence, energy] = params
        self.mobility = npr.normal(mobility, 0.05)  # draw from normal distribution centred on given value
        self.energy = npr.normal(energy, 0.05)
        self.confidence = npr.normal(confidence, 0.05)
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

    def perception(self, tx, perc):
        """
        Fall agent perception function. Filters based on agent having sufficient energy for edge and end node.

        :param tx: neo4j write transaction
        :param intf: Interface instance to simplify database calls
        :param perc: perception recieved from the node

        :return: None
        """
        super(FallAgent, self).perception(tx, perc)
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

    def choose(self, tx, perc):
        """
        Agents conscious choice from possible edges. This is based on the effort of the agent calculated from the
        combination of agent and edge values. If the agent has the effort for multiple choices the worth of the edge is
        used as a deciding factor.

        :param tx: neo4j database write transaction
        :param perc: perception from node perception function.

        :return: single edge as final choice
        """
        super(FallAgent, self).choose(tx, perc)
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

    def learn(self, tx, choice):
        """
        Agent is changed by node and can change node and edge it arrived by. This can include changes to decision
         making parameters.

        :param tx: neo4j database write transaction
        :param choice: Chosen edge for move

        :return: None
        """
        super(FallAgent, self).learn(tx, choice)
        # modify mob, conf, res and energy based on new node
        if self.fall and self.fall != "Mild":
            if self.wellbeing != "Fallen":
                self.wellbeing = "Fallen"
                intf.updateagent(tx, self.id, "wellbeing", self.wellbeing)
                clock = tx.run("MATCH (a:Clock) "
                               "RETURN a.time").values()[0][0]
                self.log = self.log + ", (Fallen, " + str(clock) + ")"
        if "modm" in choice.end_node:
            self.mobility = self.positive(npr.normal(choice.end_node["modm"], 0.05) + self.mobility)
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
            self.confidence = self.positive(npr.normal(choice.end_node["modc"], 0.05) + self.confidence)
            intf.updateagent(tx, self.id, "conf", self.confidence)
        if "modrc" in choice.end_node:
            self.confidence_resources = self.positive(npr.normal(choice.end_node["modrc"], 0.05) +
                                                      self.confidence_resources)
            intf.updateagent(tx, self.id, "conf_res", self.confidence_resources)
        if "modrm" in choice.end_node:
            self.mobility_resources = self.positive(npr.normal(choice.end_node["modrm"], 0.05) + self.mobility)
            intf.updateagent(tx, self.id, "mob_res", self.mobility_resources)
        if "energy" in choice.end_node:
            self.current_energy = npr.normal(choice.end_node["energy"], 0.05) + self.current_energy
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

    def payment(self, tx):
        """
        Modifies chosen edge and agent. These include mobility, confidence and energy modifications.

        :param tx: neo4j database write transaction
        :param intf: Interface for databse calls

        :return: None
        """
        super(FallAgent, self).payment(tx)
        # Deduct energy used on edge
        if "energy" in self.choice.keys():
            self.current_energy = npr.normal(self.choice["energy"], 0.05) + self.current_energy
            intf.updateagent(tx, self.id, "energy", self.current_energy)
        # mod variables based on edges
        if "modm" in self.choice:
            self.mobility = self.positive(npr.normal(self.choice["modm"], 0.05) + self.mobility)
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
            self.confidence = self.positive(npr.normal(self.choice["modc"], 0.05) + self.confidence)
            intf.updateagent(tx, self.id, "conf", self.confidence)

    def move(self, tx, perc):
        """
        Runs complete agent movement algorithm.

        :param tx: neo4j database write transaction
        :param intf: Interface for database calls
        :param perc: perception provided by the node the agent is currently located at

        :return: Node Agent has moved to
        """
        super(FallAgent, self).move(tx, perc)

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
