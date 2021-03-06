#!/App/tools/anaconda3/bin/python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import datetime
import pandas as pd
from pandas import DataFrame
# user define package import
import sys
sys.path.append('./')
from msgbot.favisbot import favisbot
import util.favis_util as fu
import pymysql
# set config
###################################################################################
try:
    conn = fu.get_favis_mysql_connection()
except pymysql.Error as e:
    if conn:
        conn.close()
    print ("error %s" % e.args[0])

cur = conn.cursor()

currday = datetime.datetime.today().strftime('%Y%m%d')
yesterday = (datetime.datetime.today() - datetime.timedelta(1)).strftime('%Y%m%d')
prevday = (datetime.datetime.today() - datetime.timedelta(14)).strftime('%Y%m%d')
#day = '20160801'

query = "(select * from \
		(select s.code, s.name, s.market, s.wics, sum(a.personal) personal, sum(a.foreigner) foreigner, sum(a.pension_fund) pension_fund, sum(a.institution) institution \
		from trading_trend a, stock_info s \
		where a.date between '" + prevday + "' and '"+ currday +"' and s.code = a.code and s.market = 'KOSPI' \
		   and s.code in (select code from daily_info where date = '"+yesterday+"' and marcap between 1000000 and 10000000) group by a.code) A \
		order by  foreigner desc, pension_fund desc \
		limit 5) \
		union all \
		(select * from \
		(select s.code, s.name, s.market, s.wics, sum(a.personal) personal, sum(a.foreigner) foreigner, sum(a.pension_fund) pension_fund,sum(a.institution) institution \
		from trading_trend a, stock_info s \
		where a.date between '" + prevday + "' and '"+ currday +"' and s.code = a.code and s.market = 'KOSDAQ' \
		   and s.code in (select code from daily_info where date = '"+yesterday+"' and marcap between 1000000 and 10000000)  group by a.code) A \
		order by  foreigner desc, pension_fund desc \
		limit 5) \
		union all \
		(select * from \
		(select s.code, s.name, s.market, s.wics, sum(a.personal) personal, sum(a.foreigner) foreigner, sum(a.pension_fund) pension_fund, sum(a.institution) institution \
		from trading_trend a, stock_info s \
		where a.date between '" + prevday + "' and '"+ currday +"' and s.code = a.code  and s.market = 'KOSPI' \
		   and s.code in (select code from daily_info where date = '"+yesterday+"' and marcap between 1000000 and 10000000) group by a.code) A \
		order by  pension_fund desc, foreigner desc \
		limit 5) \
		union all \
		(select * from \
		(select s.code, s.name, s.market, s.wics, sum(a.personal) personal, sum(a.foreigner) foreigner, sum(a.pension_fund) pension_fund,sum(a.institution) institution  \
		from trading_trend a, stock_info s  \
		where a.date between '" + prevday + "' and '"+ currday +"' and s.code = a.code  and s.market = 'KOSDAQ' \
		   and s.code in (select code from daily_info where date = '"+yesterday+"' and marcap between 1000000 and 10000000)  \
		group by a.code) A \
		order by  pension_fund desc, foreigner desc \
		limit 5)"
cur.execute(query)

df = pd.read_sql(query, conn)
print(df)
if conn:
    conn.close()

ret = "no|market|code|name|wics|personal|foreigner|pension_fund\n"
idx = 1
for d in df.iterrows():
	ret = ret + str(idx) +"|"+ str(d[1]['market'])+"|"+ str(d[1]['code'])+"|"+ str(d[1]['name'])+"|"+ str(d[1]['wics'])+"|"+ str(d[1]['personal'])+"|"+ str(d[1]['foreigner']) +"|"+ str(d[1]['pension_fund']) + "\n"
	if idx%5 == 0 :
		ret = ret + "\n"
	idx=idx+1
#	print("%2d|%s|%s|%s|%f|%f" % (d[1]['s_order'], str(d[1]['code']), str(d[1]['name']), str(d[1]['sector']), d[1]['per'], d[1]['roa']))


print(ret)
bot = favisbot()
bot.whisper('plain',"day_top5_bysellbuy(%s-%s) \n %s" % (prevday, currday,  ret))

