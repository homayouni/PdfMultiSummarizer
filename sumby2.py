import os
import hashlib
import base64
import json
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
import urllib.parse
import uvicorn
import asyncio
from starlette.endpoints import WebSocketEndpoint, HTTPEndpoint
from starlette.websockets import WebSocket
from starlette.routing import Route, WebSocketRoute, Mount
import codecs
# from gpt4all import GPT4All
from dotenv import load_dotenv
from starlette.staticfiles import StaticFiles
from pypdf import PdfReader
import ollama

from transformers import AutoTokenizer,TextIteratorStreamer , pipeline

load_dotenv()
HFmodel=os.getenv("HFmodel")
SummaryRatio=int(os.getenv("SummaryRatio"))
client = ollama.AsyncClient()
# GPT4All_modelname=os.getenv('GPT4All_modelname')
# GPT4All_modelname=os.getenv('GPT4All_model_path')
# GPT4Allmodel = GPT4All(model_name=GPT4All_modelname, model_path=GPT4All_model_path)

tokens = []
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"index.html")) as f:
    html = f.read()
#Build upload directory
if not os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),"upload")):
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)),"upload"))

class Homepage(HTTPEndpoint):
    async def get(self, request):
        return HTMLResponse(html)

gws =  WebSocket
class WSAPI(WebSocketEndpoint):
    task = None # For async working with  Ollama 
    task2 = None # For async working with HuggingFace  
    task3 = None# For async working with GPT4ALL  
    total_bytes_received = 0
    total_file_size = None
    file_name = None
    chunk_index=None 
    Prev_chunk_index=-1   
    encoding = "text"
    async def on_connect(self, websocket ) -> None: 
        await websocket.accept()
        print("connected")
    async def on_disconnect(self, websocket, close_code: int) -> None:
        await websocket.close(close_code)
        print("connected"+str(close_code))
    async def on_receive(self, websocket, data):
        try:
            # Parse the received message (assuming JSON format)
            jdata = json.loads(data)
            chunk_index = jdata.get('chunk_index')
            chunk_data = jdata.get('chunk_data')
            file_name = jdata.get('file_name')
            chunk_size = jdata.get('chunk_size')
            total_file_size = jdata.get('total_file_size')
            file_uploade_path=os.path.join(os.path.dirname(__file__),'upload')+"\\"+file_name
            # Save the chunk data to a file
            chunk_data = base64.b64decode ( jdata['chunk_data'])
            if (chunk_index==0 ) or (chunk_index==self.Prev_chunk_index+1)  :
                self.Prev_chunk_index=chunk_index
                writeMode='wb' if (chunk_index==0 ) else 'ab' 
                with open(file_uploade_path,writeMode) as file_obj:
                    file_obj.write(chunk_data)
                    file_obj.flush
                # Update progress
                self.total_bytes_received += len(chunk_data)
                percentage = int((self.total_bytes_received / total_file_size) * 100)
                print(f"Received {self.total_bytes_received} bytes out of {total_file_size} bytes ({percentage:.2f}%)")
                if self.total_bytes_received==total_file_size:
                    # md5_checksum = hashlib.md5(file_data).hexdigest()
                    file_size = os.path.getsize(file_uploade_path)
                    if total_file_size==file_size:
                        acknowledgment = {'file_name':file_name,
                                           'percentage':percentage,
                        "received_chunk_index": chunk_index,
                        'file_path':urllib.parse.quote('upload/'+ file_name) } 
                        await websocket.send_json(acknowledgment, mode="binary")
                        print(f"File upload complete! Saved as {file_name}")
                        self.Prev_chunk_index =-1
                        self.total_bytes_received=0
                        justfile_name, justfile_extension = os.path.splitext(file_name)
                        if (justfile_extension=='.pdf'):
                            reader = PdfReader(file_uploade_path)
                            text = ""
                            for page in reader.pages:
                                text += page.extract_text() + "\n"
                             
                            if self.task is not None:
                                
                                return
                            messages = []
                            messages.append({'role': 'user', 'content': 'summerize following text in '+str(round(len(text)/SummaryRatio)) +' words : '+text})
                            self.task2 = asyncio.create_task(self.AsyncHFsummerizer(websocket,file_name,text))
                            self.task = asyncio.create_task( self.SummText( websocket,file_name,messages))
                        #optional use of GPT4ALL
                        # self.task3 = asyncio.create_task( self.g4a( websocket,'summerize following text in 30 words : '+text,file_name))  
                        
                else : # acknowledge recived chunk and ready for next
                    acknowledgment = {
                        'file_name':file_name,
                        "received_chunk_index": chunk_index,
                        "percentage": percentage
                    }
                    await websocket.send_json(acknowledgment, mode="binary")
            else: # Error on chunking so needs  resending the file
                acknowledgment = {
                    'file_name':file_name,
                    "received_chunk_index": -1,
                    "percentage": 0
                }
                print(websocket.state)
                self.Prev_chunk_index =-1
                self.total_bytes_received=0
                await websocket.send_json(acknowledgment, mode="binary")
                
        except Exception as e:
            # By this way we can know about the type of error occurring
            print("The error is: ",e)

    async def SummText(self, websocket,file_name,messages: str):
        desc=True
        all_content = ""
        async for response in await client.chat(model='gemma:2b' , messages=messages, stream=True): #''' llama3 gemma:2b '''
            if response['done']:
                
                self.task = None
                return 
            content = response['message']['content']
            if (desc ):
                if( content==':'): # exclude the summerization note of the model 
                    desc=False
            else:
                
                all_content+=content
                acknowledgment = {

                        'file_name':file_name,
                        "textsummery_1": content,
                        "percentage": 0
                    }
                print(acknowledgment)
                await websocket.send_json(acknowledgment, mode="binary")
    async def AsyncHFsummerizer(self, websocket,file_name,text):
        tokenizer = AutoTokenizer.from_pretrained(HFmodel, max_length=1024, truncation=True)
        streamer = TextIteratorStreamer(tokenizer)
        summarizer = pipeline(task="summarization",
                            tokenizer=tokenizer,
                            model=HFmodel,
                            streamer=streamer,
                            num_beams=1,
                            length_penalty=0)
        out = []
        threshold = 1712 #
        for Sntence in text.split('. '):
            if out and (len(Sntence.split())+len(out[-1].split())< threshold):
                out[-1] += ' '+Sntence+'.'
            else:
                out.append(Sntence+'.')

        for chunk in out:
            
            word=''
            for t in summarizer(chunk,
                            max_length=round(len(chunk)/SummaryRatio),
                            min_length=10,
                            do_sample=True
                            )[0]['summary_text']:
                if (t ==" " or t ==".") :
                    print (word , end=' ')
                    acknowledgment = {
                        'file_name':file_name,
                        "textsummery_2": word+' ',
                        "percentage": 0
                    }
                    print(acknowledgment)
                    await websocket.send_json(acknowledgment, mode="binary")
                    word=''
                else : 
                    word+=t 



        self.task2 = None
    async def g4a(self, websocket,m,file_name):
        with GPT4Allmodel.chat_session():
            for  token in  GPT4Allmodel.generate(m, streaming=True):
                tokens.append(token)
                content=codecs.encode(token, encoding='utf-8', errors='strict').decode(encoding= "utf-8")
                acknowledgment = {
                    'file_name':file_name,
                    "textsummery_3": content,
                    "percentage": 0
                }
                print(acknowledgment)
                await websocket.send_json(acknowledgment, mode="binary")
            return


routes = [
   
    Mount('/static', StaticFiles(directory=os.path.dirname(__file__)+'/static'), name="static"),
    Mount('/upload', StaticFiles(directory=os.path.dirname(__file__)+'/upload'), name="static"),
    Route("/", Homepage),
    WebSocketRoute("/ws", WSAPI),
    
]

app = Starlette(routes=routes)

if __name__ == "__main__":
    print( os.getcwd() )
    uvicorn.run(
        "sumby2:app",
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        reload=False,
    )