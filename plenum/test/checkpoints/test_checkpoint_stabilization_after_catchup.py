from plenum.test import waits
from plenum.test.helper import sdk_send_random_and_check
from plenum.test.node_catchup.helper import waitNodeDataEquality
from plenum.test.pool_transactions.helper import sdk_add_new_steward_and_node
from plenum.test.test_node import checkNodesConnected

CHK_FREQ = 5
LOG_SIZE = 3 * CHK_FREQ


def test_second_checkpoint_after_catchup_can_be_stabilized(
        chkFreqPatched, looper, txnPoolNodeSet, sdk_wallet_steward,
        sdk_wallet_client, sdk_pool_handle, tdir, tconf,
        allPluginsPath):
    _, new_node = sdk_add_new_steward_and_node(
        looper, sdk_pool_handle, sdk_wallet_steward,
        'EpsilonSteward', 'Epsilon', tdir, tconf,
        allPluginsPath=allPluginsPath)
    txnPoolNodeSet.append(new_node)
    looper.run(checkNodesConnected(txnPoolNodeSet))
    waitNodeDataEquality(looper, new_node, *txnPoolNodeSet[:-1])
    # Epsilon did not participate in ordering of the batch with EpsilonSteward
    # NYM transaction and the batch with Epsilon NODE transaction.
    # Epsilon got these transactions via catch-up.

    for replica in new_node.replicas:
        assert len(replica.checkpoints) == 0

        assert replica.h == 2
        assert replica.H == 17

    sdk_send_random_and_check(looper, txnPoolNodeSet,
                              sdk_pool_handle, sdk_wallet_client, 7)
    stabilization_timeout = \
        waits.expectedTransactionExecutionTime(len(txnPoolNodeSet))
    looper.runFor(stabilization_timeout)

    for replica in new_node.replicas:
        assert len(replica.checkpoints) == 2
        keys_iter = iter(replica.checkpoints)

        assert next(keys_iter) == (3, 5)
        assert replica.checkpoints[3, 5].seqNo == 5
        assert replica.checkpoints[3, 5].digest is None
        assert replica.checkpoints[3, 5].isStable is False

        assert next(keys_iter) == (6, 10)
        assert replica.checkpoints[6, 10].seqNo == 9
        assert replica.checkpoints[6, 10].digest is None
        assert replica.checkpoints[6, 10].isStable is False

        assert replica.h == 2
        assert replica.H == 17

    sdk_send_random_and_check(looper, txnPoolNodeSet,
                              sdk_pool_handle, sdk_wallet_client, 1)
    looper.runFor(stabilization_timeout)

    for replica in new_node.replicas:
        assert len(replica.checkpoints) == 1
        keys_iter = iter(replica.checkpoints)

        assert next(keys_iter) == (6, 10)
        assert replica.checkpoints[6, 10].seqNo == 10
        assert replica.checkpoints[6, 10].digest is not None
        assert replica.checkpoints[6, 10].isStable is True

        assert replica.h == 10
        assert replica.H == 25
