from FallModel.Fall_agent import Patient, Carer
import SPmodelling.Interface as intf
import SPmodelling.Reset
import numpy.random as npr
import specification


class Reset(SPmodelling.Reset.Reset):
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
        intf.add_node(tx, ['Hos', 'Node', 'name'], {'resources': 0.2, 'modm': -0.1, 'modmood': -0.05,
                                                    'servicemodel': 'alternative'})
        intf.add_node(tx, ['Home', 'Node', 'name'], {'resources': 0.3, 'servicemodel': 'addative'})
        if specification.activities:
            intf.add_node(tx, ['SocialLunch', 'Node', 'name'], {'resources': -0.4, 'modm': 0.025, 'modmood': 0.2,
                                                                'servicemodel': 'addative'})
            intf.add_node(tx, ['SocialWalk', 'Node', 'name'], {'resources': -0.5, 'modm': 0.075, 'modmood': 0.2,
                                                               'servicemodel': 'addative'})
            intf.add_node(tx, ['SocialCraft', 'Node', 'name'], {'resources': -0.45, 'modm': 0.05, 'modmood': 0.2,
                                                                'servicemodel': 'addative'})
        else:
            intf.add_node(tx, ['Social', 'Node', 'name'], {'resources': -0.4, 'modm': 0.05, 'modmood': 0.2,
                                                           'servicemodel': 'addative'})
        if specification.Intervention != "service":
            intf.add_node(tx, ['Intervention', 'Node', 'name'], {'resources': -0.8, 'modm': 0.3, 'modmood': 0.3,
                                                                 'cap': specification.Intervention_cap, 'load': 0})
        if specification.Intervention == "open":
            intf.add_node(tx, ['InterventionOpen', 'Node', 'name'], {'resources': -0.8, 'modm': 0.3, 'modmood': 0.3,
                                                                     'cap': specification.Open_Intervention_cap,
                                                                     'load': 0})
        intf.add_node(tx, ['Care', 'Node', 'name'], {'time': 't', 'interval': 0, 'mild': 0, 'moderate': 0, 'severe': 0,
                                                     'agents': 0, 'servicemodel': 'addative'})
        intf.add_node(tx, ['GP', 'Node', 'name'], {'servicemodel': 'alternative'})
        intf.add_node(tx, ['localNHS', 'Organisation', 'name'])

    @staticmethod
    def set_edges(tx):
        """
        Generates the edges used in the commonly used system graph for Social Fall Model simulations. The variation in
        edges depends on existence of Open Intervention and the types of agents allows along the edge to the Open
        Intervention node, this is given in the specification file.

        :param tx: neo4j database write transaction

        :return: None
        """
        intf.create_edge(tx, ['Hos', 'Node', 'name'], ['Home', 'Node', 'name'], 'REACHES',
                         {'mood': 0, 'resources': -0.1, 'type': 'inactive'})
        intf.create_edge(tx, ['Home', 'Node', 'name'], ['GP', 'Node', 'name'], 'REACHES',
                         {'mood':0, 'resources': -0.3, 'modm':-0.1, 'type':'fall', 'modmood':-0.025})
        intf.create_edge(tx, ['Intervention', 'Node', 'name'], ['GP', 'Node', 'name'], 'REACHES',
                         {'mood':0, 'resources': -0.3, 'modm':-0.1, 'type':'fall', 'modmood':-0.025})
        intf.create_edge(tx, ['GP', 'Node', 'name'], ['Hos', 'Node', 'name'], 'REACHES',
                         {'mood':0, 'type':'fall'})
        intf.create_edge(tx, ['GP', 'Node', 'name'], ['Home', 'Node', 'name'], 'REACHES',
                         {'mood':0, 'type':'inactive'})
        intf.create_edge(tx, ['Home', 'Node', 'name'], ['Intervention', 'Node', 'name'], 'REACHES',
                         {'resources':-0.2, 'mood':0.1, 'allowed':'Fallen', 'ref':'True', 'type':'medical'})
        intf.create_edge(tx, ['Intervention', 'Node', 'name'], ['Home', 'Node', 'name'], 'REACHES',
                         {'resources':-0.05, 'mood':0, 'type':'inactive'})
        intf.create_edge(tx, ['Intervention', 'Node', 'name'], ['Hos', 'Node', 'name'], 'REACHES',
                         {'mood':0, 'resources': -0.8, 'modm':-0.25, 'modc':-0.35, 'type':'fall'})
        intf.create_edge(tx, ['Home', 'Node', 'name'], ['Hos', 'Node', 'name'], 'REACHES',
                         {'mood':0, 'resources': -0.8, 'modm':-0.25, 'modc':-0.5, 'type':'fall'})
        intf.create_edge(tx, ['Home', 'Node', 'name'], ['Care', 'Node', 'name'], 'REACHES',
                         {'mood':0, 'type':'immobility'})
        intf.create_edge(tx, ['Home', 'Node', 'name'], ['Home', 'Node', 'name'], 'REACHES',
                         {'mood':0, 'type':'inactive'})
        intf.create_edge(tx, ['Hos', 'Node', 'name'], ['Care', 'Node', 'name'], 'REACHES',
                         {'mood':0, 'type':'immobility'})
        if specification.activities:
            intf.create_edge(tx, ['Home', 'Node', 'name'], ['SocialLunch', 'Node', 'name'], 'REACHES',
                             {'resources':-0.1, 'mood':0.2, 'type':'social'})
            intf.create_edge(tx, ['SocialLunch', 'Node', 'name'], ['Home', 'Node', 'name'], 'REACHES',
                             {'resources':-0.1, 'mood':0, 'type':'inactive'})
            intf.create_edge(tx, ['SocialLunch', 'Node', 'name'], ['Hos', 'Node', 'name'], 'REACHES',
                             {'mood':0, 'resources': -0.8, 'modm':-0.25, 'modc':-0.35, 'type':'fall'})
            intf.create_edge(tx, ['SocialLunch', 'Node', 'name'], ['GP', 'Node', 'name'], 'REACHES',
                             {'mood':0, 'resources': -0.3, 'modm':-0.1, 'type':'fall', 'modmood':-0.025})
            intf.create_edge(tx, ['Home', 'Node', 'name'], ['SocialWalk', 'Node', 'name'], 'REACHES',
                             {'resources':-0.1, 'mood':0.25, 'type':'social'})
            intf.create_edge(tx, ['SocialWalk', 'Node', 'name'], ['Home', 'Node', 'name'], 'REACHES',
                             {'resources':-0.1, 'mood':0, 'type':'inactive'})
            intf.create_edge(tx, ['SocialWalk', 'Node', 'name'], ['Hos', 'Node', 'name'], 'REACHES',
                             {'mood':0, 'resources': -0.8, 'modm':-0.25, 'modc':-0.35, 'type':'fall'})
            intf.create_edge(tx, ['SocialWalk', 'Node', 'name'], ['GP', 'Node', 'name'], 'REACHES',
                             {'mood':0, 'resources': -0.3, 'modm':-0.1, 'type':'fall', 'modmood':-0.025})
            intf.create_edge(tx, ['Home', 'Node', 'name'], ['SocialCraft', 'Node', 'name'], 'REACHES',
                             {'resources':-0.1, 'mood':0.2, 'type':'social'})
            intf.create_edge(tx, ['SocialCraft', 'Node', 'name'], ['Home', 'Node', 'name'], 'REACHES',
                             {'resources':-0.1, 'mood':0, 'type':'inactive'})
            intf.create_edge(tx, ['SocialCraft', 'Node', 'name'], ['Hos', 'Node', 'name'], 'REACHES',
                             {'mood':0, 'resources': -0.8, 'modm':-0.25, 'modc':-0.35, 'type':'fall'})
            intf.create_edge(tx, ['SocialCraft', 'Node', 'name'], ['GP', 'Node', 'name'], 'REACHES',
                             {'mood':0, 'resources': -0.3, 'modm':-0.1, 'type':'fall', 'modmood':-0.025})
        else:
            intf.create_edge(tx, ['Home', 'Node', 'name'], ['Social', 'Node', 'name'], 'REACHES',
                             {'resources':-0.1, 'mood':0.2, 'type':'social'})
            intf.create_edge(tx, ['Social', 'Node', 'name'], ['Home', 'Node', 'name'], 'REACHES',
                             {'resources':-0.1, 'mood':0, 'type':'inactive'})
            intf.create_edge(tx, ['Social', 'Node', 'name'], ['Hos', 'Node', 'name'], 'REACHES',
                             {'mood':0, 'resources': -0.8, 'modm':-0.25, 'modc':-0.35, 'type':'fall'})
            intf.create_edge(tx, ['Social', 'Node', 'name'], ['GP', 'Node', 'name'], 'REACHES',
                             {'mood':0, 'resources': -0.3, 'modm':-0.1, 'type':'fall', 'modmood':-0.025})
        if specification.Intervention == "open":
            intf.create_edge(tx, ['InterventionOpen', 'Node', 'name'], ['GP', 'Node', 'name'], 'REACHES',
                             {'mood':0, 'resources': -0.3, 'modm':-0.1, 'modc':-0.025, 'type':'fall'})
            intf.create_edge(tx, ['InterventionOpen', 'Node', 'name'], ['Hos', 'Node', 'name'], 'REACHES',
                             {'mood':0, 'resources': -0.8, 'modm':-0.25, 'modc':-0.35, 'type':'fall'})
            intf.create_edge(tx, ['InterventionOpen', 'Node', 'name'], ['Home', 'Node', 'name'], 'REACHES',
                             {'resources':-0.2, 'mood':0, 'type':'inactive'})
            intf.create_edge(tx, ['Home', 'Node', 'name'], ['InterventionOpen', 'Node', 'name'], 'REACHES',
                             {'resources':-0.05, 'mood':0.2, 'allowed':specification.Open_Intervention_Limits,
                              'ref':'False', 'type':'medical'})

    @staticmethod
    def generate_population(tx, ps):
        """
        Generates the required number of agents split between carers and patients and starts them at the Home node.
        Builds social and care links between agents.

        :param tx: neo4j database write transaction
        :param ps: population size

        :return: None
        """
        fa = Patient(None)
        cps = ps // 4
        pps = ps - cps
        if specification.carers == "agents":
            ca = Carer(None)
            for i in range(cps):
                ca.generator(tx, [2, 2, 4, [3, 0, 0, 1, 0], 2, 8])
        elif specification.carers:
            for j in range(cps):
                intf.add_node(tx, [j, 'Carer', 'id'], {'resources':20})
        if not specification.carers:
            pps = ps
        for i in range(pps):
            fa.generator(tx, [0.8, 0.9, 1, [2, 0, 1, 2, 0], 2, 8])
            if npr.random(1) < 0.5:
                if npr.random(1) < 0.5:
                    sample_size = 2
                else:
                    sample_size = 1
                if not specification.carers:
                    cps = ps
                new_friends = npr.choice(range(cps), size=sample_size, replace=False)
                for nf in new_friends:
                    if npr.random(1) < 0.8:
                        ag_type = '"family"'
                    else:
                        ag_type = '"social"'
                    intf.create_edge(tx, [i + cps, 'Agent', 'id'], [nf, 'Agent', 'id'], 'SOCIAL', 'created: '
                                     + str(intf.get_time(tx)) + ', colocation: ' + str(intf.get_time(tx))
                                     + ', utilization: ' + str(intf.get_time(tx))
                                     + ', type: ' + ag_type)
        for i in range(ps):
            new_friends = npr.choice(range(ps), size=npr.choice(range(3)), replace=False)
            for nf in new_friends:
                if not nf == i:
                    if npr.random(1) < 0.5:
                        ag_type = '"family"'
                    else:
                        ag_type = '"social"'
                    intf.create_edge(tx, [i, 'Agent', 'id'], [nf, 'Agent', 'id'], 'SOCIAL', 'created: '
                                     + str(intf.get_time(tx)) + ', colocation: ' + str(intf.get_time(tx))
                                     + ', utilization: ' + str(intf.get_time(tx))
                                     + ', type: ' + ag_type)

    @staticmethod
    def set_service(tx):
        """
        Services to be added to the system

        :param tx: Neo4j database write transaction

        :return:None
        """
        intf.add_node(tx, ['care', 'Service', 'name'], {'resources':0.5, 'capacity':5, 'load':0, 'date':0})
        intf.add_node(tx, ['intervention', 'Service', 'name'], {'resources':-0.8, 'mobility':0.3, 'capacity':2,
                                                                'load':0, 'date':0})
        intf.create_edge(tx, ['care', 'Service', 'name'], ['Home', 'Node', 'name'], 'PROVIDE')
        intf.create_edge(tx, ['intervention', 'Service', 'name'], ['Hos', 'Node', 'name'], 'PROVIDE')


