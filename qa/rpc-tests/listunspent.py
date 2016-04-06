#!/usr/bin/env python2
# Copyright (c) 2014-2016 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *

class ListUnspentTest(BitcoinTestFramework):

    def setup_chain(self):
        print("Initializing test directory "+self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 3)

    def setup_network(self, split=False):
        self.nodes = start_nodes(3, self.options.tmpdir)

        connect_nodes_bi(self.nodes, 0, 1)
        connect_nodes_bi(self.nodes, 1, 2)
        connect_nodes_bi(self.nodes, 0, 2)

        self.is_network_split=False
        self.sync_all()

    def run_test(self):

        ##########################################
        #  Test case 1                           #
        #  Mine some coins and spend one output  #
        ##########################################

        # check there's no unspent output availabe on any nodes
        assert_equal(len(self.nodes[0].listunspent()), 0)
        assert_equal(len(self.nodes[1].listunspent()), 0)
        assert_equal(len(self.nodes[2].listunspent()), 0)

        # mine enough blocks to generate one UTXO on first node
        self.nodes[0].generate(101)
        self.sync_all()

        # list current unspents, only first node should return one unspent
        assert_equal(len(self.nodes[0].listunspent()), 1)
        assert_equal(len(self.nodes[1].listunspent()), 0)
        assert_equal(len(self.nodes[2].listunspent()), 0)

        # make sure this output is spendable
        assert(self.nodes[0].listunspent()[0]["spendable"])

        # sends some coins from first node to third node, to spend some available unspent outputs
        send_to_address = self.nodes[2].getnewaddress()
        txid = self.nodes[0].sendtoaddress(send_to_address, 10)

        # since the only available UTXO was spent, there sould be none after the transaction
        assert_equal(len(self.nodes[0].listunspent()), 0)

        # mine one more block to generate some more UTXOs
        self.nodes[0].generate(1)
        self.sync_all()

        # list unspents after the transaction
        list_unspent_after = self.nodes[0].listunspent()

        # retrieve that transaction and check if the transaction inputs are not among the unspents
        rawtx = self.nodes[0].getrawtransaction(txid, 1)
        for txin in rawtx["vin"]:
            for utxo in list_unspent_after:
                if (txin["txid"] == utxo["txid"] and txin["vout"] == utxo["vout"]):
                    raise AssertionError("Fount used output on UTXOs list")


        ###########################################################################
        #  Test case 2                                                            #
        #  Import address (watch-only) and retrieve new unspents (not spendable)  #
        ###########################################################################

        # second node shouldn't have any unpent at the moment
        assert_equal(len(self.nodes[1].listunspent()), 0)

        # import address from another node
        self.nodes[1].importaddress(send_to_address)

        # making sure this address is watch-only
        assert(self.nodes[1].validateaddress(send_to_address)["iswatchonly"])

        # there should be only one unspendable unspent, from the imported address
        assert_equal(len(self.nodes[1].listunspent()), 1)
        assert(not self.nodes[1].listunspent()[0]["spendable"])

        try:
            self.nodes[1].sendtoaddress(self.nodes[0].getnewaddress(), 1)
        except JSONRPCException:
            print("Impossible to send coins. Available output is unspendable.")


        #######################################################################
        #  Test case 3                                                        #
        #  Import private key and check for updated unspents (now spendable)  #
        #######################################################################

        # import private key, so this node can spend the available UTXO
        priv_key = self.nodes[2].dumpprivkey(send_to_address)
        self.nodes[1].importprivkey(priv_key)

        # there should be only one spendable unspent, after importing private key
        assert_equal(len(self.nodes[1].listunspent()), 1)
        assert(self.nodes[1].listunspent()[0]["spendable"])

        try:
            self.nodes[1].sendtoaddress(self.nodes[0].getnewaddress(), 0.1)
        except JSONRPCException, e:
            raise AssertionError("Not possible to send coins. Possible unsufficient funds.")

        # since we spent the only available output, there should be none now
        assert_equal(len(self.nodes[1].listunspent()), 0)

if __name__ == '__main__':
    ListUnspentTest().main()
