import specification
from FallModel.Fall_agent import Carer, Patient
import SPmodelling.Population

c_params = [2, 2, 4, [3, 0, 0, 1], 2, 8]
p_params = [0.8, 0.9, 1, [2, 0, 1, 2, 0], 2, 8]
params = [0.8, 0.9, 1]


def countactiveagents(tx, count_type="Agent"):
    """
    Utility function provides the number of agents in the database discounting those are the Care Node.

    :param tx: neo4j database read transaction
    :param count_type: type of objects located at node to be counted, defaults to agents but can be changed to agent sublabel

    :return: number of active agents in system
    """
    query_total = "MATCH (n:" + count_type + ") WITH n RETURN count(*)"
    query_care = "MATCH (n:" + count_type + ")-[r:LOCATED]->(a:Node) ""WHERE a.name='Care' ""RETURN count(*)"
    total_agents = tx.run(query_total).value()[0]
    care_agents = tx.run(query_care).value()[0]
    return total_agents - care_agents


class FallPopulation(SPmodelling.Population.Population):

    def __init__(self):
        super(FallPopulation, self).__init__()

    @staticmethod
    def check(tx, ps):
        """
        Confirms number of agents below designated population size. If population correct returns false, else returns
        total number of agents undersize and number of carers and patients missing

        :param tx: neo4j database write transaction
        :param ps: int population size to be maintained

        :return: int number of agents below population size or false if population correct
        """
        # activecarers = tx.read_transaction(countactiveagents, "Carer")
        activecarers = 0
        totalactive = countactiveagents(tx)
        if totalactive < ps:
            return [ps - totalactive, (ps//4)-activecarers, (ps - totalactive)-((ps//4)-activecarers)]
        return False

    @staticmethod
    def apply_change(tx, missing):
        """
        Replaces missing agents in system taking into account balancing the need to add new carers and patients as carers
        can become patients and also leave the system

        :param tx: neo4j database session
        :param missing: [total_missing_patients, missing_carers, missing_patients]

        :return: None
        """
        if specification.carers == "agents":
            # generate mixed set of agents
            [total_ags, carers, patients] = missing
            carer = Carer(None)
            for i in range(carers):
                carer.generator(tx, c_params)
            patient = Patient(None)
            for i in range(patients):
                patient.generator(tx, p_params)
        else:
            agent = Patient(None)
            for i in missing:
                agent.generator(tx, p_params)
