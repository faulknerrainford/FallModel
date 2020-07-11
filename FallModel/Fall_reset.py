from FallModel.Fall_agent import FallAgent, Patient
import SPmodelling.Interface as intf
from SPmodelling.Reset import Reset as SPreset
import numpy.random as npr
import specification


class Reset(SPreset):
    """
    Subclass of the SPmodelling Reset class. It is set to generate the networks currently used in Fall models and
    populates them with patients
    """
    def __init__(self):
        """
        Set the reset script name to SocialFallModel, see specification for individualised script names and reset
        settings
        """
        super(Reset, self).__init__("SocialFallModel")

    @staticmethod
    def set_nodes(tx):
        """
        Generate the set of nodes used in Fall Models, currently only variation is if the Open Intervention node is
        included and the capacities on the Intervention nodes. The existence of the Open Intervention node and the nodes
        capacities are given in the specification file.

        :param tx: neo4j database write transaction

        :return: None
        """
        tx.run("CREATE (a:Node {name:'Hos', energy:0.2, modm:-0.1, modmood:-0.05})")
        tx.run("CREATE (a:Node {name:'Home', energy:0.3})")
        tx.run("CREATE (a:Node {name:'Social', energy:-0.4, modm:0.05, modmood:0.2})")
        tx.run("CREATE (a:Node {name:'Intervention', energy:-0.8, modm:0.3, modmood:0.3, cap:{c}, load:0})",
               c=specification.Intervention_cap)
        if specification.Open_Intervention:
            tx.run("CREATE (a:Node {name:'InterventionOpen', energy:-0.8, modm:0.3, modmood:0.3, cap:{c}, load:0})",
                   c=specification.Open_Intervention_cap)
        tx.run("CREATE (a:Node {name:'Care', time:'t', interval:0, mild:0, moderate:0, severe:0, agents:0})")
        tx.run("CREATE (a:Node {name:'GP'})")

    @staticmethod
    def set_edges(tx):
        """
        Generates the edges used in the commonly used system graph for Social Fall Model simulations. The variation in
        edges depends on existence of Open Intervention and the types of agents allows along the edge to the Open
        Intervention node, this is given in the specification file.

        :param tx: neo4j database write transaction

        :return: None
        """
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Hos' AND b.name='Home' "
               "CREATE (a)-[r:REACHES {mood:0, energy:-0.1, type:'inactive'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='GP' "
               "CREATE (a)-[r:REACHES {mood:0, energy: -0.3, modm:-0.1, type:'fall', modmood:-0.025}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Intervention' AND b.name='GP' "
               "CREATE (a)-[r:REACHES {mood:0, energy: -0.3, modm:-0.1, type:'fall', modmood:-0.025}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Social' AND b.name='GP' "
               "CREATE (a)-[r:REACHES {mood:0, energy: -0.3, modm:-0.1, type:'fall', modmood:-0.025}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='GP' AND b.name='Hos' "
               "CREATE (a)-[r:REACHES {mood:0, type:'fall'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='GP' AND b.name='Home' "
               "CREATE (a)-[r:REACHES {mood:0, type:'inactive'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Social' "
               "CREATE (a)-[r:REACHES {mood:0.2, type:'social'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Social' AND b.name='Home' "
               "CREATE (a)-[r:REACHES {mood:0, type:'inactive'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Intervention' "
               "CREATE (a)-[r:REACHES {mood:0.1, allowed:'Fallen', ref:'True', type:'medical'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Intervention' AND b.name='Home' "
               "CREATE (a)-[r:REACHES {mood:0, type:'inactive'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Intervention' AND b.name='Hos' "
               "CREATE (a)-[r:REACHES {mood:0, energy: -0.8, modm:-0.25, modc:-0.35, type:'fall'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Social' AND b.name='Hos' "
               "CREATE (a)-[r:REACHES {mood:0, energy: -0.8, modm:-0.25, modc:-0.35, type:'fall'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Hos' "
               "CREATE (a)-[r:REACHES {mood:0, energy: -0.8, modm:-0.25, modc:-0.5, type:'fall'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Care' "
               "CREATE (a)-[r:REACHES {mood:0}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Home' "
               "CREATE (a)-[r:REACHES {mood:0, type:'inactive'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Hos' AND b.name='Care' "
               "CREATE (a)-[r:REACHES {mood:0}]->(b)")
        if specification.Open_Intervention:
            tx.run("MATCH (a), (b) "
                   "WHERE a.name='InterventionOpen' AND b.name='GP' "
                   "CREATE (a)-[r:REACHES {mood:0, energy: -0.3, modm:-0.1, modc:-0.025, type:'fall'}]->(b)")
            tx.run("MATCH (a), (b) "
                   "WHERE a.name='InterventionOpen' AND b.name='Hos' "
                   "CREATE (a)-[r:REACHES {mood:0, energy: -0.8, modm:-0.25, modc:-0.35, type:'fall'}]->(b)")
            tx.run("MATCH (a), (b) "
                   "WHERE a.name='InterventionOpen' AND b.name='Home' "
                   "CREATE (a)-[r:REACHES {mood:0, type:'inactive'}]->(b)")
            tx.run("MATCH (a), (b) "
                   "WHERE a.name='Home' AND b.name='InterventionOpen' "
                   "CREATE (a)-[r:REACHES {mood:0.2, allowed:{limits}, ref:'False', type:'medical'}]->(b)",
                   limits=specification.Open_Intervention_Limits)

    @staticmethod
    def generate_population(tx, ps):
        """
        Generates the required number of agents and starts them at the Home node.
        Builds social connections between agents.

        :param tx: neo4j database write transaction
        :param ps: population size

        :return: None
        """
        fa = Patient(None)
        for j in range(ps//4):
            tx.run("CREATE (a:Carer {id:{j_id}, energy:20})", j_id=j)
        for i in range(ps):
            fa.generator(tx, [0.8, 0.9, 1, [2, 0, 1, 2], 2, 8])
            if npr.random(1) < 0.5:
                if npr.random(1) < 0.5:
                    samplesize = 2
                else:
                    samplesize = 1
                newfriends = npr.choice(range(ps//4), size=samplesize, replace=False)
                for nf in newfriends:
                    intf.createedge(tx, i, nf, 'Agent', 'Carer', 'SOCIAL', 'created: '
                                    + str(intf.gettime(tx)) + ', usage: ' + str(intf.gettime(tx)) + ', carer: True')
                    intf.createedge(tx, i, nf, 'Agent', 'Carer', 'FRIEND')
        for i in range(ps):
            newfriends = npr.choice(range(ps), size=npr.choice(range(3)), replace=False)
            for nf in newfriends:
                if not nf == i:
                    intf.createedge(tx, i, nf, 'Agent', 'Agent', 'SOCIAL', 'created: '
                                    + str(intf.gettime(tx)) + ', usage: ' + str(intf.gettime(tx)) + ', carer: False')
                    intf.createedge(tx, i, nf, 'Agent', 'Agent', 'FRIEND')


class ResetV0(SPreset):
    """
    Subclass of the SPmodelling Reset class. It is set to generate the networks currently used in Fall models and
    populates them with fall agents
    """
    def __init__(self):
        """
        Set the reset script name to Fall Model so, see specification for individualised script names and reset settings
        """
        super(ResetV0, self).__init__("FallModel")

    @staticmethod
    def set_nodes(tx):
        """
        Generate the set of nodes used in Fall Models, currently only variation is if the Open Intervention node is
        included and the capacities on the Intervention nodes. The existence of the Open Intervention node and the nodes
        capacities are given in the specification file.

        :param tx: neo4j database write transaction

        :return: None
        """
        tx.run("CREATE (a:Node {name:'Hos', energy:0.2, modm:-0.1, modc:-0.05})")
        tx.run("CREATE (a:Node {name:'Home', energy:0.3})")
        tx.run("CREATE (a:Node {name:'Social', energy:-0.4, modm:0.05, modc:0.2, modrc:0.2})")
        tx.run("CREATE (a:Node {name:'Intervention', energy:-0.8, modm:0.3, modc:0.3, cap:{c}, load:0})",
               c=specification.Intervention_cap)
        if specification.Open_Intervention:
            tx.run("CREATE (a:Node {name:'InterventionOpen', energy:-0.8, modm:0.3, modc:0.3, cap:{c}, load:0})",
                   c=specification.Open_Intervention_cap)
        tx.run("CREATE (a:Node {name:'Care', time:'t', interval:0, mild:0, moderate:0, severe:0, agents:0})")
        tx.run("CREATE (a:Node {name:'GP'})")

    @staticmethod
    def set_edges(tx):
        """
        Generates the edges used in the commonly used system graph for Fall Model simulations. The variation in edges
        depends on existence of Open Intervention and the types of agents allows along the edge to the Open Intervention
        node, this is given in the specification file.

        :param tx: neo4j database write transaction

        :return: None
        """
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Hos' AND b.name='Home' "
               "CREATE (a)-[r:REACHES {effort:0.01, mobility:1, confidence:1, energy:-0.1, worth:0.1}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='GP' "
               "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, energy: -0.3, modm:-0.1, "
               "modc:-0.025}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Intervention' AND b.name='GP' "
               "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, energy: -0.3, modm:-0.1, "
               "modc:-0.025}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Social' AND b.name='GP' "
               "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, energy: -0.3, modm:-0.1, "
               "modc:-0.025}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='GP' AND b.name='Hos' "
               "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='GP' AND b.name='Home' "
               "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Social' "
               "CREATE (a)-[r:REACHES {effort:0.1, mobility:0.6, confidence:0.4, worth:1}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Social' AND b.name='Home' "
               "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, worth:0}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Intervention' "
               "CREATE (a)-[r:REACHES {effort:0.3, mobility:0.5, confidence:0.5, worth:2, allowed:'Fallen', "
               "ref:'True'}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Intervention' AND b.name='Home' "
               "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, worth:1}]->(b)")
        # Falls
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Intervention' AND b.name='Hos' "
               "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, energy: -0.8, modm:-0.25, modc:-0.35}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Social' AND b.name='Hos' "
               "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, energy: -0.8, modm:-0.25, modc:-0.35}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Hos' "
               "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, energy: -0.8, modm:-0.25, modc:-0.5}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Care' "
               "CREATE (a)-[r:REACHES {effort:0, worth:-1, mobility:1, confidence:1}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Hos' AND b.name='Care' "
               "CREATE (a)-[r:REACHES {effort:0, worth:-100, mobility:1, confidence:1}]->(b)")
        if specification.Open_Intervention:
            tx.run("MATCH (a), (b) "
                   "WHERE a.name='InterventionOpen' AND b.name='GP' "
                   "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, energy: -0.3, modm:-0.1, "
                   "modc:-0.025}]->(b)")
            tx.run("MATCH (a), (b) "
                   "WHERE a.name='InterventionOpen' AND b.name='Hos' "
                   "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, energy: -0.8, modm:-0.25, "
                   "modc:-0.35}]->(b)")
            tx.run("MATCH (a), (b) "
                   "WHERE a.name='InterventionOpen' AND b.name='Home' "
                   "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, worth:1}]->(b)")
            tx.run("MATCH (a), (b) "
                   "WHERE a.name='Home' AND b.name='InterventionOpen' "
                   "CREATE (a)-[r:REACHES {effort:0.3, mobility:0.5, confidence:0.5, worth:2, allowed:{limits}, "
                   "ref:'False'}]->(b)", limits=specification.Open_Intervention_Limits)

    @staticmethod
    def generate_population(tx, ps):
        """
        Generates the required number of agents and starts them at the Home node.

        :param tx: neo4j database write transaction
        :param ps: population size

        :return: None
        """
        fa = FallAgent(None)
        for i in range(ps):
            fa.generator(tx, [0.8, 0.9, 1])
