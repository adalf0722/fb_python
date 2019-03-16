import datetime
import requests
import sys
import re
import os
import ast
import time
import pandas as pd 
from dateutil.parser import parse
import urllib3
urllib3.disable_warnings()

def SendMessageToLineNotify(message, full_picurl, picurl):
    """ 使用Line Notify發送訊息
    參考下列網址申請personal tokens，不用五分鐘
    https://engineering.linecorp.com/tw/blog/detail/88
    取得token後，寫死在程式裡
    或是加至環境變數中使用，這比較安全一點"""
    Token = os.environ.get('KID_TOKEN')
    url = 'https://notify-api.line.me/api/notify'
    payload = {
        'message':message,
        'imageThumbnail':picurl,
        'imageFullsize':full_picurl
    }
    header = {
        'Content-Type':'application/x-www-form-urlencoded',
        'Authorization':'Bearer {}'.format(Token)
    }
    resp=requests.post(url, headers=header, data=payload)
    print(resp.text)

if len(sys.argv) != 2:
    print('Usage:', 'python',  sys.argv[0], '<hours>')
    sys.exit(1)

# 起迄時間設定，取幾個小時前至當下
delta = int(sys.argv[1])
end_date = datetime.datetime.now().strftime('%s')
start_date = (datetime.datetime.now()-datetime.timedelta(hours=delta)).strftime('%s')

# 比對貼文中的內容，有下列關鍵字的貼文才會發訊息
pattern = re.compile('免費|free|打卡|嘉年華|派對|博覽|展覽|特展|展演|拍照|演出|見面會|店長|祭典|同樂|親子|兒童|小朋友|遊行|玩偶|娃娃|玩具|參觀|市集')

#在Facebook Graph API Exploer取得token
token = os.environ.get('FB_TOKEN')

#粉絲專頁的id與名稱放在csv中，有想加入的就自行增加進去
marks = pd.read_csv('/tools/Info_fans_kid.csv')

s = requests.Session()
for index, row in marks.iterrows():
    #使用for迴圈依序讀取粉絲頁的資訊，並使用format將id與token傳入{}裡，還有起迄時間
    res = s.get('https://graph.facebook.com/v2.12/{}/posts?fields=id,name,story,permalink_url,full_picture,picture,message,created_time&limit=100&access_token={}&since={}&until={}'.format(row['id'], token, start_date, end_date), timeout=20)

    # api有限速，若被限速了，要休息幾秒再繼續
    if 'x-app-usage' in res.headers:
        rate_limit = ast.literal_eval(res.headers['x-app-usage'])
        call_count = rate_limit['call_count']
        total_time = rate_limit['total_time']
        print(call_count, total_time)
        if call_count >= 50 or total_time >= 50:
            time.sleep(5)

    # 若status_code回傳錯誤，Line通知錯誤訊息
    if res.status_code != requests.codes.ok:
        print('Error_code:', str(res.status_code))
        print(res.json()['error']['message'])
        err_msg = sys.argv[0], '\n', 'Error_code:' + str(res.status_code), '\n', res.json()['error']['message']
        SendMessageToLineNotify(err_msg,'','')
        exit(1)

    print(str(row['id'])+' '+row['name'])
    subject = row['name']
    photo = ''
    full_photo = ''
    
    time.sleep(2)

    # 粉絲頁貼文訊息處理，資料篩選整理完也Line通知
    for information in res.json()['data']:
        if 'story' in information:
            subject = information['story']
        if 'full_picture' in information:
            full_photo = information['full_picture']
        if 'picture' in information:
            photo = information['picture']
        if 'message' in information:
            result = re.search(pattern,str(information['message']))
            if result:
                localtime = datetime.datetime.strptime(parse(information['created_time']).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')+ datetime.timedelta(hours=8)
                msg = subject + '\n' + row['name'] + '\n' + str(localtime) + '\n' + row['web'].replace('www.facebook.com','fb.me') + '\n' + information['message']
                SendMessageToLineNotify(msg,full_photo,full_photo)


