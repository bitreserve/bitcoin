// Copyright (c) 2015 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include "zmqpublishwalletnotifier.h"

#include "init.h"
#include "util.h"
#include "wallet/wallet.h"

bool CZMQPublishWalletRawTransactionNotifier::NotifyTransaction(const CTransaction &transaction)
{
    if (!pwalletMain->IsMine(transaction))
        return true;

    uint256 hash = transaction.GetHash();
    LogPrint("zmq", "zmq: Publish walletrawtx %s\n", hash.GetHex());
    CDataStream ss(SER_NETWORK, PROTOCOL_VERSION);
    ss << transaction;
    int rc = zmq_send_multipart(psocket, "walletrawtx", 11, &(*ss.begin()), ss.size(), 0);
    return rc == 0;
}

bool CZMQPublishWalletHashTransactionNotifier::NotifyTransaction(const CTransaction &transaction)
{
    if (!pwalletMain->IsMine(transaction))
        return true;

    uint256 hash = transaction.GetHash();
    LogPrint("zmq", "zmq: Publish wallethashtx %s\n", hash.GetHex());
    char data[32];
    for (unsigned int i = 0; i < 32; i++)
        data[31 - i] = hash.begin()[i];
    int rc = zmq_send_multipart(psocket, "wallethashtx", 12, data, 32, 0);
    return rc == 0;
}
