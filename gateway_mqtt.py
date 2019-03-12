#!/usr/bin/python3
import paho.mqtt.client as mqtt
import json,logging,base64,time,datetime,ssl
logging.basicConfig(level=logging.DEBUG)

class GatewayMQTT(mqtt.Client):
    def __init__(self,gateway_eui):
        super(GatewayMQTT, self).__init__()
        self.logger = logging.getLogger()
        self.eui = gateway_eui.lower()
        print('set gateway eui : {}'.format(self.eui))
        self.publishTopic='gateway/{}/rx'.format(gateway_eui)
        print('MQTT topic : {}'.format(self.publishTopic))
        self.connectSuccess = False

    def connect2server(self,server,mqtt_user,mqtt_pass):
        self.username_pw_set(mqtt_user,mqtt_pass)
        self.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
        self.connect(server,1883,60)
        self.loop_start()

    def send2server(self,phyPayload,freq,coderate,rssi,snr,sf,bw):
        data = {
            'rxInfo' :{
                'mac' : self.eui,
                'timestamp' : self.getTimestamp(),
                'frequency' : int(freq*1000000),
                'channel' : 0,
                'rfChain' : 0,
                'crcStatus' : 1,
                'codeRate' : coderate,
                'rssi' : rssi,
                'loRaSNR' : snr,
                'size' : len(phyPayload),
                'dataRate' : {
                    'modulation' : 'LORA',
                    'spreadFactor' : sf,
                    'bandwidth' : bw
                    },
                'board' : 0,
                'antenna' : 0
            },
            'phyPayload' : base64.b64encode(bytes(phyPayload)).decode()
        }
        j = '{}'.format(json.dumps(data))
        self.txGet = False
        self.logger.debug('uplink payload: {}'.format(j))
        self.publish(self.publishTopic,j,qos=2)

    def on_connect(self, mqttc, obj, flags, rc) :
        if rc==0:
            print('\nconnect to server')
            self.subscribe('gateway/{}/tx'.format(self.eui))
            self.connectSuccess=True
        else:
            print('bad connection:{}'.format(rc))

    def on_message(self, mqttc, obj, msg) :
        j=json.loads(msg.payload.decode())
        txInfo=j['txInfo']
        self.logger.debug('downlink payload: {}'.format(j))
        self.wait2timestamp(txInfo['timestamp'])
        self.send2node(list(base64.b64decode(j['phyPayload'].encode())))
        self.txGet=True


    def getTimestamp(self) :
        us=int(datetime.datetime.now().timestamp()*1000000)
        return us & 0xffffffff

    def wait2timestamp(self, timestamp):
        count=0
        while True :
            t=self.getTimestamp()
            count+=1
            if t>timestamp:
                break

    def recvLoop(self, timeout=1) :
        count=0
        endTime=datetime.datetime.now().timestamp()+timeout
        self.loop_start()
        while True :
            count+=1
            currentTime=datetime.datetime.now().timestamp()
            if self.txGet or currentTime>endTime:
                self.loop_stop()
                try :
                    self.reconnect()
                except Exception as e:
                    self.logger.warning('Exception: {}'.format(e))
                break
