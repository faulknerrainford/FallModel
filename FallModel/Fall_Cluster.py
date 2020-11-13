import SPmodelling.Cluster
import SPmodelling.Interface as intf
import specification


class FallCluster(SPmodelling.Cluster.Cluster):

    def __init__(self, tx):
        super(FallCluster, self).__init__(tx, "connectedness")
        clusters = intf.clusters_in_system(tx)
        for cluster in clusters:
            if not intf.get_node_value(tx, [cluster, "Cluster", "id"], "opinion"):
                "Reached opinion setting"
                intf.update_node(tx, [cluster, "Cluster", "id"], "opinion", 0)

    def apply_change(self, tx):
        super(FallCluster, self).apply_change(tx)
        if self.current_clusters:
            clusters = self.current_clusters
        else:
            clusters = intf.clusters_in_system(tx)
        clusters = [[cluster, "Cluster", "id"] for cluster in clusters]
        for cluster in clusters:
            agents = intf.agents_in_cluster(tx, cluster)
            # get the connectedness to the cluster for each agent
            if agents:
                for agent in agents:
                    connectedness = intf.connectedness(tx, agent, cluster)
                    SPmodelling.Cluster.update_cluster_strength(tx, agent, cluster, connectedness,
                                                                "connectedness")
        SPmodelling.Cluster.update_cluster_orientation(tx, intf.get_pop_size(tx), "connectedness", 0, "ascending")

    def new_cluster(self, tx, cluster_id):
        super(FallCluster, self).new_cluster(tx, cluster_id)
        intf.update_node(tx, [cluster_id, "Cluster", "id"], "opinion", 0)


class FallOpinion(SPmodelling.Intervenor.Intervenor):
    
    def __init__(self):
        super(FallOpinion, self).__init__("FallOpinion")

    def main(self):
        super(FallOpinion, self).main()

    def check(self, tx):
        pass

    @staticmethod
    def apply_change(tx):
        clusters = intf.clusters_in_system(tx)
        if clusters:
            clusters = [[cluster, "Cluster", "id"] for cluster in clusters]
            for cluster in clusters:
                weighted_ops = 0
                friendliness = 0
                agents = intf.agents_in_cluster(tx, cluster)
                for ag in agents:
                    ag_op = intf.get_node_value(tx, ag, "opinion")
                    ag_friend = intf.get_node_value(tx, ag, "friendliness")
                    weighted_ops = weighted_ops + ag_op*ag_friend
                    friendliness = friendliness + ag_friend
                group_op = weighted_ops/friendliness
                intf.update_node(tx, cluster, "opinion", group_op)
                print("Updating Opinions")