# noinspection
class ResetV0(SPmodelling.Reset.Reset):
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
        tx.run("CREATE (a:Node {name:'Hos', resources:0.2, modm:-0.1, modc:-0.05})")
        tx.run("CREATE (a:Node {name:'Home', resources:0.3})")
        tx.run("CREATE (a:Node {name:'Social', resources:-0.4, modm:0.05, modc:0.2, modrc:0.2})")
        tx.run("CREATE (a:Node {name:'Intervention', resources:-0.8, modm:0.3, modc:0.3, cap:{c}, load:0})",
               c=specification.Intervention_cap)
        if specification.Open_Intervention:
            tx.run("CREATE (a:Node {name:'InterventionOpen', resources:-0.8, modm:0.3, modc:0.3, cap:{c}, load:0})",
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
               "CREATE (a)-[r:REACHES {effort:0.01, mobility:1, confidence:1, resources:-0.1, worth:0.1}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='GP' "
               "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, resources: -0.3, modm:-0.1, "
               "modc:-0.025}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Intervention' AND b.name='GP' "
               "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, resources: -0.3, modm:-0.1, "
               "modc:-0.025}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Social' AND b.name='GP' "
               "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, resources: -0.3, modm:-0.1, "
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
               "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, resources: -0.8, modm:-0.25, "
               "modc:-0.35}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Social' AND b.name='Hos' "
               "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, resources: -0.8, modm:-0.25, "
               "modc:-0.35}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Hos' "
               "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, resources: -0.8, modm:-0.25, "
               "modc:-0.5}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Home' AND b.name='Care' "
               "CREATE (a)-[r:REACHES {effort:0, worth:-1, mobility:1, confidence:1}]->(b)")
        tx.run("MATCH (a), (b) "
               "WHERE a.name='Hos' AND b.name='Care' "
               "CREATE (a)-[r:REACHES {effort:0, worth:-100, mobility:1, confidence:1}]->(b)")
        if specification.Open_Intervention:
            tx.run("MATCH (a), (b) "
                   "WHERE a.name='InterventionOpen' AND b.name='GP' "
                   "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, resources: -0.3, modm:-0.1, "
                   "modc:-0.025}]->(b)")
            tx.run("MATCH (a), (b) "
                   "WHERE a.name='InterventionOpen' AND b.name='Hos' "
                   "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, resources: -0.8, modm:-0.25, "
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
