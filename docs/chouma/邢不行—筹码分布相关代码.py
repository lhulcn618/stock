import pandas as pd
import numpy as np
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行


# ===导入数据
df = pd.read_csv('sh600000.csv', encoding='gbk', skiprows=1, parse_dates=['交易日期'])
df = df.sort_values(by='交易日期', ascending=True).reset_index(drop=True)  # 按照日期排列
df.reset_index(drop=True, inplace=True)


# ====计算复权价：
df['涨跌幅'] = df['收盘价'] / df['前收盘价'] - 1
df['复权因子'] = (1 + df['涨跌幅']).cumprod()
# 后复权收盘价
df['收盘价_复权'] = df['复权因子'] * (df.iloc[0]['收盘价'] / df.iloc[0]['复权因子'])
df['均价'] = df['成交额'] / df['成交量']
df['均价_复权'] = df['收盘价_复权'] * df['均价'] / df['收盘价']
df['均价_复权'] = np.round(df['均价_复权'], 2)  # 保留两位小数
# 计算每日股票换手率
df['换手率'] = df['成交额'] / df['流通市值']
# 截取需要的列
df = df[['交易日期', '均价_复权', '换手率', '前收盘价']]


# ====计算筹码分布
# 存储筹码分布数据的dataframe
chips = pd.DataFrame()

# 股票初始发行
chips.loc[0, '价格'] = df['前收盘价'][0]  # 发行价格
chips.loc[0, '比例'] = 1

# 遍历每根K线
for index, row in df.iterrows():

    price = row['均价_复权']
    turn_over = row['换手率']

    # 如果价格从未出现过
    if price not in chips['价格'].tolist():
        # 所有价格的筹码比例 ×（1 - 换手率）
        chips['比例'] = chips['比例'] * (1 - turn_over)
        # 将新价格添加到筹码分布中
        _t = pd.DataFrame({'价格': [price], '比例': [turn_over]})
        chips = pd.concat([chips, _t], ignore_index=True)

    # 如果价格出现过
    else:
        # 所有价格的筹码比例 ×（1 - 换手率）
        chips['比例'] = chips['比例'] * (1 - turn_over)
        # 当日价格的筹码在之前变动的基础上加上今日换手率
        chips.loc[chips['价格'] == price, '比例'] += turn_over

# 按照价格从大到小排序
# chips.sort_values('价格', inplace=True, ascending=False)
# chips.reset_index(inplace=True, drop=True)
# chips[chips['比例'] >= 0.0001].to_csv('筹码分布结果.csv', index=False)


# ====对筹码进行汇总
chips['价格_汇总'] = np.round(chips['价格'], 0)
chips = chips.groupby('价格_汇总')[['比例']].sum()
chips.sort_values('价格_汇总', inplace=True, ascending=False)
chips[chips['比例'] >= 0.0001].to_csv('筹码分布结果_汇总.csv')
print(chips)

