from copy import deepcopy
import functools
import logging
from multiprocessing import Pool
import random
import sys

from lib_caida_collector import CaidaCollector

from .attacks import Attack
from .data_point import DataPoint
from .scenario import Scenario

from ..engine import BGPAS, SimulatorEngine


def my_decorator(func):
    @functools.wraps(func)
    def function_that_runs_func(*args, **kwargs):
        # Inside the decorator
        # Run the function
        return func(*args, **kwargs)
    return function_that_runs_func


if "pypy" in sys.executable:
    mp_decorator = my_decorator
else:
    import ray
    mp_decorator = ray.remote


class Graph:
    from .graph_writer import aggregate_and_write, get_graphs_to_write
    from .graph_writer import _get_line, _write

    def __init__(self,
                 percent_adoptions=[0, 5, 10, 20, 30, 50, 75, 100],
                 adopt_as_classes=[],
                 AttackCls=None,
                 num_trials=1,
                 propagation_rounds=1,
                 base_as_cls=BGPAS,
                 profiler=None):
        assert isinstance(percent_adoptions, list)
        self.percent_adoptions = percent_adoptions
        self.adopt_as_classes = adopt_as_classes
        self.num_trials = num_trials
        # Why propagation rounds? Because some atk/def scenarios might require
        # More than one round of propagation
        self.propagation_rounds = propagation_rounds
        self.AttackCls = AttackCls
        self.base_as_cls = base_as_cls
        self.profiler = profiler

    def _get_mp_chunks(self, parse_cpus):
        """Not a generator since we need this for multiprocessing"""

        percents_and_trials = []
        for percent_adoption in self.percent_adoptions:
            for trial in range(self.num_trials):
                percents_and_trials.append((percent_adoption, trial))

        # Refactor this later
        chunks = [[] for _ in range(min(parse_cpus, len(percents_and_trials)))]
        chunk_index = 0
        for percent_and_trial in percents_and_trials:
            chunks[chunk_index].append(percent_and_trial)
            chunk_index += 1
            if chunk_index == len(chunks):
                chunk_index = 0
        return chunks

    def run(self, parse_cpus, _dir, caida_dir=None, debug=False):
        self.data_points = dict()
        self._dir = _dir
        self.caida_dir = caida_dir

        if debug:
            # Done just to get subgraphs, change this later
            engine = CaidaCollector(BaseASCls=self.base_as_cls,
                                    GraphCls=SimulatorEngine,
                                    _dir=self.caida_dir,
                                    _dir_exist_ok=True).run(tsv=False)

            self.subgraphs = self._get_subgraphs(engine)
            self._validate_subgraphs()
            for chunk in self._get_mp_chunks(parse_cpus):
                result = self._run_mp_chunk(chunk,
                                            engine=engine,
                                            subgraphs=self.subgraphs)
                for data_point, trial_info_list in result.items():
                    if data_point not in self.data_points:
                        self.data_points[data_point] = []
                    self.data_points[data_point].extend(trial_info_list)
        else:
            print("About to run pool")
            if "pypy" in sys.executable:
                # Pool is much faster than ProcessPoolExecutor
                with Pool(parse_cpus) as pool:
                    for result in pool.map(self._run_mp_chunk,
                                           self._get_mp_chunks(parse_cpus)):
                        for data_point, trial_info_list in result.items():
                            if data_point not in self.data_points:
                                self.data_points[data_point] = []
                            self.data_points[data_point].extend(
                                trial_info_list)
            else:
                results = [self.__class__._run_mp_chunk.remote(self, x)
                           for x in self._get_mp_chunks(
                               int(ray.cluster_resources()["CPU"]))]
                for result in results:
                    for data_point, trial_info_list in ray.get(result).items():
                        if data_point not in self.data_points:
                            self.data_points[data_point] = []
                        self.data_points[data_point].extend(trial_info_list)

        print("\nGraph complete")
        if not debug:
            # Done just to get subgraphs, change this later
            engine = CaidaCollector(BaseASCls=self.base_as_cls,
                                    GraphCls=SimulatorEngine,
                                    _dir=self.caida_dir,
                                    _dir_exist_ok=True).run(tsv=False)

            self.subgraphs = self._get_subgraphs(engine)
            self._validate_subgraphs()

    @mp_decorator
    def _run_mp_chunk(self, chunk, engine=None, subgraphs=None):
        if engine is None:
            # Engine is not picklable or dillable AT ALL, so do it here
            # Changing recursion depth does nothing
            # Making nothing a reference does nothing
            engine = CaidaCollector(BaseASCls=self.base_as_cls,
                                    GraphCls=SimulatorEngine,
                                    _dir=self.caida_dir,
                                    _dir_exist_ok=True).run(tsv=False)

        if subgraphs is None:
            self.subgraphs = self._get_subgraphs(engine)
            self._validate_subgraphs()

        data_points = dict()

        for percent_adopt, trial in chunk:

            og_attack = self._get_attack()
            adopting_asns = self._get_adopting_ases(percent_adopt, og_attack)
            assert len(adopting_asns) != 0
            for ASCls in self.adopt_as_classes:

                print(f"Adopt {percent_adopt} trial {trial} {ASCls.name}",
                      end=" " * 10 + "\r")
                # In case the attack has state we deepcopy it
                # so that it doesn't remain from policy to policy
                attack = deepcopy(og_attack)
                self._replace_engine_policies({x: ASCls
                                               for x in adopting_asns}, engine)
                for propagation_round in range(self.propagation_rounds):
                    # Generate the test
                    scenario = Scenario(trial=trial,
                                        engine=engine,
                                        attack=attack,
                                        profiler=self.profiler)
                    # Run test, remove reference to engine and return it
                    scenario.run(self.subgraphs, propagation_round)
                    # Get data point - just a frozen data class
                    # Just makes it easier to access properties later
                    dp = DataPoint(percent_adopt, ASCls, propagation_round)
                    # Append the test to all tests for that data point
                    data_points[dp] = data_points.get(dp, [])
                    data_points[dp].append(scenario)
                    for func in attack.post_run_hooks:
                        func(engine, dp)
        return data_points

    def _get_subgraphs(self, engine):
        """Returns all the subgraphs that you want to keep track of"""

        top_level = set(x.asn for x in engine if x.input_clique)
        stubs_and_mh = set([x.asn for x in engine if x.stub or x.multihomed])

        subgraphs = dict()
        # Remove sets to make keeping deterministic properties easier
        subgraphs["etc"] = set([x.asn for x in engine
                                if x.asn not in top_level
                                and x.asn not in stubs_and_mh])
        subgraphs["input_clique"] = top_level
        subgraphs["stubs_and_mh"] = stubs_and_mh
        return subgraphs

    def _validate_subgraphs(self):
        """Makes sure subgraphs are mutually exclusive and contain ASNs"""

        all_ases = []
        for subgraph_asns in self.subgraphs.values():
            msg = "Subgraphs must be sets for fast lookups"
            assert isinstance(subgraph_asns, set), msg
            all_ases.extend(subgraph_asns)
        for x in all_ases:
            assert isinstance(x, int), "Subgraph doesn't contain ASNs"

        msg = "subgraphs not mutually exclusive"
        assert len(all_ases) == len(set(all_ases)), msg

    def _get_attack(self):
        return self.AttackCls(*random.sample(self.subgraphs["stubs_and_mh"],
                                             2))

    def _get_adopting_ases(self, percent_adopt, attack) -> list:
        """Return a list of adopting ASNs that aren't attackers"""

        asns_adopting = list()
        for subgraph_asns in self.subgraphs.values():
            # Get all possible ASes that could adopt
            possible_adopting_ases = self._get_possible_adopting_asns(
                subgraph_asns, attack)

            # N choose k, k is number of ASNs that will adopt
            k = len(possible_adopting_ases) * percent_adopt // 100
            if k == 0:
                logging.debug("ASNs adopting rounded down to 0, "
                              "increasing it to 1")
                k = 1
            elif k == len(possible_adopting_ases):
                logging.debug("K is 100%, changing to 100% -1")
                k -= 1

            asns_adopting.extend(random.sample(possible_adopting_ases, k))
        asns_adopting += self._get_default_adopters(attack)
        assert len(asns_adopting) == len(set(asns_adopting))
        return asns_adopting

    def _get_default_adopters(self, attack):
        return [attack.victim_asn]

    def _get_default_non_adopters(self, attack):
        return [attack.attacker_asn]

    def _get_possible_adopting_asns(self, subgraph_asns: set, attack: Attack):
        """Returns the set of all possible adopting ASNs

        Done here so that you can easily override to also remove victims
        from possible adopters
        """

        uncountable = self._get_default_adopters(attack)
        uncountable += self._get_default_non_adopters(attack)

        # Return all ASes other than the attacker
        return subgraph_asns.difference(set(uncountable))

    def _replace_engine_policies(self, as_cls_dict, base_engine):
        for asn, as_obj in base_engine.as_dict.items():
            as_obj.__class__ = as_cls_dict.get(asn, self.base_as_cls)
            # reset_base is set to false so that we don't override AS info
            as_obj.__init__(reset_base=False)

    @property
    def total_scenarios(self):
        total_scenarios = self.num_trials * len(self.percent_adoptions)
        total_scenarios *= len(self.adopt_as_classes)
        total_scenarios *= self.propagation_rounds
        return total_scenarios
