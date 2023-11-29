from fastapi import FastAPI, Request,Response
from fastapi.responses import StreamingResponse

from transformers import AutoTokenizer, AutoModel
import uvicorn, json, datetime
import torch

DEVICE = "cuda"
DEVICE_ID = "0"
CUDA_DEVICE = f"{DEVICE}:{DEVICE_ID}" if DEVICE_ID else DEVICE


def torch_gc():
    if torch.cuda.is_available():
        with torch.cuda.device(CUDA_DEVICE):
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()


app = FastAPI()


from fastapi.middleware.cors import CORSMiddleware

# 配置CORS中间件，允许所有源、所有HTTP方法和所有请求头
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
    max_age=3600,
)




@app.post("/")
async def create_item(request: Request):
    global model, tokenizer
    json_post_raw = await request.json()
    json_post = json.dumps(json_post_raw)
    json_post_list = json.loads(json_post)
    prompt = json_post_list.get('prompt')
    history = json_post_list.get('history')
    max_length = json_post_list.get('max_length')
    top_p = json_post_list.get('top_p')
    temperature = json_post_list.get('temperature')
    response, history = model.chat(tokenizer,
                                   prompt,
                                   history=history,
                                   max_length=max_length if max_length else 2048,
                                   top_p=top_p if top_p else 0.7,
                                   temperature=temperature if temperature else 0.95)
    now = datetime.datetime.now()
    time = now.strftime("%Y-%m-%d %H:%M:%S")
    answer = {
        "response": response,
        "history": history,
        "status": 200,
        "time": time
    }
    log = "[" + time + "] " + '", prompt:"' + prompt + '", response:"' + repr(response) + '"'
    print(log)
    torch_gc()
    return answer



# open_ai
@app.options("/v1/chat/completions")
async def create_item3(request: Request):
    response = Response()
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Max-Age"] = "86400"
    response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
    response.headers["Content-Encoding"] = "br"
    response.headers["Content-Type"] = "application/json"
    response.headers["Server"] = "Vercel"
    response.headers["Strict-Transport-Security"] = "max-age=63072000"
    response.headers["X-Matched-Path"] = "/api/openai/[...path]"

    return response

@app.post("/v1/chat/completions")
async def create_item2(request: Request):
    global model, tokenizer
    try:
        ccc = await request.json()
        print(ccc)
    except:
        return ''
        
    messages = json.loads(json.dumps(ccc)).get("messages",'')

    history = [] #整理后的上下文和问题; chatglm2-6b 历史对话在列表里面
    
    for i in messages:
        history.append(i.get('content')+'\n')
        
    prompt = history.pop()
    
    print('prompt:',prompt)
    history = []
    #max_length = None
    max_length = 32768
    top_p = 0.8
    temperature = 0.95
    
    

    #headers = request.headers
    #for key, value in headers.items():
    #    print(f"{key}: {value}")
    
    


    
    def _predict(prompt,history,max_length,top_p,temperature):
        past_key_values = None
        txt_ = '' #回复时，重复的部分
        
        def tun_stream(response,past_key_values_):
            nonlocal txt_
            nonlocal past_key_values
            
            past_key_values = past_key_values_
            
            past_key_values = past_key_values
            if len(response) > len(txt_):
                a = response[len(txt_):] # 新内容是个重复并延续的。; a 是新的内容
                txt_ = txt_ + a
            elif len(response) == len(txt_):
                # 发重复了，忽略
                a=''
                
            else:
                a = response
                txt_ = a
            
            #print('a:',a)
            #print('txt_:',txt_)
            
            x2x_json = {"choices":[{"delta":{"content":a}}]}
            x3x_str = json.dumps(x2x_json)
            x4x_str = f"data: {x3x_str}\n\n"
            x5x_byte = x4x_str.encode('utf-8')
            return x5x_byte
            
            
            
        for response, history, past_key_values in model.stream_chat(tokenizer, prompt, history, past_key_values=past_key_values,
                                                                    return_past_key_values=True,
                                                                    max_length=max_length, top_p=top_p,
                                                                    temperature=temperature):
            
            
            yield tun_stream(response,past_key_values)


    
    return StreamingResponse(_predict(prompt,history,max_length,top_p,temperature), media_type="text/event-stream")
    
    

'''

#  
# open_ai
@app.post("/v1/chat/completions")
async def create_item(request: Request):
    global model, tokenizer
    json_post_raw = await request.json()
    json_post = json.dumps(json_post_raw)
    
    #print('json_post_raw:',json_post_raw)
    # {'messages': [{'role': 'user', 'content': '2131'}, {'role': 'assistant', 'content': ''}, {'role': 'user', 'content': '123'}], 'model': 'gpt-3.5-turbo', 'stream': True, 'temperature': 1, 'top_p': 1}
    
    
    def generate(res):
        # res 文本回复, 本函数是转流格式回复
        for xx in res:
            x2x_json = {"choices":[{"delta":{"content":xx}}]}
            x3x_str = json.dumps(x2x_json)
            x4x_str = f"data: {x3x_str}\n\n"
            x5x_byte = x4x_str.encode('utf-8')
            yield x5x_byte

    messages = json.loads(json_post).get("messages",'')
        
    #print('messages:',messages) # chatgpt应用端发送的 消息，含历史上下文和问题。

    history = [] #整理后的上下文和问题; chatglm2-6b 历史对话在列表里面
    
    for i in messages:
        #prompt = prompt + f"{i.get('role')}:{i.get('content')}\n"
        history.append(i.get('content')+'\n')
        
    prompt = history.pop()
    
    
    print('prompt:',prompt)
    history = []
    #max_length = None
    max_length = 32768
    top_p = 0.8
    temperature = 0.95
    
    res, history = model.chat(tokenizer,
                                           prompt,
                                           history=history,
                                           max_length=max_length if max_length else 8192,
                                           top_p=top_p if top_p else 0.8,
                                           temperature=temperature if temperature else 0.95) # 产生结果

    print('res:',res)
    
    return StreamingResponse(generate(res), media_type="text/event-stream")
    
'''



if __name__ == '__main__':


    #mod = r'C:\Users\Administrator\.cache\huggingface\hub\chatglm2-6b-32k'
    mod = r'C:\Users\Administrator\.cache\huggingface\hub\chatglm3-6b'
    tokenizer = AutoTokenizer.from_pretrained(mod, trust_remote_code=True)
    #model = AutoModel.from_pretrained(mod, trust_remote_code=True).quantize(4).half().cuda()
    model = AutoModel.from_pretrained(mod, trust_remote_code=True).quantize(4).quantize(4).half().cuda()
    #model = AutoModel.from_pretrained(mod, trust_remote_code=True).quantize(8).half().cuda()
    #model = AutoModel.from_pretrained(mod, trust_remote_code=True).cuda()
    model.eval()
    uvicorn.run(app, host='0.0.0.0', port=9527, workers=1)
