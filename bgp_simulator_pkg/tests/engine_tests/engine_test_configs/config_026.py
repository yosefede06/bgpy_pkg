from ..graphs import graph_019
from ..utils import EngineTestConfig

from ....simulation_engine import ROVAS
from ....enums import ASNs
from ....simulation_framework import ScenarioConfig, ValidPrefix


config_026 = EngineTestConfig(
    name="026",
    desc="Test of tiebreak preference",
    scenario_config=ScenarioConfig(
        ScenarioCls=ValidPrefix,
        BaseASCls=ROVAS,
        override_victim_asns={ASNs.VICTIM.value},
        override_non_default_asn_cls_dict=dict(),
    ),
    graph=graph_019,
)
