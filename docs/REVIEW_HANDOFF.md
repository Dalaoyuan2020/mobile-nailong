# 给下一位Agent的审查入口

当前审查分支：`codex/case26-shell-first`；[草稿PR #1](https://github.com/Dalaoyuan2020/mobile-nailong/pull/1)。先确认checkout的是PR最新head；主分支未合入前不能代表本方案。

先读[PRD](PRD.md)确定产品目标，再读[PDR](PDR.md)找设计证据和缺口，随后核对[BOM](BOM.md)、[功能路线](FUNCTIONS.md)、[总装侧视](../cad/standee/upright_side.png)及[仿真说明](../simulation/README.md)。

已交付：竖箱奶龙粗模、可回源脚本与STEP/STL、16实体几何验证、可复现的运动学/准静态估算及24项断言、修复后的交互估算页。尚未交付：真实驱动、控制固件、手机应用、目标定位、自动跟随和实物承载测试。

本轮交接检查：24项计算断言通过；独立仿真页联网/阻断网络两种条件下均可初始化、调板高与速度，360 px宽度无横向溢出、无脚本异常；当前Markdown本地链接已核对。CAD未因文档改动重新生成，原几何检查记录见`cad/standee/validation.json`。

## 可直接复制的审查任务

```text
请审查 mobile-nailong 仓库 codex/case26-shell-first 分支最新提交及PR #1，不要基于旧main的横放方案给结论。
先读 docs/PRD.md、docs/PDR.md、docs/BOM.md、docs/FUNCTIONS.md，再核对CAD和simulation。
产品是爆改普通行李箱：平稳、手机遥控、自动跟随主人；奶龙是可拆换装。自动跟随是核心交付，当前尚未实现。
当前外形是正常竖箱藏在1.6–1.8m奶龙切型板后，最低脚尖离地20mm；现有轮子仅被动占位，固定夹具未定型。
请重点审：支持距与重心、风与板挠曲、拉杆/夹具/壳体载荷、开箱/储物/手推、驱动持续扭矩与轮速、制动/断电滑行、跟随距离与方位来源、目标丢失、传感器遮挡及控制权。
区分已验证的代码/几何、假设计算、待实现功能和待实测性能。PRD中0.8m/s裸箱跟随等建议指标需审，不得当成既成能力。
运行 python simulation/simulate.py --output <临时结果路径>；浏览器打开 simulation/nailong-motion.html，可调整高度/配重/速度/半径/风。
不要自动重导出全部CAD、改模型、采购、合并PR或运行硬件。先交审查意见。
输出：通过/有条件通过/需修改；按严重程度列具体文件位置、问题、证据或复现、对应需求ID、最小整改和复验方法。找不到依据就标未验证，不凭外形图放行制造。
```

可运行的检查：

```powershell
python simulation/simulate.py --output review-results.json
```

CAD环境与复现见[README](../README.md)。`cad/case26/`保留原壳体设计坐标，当前总装由`cad/handle/case_pose.py`旋转摆正；不要把旧540 mm孔距当作竖箱前后支持距。

旧PLAN/TASKS等横放设计保留历史链接，不作为当前需求。`SOURCES.md`是资料摘录，未在本仓库复现实验，不能把别人的性能值当成当前样机性能。
