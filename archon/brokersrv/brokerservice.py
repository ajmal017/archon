"""
broker with redis middleware
"""

import json
import os
import datetime
import time
from pymongo import MongoClient
import logging
import redis

from archon.broker.config import *
import archon.brokersrv.facader as facader
import archon.exchange.exchanges as exc
from archon.model import models
import archon.util.orderbooks as orderbooks
from archon.feeds import cryptocompare
from archon.util import *
import archon.exchange.bitmex.fields as bitmexfields
from archon.exchange.bitmex.ws.bitmex_ws import BitMEXWebsocket
from archon.util.custom_logger import setup_logger, remove_loggers
import archon.exchange.bitmex.bitmex as mex
from .feeder import Feeder
from .topics import *
from pathlib import Path
                
standard_apikeys_file = "apikeys.toml"
standard_conf_file = "config.toml"

class BrokerService:

    def __init__(self, setAuto=True, setMongo=True, setRedis=True, initFeeder=True):

        setup_logger(logger_name="brokerservice", log_file='brokerservice.log')
        self.logger = logging.getLogger("brokerservice")
        
        self.afacade = facader.FacadeRaw()
        #TODO 
        #in memory data
        self.balances = None
        #self.openorders = list()
        #self.submitted_orders = list()
        #self.active_exchanges = list()
        #self.selected_exchange = None

        conf_file = "conf.toml"
        
        wdir = self.get_workingdir()

        keys_filename = standard_conf_file
        path_file_conf = wdir + "/" + keys_filename
        if setAuto:
            self.set_keys_exchange_file()
                        
        if not os.path.exists(path_file_conf): 
            self.logger.error("no toml file. expected path %s"%str(path_file_conf))
        else:
            try:
                all_conf = parse_toml(path_file_conf)
            except:
                self.logger.error("config file %s not properly formatted"%str(conf_file))

        if setMongo:
            try:
                mongo_conf = all_conf["MONGO"]
                self.logger.info("mongo conf %s"%str(mongo_conf))
                uri = mongo_conf["uri"]  
                self.set_mongo(uri)
                self.using_mongo = True
            except Exception as e:
                self.using_mongo = False                    
                self.logger.error("could not set mongo. wrong configuration or config file")
                self.logger.error(str(e))
    

        self.starttime = datetime.datetime.utcnow()        
        #TODO conf

        #init feeder stream
        self.logger.info("Init feeder stream")
        if setRedis:
            self.logger.info(all_conf)
            try:
                redis_conf = all_conf["REDIS"]       
                host = redis_conf["host"]     
                port = redis_conf["port"]
                self.redis_client = redis.Redis(host=host, port=port)
            except Exception as e:
                self.logger.error("could not set redis %s %s"%(str(host),str(port)))
                self.logger.error(str(e))


        #self.init_bitmex_ws(self.redis_client)

        #init feeder thread
        if initFeeder:
            f = Feeder(self)
            f.start()
            f.join()

    def get_workingdir(self):
        home = str(Path.home())
        wdir = home + "/.archon" 

        if not os.path.exists(wdir):
            os.makedirs(wdir)

        return wdir          

    def set_mongo(self, uri):        
        self.logger.debug("using mongo %s"%str(uri))
        mongoclient = MongoClient(uri)
        self.db = mongoclient["broker-db"]

    def get_redis(self):
        return self.redis_client

    def get_db(self):
        return self.db

    def set_keys_exchange_file(self,keys_filename=standard_apikeys_file,exchanges=None):
        wdir = self.get_workingdir()
        path_file_apikeys = wdir + "/" + keys_filename
        if not os.path.exists(path_file_apikeys): 
            self.logger.error("no %s file. expected path %s"%(keys_filename,str(path_file_apikeys)))
        apikeys = parse_toml(path_file_apikeys)
        self.logger.info("set keys %s"%apikeys.keys())
        if exchanges:
            for e in exchanges:
                try:
                    self.set_keys_exchange(e, apikeys[e])
                except Exception as err:
                    self.logger.error("could not set %s"%err)
        else:            
            try:            
                for k,v in apikeys.items():
                    if exc.exchange_exists(k):
                        try:
                            self.set_keys_exchange(k, apikeys[k])
                        except Exception as err:
                            self.logger.error("could not set %s"%err)
                    else:
                        self.logger.error ("exchange not supported or not set")
                #self.logger.info("active exchanges %s"%self.active_exchanges)
                    
            except Exception as err: 
                self.logger.error("error parsing apikeys file %s"%(err))
            

    def set_keys_exchange(self, exchange, keys):
        pubkey = keys["public_key"]
        secret = keys["secret"]
        self.logger.info ("set keys %s %s"%(exchange,keys['public_key']))
        #self.db.apikeys.save({"exchange":exchange,"pubkey":pubkey,"secret":secret})
        self.afacade.set_api_keys(exchange, pubkey, secret)
        
    def get_active_exchanges(self):
        return self.active_exchanges

    def get_apikeys_all(self):
        return list(self.db.apikeys.find())
    
    def get_by_id(self, oid):
        x = list(filter(lambda x: x['oid'] == oid, self.openorders))
        return x[0]

    def set_mail_config(self, apikey, domain):
        """ mailgun config """
        self.mail_api_key = apikey
        self.mail_domain = domain
        #self.email_from = email_from
        #self.email_to = email_to  
        # 

    # --- WS specific ---

    def init_bitmex_ws(self, redis_client, symbol=mex.instrument_btc_perp):  
        apikeys = parse_toml(standard_apikeys_file)  
        k,s = apikeys["BITMEX"]["public_key"],apikeys["BITMEX"]["secret"]
        self.bitmexws = BitMEXWebsocket(redis_client, symbol=symbol, api_key=k, api_secret=s)

    # ----------------------    

    def openorders(self, e):
        if e==exc.BITMEX:
            #print (REP_TOPIC_ORDERS_BITMEX)
            raw = self.redis_client.get(REP_TOPIC_ORDERS_BITMEX)
            try:
                raw = raw.decode('utf-8')
                oo = json.loads(raw)["data"]
            except:
                oo = []
            return oo   
        elif e==exc.DERIBIT:
            raw = self.redis_client.get(REP_TOPIC_ORDERS_DERIBIT)
            raw = raw.decode('utf-8')
            try:
                oo = json.loads(raw)["data"]
            except:
                oo = []
            return oo   


    def orderbook(self, e):
        if e==exc.BITMEX:
            try:
                raw = self.redis_client.get(REP_TOPIC_MARKET_BOOK_BITMEX)
                raw = raw.decode('utf-8')
                raw = raw.replace("\'", "\"")
                book = json.loads(raw)["data"]
                return book
            except:
                raise Exception("orderbook not set")

        elif e==exc.DERIBIT:
            try:
                raw = self.redis_client.get(REP_TOPIC_MARKET_BOOK_DERIBIT)
                raw = raw.decode('utf-8')
                raw = raw.replace("\'", "\"")
                book = json.loads(raw)["data"]
                return book
            except:
                raise Exception("orderbook not set")


    def position(self, e):
        if e==exc.BITMEX:
            raw = self.redis_client.get(REP_TOPIC_POS_BITMEX)
            raw = raw.decode('utf-8')
            #print (">> ",type(raw))
            pos = raw.replace("\'", "\"")
            try:
                #print (pos)
                pos = json.loads(pos)["data"]["position"]
            except Exception as e:
                self.logger.error("convert error ",e)
            return pos

    def submit_order_post(self, order, exchange=None):
        self.logger.error("post not supported")
        """
        
        #TODO check balance before submit
        #market,ttype,order_price,qty = order
        self.log_submit_order(order)
        
        self.submitted_orders.append(order)
        [order_result,order_success] = self.afacade.submit_order(order, exchange)
        self.logger.info("order result %s"%order_result)
        """
        if exchange==exc.DERIBIT:
            #self.logger.error("post not working")
            #[order_result,order_success] = 
            result = self.afacade.submit_order_post(order, exchange)
        elif exchange==exc.BITMEX:
            #[order_result,order_success] = self.afacade.submit_order_post(order, exchange)
            result = self.afacade.submit_order_post(order, exchange)
            self.logger.info("order result %s"%result)
        else:
            self.logger.error("not supportec")

        #return [order_result,order_success]        
        return result

    def cancel_order(self, oid, exchange): 
        self.logger.debug("cancel %s"%str(oid))
        #self.log_cancel_order(oid)
        result = self.afacade.cancel_id(oid, exchange=exchange)        
        return result


    #def submit_order(self, order, exchange=None):         
    #def submit_order_post(self, order, exchange=None):
    #def cancel_order(self, oid, exchange): 
    #def cancel_all(self, exchange=None):

    #def sync_orderbook(self, market, exchange):
    #def sync_balances(self):