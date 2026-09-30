from core.store import JsonStore
from core.permissions import (
    prefix_matches_profile,
    actor_permissions
)

class RegistryService:

    def __init__(
        self,
        registry_path
    ):

        self.store = JsonStore(
            registry_path,
            {
                "schema_version": 1,
                "actors": []
            }
        )


    def get_actor(
        self,
        actor_id
    ):

        data = self.store.read()

        for actor in data.get(
            "actors",
            []
        ):

            if (
                actor.get(
                    "actor_id"
                )
                == actor_id
            ):

                if (
                    actor.get(
                        "status"
                    )
                    != "active"
                ):

                    raise PermissionError(
                        "Credential is not active."
                    )

                if not prefix_matches_profile(
                    actor
                ):

                    raise PermissionError(
                        "Credential prefix does "
                        "not match profile type."
                    )

                return actor

        raise LookupError(
            "Actor credential not found."
        )
    def list_actors(
        self
    ):

        data = self.store.read()

        safe_actors = []

        for actor in data.get(
            "actors",
            []
        ):

            safe_actors.append({

                "actor_id":
                    actor.get(
                        "actor_id"
                    ),

                "display_name":
                    actor.get(
                        "display_name"
                    ),

                "profile_type":
                    actor.get(
                        "profile_type"
                    ),

                "role":
                    actor.get(
                        "role"
                    ),

                "institution_id":
                    actor.get(
                        "institution_id"
                    ),

                "scope":
                    actor.get(
                        "scope"
                    ),

                "status":
                    actor.get(
                        "status"
                    ),

                "permissions":
                    sorted(
                        actor_permissions(
                            actor
                        )
                    )
            })

        return safe_actors