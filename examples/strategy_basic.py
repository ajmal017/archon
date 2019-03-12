"""
basic candle based strategy
"""

import sys

import archon.exchange.exchanges as exc
import archon.facade as facade
import archon.broker as broker
import archon.model.models as models
from util import *

import json
import requests
import pickle
import time

from agent import Agent

import traceback

class BasicStrategy(Agent):

    def __init__(self, arch):
        setup_logger(logger_name=__name__, log_file=__name__ + '.log')
        self.logger = logging.getLogger(__name__)
        super().__init__(arch)
        
    def show_balance(self):
        b = self.broker.afacade.balance_all(exc.BINANCE)
        btc_b = list(filter(lambda x: x["symbol"] == "BTC", b))[0]["amount"]
        
    def candle_signal(self, candles, market):
        down = 0
        prevc = -1
        firstprice = candles[0][4]
        lastprice = candles[-1][4]
        for z in candles[-10:]:
            ts = z[0]
            o,h,l,c = z[1:5]
            c = float(c)            
            prevc = c
            print (ts,c)

        if lastprice > firstprice:
            self.logger.info("%s %s %.5f %i"%(market,ts,c))
        

    def sync_all_candles(self, markets):
        for m in markets[:10]:
            try:
                s = m['nom']
                market = models.market_from(s,"BTC")
                self.broker.sync_candle_minute(market,exc.BINANCE)
                
                x = self.broker.db.candles.find_one()
                self.logger.info(x["time_insert"])
                time.sleep(0.05)
            except Exception as err:
                logger.error("pair error %s"%err) 

    def show_candles(self):
        allx = self.broker.db.candles.find()
        for x in allx:
            c = x['candles']
            self.candle_signal(c,x["market"])

    def run(self):
        self.logger.info("starting basic strategy")
        series = list()

        markets = self.broker.fetch_global_markets(denom='BTC')
        #self.show_balance()

        while True:
            
            try:
                self.sync_openorders()     
                oo = self.openorders                
                self.logger.info("open orders %s"%str(oo))

                self.broker.db.candles.drop()
                self.sync_all_candles(markets)

                if len(oo) > 0:
                    self.logger.info("cancel all")
                    #self.cancel_all()

                else:
                    self.logger.info("scan number of markets %i"%len(markets))

                    self.show_candles()
                    
            except Exception as err:
                #traceback.print_exc()
                self.logger.error("error %s"%err)

            time.sleep(5.0)


if __name__=='__main__':
    a = broker.Broker()
    a.set_keys_exchange_file()
    ae = [exc.BINANCE]
    a.set_active_exchanges(ae)
    try:
        ag = BasicStrategy(a)
        ag.run()
        strat_started = True
    except Exception as err:
        print ("bot not started ",err)
