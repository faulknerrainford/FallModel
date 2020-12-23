from FallModel.Fall_agent import Patient
from FallModel import Fall_nodes as Nodes
from FallModel import Fall_services as Services
from FallModel import Fall_reset as Reset
from FallModel.Fall_Cluster import FallCluster as Cluster
from FallModel.Fall_Population import FallPopulation as Population
from FallModel.Fall_Viewer import OpinionViewer as Monitor

specname = "opinionShortRun0to9"

nodes = [Nodes.CareNode(), Nodes.SocialNode("SocialWalk"), Nodes.SocialNode("SocialCraft"),
         Nodes.SocialNode("SocialLunch"), Nodes.HosNode(), Nodes.GPNode(), Nodes.HomeNode()]

PatientClasses = None
AgentClasses = {"Patient": Patient}
NodeClasses = {"Care": Nodes.CareNode, "Hos": Nodes.HosNode, "Social": Nodes.SocialNode, "GP": Nodes.GPNode,
               "Intervention": Nodes.InterventionNode, "InterventionOpen": Nodes.InterventionNode,
               "Home": Nodes.HomeNode, "SocialLunch": Nodes.SocialNode, "SocialCraft": Nodes.SocialNode,
               "SocialWalk": Nodes.SocialNode}
ServiceClasses = {"care": Services.Care, "intervention": Services.Intervention}

carers = None
Intervention = "service"
savedirectory = "testfile"
activities = True

database_uri = "bolt://localhost:7687"

Flow_auth = Inter_auth = Balancer_auth = Population_auth = Structure_auth = Reset_auth = ("Inter", "fall")
Monitor_auth = ("Viewer", "watch")
