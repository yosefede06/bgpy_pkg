from ..graphs import graph_003
from ..utils import EngineTestConfig

from ....simulation_engine import BGPAS
from ....enums import ASNs
from ....simulation_framework import ScenarioConfig, SubprefixHijack


config_009 = EngineTestConfig(
    name="009",
    desc="Fig 2 (ROVSimpleAS)",
    scenario_config=ScenarioConfig(
        ScenarioCls=SubprefixHijack,
        BaseASCls=BGPAS,
        override_attacker_asns={ASNs.ATTACKER.value},
        override_victim_asns={ASNs.VICTIM.value},
        override_non_default_asn_cls_dict=dict(),
    ),
    graph=graph_003,
)
