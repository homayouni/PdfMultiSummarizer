# PdfMultiSummarizer
The project is expected to summerize Pdf file content after uploading at frontend using React, babel/standalone, then being received in the Backend using Websocket to server based on Starlette framework using Ollama  (Gemma, Llama3,..), HugginFace ( Falcon/Text_summerizer) , GPT4All ( Models..)
## Conserns:
- Sequential Chunked large/huge files upload using Websocket with verifiaction and uploade progress,
- Addressing uploaded file at the server ,
- Using React, babel/standalone at the Frontend to be able to use React without need of running node server
- Using Starlette Framework at the Backend
- Using multiple Opensource large language models (AI LLM) locally hosted like Ollama, Huggingface llm models,  GPT4ALL
- Streaming responce 
### Usage :
  1. Downloade and install Ollama
  2. Downlaode desired model for example "Llama 3 8B" by:
  ```
  ollama run gemma:2b
  ```
  3. Downlaode suitable Hugging Fcae model for example "Falconsai/text_summarization" by:
  ```
  git clone https://huggingface.co/Falconsai/text_summarization
  ```
  4. Optional downloade GPT4ALL suitable model for example mistral-7b-openorca.gguf2.Q4_0.gguf from:
  ```
  https://gpt4all.io/models/gguf/mistral-7b-openorca.gguf2.Q4_0.gguf
  ```
  5. Clone the project .
  6. Install required python packages by  :
  ```
  pip install -r requirements.txt
  ```
  7. Configure the .env file for pointing the local directory path of the HF model and optional GPT4All model
  8. Move to the project directory and Run the project by:
  ```
  python sumby2.py
  ```
  The Pdf Summarizer would be available at : 
  ```
  localhost:8000
  ```

  
  
  
