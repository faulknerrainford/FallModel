from FallModel import Fall_nodes as Nodes
from FallModel import Fall_Monitor as Monitor
from FallModel import Fall_Balancer as Balancer
from FallModel import Fall_agent as Agents
from FallModel import Fall_Population as Population
from FallModel import Fall_reset as Reset
import sys

specname = "control2"

nodes = [Nodes.CareNode(), Nodes.HosNode(), Nodes.SocialNode(), Nodes.GPNode(), Nodes.InterventionNode(),
         Nodes.HomeNode()]

Intervention_cap = 2
Open_Intervention = False
Open_Intervention_cap = 0
Intervention_Limit = "'Fallen, At risk, Healthy'"
dynamic = False

savedirectory = "/Fall_Data/"

database_uri = "bolt://localhost:7687"

Flow_auth = ("Flow", "Flow")
Balancer_auth = ("Balancer", "bal")
Population_auth = ("Population", "pop")
Structure_auth = ("Structure", "struct")
Reset_auth = ("dancer", "dancer")
Monitor_auth = ("monitor", "monitor")
