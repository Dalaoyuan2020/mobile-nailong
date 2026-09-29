# 资料（只放链接和原文里写明的事）

收集日：2026-09-29。不写方案。

## 1. 行李箱跟随 / 电动箱

- [US10180683B1](https://patents.google.com/patent/US10180683B1/en) Robotic platform follow a user device
  - Follow me / manual 两模式
  - 障碍识别后改路
  - 手机里的加速度计、陀螺、指南用来算用户相对箱子的角度
  - 电机和轮之间加悬架；平台和箱壳之间加悬架
- [CN110250695B](https://patents.google.com/patent/CN110250695B/zh) 智能跟随行李箱
  - 动力轮沿箱底 **长边** 方向走，比沿短边走更难前后翻
  - 原因：前后从动轮距离加大，力臂加长
  - 文中写起步、急停、凹凸路容易因重心高而倒
- [CN110664075A](https://patents.google.com/patent/CN110664075A/zh) 自动跟随行李箱
  - 超声 + GPS + MEMS 六轴陀螺 + 摄像头
  - 电池在箱底
- [WO2026016603A1](https://patents.google.com/patent/WO2026016603A1/zh) 电动驱动装置及电动行李箱
  - 外挂盒子：轮和方向杆可伸缩，可拆下收进箱里
- CSDN：[基于STM32的智能行李箱](https://blog.csdn.net/weixin_29185167/article/details/164307162)
  - HC-SR04 跟人
  - MPU6050 跌倒检测；文中示例阈值 pitch/roll **60°**
  - FSR402 称重
- IJEDR PDF：[Autonomous luggage trolley](https://rjwave.org/ijedr/papers/IJEDRB003042.pdf)
  - 铝架 60 × 40 × 80 cm，中间放登机箱
  - 前万向从动 + 后驱动
  - 电路放货舱下层，文中写明是为了压低重心
  - 跟距 0.5–1.2 m；30 次室内 87%
- IJSRD PDF：[Design, Fabrication, Assembly and Testing of Motorized Suitcase](https://www.ijsrd.com/articles/IJSRDV7I70164.pdf)
  - 24 V 250 W 电机、链传、钢管架 558.8 × 355.6 × 355.6 mm
- TAR UMT：[Design and Fabrication of Motorized Suitcase](https://eprints.tarc.edu.my/id/eprint/10284)
  - 目标空重 <10 kg，实测 15.5 kg；尺寸 0.65 × 0.25 × 0.38 m
- JSME：[Inverted Two-Wheeled Luggage Transport Vehicle](https://www.jstage.jst.go.jp/article/jrobomech/33/3/33_643/_pdf)
  - 两轮倒立行李车，静不稳，要闭环
- Royal Society：[The rolling suitcase instability](https://royalsocietypublishing.org/rspa/article/473/2202/20170076/57351/The-rolling-suitcase-instability-a-coupling)
  - 拖行李箱侧摇与平移耦合；超过某个 Froude 数会翻

## 2. 立牌 / 人字牌 / 风载

- eSigns：[How to Secure A-Frame Signs Outdoors](https://www.esigns.com/signs-101/how-secure-a-frame-signs-in-windy-areas.html)
  - 配重要装在底座里；不要把重物挂在牌上（会抬高重心）
  - 两侧注满且对称
- JS Burgess：[Wind Loading Considerations for Stillages & A-frames](https://www.jsburgess.co.uk/stillages-a-frames-wind-loading-considerations/)
  - 倾覆：重心投影跑出底边
  - 风压按 EN1991-1-4
  - 句子：Keep the CoM low and the base wide
- Access Display [Tip 'n Roll 说明书 PDF](https://cdn.shopify.com/s/files/1/0036/4393/2761/files/tip_n_roll_sidewalk_sign.pdf)
  - 底座注水 **2.5–4 加仑**（约 25–40 lb）
  - 板背加 Stabilizer Plate 贴杆
  - 搬运：提顶倾到轮上推
- Wind Sign 说明书：板每面 ≤ 5 lb；配重表 70 lb → 40 mph，100 lb → 55 mph
- Illinois IDOT PDF：[temporary sign supports wind](https://www.ideals.illinois.edu/items/140293/bitstreams/452161/data.pdf)
  - 20 mph 可部署；40 mph 不推荐任何测试过的临时牌架
  - 刚性支撑要加沙袋
- 人形 KT 架供货：常见展示高 **1.6–1.8 m**；带万向轮款约 300–500
- KT 厚度供货文：5 mm 约 0.8 kg/m²；3–5 mm 不推荐户外

## 3. 底盘现货价格（搜索页，不是推荐）

- 铝合金大载重 500×300，标 20 kg，页面价 **395**
- 同店 500×400 起 **511**
- 电赛 4WD 铝板 **3.7–50**
- 履带运输底盘 **850–4980**
- 平板电动遥控车 **2188**

搜索词：`铝合金重载底盘 20kg` `520 减速电机` `2.4G 遥控车`

## 4. 26 寸箱外形（行业对照，含轮含把手有差）

- [Indexia 2026 对照](https://indexiahq.com/suitcase-size-guide-2026/) 26 寸约 **68–73 × 43–48 × 27–31 cm**
- LuggageX 26"：66 × 47 × 31 cm

## 5. 与拉杆固定有关

- Tip 'n Roll：立杆插底座中孔，板背用 Stabilizer Plate 夹在杆上
- 人像立牌铁架供货：主杆预留螺丝孔打 KT / PVC
