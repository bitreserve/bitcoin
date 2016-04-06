#!/usr/bin/env python2
# Copyright (c) 2014-2016 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *

class ImportMultiTest (BitcoinTestFramework):
    def setup_chain(self):
        print("Initializing test directory "+self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 2)

    def setup_network(self, split=False):
        self.nodes = start_nodes(2, self.options.tmpdir)
        self.is_network_split=False

    def run_test (self):
        import time
        begintime = int(time.time())

        print "Mining blocks..."
        self.nodes[0].generate(1)
        self.nodes[1].generate(1)

        # keyword definition
        PRIV_KEY = 'privkey'
        PUB_KEY = 'pubkey'
        ADDRESS_KEY = 'address'
        SCRIPT_KEY = 'script'

        # address
        address1 = self.nodes[0].getnewaddress()
        # pubkey
        address2 = self.nodes[0].getnewaddress()
        address2_pubkey = self.nodes[0].validateaddress(address2)['pubkey']                 # Using pubkey
        # privkey
        address3 = self.nodes[0].getnewaddress()
        address3_privkey = self.nodes[0].dumpprivkey(address3)                              # Using privkey
        # scriptPubKey
        address4 = self.nodes[0].getnewaddress()
        address4_scriptpubkey = self.nodes[0].validateaddress(address4)['scriptPubKey']     # Using scriptpubkey


        #Check only one address
        address_info = self.nodes[0].validateaddress(address1)
        assert_equal(address_info['ismine'], True)

        #Node 1 sync test
        assert_equal(self.nodes[1].getblockcount(),1)

        #Address Test - before import
        address_info = self.nodes[1].validateaddress(address1)
        assert_equal(address_info['iswatchonly'], False)
        assert_equal(address_info['ismine'], False)

        address_info = self.nodes[1].validateaddress(address2)
        assert_equal(address_info['iswatchonly'], False)
        assert_equal(address_info['ismine'], False)

        address_info = self.nodes[1].validateaddress(address3)
        assert_equal(address_info['iswatchonly'], False)
        assert_equal(address_info['ismine'], False)

        # import multi
        result1 = self.nodes[1].importmulti( [
            { "type": ADDRESS_KEY, "value": address1 , "label":"new account 1" , "timestamp": begintime } ,
            { "type": PUB_KEY , "value": address2_pubkey , "label":"new account 1", "timestamp": begintime},
            { "type": PRIV_KEY , "value": address3_privkey , "timestamp": begintime},
            { "type": SCRIPT_KEY , "value": address4_scriptpubkey , "timestamp": begintime},
            ])

        #Addresses Test - after import
        address_info = self.nodes[1].validateaddress(address1)
        assert_equal(address_info['iswatchonly'], True)
        assert_equal(address_info['ismine'], False)
        address_info = self.nodes[1].validateaddress(address2)
        assert_equal(address_info['iswatchonly'], True)
        assert_equal(address_info['ismine'], False)
        address_info = self.nodes[1].validateaddress(address3)
        assert_equal(address_info['iswatchonly'], False)
        assert_equal(address_info['ismine'], True)
        address_info = self.nodes[1].validateaddress(address4)
        assert_equal(address_info['iswatchonly'], True)
        assert_equal(address_info['ismine'], False)

        assert_equal(result1[0]['success'], True)
        assert_equal(result1[1]['success'], True)
        assert_equal(result1[2]['success'], True)
        assert_equal(result1[3]['success'], True)

        #importmulti without rescan
        result2 = self.nodes[1].importmulti( [
            { "type": ADDRESS_KEY, "value": self.nodes[0].getnewaddress() } ,
            { "type": ADDRESS_KEY, "value": self.nodes[0].getnewaddress() } ,
            { "type": ADDRESS_KEY, "value": self.nodes[0].getnewaddress() , "label":"random account" } ,
            { "type": PUB_KEY, "value": self.nodes[0].validateaddress(self.nodes[0].getnewaddress())['pubkey'] } ,
            { "type": SCRIPT_KEY, "value": self.nodes[0].validateaddress(self.nodes[0].getnewaddress())['scriptPubKey'] },
            ], { "rescan":False } )

        # all succeed
        assert_equal(result2[0]['success'], True)
        assert_equal(result2[1]['success'], True)
        assert_equal(result2[2]['success'], True)
        assert_equal(result2[3]['success'], True)
        assert_equal(result2[4]['success'], True)

        # empty json case
        assert_raises(JSONRPCException, self.nodes[1].importmulti)

        # parcial success case
        result3 = self.nodes[1].importmulti( [
            { "type": ADDRESS_KEY, "value": self.nodes[0].getnewaddress() },
            { "type": PUB_KEY },
            { "type": PUB_KEY , "value": "123456789"},
            ] )

        assert_equal(result3[0]['success'], True)
        assert_equal(result3[1]['success'], False)
        assert_equal(result3[1]['error']['code'], -1)
        assert_equal(result3[1]['error']['message'], 'Missing required fields')
        assert_equal(result3[2]['success'], False)
        assert_equal(result3[2]['error']['code'], -5)
        assert_equal(result3[2]['error']['message'], 'Pubkey must be a hex string')

        # If we import a PubKey/ScriptPubKey/Address for an address that we already have the private key it should fail
        walletaddress = self.nodes[1].getnewaddress()
        walletaddressinfo = self.nodes[1].validateaddress(walletaddress)

        result4 = self.nodes[1].importmulti( [
                { "type": PUB_KEY , "value": walletaddressinfo['pubkey'] ,  "timestamp": begintime},
                { "type": SCRIPT_KEY, "value": walletaddressinfo['scriptPubKey'] , "timestamp": begintime},
                { "type": ADDRESS_KEY , "value": walletaddress , "timestamp": begintime}
                ])

        assert_equal(result4[0]['success'], False)
        assert_equal(result4[0]['error']['code'], -4)
        assert_equal(result4[0]['error']['message'], 'The wallet already contains the private key for this address or script')
        assert_equal(result4[1]['success'], False)
        assert_equal(result4[1]['error']['code'], -4)
        assert_equal(result4[1]['error']['message'], 'The wallet already contains the private key for this address or script')
        assert_equal(result4[2]['success'], False)
        assert_equal(result4[2]['error']['code'], -4)
        assert_equal(result4[2]['error']['message'], 'The wallet already contains the private key for this address or script')

if __name__ == '__main__':
    ImportMultiTest ().main ()
