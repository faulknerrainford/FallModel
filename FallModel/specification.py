from FallModel import Fall_nodes as Nodes
from FallModel import Fall_Monitor as Monitor
from FallModel import Fall_Balancer as Balancer
from FallModel import Patient as Agent
from FallModel import Fall_Population as Population
from FallModel import Fall_reset as Reset
import sys

specname = socialV1Test

nodes = [Nodes.CareNode(), Nodes.HosNode(), Nodes.SocialNode(), Nodes.GPNode(), Nodes.InterventionNode(),
         Nodes.InterventionNode("InterventionOpen"), Nodes.HomeNode()]

Intervention_cap = 2
Open_Intervention = True
Open_Intervention_cap = 2
Open_Intervention_Limits = ["Healthy", "At risk"]

savedirectory = "testfile"

database_uri = "bolt://localhost:7687"

Flow_auth = ("Flow", "Flow")
Balancer_auth = ("Balancer", "bal")
Population_auth = ("Population", "pop")
Structure_auth = ("Structure", "struct")
Reset_auth = ("dancer", "dancer")
Monitor_auth = ("monitor", "monitor")
