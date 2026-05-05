"""Boundary for DecisionRisk scenario ensemble operations over MiroFish simulations."""


class MiroFishSimulationFacade:
    def run_scenario(self, scenario_run_ref: object) -> dict:
        raise NotImplementedError("Live MiroFish simulation integration is post-foundation work.")
