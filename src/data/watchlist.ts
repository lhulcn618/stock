export interface WatchlistSeed {
  code: string;
  name: string;
}

// 手动维护这里即可：增删股票时保留 code，name 方便你快速识别和剔除。
export const watchlistSeeds: WatchlistSeed[] = [
  { code: "300846", name: "首都在线" },	
  { code: "601868", name: "中国能建" },	
  { code: "601669", name: "中国电建" },
  { code: "601611", name: "中国核建" },
  { code: "600150", name: "中国船舶" },
  { code: "600118", name: "中国卫星" },
  { code: "600176", name: "中国巨石" },
  { code: "002339", name: "积成电子" },
  { code: "300265", name: "通光线缆" },
  { code: "300191", name: "潜能恒信" },
  { code: "300875", name: "捷强装备" },
  { code: "300775", name: "三角防务" },
  { code: "600026", name: "中远海能" },
  { code: "000070", name: "特发信息" },
  { code: "002025", name: "航天电器" },
  { code: "002792", name: "通宇通讯" },
  { code: "002281", name: "光迅技术" },
  { code: "300302", name: "同有科技" },
  { code: "300166", name: "东方国信" },
  { code: "000988", name: "华工科技" },
  { code: "300389", name: "艾比森" },  
  { code: "000815", name: "美利云" },
	{ code: "002261", name: "拓维信息" },
  { code: "600410", name: "华胜天成" },
  { code: "002342", name: "巨力索具" },
  { code: "600367", name: "红星发展" },
  { code: "002432", name: "九安医疗" },
  { code: "603650", name: "彤程新材" },
  { code: "000021", name: "深科技" },
  { code: "002156", name: "通富微电" },
  { code: "300672", name: "国科徽" },
  { code: "601615", name: "明阳智能" },
  { code: "300479", name: "神思电子" },
  { code: "603887", name: "城地香江" },
  { code: "301306", name: "西测测试" },
  { code: "002202", name: "金风科技" },
  { code: "002130", name: "沃尔核材" },
  { code: "301128", name: "张瑞技术" },  
  { code: "603629", name: "雷曼光电" },  
  { code: "300162", name: "利通电子" },  
  { code: "301293", name: "三博脑科" },
  { code: "603739", name: "蔚蓝生物" },
  { code: "300058", name: "蓝色光标" },
  { code: "600633", name: "浙数文化" },
  { code: "002624", name: "完美世界" },
  { code: "000930", name: "中粮科技" }
];

export const watchlistCodes = watchlistSeeds.map((item) => item.code);
