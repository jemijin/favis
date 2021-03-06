#!/usr/bin/python
import requests
import pandas as pd
import io
import sys
import time
import json
from bs4 import BeautifulSoup
import sqlite3

DB_STOCK_MASTER = "../db/stock_master.db"

def get_krx_stock_master():
    # STEP 01: Generate OTP
    gen_otp_url = 'http://marketdata.krx.co.kr/contents/COM/GenerateOTP.jspx'
    gen_otp_data = {
        'name':'fileDown',
        'filetype':'xls',
        'url':'MKD/04/0406/04060100/mkd04060100_01',
        'market_gubun':'ALL', # ''ALL':전체, STK': 코스피
        'isu_cdnm':'전체',
        'isu_cd':'',
        'isu_nm':'',
        'isu_srt_cd':'',
        'sort_type':'A',
        'std_ind_cd':'01',
        'par_pr':'',
        'cpta_scl':'',
        'sttl_trm':'',
        'lst_stk_vl':'1',
        'in_lst_stk_vl':'',
        'in_lst_stk_vl2':'',
        'cpt':'1',
        'in_cpt':'',
        'in_cpt2':'',
        'pagePath':'/contents/MKD/04/0406/04060100/MKD04060100.jsp',
    }

    r = requests.post(gen_otp_url, gen_otp_data)
    code = r.content

    # STEP 02: download
    down_url = 'http://file.krx.co.kr/download.jspx'
    down_data = {
        'code': code,
    }

    r = requests.post(down_url, down_data)
    f = io.BytesIO(r.content)
    
    usecols = ['종목코드', '기업명', '업종코드', '업종', '대표전화', '주소']
    df = pd.read_excel(f, converters={'종목코드': str, '업종코드': str}, usecols=usecols)
    df.columns = ['code', 'name', 'sector_code', 'sector', 'telephone', 'address']
    
    return df
    
# sector, wics, name_en
def get_sector(code):
    name_en, sector, wics, market = 'nan', 'nan', 'nan', 'nan'
    url = 'http://companyinfo.stock.naver.com/v1/company/c1010001.aspx?cmp_cd=' + code
    r = requests.get(url)
    soup = BeautifulSoup(r.text,"lxml")
    td = soup.find('td', {'class':'cmp-table-cell td0101'})
    if td == None:
        return sector, wics, name_en
        
    dts = td.findAll('dt')

    # dts[1], name_en
    name_en = dts[1].text
    
    # dts[2], sector
    s = dts[2]
    if s.text.find('KOSPI :') >= 0:
        market = 'KOSPI'
        sector = s.text.split(' : ')[1]
    elif dts[2].text.find('KOSDAQ :') >= 0:
        market = 'KOSDAQ'
        sector = s.text.split(' : ')[1]
            
    # dts[3], wics
    s = dts[3]
    if s.text.find('WICS :') >= 0:
        wics = s.text.split(' : ')[1]

    return market, wics, name_en


# desc, desc_date
def get_desc(code):
    url = 'http://companyinfo.stock.naver.com/v1/company/cmpcomment.aspx'
 
    cmt_text = ' '
    cmt_date = time.strftime("%Y-%m-%d")
 
    if code[-1] == '5': # pre_order
        code = code[0:-1] + '0'
    if code[-1] == '7': # pre_order
        code = code[0:-1] + '0'
 
    headers = {'Host':'companyinfo.stock.naver.com'}
    r = requests.post(url, data={'cmp_cd': code}, headers=headers)
    if r.text == "":
        return (cmt_text, cmt_date)
 
    j = json.loads(r.text)
    cmt_date = j['dt'].replace('.', '-')
    cmts = j['data'][0]
    cmts = [cmts['COMMENT_1'], cmts['COMMENT_2'], cmts['COMMENT_3'],  cmts['COMMENT_4'], cmts['COMMENT_5'] ]
    cmt_text = '. '.join(cmts)
    return (cmt_text, cmt_date)    
    
    
if __name__ == "__main__":
    print("1) get krx stock master")
    df = get_krx_stock_master()   
    
    conn = sqlite3.connect(DB_STOCK_MASTER)
    
    df_master = df[['code', 'name', 'sector_code', 'sector']]
    df_master.to_sql('stock_master', conn, if_exists='replace', index=False)
    
    # stock_desc 테이블  쓰기
    df_desc = df[['code', 'name', 'telephone', 'address']].copy()
    df_desc['market'] = ''
    df_desc['wics'] = ''
    df_desc['name_en'] = ''
    df_desc['desc'] = ''
    df_desc['desc_date'] = ''
    
    print("2) save krx stock master")
    df_desc.to_sql('stock_desc', conn, if_exists='replace', index=False)
    
    cur = conn.cursor()

    df_desc = pd.read_sql_query('SELECT * FROM stock_desc', conn)

    print("3) get stock desc and update db")
    cnt = 0
    for idx, row in df_desc.iterrows():
        if row['wics'] == '':
            #print('sector', row['code'], row['name'])
            market, wics, name_en = get_sector(row['code'])
            #print (market, wics, name_en)
            cur.execute('UPDATE stock_desc SET market=?, wics=?, name_en=? WHERE code=?', (market, wics, name_en, row['code']) )
            conn.commit()
    
        if row['desc_date'] == '':
            desc, desc_date = get_desc(row['code'])
            #print (desc, desc_date)
            cur.execute('UPDATE stock_desc SET desc=?, desc_date=? WHERE code=?', (desc, desc_date, row['code']) )
            conn.commit()
        cnt = cnt + 1
        
        if (cnt % 100) == 0:
            print("3) get krx stock master (%s)" % cnt)

    conn.close()    
    
    print ("total %s record inserted" % cnt)
    

