#!/usr/bin/env python3
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

        print ("Mining blocks...")
        self.nodes[0].generate(1)
        self.nodes[1].generate(1)

        # keyword definition
        PRIV_KEY = 'privkey'
        PUB_KEY = 'pubkey'
        ADDRESS_KEY = 'address'
        SCRIPT_KEY = 'script'


        node0_address1 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        node0_address2 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        node0_address3 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())

        #Check only one address
        assert_equal(node0_address1['ismine'], True)

        #Node 1 sync test
        assert_equal(self.nodes[1].getblockcount(),1)

        #Address Test - before import
        address_info = self.nodes[1].validateaddress(node0_address1['address'])
        assert_equal(address_info['iswatchonly'], False)
        assert_equal(address_info['ismine'], False)


        # RPC importmulti -----------------------------------------------

        # Bitcoin Address
        print("Should import an address")
        address = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        result = self.nodes[1].importmulti([{
            "scriptPubKey": {
                "address": address['address']
            }
        }])
        assert_equal(result[0]['success'], True)
        address_assert = self.nodes[1].validateaddress(address['address'])
        assert_equal(address_assert['iswatchonly'], True)
        assert_equal(address_assert['ismine'], False)


        # ScriptPubKey
        print("Should import a scriptPubKey")
        address = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        result = self.nodes[1].importmulti([{
            "scriptPubKey": address['scriptPubKey']
        }])
        assert_equal(result[0]['success'], True)
        address_assert = self.nodes[1].validateaddress(address['address'])
        assert_equal(address_assert['iswatchonly'], True)
        assert_equal(address_assert['ismine'], False)


        # Address + Public key
        print("Should import an address with public key")
        address = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        result = self.nodes[1].importmulti([{
            "scriptPubKey": {
                "address": address['address']
            },
            "pubkeys": [ address['pubkey'] ]
        }])
        assert_equal(result[0]['success'], True)
        address_assert = self.nodes[1].validateaddress(address['address'])
        assert_equal(address_assert['iswatchonly'], True)
        assert_equal(address_assert['ismine'], False)


        # ScriptPubKey + Public key
        print("Should import a scriptPubKey with public key")
        address = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        request = [{
            "scriptPubKey": address['scriptPubKey'],
            "pubkeys": [ address['pubkey'] ]
        }];
        result = self.nodes[1].importmulti(request)
        assert_equal(result[0]['success'], True)
        address_assert = self.nodes[1].validateaddress(address['address'])
        assert_equal(address_assert['iswatchonly'], True)
        assert_equal(address_assert['ismine'], False)

        # Address + Private key
        print("Should import an address with private key")
        address = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        result = self.nodes[1].importmulti([{
            "scriptPubKey": {
                "address": address['address']
            },
            "keys": [ self.nodes[0].dumpprivkey(address['address']) ]
        }])
        assert_equal(result[0]['success'], True)
        address_assert = self.nodes[1].validateaddress(address['address'])
        assert_equal(address_assert['iswatchonly'], False)
        assert_equal(address_assert['ismine'], True)

        # ScriptPubKey + Private key
        print("Should import a scriptPubKey with private key")
        address = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        result = self.nodes[1].importmulti([{
            "scriptPubKey": address['scriptPubKey'],
            "keys": [ self.nodes[0].dumpprivkey(address['address']) ]
        }])
        assert_equal(result[0]['success'], True)
        address_assert = self.nodes[1].validateaddress(address['address'])
        assert_equal(address_assert['iswatchonly'], False)
        assert_equal(address_assert['ismine'], True)


        # P2SH address
        sig_address_1 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        sig_address_2 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        sig_address_3 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        multi_sig_script = self.nodes[0].createmultisig(2, [sig_address_1['address'], sig_address_2['address'], sig_address_3['pubkey']])
        self.nodes[1].generate(100)
        transactionid = self.nodes[1].sendtoaddress(multi_sig_script['address'], 10.00)
        self.nodes[1].generate(1)
        transaction = self.nodes[1].gettransaction(transactionid);

        print("Should import a p2sh")
        result = self.nodes[1].importmulti([{
            "scriptPubKey": {
                "address": multi_sig_script['address']
            }
        }])
        assert_equal(result[0]['success'], True)
        address_assert = self.nodes[1].validateaddress(multi_sig_script['address'])
        assert_equal(address_assert['isscript'], True)
        assert_equal(address_assert['iswatchonly'], True)
        p2shunspent = self.nodes[1].listunspent(0,999999, [multi_sig_script['address']])[0]
        assert_equal(p2shunspent['spendable'], False)
        assert_equal(p2shunspent['solvable'], False)


        # P2SH + Redeem script
        sig_address_1 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        sig_address_2 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        sig_address_3 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        multi_sig_script = self.nodes[0].createmultisig(2, [sig_address_1['address'], sig_address_2['address'], sig_address_3['pubkey']])
        self.nodes[1].generate(100)
        transactionid = self.nodes[1].sendtoaddress(multi_sig_script['address'], 10.00)
        self.nodes[1].generate(1)
        transaction = self.nodes[1].gettransaction(transactionid);

        print("Should import a p2sh with respective redeem script")
        result = self.nodes[1].importmulti([{
            "scriptPubKey": {
                "address": multi_sig_script['address']
            },
            "redeemscript": multi_sig_script['redeemScript']
        }])
        assert_equal(result[0]['success'], True)

        p2shunspent = self.nodes[1].listunspent(0,999999, [multi_sig_script['address']])[0]
        assert_equal(p2shunspent['spendable'], False)
        assert_equal(p2shunspent['solvable'], True)


        # P2SH + Redeem script + Private Keys
        sig_address_1 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        sig_address_2 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        sig_address_3 = self.nodes[0].validateaddress(self.nodes[0].getnewaddress())
        multi_sig_script = self.nodes[0].createmultisig(2, [sig_address_1['address'], sig_address_2['address'], sig_address_3['pubkey']])
        self.nodes[1].generate(100)
        transactionid = self.nodes[1].sendtoaddress(multi_sig_script['address'], 10.00)
        self.nodes[1].generate(1)
        transaction = self.nodes[1].gettransaction(transactionid);

        print("Should import a p2sh with respective redeem script and private keys")
        result = self.nodes[1].importmulti([{
            "scriptPubKey": {
                "address": multi_sig_script['address']
            },
            "redeemscript": multi_sig_script['redeemScript'],
            "keys": [ self.nodes[0].dumpprivkey(sig_address_1['address']), self.nodes[0].dumpprivkey(sig_address_2['address'])]
        }])
        assert_equal(result[0]['success'], True)

        p2shunspent = self.nodes[1].listunspent(0,999999, [multi_sig_script['address']])[0]
        assert_equal(p2shunspent['spendable'], False)
        assert_equal(p2shunspent['solvable'], True)

        # TODO Internal tests?

        # TODO Watchonly tests?

        # TODO Consistency tests?



if __name__ == '__main__':
    ImportMultiTest ().main ()
