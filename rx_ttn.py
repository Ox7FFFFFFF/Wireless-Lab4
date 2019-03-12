#!/usr/bin/env python3
from time import sleep
from SX127x.LoRa import *
from SX127x.board_config import BOARD
from random import randrange
import LoRaWAN
from LoRaWAN.MHDR import MHDR
import json,logging,base64,datetime,time
from gateway_mqtt import GatewayMQTT

BOARD.setup()
class LoRaWANrcv(LoRa):
    def __init__(self,eui, verbose = False):
        super(LoRaWANrcv, self).__init__(verbose)
        self.gateway=GatewayMQTT(eui)
        self.gateway.send2node=self.send2node
        self.gateway.connect2server(LORA_SERVER,LORA_ACCOUNT,LORA_PASSWORD)

    def on_tx_done(self):
        print("RxDone")
        global SUCCESS_PACKET
        SUCCESS_PACKET+=1
        self.clear_irq_flags(TxDone=1)
        print("Tx Done timestamp : {}".format(self.getTimeStamp()))
        print("==============================")
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping(DIO_RX)
        self.set_pa_config(pa_select=1)
        self.reset_ptr_rx()
        self.set_mode(MODE.STDBY)
        self.set_mode(MODE.RXCONT)

    def getTimeStamp(self):
        us = int(datetime.datetime.now().timestamp()*1000000)
        return (us & 0xFFFFFFFF)

    def on_rx_done(self):
        global TOTAL_PACKET
        TOTAL_PACKET+=1
        print("RxDone")
        
        self.clear_irq_flags(RxDone=1)
        payload = self.read_payload(nocheck=True)
        #print("pkt_snr:",self.get_pkt_snr_value())
        #print("pkt_rssi:",self.get_pkt_rssi_value())
        #print("rssi:",self.get_rssi_value())
        self.gateway.send2server(payload,FREQ,CODERATE,-30,15,SF,125)
        self.gateway.recvLoop(timeout=1) # timeout in second

    def send2node(self, phyPayload) :
        self.set_mode(MODE.STDBY)
        self.set_dio_mapping(DIO_TX)
        self.write_payload(phyPayload)
        print('Send downlink to node\n')
        self.set_mode(MODE.TX)


    def start(self):
        self.reset_ptr_rx()
        self.set_mode(MODE.RXCONT)
        while True:
             sleep(.5)


#parameter
SYNC = 0x34
PERAMBLE = 8
DIO_TX = [1,0,0,0,0,0]
DIO_RX = [0,0,0,0,0,0]
ITX = 0
RX_CRC = True

#Gateway setting
SF = SF.SF7
BW = BW.BW125
FREQ = AS923.FREQ1
CODERATE = CODING_RATE_STR.CR4_5


#LoRa Server connect
LORA_SERVER = 'mqtt.hscc.csie.ncu.edu.tw'
LORA_ACCOUNT = 'engineer'
LORA_PASSWORD = 'nculoraserver'
GATEWAY_MAC = 'b827ebffffdf0ee9'

#TEST
SUCCESS_PACKET = 0
TOTAL_PACKET = 0

lora = LoRaWANrcv(GATEWAY_MAC,verbose=False)

# Setup
lora.set_mode(MODE.SLEEP)
lora.set_pa_config(pa_select=1)
lora.set_dio_mapping(DIO_RX)
lora.set_freq(FREQ)
lora.set_bw(BW)
lora.set_spreading_factor(SF)
lora.set_sync_word(SYNC)
lora.set_invert_iq_tx(ITX)
lora.set_preamble(PERAMBLE)
lora.set_rx_crc(RX_CRC)

#print(lora)
#lora.set_agc_auto_on(1)
assert(lora.get_agc_auto_on() == 1)

try:
    print("Waiting for incoming LoRaWAN messages")
    lora.start()
except KeyboardInterrupt:
    sys.stdout.flush()
    print("\nKeyboardInterrupt")
finally:
    sys.stdout.flush()
    print('Total Packet:   {}'.format(TOTAL_PACKET))
    print('Success Packet: {}'.format(SUCCESS_PACKET))
    print('Fail Packet:    {}'.format(TOTAL_PACKET-SUCCESS_PACKET))
    if TOTAL_PACKET > 0:
        print('Success Rate:   {}%'.format(SUCCESS_PACKET/TOTAL_PACKET*100))
    lora.set_mode(MODE.SLEEP)
    BOARD.teardown()
