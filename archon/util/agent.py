"""
basic agent
"""

import sys
import os
import threading

import archon
import archon.facade as facade
import archon.broker as broker
import archon.exchange.exchanges as exc
import archon.markets as markets
import time
import datetime
import toml
import archon.model.models as models
from archon.util.custom_logger import setup_logger
import logging

from util import *
import random
import math

SIGNAL_LONG = 1
SIGNAL_NOACTION = 0
POSITION_LONG = "LONG"
POSITON_FLAT = "FLAT"


def toml_file(fs):
    with open(fs, "r") as f:
        return f.read()

def agent_config():
    toml_string = toml_file("agent.toml")
    parsed_toml = toml.loads(toml_string)
    return parsed_toml


class Agent(threading.Thread):

    def __init__(self, abroker, exchange):
        threading.Thread.__init__(self)   
        setup_logger(logger_name=__name__, log_file='broker.log')
        self.logger = logging.getLogger(__name__)     
        #config = agent_config()["AGENT"]
        #m = config["market"]    
        market = "LTC_BTC"
        self.agent_id = "agent" #config["agentid"]
        self.threadID = "thread-" + self.agent_id
        self.afacade = facade.Facade()
        self.abroker = abroker
        nom,denom = market.split('_')
        #TODO config
        self.e = exchange
        #self.market = models.get_market(nom,denom,self.e)
        self.market = market
        self.rho = 0.1

        #TODO broker already keeps track
        self.openorders = list()

        self.positions = list()

        self.round_precision = 8
        #pip paramter for ordering
        self.pip = 0.0000001
        self.logger.info("agent inited")

    def show_positions(self):
        for p in self.positions:
            self.logger.info("postion %s"%p)

    def balances(self):
        b = self.abroker.afacade.balance_all(exc.BINANCE)
        return b

    def cancel_all(self):
        self.logger.info("cancel all")
        oo = self.openorders
        self.logger.info(oo)
        for o in oo:
            self.logger.info("cancelling %s"%o)
            result = self.afacade.cancel(o) #, exchange=self.e)
            self.logger.info("cancel result: " + str(result))
            time.sleep(0.5)


    def cancel_bids(self):
        oo = self.afacade.open_orders_symbol(self.market,self.e)
        n = exc.NAMES[self.e]
        i = 0
        for o in oo:
            if o['otype']=='bid':
                self.logger.info("cancelling %s"%o)
                k = "oid"
                oid = o[k]
                result = self.afacade.cancel(o, exchange=self.e)
                self.logger.info("result" + str(result))

    def submit_buy(self,price, qty):
        o = [self.market, "BUY", price, qty]
        self.logger.info("submit ",o)
        [order_result,order_success] = self.afacade.submit_order(o, self.e)
        self.logger.info(order_result,order_success)
        if order_result:
            #TODO calculate average entry price   
            entry_time = datetime.now()
            position = [POSITION_LONG, market, price, entry_time]
            self.positions.append(position)

    def submit_sell(self,price, qty):
        o = [self.market, "SELL", price, qty]
        self.logger.info("submit ",o)
        [order_result,order_success] = self.afacade.submit_order(o, self.e)
        self.logger.info(order_result,order_success)   
        #if order_result:
        #    #position = [POSITION_FL, market, price]
        #    #TODO check whether we have partially sold or flat

    def orderbook(self,market=None):        
        if market==None: market=self.market
        self.logger.debug("get orderbook %s"%market)
        [obids,oasks] = self.afacade.get_orderbook(market,self.e)
        return [obids,oasks]

    def global_orderbook(self,market=None):
        if market==None: market=self.market
        [obids,oasks,ts] = self.abroker.get_global_orderbook(market)
        return [obids,oasks,ts]

    def show_ob(self):
        """ show orderbook """
        oo = self.afacade.open_orders_symbol(self.market,self.e)
        open_bids = list(filter(lambda x: x['otype']=='bid',oo))
        open_asks = list(filter(lambda x: x['otype']=='ask',oo))
        mybidprice = -1
        myaskprice = -1
        if len(open_bids)>0:
            mybidprice = open_bids[0]['price']
        if len(open_asks)>0:
            myaskprice = open_asks[0]['price']            

        else:
            mybidprice = 0
        [obids,oasks] = self.orderbook()
        
        oasks.reverse()
        for a in oasks[-3:]:
            p,q = a['price'],a['quantity']
            if p == myaskprice:
                self.logger.debug(p,q,"*")
            else:
                self.logger.debug(p,q)
        self.logger.debug('-----')        
        for b in obids[:5]:
            p,q = b['price'],b['quantity']
            if p == mybidprice:
                self.logger.debug(p,q,"*")
            else:
                self.logger.debug(p,q)

    def sync_openorders(self):
        try:
            self.logger.info("sync orders %s" %str(self.e))
            #oo = self.afacade.open_orders_symbol(self.market,self.e)
            oo = self.afacade.open_orders(exc.BINANCE)
            self.logger.info("oo %s" %str(oo))
            if oo != None:
                self.openorders = oo
                self.open_bids = list(filter(lambda x: x['otype']=='bid',self.openorders))
                self.open_asks = list(filter(lambda x: x['otype']=='ask',self.openorders))
        except Exception as e:
            self.logger.error(e)

    def run(self):
        raise NotImplementedError("error message")
