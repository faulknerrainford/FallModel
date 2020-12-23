import SPmodelling.Cluster
import SPmodelling.Interface as intf
import specification


class FallCluster(SPmodelling.Cluster.Cluster):
    """
    Specialised clustering for Fall model
    """

    def __init__(self, dri):
        """
        Sets up correct strength parameter for clusters

        :param tx: neo4j database write transaction
        """
        super(FallCluster, self).__init__(dri, "connectedness")
        clusters = intf.clusters_in_system(dri)
        for cluster in clusters:
            if not intf.get_node_value(dri, [cluster, "Cluster", "id"], "opinion"):
                intf.update_node(dri, [cluster, "Cluster", "id"], "opinion", 0)

    def apply_change(self, dri):
        """
        Updates the clustering in the system

        :param dri: neo4j database write transaction

        :return: None
        """
        super(FallCluster, self).apply_change(tx)
        if self.current_clusters:
            clusters = self.current_clusters
        else:
            clusters = intf.clusters_in_system(dri)
        clusters = [[cluster, "Cluster", "id"] for cluster in clusters]
        for cluster in clusters:
            agents = intf.agents_in_cluster(dri, cluster)
            # get the connectedness to the cluster for each agent
            if agents:
                for agent in agents:
                    connectedness = intf.connectedness(dri, agent, cluster)
                    SPmodelling.Cluster.update_cluster_strength(dri, agent, cluster, connectedness,
                                                                "connectedness")
        SPmodelling.Cluster.update_cluster_orientation(dri, intf.get_pop_size(dri), "connectedness", 0, "ascending")

    def new_cluster(self, dri, cluster_id):
        """
        Adds a new cluster to the system based on the cluster number

        :param dri: neo4j database write transaction
        :param cluster_id: id number of cluster to be added to the system

        :return: None
        """
        super(FallCluster, self).new_cluster(dri, cluster_id)
        intf.update_node(dri, [cluster_id, "Cluster", "id"], "opinion", 0)


class FallOpinion(SPmodelling.Intervenor.Intervenor):
    """
    Intervenor to update the opinions of clusters based on the agents in them
    """

    def __init__(self):
        super(FallOpinion, self).__init__("FallOpinion")

    def main(self):
        super(FallOpinion, self).main()

    def check(self, dri):
        pass

    @staticmethod
    def apply_change(dri):
        """
        For each cluster form a weighted average opinion of the agents in the group and update the cluster

        :param dri: neo4j database write transaction

        :return: None
        """
        clusters = intf.clusters_in_system(dri)
        if clusters:
            clusters = [[cluster, "Cluster", "id"] for cluster in clusters]
            for cluster in clusters:
                weighted_ops = 0
                friendliness = 1
                agents = intf.agents_in_cluster(dri, cluster)
                if agents:
                    for ag in agents:
                        ag_mob = intf.get_node_value(dri, ag, "mobility")
                        if ag_mob and ag_mob > 0:
                            ag_op = intf.get_node_value(dri, ag, "opinion")
                            ag_friend = intf.get_node_value(dri, ag, "friendliness")
                            weighted_ops = weighted_ops + ag_op*ag_friend
                            friendliness = friendliness + ag_friend
                    group_op = weighted_ops/friendliness
                    intf.update_node(dri, cluster, "opinion", group_op)
