// Copyright (c) 2015 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef BITCOIN_ZMQ_ZMQPUBLISHWALLETNOTIFIER_H
#define BITCOIN_ZMQ_ZMQPUBLISHWALLETNOTIFIER_H

#include "zmqpublishnotifier.h"

class CZMQPublishWalletHashTransactionNotifier : public CZMQAbstractPublishNotifier
{
public:
    bool NotifyTransaction(const CTransaction &transaction);
};

class CZMQPublishWalletRawTransactionNotifier : public CZMQAbstractPublishNotifier
{
public:
    bool NotifyTransaction(const CTransaction &transaction);
};

#endif // BITCOIN_ZMQ_ZMQPUBLISHWALLETNOTIFIER_H
