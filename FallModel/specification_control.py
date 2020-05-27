from FallModel import Fall_nodes as Nodes
from FallModel import Monitor as Monitor
from FallModel import Balancer as Balancer
from FallModel import FallAgent as Agent
from FallModel import Fall_Population as Population
from FallModel import ResetV0 as Reset
import sys

specname = "control4"

nodes = [Nodes.CareNode(), Nodes.HosNodeV0(), Nodes.SocialNode(), Nodes.GPNode(), Nodes.InterventionNode(),
         Nodes.HomeNodeV0()]

Intervention_cap = 4
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
