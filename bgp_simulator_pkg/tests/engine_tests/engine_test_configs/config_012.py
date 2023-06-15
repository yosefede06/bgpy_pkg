from ..graphs import graph_006
from ..utils import EngineTestConfig

from ....simulation_engine import BGPSimpleAS, ROVAS
from ....enums import ASNs
from ....simulation_framework import ScenarioConfig, NonRoutedPrefixHijack


config_012 = EngineTestConfig(
    name="012",
    desc="NonRouted Prefix Hijack",
    scenario_config=ScenarioConfig(
        ScenarioCls=NonRoutedPrefixHijack,
        AdoptASCls=ROVAS,
        BaseASCls=BGPSimpleAS,
        override_attacker_asns={ASNs.ATTACKER.value},
        override_victim_asns={ASNs.VICTIM.value},
        override_non_default_asn_cls_dict={2: ROVAS},
    ),
    graph=graph_006,
)
