import pandas as pd
import numpy as np
from lxml import etree
import requests
import re
import json
# 设置展示的最大宽度
desired_width = 3200
pd.set_option('display.width', desired_width)
# 显示的最大列数，解决中间被省略为...的问题
pd.set_option("display.max_columns",None)
# 将标题和数据左对齐,默认右对齐
pd.set_option('colheader_justify', 'left')
import warnings
warnings.filterwarnings('ignore')

def get_data(url):
    """获取指定url的数据, 并将结果新增city字段
       url:数据地址
       city:改地址的城市名称
    """
    res = requests.get(url, headers=headers)
    # print(res.text)
    res_elements = etree.HTML(res.text)
    return res_elements

def get_resblock_id(res_elements):
    """获取小区的resblock_id"""
    # 提取目标数据的标签
    table = res_elements.xpath('//div[@class="list-more"]/dl/dd/a[@rel="nofollow"]')
    # 转换成字符串
    ss = etree.tostring(table[0], encoding='utf-8').decode()
    # 正则提取resblock_id
    resblock_id = re.findall('.+c(\d+)rs.+', ss)[0].strip()
    return resblock_id




def get_commu_info(res_elements):
    """获取小区相关的情况"""
    # 获取小区的resblock_id
    resblock_id = get_resblock_id(res_elements)
    # 获取小区的信息
    url = f'https://sh.ke.com/api/listtop?type=resblock&resblock_id={resblock_id}&source=ershou_xiaoqu'
    res = pd.Series()
    response = requests.get(url, headers=headers)
    html = response.text

    # 将json解析为dict
    html_dic = json.loads(html)
    # 解析json
    xiaoqu_info = html_dic['data']['info']
    res['小区名称'] = xiaoqu_info['name'].strip()
    res['区名'] = xiaoqu_info['districtName'].strip()
    res['板块名称'] = xiaoqu_info['bizcircleName'].strip()
    res['小区均价']= xiaoqu_info['unitPrice']
    res['近90天成交套数'] = xiaoqu_info['90saleCount']
    res['近30天带看数'] = xiaoqu_info['day30See']
    res['正在出售套数'] = xiaoqu_info['sellNum']
    return res


def get_house_info(res_elements,commu_info):
    """当小区有在售二手房时, 获取在售的房子信息, 包括所属板块,几室几厅,面积, 售价"""

    # 存储结果用的DataFrame
    df_house = pd.DataFrame(columns=columns)
    # 获取该小区在售的房屋套数

    # 获取在售房屋列表
    table = res_elements.xpath('//div[@class="info clear"]')
    print('-' * 60)
    # 提取在售房屋的信息
    for i,house in enumerate(table):
        house_res = commu_info.copy()
        print(f'第{i+1}套')
        # 将选出来得条目转成text, 再转成网页树
        ss = etree.tostring(house,encoding='utf-8').decode()
        house = etree.HTML(ss)

        # 提取房子信息
        # 标题
        title = house.xpath('//div[@class="title"]/a[@class="LOGCLICKDATA "]/text()')[0]
        print(f"title:{title}")
        house_res['title'] = title

        # 板块
        region_name = house.xpath('//div[@class="positionInfo"]/a/text()')
        print(f"板块名称:{region_name}")
        if house_res['小区名称']!=region_name[0].strip():
            continue
        # 房屋信息
        house_info = house.xpath('//div[@class="houseInfo"]/text()')[0]
        print(f"房屋信息:{house_info}")
        house_res['室厅'] = house_info.split('|')[0]
        house_res['面积'] = house_info.split('|')[1]
        house_res['卧室朝向'] = house_info.split('|')[2]
        house_res['装修'] = house_info.split('|')[3]
        house_res['楼层'] = house_info.split('|')[4]
        house_res['年份'] = house_info.split('|')[5]
        house_res['类型'] = house_info.split('|')[6]

        # 价格
        price = house.xpath('//div[@class="priceInfo"]/div[@class="totalPrice totalPrice2"]')[0].xpath('string(.)')
        print(f'总价:{price}')
        house_res['总价'] = price

        # 单价
        unit_price = house.xpath('//div[@class="priceInfo"]/div[@class="unitPrice"]')[0].xpath('string(.)')
        print(f"单价:{unit_price}")
        house_res['单价'] = unit_price

        print('-'*60)
        df_house = df_house.append(house_res,ignore_index=True)
    return df_house



def main(df):
    """"""
    res = []
    for addr_name in addr_names:
        print(f"{addr_name=}")
        # 获取网页
        url = f'https://sh.lianjia.com/ershoufang/rs{addr_name}/'
        res_elements = get_data(url)
        # 提取消息概况信息
        commu_info = get_commu_info(res_elements)

        # 获取二手房信息
        if commu_info['正在出售套数'] ==0:
            print(f'小区{addr_name}没有在售二手房')
            df = df.append(commu_info,ignore_index=True)
        else:
            df_house = get_house_info(res_elements, commu_info)
            df = pd.concat([df,df_house],ignore_index=True)

    return df


if __name__=="__main__":

    addr_names = ['金领国际','龚路新村','龚华公寓','龚路新城','金利公寓']
    # addr_names = ['金领国际','金利公寓']


    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.1 \
    (KHTML, like Gecko) Chrome/14.0.835.163 Safari/535.1'}
    columns = ['区名','板块名称','小区名称','小区均价', '正在出售套数','近30天带看数','近90天成交套数','title', '室厅', '面积', '卧室朝向', '装修', '楼层', '年份', '类型', '总价', '单价']
    df = pd.DataFrame(columns=columns)

    df = main(df)
    print(df)


