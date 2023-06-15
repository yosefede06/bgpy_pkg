from ..graphs import graph_001
from ..utils import EngineTestConfig

from ....simulation_engine import BGPAS
from ....enums import ASNs
from ....simulation_framework import ScenarioConfig, SubprefixHijack


config_002 = EngineTestConfig(
    name="002",
    desc="BGP hidden hijack",
    scenario_config=ScenarioConfig(
        ScenarioCls=SubprefixHijack,
        BaseASCls=BGPAS,
        override_attacker_asns={ASNs.ATTACKER.value},
        override_victim_asns={ASNs.VICTIM.value},
        override_non_default_asn_cls_dict=dict(),
    ),
    graph=graph_001,
)
