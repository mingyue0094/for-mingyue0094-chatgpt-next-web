
# 安装模块
# pip3 install flask requests requests[socks] flask_cors


# 代理相关
proxies = None   #默认直连搜索

# 设置SOCKS5代理。 部署这个服务的，搜索时需要代理修改这里。。
#proxies = {
#    'http': 'socks5://192.168.1.20:8080',
#    'https': 'socks5://192.168.1.20:8080''
#}


# 搜索的key
# key # https://cse.google.com/cse/create/new
API_KEY = 'A******-J1*****************************' # 需要改自己的
SEARCH_ENGINE_ID = '*****************'              # 需要改自己的

# openai api 接口，要修改
target_url = 'http://接受openai格式的接口地址/v1/chat/completions'


"""
本项目功能：
    
    1.  中转请求到  target_url 接口
    2.  中转前，如果用户消息开头是 !webSearch_Pro! 那么，先搜索，然后搜索结果插入模板后，生成新的消息，然后在转发到 target_url 接口
    3   这个项目是配合  https://github.com/mingyue0094/ChatGPT-Next-Web/tree/dev_for_me 使用的，属于他的一个基础组件。
    4   监听端口是 8000
    
"""

from flask import Flask, Response, request
import requests
from flask_cors import CORS, cross_origin
import json
import time
import random
import os
import threading
import datetime




class Message_data:
    message = {}


    def make_prompt_form_web_ret_get_answer(self,txt,webmsg):
        # 根据web搜索结果回答问题的提问模板。

        a = '''Using the provided web search results, write a comprehensive reply to the given query.
If the provided search results refer to multiple subjects with the same name, write separate answers for each subject.\nMake sure to cite results using \`[[number](URL)]\` notation after the reference.\n\nWeb search json results:\n"""\n'''

        b = '''"""\n\nCurrent date:\n"""\n'''
        c = '''\n"""\n\nQuery:\n"""\n'''

        e = '''\n"""\nReply in chinese and markdown.'''

        f = a + webmsg + b + str(datetime.datetime.now()) + c + txt + e
        
        print(f)
        
        return f

    def make_bin(self,a):
        x2x_json = {"choices":[{"delta":{"content":a}}]}
        x3x_str = json.dumps(x2x_json)
        x4x_str = f"data: {x3x_str}\n\n"
        x5x_byte = x4x_str.encode('utf-8')
        return x5x_byte
    
    def get_search(self,query):
        # query 搜索的关键词

        results = []
        for page in range(1,2): # 1次循环是1页，10个结果
            start = (page - 1) * 10 + 1
            try:
                url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={query}&start={start}"
                data = requests.get(url, proxies=proxies).json()

                search_items = data.get("items")

                # iterate over 10 results found
                for i, search_item in enumerate(search_items, start=1):

                    # get the page title
                    title = search_item.get("title")
                    # page snippet
                    snippet = search_item.get("snippet")
                    # alternatively, you can get the HTML snippet (bolded keywords)
                    html_snippet = search_item.get("htmlSnippet")
                    # extract the page url
                    link = search_item.get("link")

                    r = {"body":snippet,
                         "href":link,
                         "title":title}

                    results.append(r)
            except Exception as e:
                print(e)
            

        # 返回一个json响应，包含搜索结果
        return {'results': results}







message_data = Message_data()



def search_web(keywords,k,message_data):
    if message_data.message[k].get("need_search"):
        try:
            message_data.message[k]["ret"] = json.dumps(message_data.get_search(keywords),ensure_ascii=False)
            message_data.message[k]["status"] = 1
        except Exception as e:
            print(e)

            message_data.message[k]["status"] = 1 #出错，直接设置状态为搜索完成。
            pass




app = Flask(__name__)
cors = CORS(app)
cors = CORS(app, resources={r"/*": {"origins": "*"}})


#generate(request.json["messages"][-1]["content"],request.method,request.headers,request.json,request.args,_stream,result,message_data,return_str=0)
def generate(content,method,headers,_reqjson,_reqargs,_stream,result,message_data,return_str=0):

    if return_str:
        # 文本返回
        if message_data.message.get(result).get('need_search'):
            #需要搜索
            while message_data.message.get(result).get('status') != 1:
                time.sleep(0.01)

            content = message_data.make_prompt_form_web_ret_get_answer(content,message_data.message.get(result).get('ret')) # 生成提问语句
            _reqjson["messages"][-1]["content"] = content # 替换请求时的问题


        response = requests.request(
                                    method=method,
                                    url=target_url,
                                    headers=headers,
                                    json=_reqjson,
                                    params=_reqargs,
                                    stream=False,
                                    timeout=60,
                                    )
        return response.text

    else:
        # stream 返回
        if message_data.message.get(result).get('need_search'):
            # 先返回个提示
            for i in '正在联网':
                yield message_data.make_bin(i)
                time.sleep(0.7)
                
            while message_data.message.get(result).get('status') != 1:
                yield message_data.make_bin('')

            yield message_data.make_bin('\n搜索完成，准备回答\n')


            content = message_data.make_prompt_form_web_ret_get_answer(content,message_data.message.get(result).get('ret')) # 生成提问语句
            _reqjson["messages"][-1]["content"] = content # 替换请求时的问题

        print('streamn 模式')
        message_data.message.pop(result) #提取搜索结果后，删除存结果的字典，节省内存。result是设置的请求的id
        
        response = requests.request(
                                    method=method,
                                    url=target_url,
                                    headers=headers,
                                    json=_reqjson,
                                    params=_reqargs,
                                    stream=_stream,
                                    timeout=60,
                                    )
        print("response.status_code:",response.status_code)
        if response.status_code == 401:
            yield message_data.make_bin('api key 失效了')
            return ''

        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                yield chunk


@app.route('/v1/chat/completions', methods=['POST','GET'])
@cross_origin()  # 使用此注释来启用跨域支持
def proxy():
    current_timestamp = int(time.time()) # 获取当前时间戳
    random_number = random.randint(100000, 999999)  # 生成随机的6位数字
    result = str(current_timestamp) + str(random_number)  # 将时间戳和随机数字拼接在一起
    #print(result)
    message_data.message[result]={"need_search":0,"keywords":"","status":0,"ret":{}} # status = 1 表示搜索完毕，结果放到ret

    try:
        headers = request.headers
        data = request.data

        try:
            if request.json.get('messages',[])[-1].get('content','').startswith('!webSearch_Pro!'):
                request.json["messages"][-1]["content"] = request.json["messages"][-1]["content"][15:] #去掉标识，还原本来问题。
                message_data.message[result]["need_search"] = 1

            keywords = request.json["messages"][-1]["content"]
            thread = threading.Thread(target=search_web, args=(keywords,result,message_data,)).start()

            stream = request.json.get('stream',True)
            if stream:
                return Response(generate(request.json["messages"][-1]["content"],request.method,request.headers,request.json,request.args,stream,result,message_data),content_type="text/event-stream") # flask 的写法
                #return Response(generate(request,result,message_data),content_type="text/event-stream") # flask 的写法
                #return Response(generate(),media_type="text/event-stream")# fastapi的 写法
            else:
                return generate(request.json["messages"][-1]["content"],request.method,request.headers,request.json,request.args,stream,result,message_data,1) # 不是流式 
        except Exception as e:
            print(e)

            return str('请求出问题了'), 500

    except:
        return str('请求出大问题了'), 500



@app.route('/search')
def search():
    # 从请求参数中获取关键词
    query = request.args.get('q')
    return message_data.get_search(query)
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000,debug=True)
