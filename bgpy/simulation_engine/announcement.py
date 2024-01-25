from dataclasses import dataclass, asdict, replace
from typing import Any, Optional, TYPE_CHECKING

from yamlable import YamlAble, yaml_info

if TYPE_CHECKING:
    from bgpy.enums import Relationships


# Timing tests over a 2m period indicate that
# slots offers basically no speedup here.
# besides, YamlAble doesn't have slots, so this
# doesn't matter
@yaml_info(yaml_tag="Announcement")
@dataclass(slots=True, frozen=True)
class Announcement(YamlAble):
    """BGP Announcement"""

    # MUST use slots for speed
    # Since anns get copied across 70k ASes
    prefix: str
    # Equivalent to the next hop in a normal BGP announcement
    next_hop_asn: int
    # NOTE: must use list here for C++ compatability
    as_path: tuple[int]
    timestamp: int
    seed_asn: Optional[int]
    recv_relationship: "Relationships"
    withdraw: bool = False
    traceback_end: bool = False
    # ROV, ROV++ optional attributes
    roa_valid_length: Optional[bool] = None
    roa_origin: Optional[int] = None
    # BGPsec optional attributes
    # BGPsec next ASN that should receive the control plane announcement
    # NOTE: this is the opposite direction of next_hop, for the data plane
    bgpsec_next_asn: Optional[int] = None
    bgpsec_as_path: tuple[int, ...] = ()
    # For pathend. Similar to ROA info, we store this instead of deal with RPKI
    pathend_valid: Optional[bool] = None

    def prefix_path_attributes_eq(self, ann: Optional["Announcement"]) -> bool:
        """Checks prefix and as path equivalency"""

        if ann is None:
            return False
        elif isinstance(ann, Announcement):
            return (ann.prefix, ann.as_path) == (self.prefix, self.as_path)
        else:
            raise NotImplementedError

    def copy(
        self, overwrite_default_kwargs: Optional[dict[Any, Any]] = None
    ) -> "Announcement":
        """Creates a new ann with proper sim attrs"""

        # Replace seed asn and traceback end every time by default
        kwargs = {"seed_asn": None, "traceback_end": False}
        if overwrite_default_kwargs:
            kwargs.update(overwrite_default_kwargs)

        # Mypy says it gets this wrong
        # https://github.com/microsoft/pyright/issues/1047#issue-705124399
        return replace(self, **kwargs)  # type: ignore

    def bgpsec_valid(self, asn: int) -> bool:
        """Returns True if valid by BGPSec else False"""

        return self.bgpsec_next_asn == asn and self.bgpsec_as_path == self.as_path

    @property
    def invalid_by_roa(self) -> bool:
        """Returns True if Ann is invalid by ROA

        False means ann is either valid or unknown
        """

        # Not covered by ROA, unknown
        if self.roa_origin is None:
            return False
        else:
            return self.origin != self.roa_origin or not self.roa_valid_length

    @property
    def valid_by_roa(self) -> bool:
        """Returns True if Ann is valid by ROA

        False means ann is either invalid or unknown
        """

        # Need the bool here for mypy, ugh
        return bool(self.origin == self.roa_origin and self.roa_valid_length)

    @property
    def unknown_by_roa(self) -> bool:
        """Returns True if ann is not covered by roa"""

        return not self.invalid_by_roa and not self.valid_by_roa

    @property
    def covered_by_roa(self) -> bool:
        """Returns if an announcement has a roa"""

        return not self.unknown_by_roa

    @property
    def roa_routed(self) -> bool:
        """Returns bool for if announcement is routed according to ROA"""

        return self.roa_origin != 0

    @property
    def origin(self) -> int:
        """Returns the origin of the announcement"""

        return self.as_path[-1]

    def __str__(self) -> str:
        return f"{self.prefix} {self.as_path} {self.recv_relationship}"

    def __hash__(self):
        """Hash func. Needed for ROV++"""
        return hash(str(self))

    ##############
    # Yaml funcs #
    ##############

    def __to_yaml_dict__(self) -> dict[str, Any]:
        """This optional method is called when you call yaml.dump()"""

        return asdict(self)

    @classmethod
    def __from_yaml_dict__(
        cls: type["Announcement"], dct: dict[str, Any], yaml_tag: Any
    ) -> "Announcement":
        """This optional method is called when you call yaml.load()"""

        return cls(**dct)
