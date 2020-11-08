from gevent import monkey
monkey.patch_all() 
#import eventlet
#eventlet.monkey_patch()
from random import randint

from flask import Flask, render_template,request
from flask_socketio import SocketIO,emit
import numpy
import json
import sys
import requests
from deepkinzero_EndToEnd import Run

results = { # save the prediction results for now. not very needed but for transport error workaround its necessary


}

ModelParams = {"rnn_unit_type": "LNlstm", "num_layers": 2, "num_hidden_units": 512, "dropoutval": 0.5, "learningrate": 0.001, "useAtt": True, "useEmbeddingLayer": False, "useEmbeddingLayer": False, "num_of_Convs": [], "UseBatchNormalization1": True, "UseBatchNormalization2": True, "EMBEDDING_DIM": 500, "ATTENTION_SIZE": 20, "IncreaseEmbSize": 0, "Bidirectional":True, "Dropout1": True, "Dropout2": True, "Dropout3": False, "regs": 0.001, "batch_size": 64, "ClippingGradients": 9.0, "activation1": None, "LRDecay":True, "seed":100, "NumofModels": 10} #a dictionary indicating the parameters provided for the model

app = Flask(__name__)


#right now its using threading as async mode. for better performance eventlet or gevent should be used.gevent is tested with full input and its working fine when sleep(0) are added. but the main problem is when there is low amount of input coming from client(few lines) it throws client gone transport error. for some reason io is blocked and client is disconnected. most probably because of deepkinzero. maybe add more socket.sleep because when input is full, they work
#so when threading(long polling) is used this error doenst happen but less performant,because long polling is worse than actual websocket(gevent or eventlet)
socketio = SocketIO(app,async_handlers=True, engineio_logger=True,cors_allowed_origins='*',ping_timeout=1000000,ping_interval=30,async_mode="gevent")
thread = None



@socketio.on('connect')
def onConnect():
    print("Client connected with socket id: "+str(request.sid))

    emit("connected")


def getAminoAcidSeq(id):
    url = "https://www.uniprot.org/uniprot/"+str(id)+".fasta"
    fastaData = requests.get(url).text
    aminoAcidSeq = fastaData.split("\n",1)[1].replace('\n',"")
    print(aminoAcidSeq)

    
#this function exists because if server stuck with doing too much work and client disconnects(the famous transport error connection closed.this error happens because server is too busy doing dkz work and cant reply to client ping pong so client dcs) client cant get result data.
#so by reconnecting and asking for result client gets the saved result. actually this is a workaround but working fine.


@socketio.on('getResult')
def getPredictionResult(resultId):
    result = results.get(resultId)
    print("client asking for result")
    print(result)
    if result != None:

        emit('result', {'resultData': result})
        results.pop('resultId', None)



def checkDataFromClient(dataFromClient): #check incoming data from server whether its correct format or not
    #right now we dont know what is the exact correct format so just perform simple check
    
    for inputLine in dataFromClient:
        if len(inputLine) !=3 :
            return False
        for element in inputLine:
            if " " in element or element =="":
                return False
        
    return True
        

@socketio.on('analize') #recieve input from client and run deepkinzero.
def analizeKinase(dataFromClient):
    if checkDataFromClient(dataFromClient):
        print('received kinase data: ' + str(dataFromClient))
        ModelParams = {"rnn_unit_type": "LNlstm", "num_layers": 2, "num_hidden_units": 512, "dropoutval": 0.5, "learningrate": 0.001, "useAtt": True, "useEmbeddingLayer": False, "useEmbeddingLayer": False, "num_of_Convs": [], "UseBatchNormalization1": True, "UseBatchNormalization2": True, "EMBEDDING_DIM": 500, "ATTENTION_SIZE": 20, "IncreaseEmbSize": 0, "Bidirectional":True, "Dropout1": True, "Dropout2": True, "Dropout3": False, "regs": 0.001, "batch_size": 64, "ClippingGradients": 9.0, "activation1": None, "LRDecay":True, "seed":100, "NumofModels": 10} #a dictionary indicating the parameters provided for the model
        #global thread
        #if thread is None:
        # print('thread ding')
        #thread = socketio.start_background_task(target=Run,Model = 'ZSL', TrainingEpochs = 50,
        #AminoAcidProperties = False, ProtVec = True, NormalizeDE=True,
        #ModelParams= ModelParams, Family = True, Group = True, Pathways = False, Kin2Vec=True, Enzymes = True,
        #LoadModel = True, CustomLabel="RunWithBestModel",
        #TrainData = '', TestData = dataFromClient, ValData='', TestKinaseCandidates= 'Data/AllCandidates.txt', ValKinaseCandidates= '',
        #ParentLogDir = 'Logs', EmbeddingOrParams=True, OutPath = 'Output/predictions.csv', Top_n = 10, CheckpointPath='BestModelCheckpoint',socket=socketio,socketId=request.sid)
        resultId = str(random_with_N_digits(6))
        allData = Run(Model = 'ZSL', TrainingEpochs = 50,
        AminoAcidProperties = False, ProtVec = True, NormalizeDE=True,
        ModelParams= ModelParams, Family = True, Group = True, Pathways = False, Kin2Vec=True, Enzymes = True,
        LoadModel = True, CustomLabel="RunWithBestModel",
        TrainData = '', TestData = dataFromClient, ValData='', TestKinaseCandidates= 'Data/AllCandidates.txt', ValKinaseCandidates= '',
        ParentLogDir = 'Logs', EmbeddingOrParams=True, OutPath = 'Output/predictions.csv', Top_n = 10, CheckpointPath='BestModelCheckpoint',socket=socketio,socketId=request.sid,resultId=resultId,results=results)
        #emit('result', {'resultData': allData})

        print("completed")
    else:
        emit('wrong_data')

def random_with_N_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)

if __name__ == '__main__':
    #getAminoAcidSeq("P29322") # for demonstration.use this function later

    print("DeepKinZero server is started.")

    socketio.run(app,None,4000)
