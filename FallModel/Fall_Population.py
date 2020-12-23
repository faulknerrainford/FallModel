import specification
from FallModel.Fall_agent import Carer, Patient
import SPmodelling.Population

c_params = [2, 2, 4, [3, 0, 0, 1], 2, 8]
p_params = [0.8, 0.9, 1, [2, 0, 1, 2, 0], 2, 8]
params = [0.8, 0.9, 1]


def countactiveagents(dri, count_type="Agent"):
    """
    Utility function provides the number of agents in the database discounting those are the Care Node.

    :param dri: neo4j database driver
    :param count_type: type of objects located at node to be counted, defaults to agents but can be changed to agent sublabel

    :return: number of active agents in system
    """
    query_total = "MATCH (n:" + count_type + ") WITH n RETURN count(*)"
    query_care = "MATCH (n:" + count_type + ")-[r:LOCATED]->(a:Node) ""WHERE a.name='Care' ""RETURN count(*)"
    ses = dri.session()
    total_agents = ses.run(query_total).value()[0]
    care_agents = ses.run(query_care).value()[0]
    ses.close()
    return total_agents - care_agents


class FallPopulation(SPmodelling.Population.Population):

    def __init__(self):
        super(FallPopulation, self).__init__()

    @staticmethod
    def check(dri, ps):
        """
        Confirms number of agents below designated population size. If population correct returns false, else returns
        total number of agents undersize and number of carers and patients missing

        :param dri: neo4j database driver
        :param ps: int population size to be maintained

        :return: int number of agents below population size or false if population correct
        """
        # activecarers = dri.read_transaction(countactiveagents, "Carer")
        activecarers = 0
        totalactive = countactiveagents(dri)
        if totalactive < ps:
            return [ps - totalactive, (ps//4)-activecarers, (ps - totalactive)-((ps//4)-activecarers)]
        return False

    @staticmethod
    def apply_change(dri, missing):
        """
        Replaces missing agents in system taking into account balancing the need to add new carers and patients as carers
        can become patients and also leave the system

        :param dri: neo4j database driver
        :param missing: [total_missing_patients, missing_carers, missing_patients]

        :return: None
        """
        if specification.carers == "agents":
            # generate mixed set of agents
            [total_ags, carers, patients] = missing
            carer = Carer(None)
            for i in range(carers):
                carer.generator(dri, c_params)
            patient = Patient(None)
            for i in range(patients):
                patient.generator(dri, p_params)
        else:
            agent = Patient(None)
            for i in missing:
                agent.generator(dri, p_params)
