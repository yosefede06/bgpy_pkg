from bgpy.shared.enums import Relationships
from bgpy.simulation_engine import BGP
from bgpy.simulation_engine import Announcement as Ann


class PeerROV(BGP):
    """An Policy that deploys PeerROV"""

    name: str = "TutorialPeerROV"

    def _valid_ann(self, ann: Ann, recv_rel: Relationships) -> bool:
        """Returns announcement validity

        Returns false if invalid by roa and coming from a peer,
        otherwise uses standard BGP (such as no loops, etc)
        to determine validity
        """

        # Invalid by ROA is not valid by ROV
        # Since this type of real world ROV only does peer filtering, only peers here
        if ann.invalid_by_roa and ann.recv_relationship == Relationships.PEERS:
            return False
        # Use standard BGP to determine if the announcement is valid
        else:
            return super(PeerROV, self)._valid_ann(ann, recv_rel)
