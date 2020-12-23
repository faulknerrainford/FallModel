import sys
sys.path.insert(1, '/Users/stormbridge/PycharmProjects/SPmodelling')
import SPmodelling.SPm
from FallModel.Fall_Cluster import FallOpinion

if __name__ == '__main__':
    SPmodelling.SPm.main(10, 500, 1000, coremodules=["Flow", "Social", "Cluster", "Population", "Monitor"],
                         additionalmodules=[FallOpinion()], reset=True)
