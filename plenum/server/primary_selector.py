from typing import Iterable, List

from plenum.common.types import ViewChangeDone
from plenum.server.router import Route
from stp_core.common.log import getlogger
from plenum.server.primary_decider import PrimaryDecider

logger = getlogger()


# TODO: Assumes that all nodes are up. Should select only
# those nodes which are up
class PrimarySelector(PrimaryDecider):
    """
    Simple implementation of primary decider. 
    Decides on a primary in round-robin fashion.
    """

    def __init__(self, node):
        super().__init__(node)
        # Stores the last `ViewChangeDone` message sent for specific instance.
        # If no view change has happened, a node simply send a ViewChangeDone
        # with view no 0 to a newly joined node
        self.view_change_done_messages = {}

    @property
    def routes(self) -> Iterable[Route]:
        return [(ViewChangeDone, self.processViewChangeDone)]

    def processViewChangeDone(self,
                              msg: ViewChangeDone,
                              sender: str) -> None:
        """
        Processes ViewChangeDone messages. Once 2f + 1 messages have been 
        received, decides on a primary for specific replica. 

        :param msg: ViewChangeDone message
        :param sender: the name of the node from which this message was sent
        """

        logger.debug("{}'s elector started processing ViewChangeDone msg "
                     "from {} : {}"
                    .format(self.name, sender, msg))

        primary_name = msg.name
        instance_id = msg.instId
        replica = self.replicas[instance_id]


        if instance_id == 0 and replica.getNodeName(primary_name) == self.previous_master_primary:
            self.discard(primary_name,
                         '{} got Primary from {} for {} who was primary of '
                         'master in previous view too'
                         .format(self, sender, primary_name),
                         logMethod=logger.warning)
            return

        sender_replica_name = replica.generateName(sender, instance_id)

        # Nodes should not be able to declare `Primary` winner more than once
        if instance_id not in self.primaryDeclarations:
             self.setDefaults(instance_id)
        if sender_replica_name in self.primaryDeclarations[instance_id]:
            self.discard(msg,
                         "already got primary declaration from {}".
                         format(sender_replica_name),
                         logger.warning)

            key = (Primary.typename, instId, sender_replica_name)
            self.duplicateMsgs[key] = self.duplicateMsgs.get(key, 0) + 1
            # If got more than one duplicate message then blacklist
            # if self.duplicateMsgs[key] > 1:
            #     self.send(BlacklistMsg(
            #         Suspicions.DUPLICATE_PRI_SENT.code, sender))

        # TODO: 2f+ 1
        # One of them should be next primary
        # Another one - current node

        # TODO implement logic here; the commented code is a starting point based on PrimaryElector
        # logger.debug("{}'s elector started processing primary msg from {} : {}"
        #              .format(self.name, sender, prim))
        # instId = prim.instId
        # replica = self.replicas[instId]
        # if instId == 0 and replica.getNodeName(prim.name) == self.previous_master_primary:
        #     self.discard(prim, '{} got Primary from {} for {} who was primary'
        #                       ' of master in previous view too'.
        #                  format(self, sender, prim.name),
        #                  logMethod=logger.warning)
        #     return
        #
        # sndrRep = replica.generateName(sender, prim.instId)
        #
        # # Nodes should not be able to declare `Primary` winner more than more
        # if instId not in self.primaryDeclarations:
        #     self.setDefaults(instId)
        # if sndrRep not in self.primaryDeclarations[instId]:
        #     self.primaryDeclarations[instId][sndrRep] = (prim.name,
        #                                                  prim.ordSeqNo)
        #
        #     # If got more than 2f+1 primary declarations then in a position to
        #     # decide whether it is the primary or not `2f + 1` declarations
        #     # are enough because even when all the `f` malicious nodes declare
        #     # a primary, we still have f+1 primary declarations from
        #     # non-malicious nodes. One more assumption is that all the non
        #     # malicious nodes vote for the the same primary
        #
        #     # Find for which node there are maximum primary declarations.
        #     # Cant be a tie among 2 nodes since all the non malicious nodes
        #     # which would be greater than or equal to f+1 would vote for the
        #     # same node
        #
        #     if replica.isPrimary is not None:
        #         logger.debug(
        #             "{} Primary already selected; ignoring PRIMARY msg".format(
        #                 replica))
        #         return
        #
        #     if self.hasPrimaryQuorum(instId):
        #         if replica.isPrimary is None:
        #             primary, seqNo = mostCommonElement(
        #                 self.primaryDeclarations[instId].values())
        #             logger.display("{} selected primary {} for instance {} "
        #                            "(view {})".format(replica, primary,
        #                                               instId, self.viewNo),
        #                            extra={"cli": "ANNOUNCE",
        #                                   "tags": ["node-election"]})
        #             logger.debug("{} selected primary on the basis of {}".
        #                          format(replica,
        #                                 self.primaryDeclarations[instId]),
        #                          extra={"cli": False})
        #
        #             # If the maximum primary declarations are for this node
        #             # then make it primary
        #             replica.primaryChanged(primary, seqNo)
        #
        #             if instId == 0:
        #                 self.previous_master_primary = None
        #
        #             # If this replica has nominated itself and since the
        #             # election is over, reset the flag
        #             if self.replicaNominatedForItself == instId:
        #                 self.replicaNominatedForItself = None
        #
        #             self.node.primary_found()
        #
        #             self.scheduleElection()
        #         else:
        #             self.discard(prim,
        #                          "it already decided primary which is {}".
        #                          format(replica.primaryName),
        #                          logger.debug)
        #     else:
        #         logger.debug(
        #             "{} received {} but does it not have primary quorum "
        #             "yet".format(self.name, prim))
        # else:
        #     self.discard(prim,
        #                  "already got primary declaration from {}".
        #                  format(sndrRep),
        #                  logger.warning)
        #
        #     key = (Primary.typename, instId, sndrRep)
        #     self.duplicateMsgs[key] = self.duplicateMsgs.get(key, 0) + 1
        #     # If got more than one duplicate message then blacklist
        #     # if self.duplicateMsgs[key] > 1:
        #     #     self.send(BlacklistMsg(
        #     #         Suspicions.DUPLICATE_PRI_SENT.code, sender))

    def decidePrimaries(self):  # overridden method of PrimaryDecider
        self._scheduleSelection()

    def _scheduleSelection(self):
        """
        Schedule election at some time in the future. Currently the election
        starts immediately.
        """
        self._schedule(self._startSelection)

    def _startSelection(self):
        logger.debug("{} starting selection".format(self))
        for instance_id, replica in enumerate(self.replicas):
            if replica.primaryName is not None:
                continue
            new_primary_id = (self.viewNo + instance_id) % self.node.totalNodes
            new_primary_name = replica.generateName(
                nodeName=self.node.get_name_by_rank(new_primary_id),
                instId=instance_id)
            logger.display("{} selected primary {} for instance {} (view {})"
                           .format(replica,
                                   new_primary_name,
                                   instance_id,
                                   self.viewNo),
                           extra={"cli": "ANNOUNCE",
                                  "tags": ["node-election"]})
            replica.primaryChanged(new_primary_name)

    def viewChanged(self, viewNo: int):
        if viewNo > self.viewNo:
            self.viewNo = viewNo
            self._startSelection()
        else:
            logger.warning("Provided view no {} is not greater than the "
                           "current view no {}".format(viewNo, self.viewNo))

    # TODO: there is no such method in super class, it should be declared
    def get_msgs_for_lagged_nodes(self) -> List[ViewChangeDone]:
        msgs = []
        for instance_id, replica in enumerate(self.replicas):
            msg = self.view_change_done_messages.get(instance_id,
                                                     ViewChangeDone(
                                                         replica.primaryName,
                                                         instance_id,
                                                         self.viewNo,
                                                         None))
            msgs.append(msg)
        return msgs

