from itertools import product

import pytest

from ....simulation_engine import BGPSimpleAS
from ....simulation_engine import BGPAS
from ....simulation_engine import ROVAS
from ....simulation_engine import ROVSimpleAS
from ....simulation_engine import RealROVSimpleAS
from ....simulation_engine import RealPeerROVSimpleAS

from ....simulation_framework import NonRoutedPrefixHijack
from ....simulation_framework import NonRoutedSuperprefixHijack
from ....simulation_framework import NonRoutedSuperprefixPrefixHijack
from ....simulation_framework import PrefixHijack
from ....simulation_framework import ValidPrefix
from ....simulation_framework import SubprefixHijack
from ....simulation_framework import SuperprefixPrefixHijack
from ....simulation_framework import ScenarioConfig

from ....simulation_framework import Simulation

AS_CLASSES = (
    BGPSimpleAS,
    BGPAS,
    ROVAS,
    ROVSimpleAS,
    RealROVSimpleAS,
    RealPeerROVSimpleAS,
)

SCENARIOS = (
    NonRoutedPrefixHijack,
    NonRoutedSuperprefixHijack,
    NonRoutedSuperprefixPrefixHijack,
    PrefixHijack,
    SubprefixHijack,
    SuperprefixPrefixHijack,
    ValidPrefix,
)
NUM_ATTACKERS = (1, 2)
PARSE_CPUS = (1, 2)


# Really does need all these combos
# Since certain as classes might break with mp
@pytest.mark.slow
@pytest.mark.framework
@pytest.mark.parametrize(
    "AdoptASCls, BaseASCls, ScenarioCls, num_attackers, parse_cpus",
    [
        x
        for x in product(
            *[AS_CLASSES, AS_CLASSES, SCENARIOS, NUM_ATTACKERS, PARSE_CPUS]
        )
        # Where BaseASCls != AdoptASCls
        if x[0] != x[1]
    ],
)
def test_sim_inputs(
    AdoptASCls, BaseASCls, ScenarioCls, num_attackers, parse_cpus, tmp_path
):
    """Test basic functionality of process_incoming_anns"""

    sim = Simulation(
        percent_adoptions=(0.0, 0.5, 1.0),
        scenario_configs=(
            ScenarioConfig(
                ScenarioCls=ScenarioCls,
                AdoptASCls=AdoptASCls,
                BaseASCls=BaseASCls,
                num_attackers=num_attackers,
            ),
        ),
        num_trials=2,
        output_path=tmp_path / "test_sim_inputs",
        parse_cpus=parse_cpus,
    )
    sim.run()
