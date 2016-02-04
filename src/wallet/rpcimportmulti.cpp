// Copyright (c) 2009-2015 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include "base58.h"
#include "chain.h"
#include "rpc/server.h"
#include "init.h"
#include "main.h"
#include "script/script.h"
#include "script/standard.h"
#include "sync.h"
#include "util.h"
#include "utiltime.h"
#include "wallet.h"

#include <fstream>
#include <stdint.h>

#include <boost/algorithm/string.hpp>
#include <boost/date_time/posix_time/posix_time.hpp>

#include <univalue.h>

#include <boost/foreach.hpp>


//namespaces
using namespace std;

//extern functions
extern void ImportAddress(const CBitcoinAddress& address, const string& strLabel);
extern void ImportScript(const CScript& script, const string& strLabel, bool isRedeemScript);
extern bool EnsureWalletIsAvailable(bool avoidException);
extern void EnsureWalletIsUnlocked();

//binding names
const string TYPE_PARAM = "type";
const string TYPE_PRIVKEY_PARAM = "privkey";
const string TYPE_PUBKEY_PARAM = "pubkey";
const string TYPE_ADDRESS_PARAM = "address";
const string VALUE_PARAM = "value";
const string LABEL_PARAM = "label";
const string TIMESTAMP_PARAM = "timestamp";
const string P2SH_PARAM = "p2sh";

void ImportAddressKey(const string& script,const string& label, bool isF2SH){
    CBitcoinAddress address(script);
    if (address.IsValid()) {
        if (isF2SH)
            throw JSONRPCError(RPC_INVALID_ADDRESS_OR_KEY, "Cannot use the p2sh flag with an address - use a script instead");
        ImportAddress(address, label);
    } else if (IsHex(script)) {
        std::vector<unsigned char> data(ParseHex(script));
        ImportScript(CScript(data.begin(), data.end()), label, isF2SH);
    } else {
        throw JSONRPCError(RPC_INVALID_ADDRESS_OR_KEY, "Invalid Bitcoin address or script");
    }
}

void ImportPublicKey(const string& pubkey,const string& label){
    //Legacy code - begin
    if (!IsHex(pubkey))
        throw JSONRPCError(RPC_INVALID_ADDRESS_OR_KEY, "Pubkey must be a hex string");
    std::vector<unsigned char> data(ParseHex(pubkey));
    CPubKey pubKey(data.begin(), data.end());
    if (!pubKey.IsFullyValid())
        throw JSONRPCError(RPC_INVALID_ADDRESS_OR_KEY, "Pubkey is not a valid public key");

    ImportAddress(CBitcoinAddress(pubKey.GetID()), label);
    ImportScript(GetScriptForRawPubKey(pubKey), label, false);
    //Legacy code - end
}

void ImportPrivateKey(const string& privkey,const string& label){
    //Legacy code - begin
    CBitcoinSecret vchSecret;
    bool fGood = vchSecret.SetString(privkey);

    if (!fGood) throw JSONRPCError(RPC_INVALID_ADDRESS_OR_KEY, "Invalid private key encoding");

    CKey key = vchSecret.GetKey();
    if (!key.IsValid()) throw JSONRPCError(RPC_INVALID_ADDRESS_OR_KEY, "Private key outside allowed range");

    CPubKey pubkey = key.GetPubKey();
    assert(key.VerifyPubKey(pubkey));
    CKeyID vchAddress = pubkey.GetID();
    {
        pwalletMain->MarkDirty();
        pwalletMain->SetAddressBook(vchAddress, label, "receive");

        // Don't throw error in case a key is already there
        if (pwalletMain->HaveKey(vchAddress))
            return ;//NullUniValue;

        pwalletMain->mapKeyMetadata[vchAddress].nCreateTime = 1;

        if (!pwalletMain->AddKeyPubKey(key, pubkey))
            throw JSONRPCError(RPC_WALLET_ERROR, "Error adding key to wallet");

        // whenever a key is imported, we need to scan the whole chain
        pwalletMain->nTimeFirstKey = 1; // 0 would be considered 'no value'
    }
    //Legacy code - end
}

