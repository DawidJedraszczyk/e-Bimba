from dataclasses import dataclass

from .estimator import Estimates
from .plan import Plan


@dataclass
class DiscoveredStop:
    estimates: Estimates
    best: dict[int, Plan]

    def register_plan(self, plan: Plan) -> bool:
        prev = self.best.get(plan.generation)

        if prev is None:
            self.best[plan.generation] = plan
            return True

        if plan.score < prev.score:
            self.best[plan.generation] = plan
            prev.superseded = True
            return True

        return False
