#!/usr/bin/env python
# coding: utf-8

# In[289]:


import datetime
import pandas as pd
import tushare as ts
import sys
import requests


# In[282]:


tushare_token = sys.argv[1]
# tushare_token = 'c0641675f20fa1b0c0787235e132a60a1242a89bdf953952773d71e5'
ts.set_token(tushare_token)

pro = ts.pro_api(tushare_token)


# ## 定义股票价格四线预警类

# In[268]:


class stock_alert(object):
    def __init__(self,stock_code):
        self.stock_code = stock_code
        self.today = datetime.datetime.today().date()
    
    # 获取实时数据
    def get_real_info(self):
        df_real = ts.get_realtime_quotes(self.stock_code.split('.')[0])
        df_real['price'] = df_real['price'].astype(float)
        real_info = df_real.iloc[0].to_dict()
        df_real['date'] = pd.to_datetime(df_real['date'])
        df_real['date_week'] = df_real['date'].apply(lambda x:x + datetime.timedelta(4 - x.weekday()))
        data_real = df_real[['date','date_week','price']]
        data_real.columns = ['date','date_week','close']
        return real_info,data_real
    
    # 获取历史数据
    def get_history_info(self):
        real_info,data_real = self.get_real_info()
        
        start_date = (self.today+datetime.timedelta(-500)).strftime('%Y%m%d')
        end_date = ''.join(real_info['date'].split('-'))
        df = ts.pro_bar(ts_code=self.stock_code, adj='qfq', start_date=start_date, end_date=end_date,ma=[5, 20, 50])
        df['date'] = df['trade_date'].apply(lambda x:datetime.datetime.strptime(x,'%Y%m%d'))
        # 添加当周周五，计算周均线
        df['date_week'] = df['date'].apply(lambda x:x + datetime.timedelta(4 - x.weekday()))
        data_history = df.sort_values(by=['date'],ascending=False).loc[1:][['date','date_week','close']]
        return data_history
    
    # 合并实时数据与历史数据
    def merge_data(self):
        real_info,data_real = self.get_real_info()
        data_history = self.get_history_info()
        data = pd.concat([data_real,data_history])
        return data
    
    # 计算5日、21日、60日、5周线、21周线、60周线
    def calc_ma(self):
        data = self.merge_data()
        data['ma5'] = data['close'][::-1].rolling(5).mean()[::-1]
        data['ma21'] = data['close'][::-1].rolling(21).mean()[::-1]
        data['ma60'] = data['close'][::-1].rolling(60).mean()[::-1]
        ma21_week = data.groupby('date_week')['close'].first().rolling(21).mean().to_frame(name = 'ma21_week').reset_index()
        ma60_week = data.groupby('date_week')['close'].first().rolling(60).mean().to_frame(name = 'ma60_week').reset_index()
        data_21week = pd.merge(data,ma21_week,on='date_week')
        data_60week = pd.merge(data_21week,ma60_week)
        return data_60week
    
    # 输出最新价及4线
    def print_info(self):
        data_60week = self.calc_ma()
        real_info,data_real = self.get_real_info()
        ma_info = data_60week.iloc[0].to_dict()
        ma_ls = [ma_info['ma21'],ma_info['ma60'],ma_info['ma21_week'],ma_info['ma60_week']]
        flag_ls = [float(real_info['price']) >= i for i in ma_ls]
        mark_ls = ['最新价在此之上' if flag  else '最新价在此下方' for flag in flag_ls] 
        print_info = f'''
        {real_info["time"]}: {real_info["name"]}({real_info["code"]}), 最新价{real_info["price"]}, 处于{sum(flag_ls)}线上方
        - 21日线:{ma_info["ma21"]:.2f}, {mark_ls[0]}
        - 60日线: {ma_info["ma60"]:.2f}, {mark_ls[1]}
        - 21周线: {ma_info["ma21_week"]:.2f}, {mark_ls[2]}
        - 60周线: {ma_info["ma60_week"]:.2f}, {mark_ls[3]}
        '''
#         print(print_info)
        return print_info
        


# # 微信推送

# In[283]:


wechatkey = sys.argv[2]


# In[288]:


def wechatMsg(msg,wechatkey):
#     env_dist = os.environ
    # key1 = env_dist.get('wechat_key1')  # John
    # key2 = env_dist.get('wechat_key2') # Shin
    # keys = [key1,key2]
    params = {'text':'股价4线提示','desp':f'{msg}'}
    url = f'http://sc.ftqq.com/{wechatkey}.send'
    requests.get(url,params = params)


# In[285]:


mystocks = ['300136.SZ','300618.SZ','300496.SZ','603019.SH','603611.SH','600446.SH','603799.SH','300348.SZ','300377.SZ']

msg_ls = []
for stock in mystocks:
    mystock = stock_alert(stock)
    print_info = mystock.print_info()
    msg_ls.append(print_info)


# In[287]:


msg = '\n'.join(msg_ls)


# In[ ]:


wechatMsg(msg,wechatkey)

