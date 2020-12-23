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
    def set_nodes(dri):
        """
        Generate the set of nodes used in Fall Models, currently only variation is if the Open Intervention node is
        included and the capacities on the Intervention nodes. The existence of the Open Intervention node and the nodes
        capacities are given in the specification file.

        :param dri: neo4j database driver

        :return: None
        """
        ses = dri.session()
        ses.run("CREATE (a:Node {name:'Hos', resources:0.2, modm:-0.1, modmood:-0.05, servicemodel:'alternative'})")
        ses.run("CREATE (a:Node {name:'Home', resources:0.3, servicemodel:'addative'})")
        if specification.activities:
            ses.run("CREATE (a:Node {name:'SocialLunch', resources:-0.4, modm:0.025, modmood:0.2, "
                    "servicemodel:'addative'})")
            ses.run("CREATE (a:Node {name:'SocialWalk', resources:-0.5, modm:0.075, modmood:0.2, "
                    "servicemodel:'addative'})")
            ses.run("CREATE (a:Node {name:'SocialCraft', resources:-0.45, modm:0.05, modmood:0.2, "
                    "servicemodel:'addative'})")
        else:
            ses.run("CREATE (a:Node {name:'Social', resources:-0.4, modm:0.05, modmood:0.2, servicemodel:'addative'})")
        if specification.Intervention != "service":
            ses.run("CREATE (a:Node {name:'Intervention', resources:-0.8, modm:0.3, modmood:0.3, cap:$c, load:0})",
                    c=specification.Intervention_cap)
        if specification.Intervention == "open":
            ses.run("CREATE (a:Node {name:'InterventionOpen', resources:-0.8, modm:0.3, modmood:0.3, cap:$c, load:0})",
                    c=specification.Open_Intervention_cap)
        ses.run("CREATE (a:Node {name:'Care', time:'t', interval:0, mild:0, moderate:0, severe:0, agents:0, "
                "servicemodel:'addative'})")
        ses.run("CREATE (a:Node {name:'GP', servicemodel:'alternative'})")
        ses.run("CREATE (a:Organisation {name:'localNHS'})")
        ses.close()

    @staticmethod
    def set_edges(dri):
        """
        Generates the edges used in the commonly used system graph for Social Fall Model simulations. The variation in
        edges depends on existence of Open Intervention and the types of agents allows along the edge to the Open
        Intervention node, this is given in the specification file.

        :param dir: neo4j database driver

        :return: None
        """
        ses = dri.session()
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Hos' AND b.name='Home' "
                "CREATE (a)-[r:REACHES {mood:0, resources:-0.1, type:'inactive'}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Home' AND b.name='GP' "
                "CREATE (a)-[r:REACHES {mood:0, resources: -0.3, modm:-0.1, type:'fall', modmood:-0.025}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Intervention' AND b.name='GP' "
                "CREATE (a)-[r:REACHES {mood:0, resources: -0.3, modm:-0.1, type:'fall', modmood:-0.025}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='GP' AND b.name='Hos' "
                "CREATE (a)-[r:REACHES {mood:0, type:'fall'}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='GP' AND b.name='Home' "
                "CREATE (a)-[r:REACHES {mood:0, type:'inactive'}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Home' AND b.name='Intervention' "
                "CREATE (a)-[r:REACHES {resources:-0.2, mood:0.1, allowed:'Fallen', ref:'True', type:'medical'}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Intervention' AND b.name='Home' "
                "CREATE (a)-[r:REACHES {resources:-0.05, mood:0, type:'inactive'}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Intervention' AND b.name='Hos' "
                "CREATE (a)-[r:REACHES {mood:0, resources: -0.8, modm:-0.25, modc:-0.35, type:'fall'}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Home' AND b.name='Hos' "
                "CREATE (a)-[r:REACHES {mood:0, resources: -0.8, modm:-0.25, modc:-0.5, type:'fall'}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Home' AND b.name='Care' "
                "CREATE (a)-[r:REACHES {mood:0, type:'immobility'}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Home' AND b.name='Home' "
                "CREATE (a)-[r:REACHES {mood:0, type:'inactive'}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Hos' AND b.name='Care' "
                "CREATE (a)-[r:REACHES {mood:0, type:'immobility'}]->(b)")
        if specification.activities:
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='Home' AND b.name='SocialLunch' "
                    "CREATE (a)-[r:REACHES {resources:-0.1, mood:0.2, type:'social'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='SocialLunch' AND b.name='Home' "
                    "CREATE (a)-[r:REACHES {resources:-0.1, mood:0, type:'inactive'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='SocialLunch' AND b.name='Hos' "
                    "CREATE (a)-[r:REACHES {mood:0, resources: -0.8, modm:-0.25, modc:-0.35, type:'fall'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='SocialLunch' AND b.name='GP' "
                    "CREATE (a)-[r:REACHES {mood:0, resources: -0.3, modm:-0.1, type:'fall', modmood:-0.025}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='Home' AND b.name='SocialWalk' "
                    "CREATE (a)-[r:REACHES {resources:-0.1, mood:0.25, type:'social'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='SocialWalk' AND b.name='Home' "
                    "CREATE (a)-[r:REACHES {resources:-0.1, mood:0, type:'inactive'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='SocialWalk' AND b.name='Hos' "
                    "CREATE (a)-[r:REACHES {mood:0, resources: -0.8, modm:-0.25, modc:-0.35, type:'fall'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='SocialWalk' AND b.name='GP' "
                    "CREATE (a)-[r:REACHES {mood:0, resources: -0.3, modm:-0.1, type:'fall', modmood:-0.025}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='Home' AND b.name='SocialCraft' "
                    "CREATE (a)-[r:REACHES {resources:-0.1, mood:0.2, type:'social'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='SocialCraft' AND b.name='Home' "
                    "CREATE (a)-[r:REACHES {resources:-0.1, mood:0, type:'inactive'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='SocialCraft' AND b.name='Hos' "
                    "CREATE (a)-[r:REACHES {mood:0, resources: -0.8, modm:-0.25, modc:-0.35, type:'fall'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='SocialCraft' AND b.name='GP' "
                    "CREATE (a)-[r:REACHES {mood:0, resources: -0.3, modm:-0.1, type:'fall', modmood:-0.025}]->(b)")
        else:
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='Home' AND b.name='Social' "
                    "CREATE (a)-[r:REACHES {resources:-0.1, mood:0.2, type:'social'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='Social' AND b.name='Home' "
                    "CREATE (a)-[r:REACHES {resources:-0.1, mood:0, type:'inactive'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='Social' AND b.name='Hos' "
                    "CREATE (a)-[r:REACHES {mood:0, resources: -0.8, modm:-0.25, modc:-0.35, type:'fall'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='Social' AND b.name='GP' "
                    "CREATE (a)-[r:REACHES {mood:0, resources: -0.3, modm:-0.1, type:'fall', modmood:-0.025}]->(b)")
        if specification.Intervention == "open":
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='InterventionOpen' AND b.name='GP' "
                    "CREATE (a)-[r:REACHES {mood:0, resources: -0.3, modm:-0.1, modc:-0.025, type:'fall'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='InterventionOpen' AND b.name='Hos' "
                    "CREATE (a)-[r:REACHES {mood:0, resources: -0.8, modm:-0.25, modc:-0.35, type:'fall'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='InterventionOpen' AND b.name='Home' "
                    "CREATE (a)-[r:REACHES {resources:-0.2, mood:0, type:'inactive'}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='Home' AND b.name='InterventionOpen' "
                    "CREATE (a)-[r:REACHES {resources:-0.05, mood:0.2, allowed:$limits, ref:'False', "
                    "type:'medical'}]->(b)",
                    limits=specification.Open_Intervention_Limits)
        ses.close()

    @staticmethod
    def generate_population(dri, ps):
        """
        Generates the required number of agents split between carers and patients and starts them at the Home node.
        Builds social and care links between agents.

        :param dir: neo4j database driver
        :param ps: population size

        :return: None
        """
        fa = Patient(None)
        cps = ps // 4
        pps = ps - cps
        if specification.carers == "agents":
            ca = Carer(None)
            for i in range(cps):
                ca.generator(dri, [2, 2, 4, [3, 0, 0, 1, 0], 2, 8])
        elif specification.carers:
            for j in range(cps):
                ses = dri.session()
                ses.run("CREATE (a:Carer {id:{j_id}, resources:20})", j_id=j)
                ses.close()
        if not specification.carers:
            pps = ps
        for i in range(pps):
            fa.generator(dri, [0.8, 0.9, 1, [2, 0, 1, 2, 0], 2, 8])
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
                    intf.create_edge(dri, [i + cps, 'Agent', 'id'], [nf, 'Agent', 'id'], 'SOCIAL', 'created: '
                                     + str(intf.get_time(dri)) + ', colocation: ' + str(intf.get_time(dri))
                                     + ', utilization: ' + str(intf.get_time(dri))
                                     + ', type: ' + ag_type)
        for i in range(ps):
            new_friends = npr.choice(range(ps), size=npr.choice(range(3)), replace=False)
            for nf in new_friends:
                if not nf == i:
                    if npr.random(1) < 0.5:
                        ag_type = '"family"'
                    else:
                        ag_type = '"social"'
                    intf.create_edge(dri, [i, 'Agent', 'id'], [nf, 'Agent', 'id'], 'SOCIAL', 'created: '
                                     + str(intf.get_time(dri)) + ', colocation: ' + str(intf.get_time(dri))
                                     + ', utilization: ' + str(intf.get_time(dri))
                                     + ', type: ' + ag_type)

    @staticmethod
    def set_service(dri):
        """
        Services to be added to the system

        :param dri: Neo4j database driver

        :return:None
        """
        ses = dri.session()
        ses.run("CREATE (a:Service {name:'care', resources:0.5, capacity:5, load:0, date:0})")
        ses.run("CREATE (a:Service {name:'intervention', resources:-0.8, mobility:0.3, capacity:2, load:0, date:0})")
        ses.run("MATCH (s:Service), (n:Node) "
                "WHERE s.name='care' AND n.name='Home' "
                "CREATE (s)-[r:PROVIDE]->(n)")
        ses.run("MATCH (s:Service), (n:Node) "
                "WHERE s.name='intervention' AND n.name='Hos' "
                "CREATE (s)-[r:PROVIDE]->(n)")
        ses.close()


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
    def set_nodes(dri):
        """
        Generate the set of nodes used in Fall Models, currently only variation is if the Open Intervention node is
        included and the capacities on the Intervention nodes. The existence of the Open Intervention node and the nodes
        capacities are given in the specification file.

        :param dri: neo4j database driver

        :return: None
        """
        ses = dri.session()
        ses.run("CREATE (a:Node {name:'Hos', resources:0.2, modm:-0.1, modc:-0.05})")
        ses.run("CREATE (a:Node {name:'Home', resources:0.3})")
        ses.run("CREATE (a:Node {name:'Social', resources:-0.4, modm:0.05, modc:0.2, modrc:0.2})")
        ses.run("CREATE (a:Node {name:'Intervention', resources:-0.8, modm:0.3, modc:0.3, cap:{c}, load:0})",
                c=specification.Intervention_cap)
        if specification.Open_Intervention:
            ses.run("CREATE (a:Node {name:'InterventionOpen', resources:-0.8, modm:0.3, modc:0.3, cap:{c}, load:0})",
                    c=specification.Open_Intervention_cap)
        ses.run("CREATE (a:Node {name:'Care', time:'t', interval:0, mild:0, moderate:0, severe:0, agents:0})")
        ses.run("CREATE (a:Node {name:'GP'})")
        ses.close()

    @staticmethod
    def set_edges(dri):
        """
        Generates the edges used in the commonly used system graph for Fall Model simulations. The variation in edges
        depends on existence of Open Intervention and the types of agents allows along the edge to the Open Intervention
        node, this is given in the specification file.

        :param dri: neo4j database driver

        :return: None
        """
        ses = dri.session()
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Hos' AND b.name='Home' "
                "CREATE (a)-[r:REACHES {effort:0.01, mobility:1, confidence:1, resources:-0.1, worth:0.1}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Home' AND b.name='GP' "
                "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, resources: -0.3, modm:-0.1, "
                "modc:-0.025}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Intervention' AND b.name='GP' "
                "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, resources: -0.3, modm:-0.1, "
                "modc:-0.025}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Social' AND b.name='GP' "
                "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, resources: -0.3, modm:-0.1, "
                "modc:-0.025}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='GP' AND b.name='Hos' "
                "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='GP' AND b.name='Home' "
                "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Home' AND b.name='Social' "
                "CREATE (a)-[r:REACHES {effort:0.1, mobility:0.6, confidence:0.4, worth:1}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Social' AND b.name='Home' "
                "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, worth:0}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Home' AND b.name='Intervention' "
                "CREATE (a)-[r:REACHES {effort:0.3, mobility:0.5, confidence:0.5, worth:2, allowed:'Fallen', "
                "ref:'True'}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Intervention' AND b.name='Home' "
                "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, worth:1}]->(b)")
        # Falls
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Intervention' AND b.name='Hos' "
                "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, resources: -0.8, modm:-0.25, "
                "modc:-0.35}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Social' AND b.name='Hos' "
                "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, resources: -0.8, modm:-0.25, "
                "modc:-0.35}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Home' AND b.name='Hos' "
                "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, resources: -0.8, modm:-0.25, "
                "modc:-0.5}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Home' AND b.name='Care' "
                "CREATE (a)-[r:REACHES {effort:0, worth:-1, mobility:1, confidence:1}]->(b)")
        ses.run("MATCH (a), (b) "
                "WHERE a.name='Hos' AND b.name='Care' "
                "CREATE (a)-[r:REACHES {effort:0, worth:-100, mobility:1, confidence:1}]->(b)")
        if specification.Open_Intervention:
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='InterventionOpen' AND b.name='GP' "
                    "CREATE (a)-[r:REACHES {worth:-5, effort:0, mobility:1, confidence:1, resources: -0.3, modm:-0.1, "
                    "modc:-0.025}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='InterventionOpen' AND b.name='Hos' "
                    "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, resources: -0.8, modm:-0.25, "
                    "modc:-0.35}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='InterventionOpen' AND b.name='Home' "
                    "CREATE (a)-[r:REACHES {effort:0, mobility:1, confidence:1, worth:1}]->(b)")
            ses.run("MATCH (a), (b) "
                    "WHERE a.name='Home' AND b.name='InterventionOpen' "
                    "CREATE (a)-[r:REACHES {effort:0.3, mobility:0.5, confidence:0.5, worth:2, allowed:{limits}, "
                    "ref:'False'}]->(b)", limits=specification.Open_Intervention_Limits)
        ses.close()

    @staticmethod
    def generate_population(dri, ps):
        """
        Generates the required number of agents and starts them at the Home node.

        :param dri: neo4j database driver
        :param ps: population size

        :return: None
        """
        fa = FallAgent(None)
        for i in range(ps):
            fa.generator(dri, [0.8, 0.9, 1])