void SearchImportStartIndex(const UniValue& jsonRequest,CBlockIndex *pindex){
    string currentTimestamp = "";

    //Find the smallest timestamp
    BOOST_FOREACH(const UniValue& jParam, jsonRequest.getValues()){
        if (jParam.exists(TIMESTAMP_PARAM)){
            const string & timestamp = find_value(jParam,TIMESTAMP_PARAM).get_str();

            if (currentTimestamp == "" //first case
                    || timestamp < currentTimestamp){
                currentTimestamp = timestamp;
            }
        }else {
            break;
        }
    }

    if (currentTimestamp != ""){
        int time = atoi(currentTimestamp); //todo: specify the timestamp format and interpretation
        pindex = chainActive.FindLatestBefore(time);
        if (!pindex)
            throw JSONRPCError(RPC_INVALID_PARAMETER, "No block before timestamp"); //TODO: change this error enum?
    }
}

void ScanWallet(CBlockIndex *pindex){
    pwalletMain->ScanForWalletTransactions(pindex, true);
    pwalletMain->ReacceptWalletTransactions();
}

void ParseImportMulti(const UniValue& jsonRequest, bool fRescan){
    //Locks the wallet
    LOCK2(cs_main, pwalletMain->cs_wallet);
    EnsureWalletIsUnlocked();

    //For default is genesis
    CBlockIndex *pindex = chainActive.Genesis();

    if (fRescan){
        SearchImportStartIndex(jsonRequest,pindex); //Search the chain
    }

    //Import values
    try {
        BOOST_FOREACH(const UniValue& jParam, jsonRequest.getValues()){
            const string& type = find_value(jParam,TYPE_PARAM).get_str();
            const string& value = find_value(jParam,VALUE_PARAM).get_str();
            string label = jParam.exists(LABEL_PARAM) ? find_value(jParam,LABEL_PARAM).get_str() : "";

            if (type == TYPE_PRIVKEY_PARAM){
                ImportPrivateKey(value,label);
            }else if (type == TYPE_PUBKEY_PARAM) {
                ImportPublicKey(value,label);
            }else if (type == TYPE_ADDRESS_PARAM) {
                bool isF2SH = jParam.exists(P2SH_PARAM) ? find_value(jParam,P2SH_PARAM).get_bool() : false;
                ImportAddressKey(value,label,isF2SH);
            }else {
                throw ;
            }
        }
    }catch(...){
        throw runtime_error("Invalid JSON request");
    }

    //Scanning the chain
    if (fRescan){
        ScanWallet(pindex);
    }
}

UniValue importmulti(const UniValue& params, bool fHelp){
    //Initial validation
    if (!EnsureWalletIsAvailable(fHelp))
        return NullUniValue;

    //Help + invalid parameters number validation + invalid parameter type (must be JSON)
    if (fHelp || params.size() != 1 || (params[0].getType() != UniValue::VARR)){
        stringstream sError;
        sError << "importmulti '[{\""<< TYPE_PARAM << "\":\""<< TYPE_PRIVKEY_PARAM<< "\",\""<< VALUE_PARAM <<"\":\"mkjjX...\"},...]'' (rescan)" << endl << endl
               << "Import several types of addresses (private and public keys, transaction addresses/scripts) with only one rescan " << endl
               << "Arguments:"<<endl
               << "1. json request array"<<"\t"<<"(json, required) Data to be imported"<<endl
               << "  " << "[     (json array of json objects)" << endl
               << "    " << "{" << endl
               << "      " << "\""<< TYPE_PARAM << "\": \""<< TYPE_PRIVKEY_PARAM << " | " << TYPE_PUBKEY_PARAM << " | " << TYPE_ADDRESS_PARAM << "\","<< "\t" <<"(string, required) Type of address" << endl
               << "      " << "\""<< VALUE_PARAM << "\": \"...\","      << "\t\t\t\t" << "(string, required) Value of the address" << endl
               << "      " << "\""<< TIMESTAMP_PARAM <<"\": \"...\","   << "\t\t\t" << "(string, optional) Timestamp" << endl
               << "      " << "\""<< LABEL_PARAM << "\": \"...\""       << "\t\t\t\t" << "(string, optional) Label" << endl
               << "      " << "\""<< P2SH_PARAM << "\": true | false"   << "\t\t\t" << "(bool, optional, default=false) Value is a P2SH" << endl
               << "    " << "}" << endl
               << "  " << ",..." << endl
               << "  " << "]" << endl
               << "2. rescan"<<"\t\t"<<"(boolean, optional, default=true)"<<endl;
        throw runtime_error(sError.str().c_str());
    }

    //Execution
    ParseImportMulti(params[0],params[1].get_bool());

    return NullUniValue;
}
