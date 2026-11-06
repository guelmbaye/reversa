from dataclasses import dataclass
from app.schemas import Action
from app.world.worlds import build_world
from app.world.models import WorldState

@dataclass
class WorldOracle:
    _world_id: str
    _state: WorldState
    _expected: Action

    @classmethod
    def create(cls, world_id: str):
        state, expected = build_world(world_id)
        return cls(world_id, state, expected)

    @property
    def state(self) -> WorldState:
        return self._state

    def reveal(self) -> dict:
        # Only the verifier / harness may call this after execution.
        return {
            "world_id": self._world_id,
            "expected_action": self._expected.value,
        }
