# SZU_Rush_for_Lessons


#### 一个非常简单的，基于python-selenium的深大抢课脚本，纯靠控制浏览器重复点击发送请求。


##### 最近一次使用是2020年下半学期的抢课，就是疫情那个学期的抢课，后面如果不能用了会继续更新。
#### 提供了VPN和webVPN两种模式下的抢课，目前只能抢本班课程、方案内课程，可以同时抢多门课。

##### 使用过程：

###### 激活 conda 环境与安装依赖：

```bash
conda activate course_env
pip install selenium
```

Mac / Linux 用户无需额外下载 chromedriver，新版 Selenium 4+ 会自动管理驱动；如使用 Windows 可确保对应版本的 chromedriver 位于 PATH 或当前目录。

##### 🚀 极速抢课使用方法（零手动输入）：

脚本已升级**【容量满员直接排除】**策略（20/20、10/10 等满员课程 0 毫秒跳过，不发无效请求也不弹窗；一旦有人退课变成 19/20 等，毫秒级秒抢）。

###### 1. 多进程并发模式（速度最快，每个进程只盯一页，超高频刷新）：

你可以打开 3 个终端窗口并发运行：

```bash
# 终端 1：只盯第 1 页的课程
conda activate course_env
python Spider.py 1

# 终端 2：只盯第 2 页的课程
conda activate course_env
python Spider.py 2

# 终端 3：只盯第 3 页的课程
conda activate course_env
python Spider.py 3
```

###### 2. 单进程全自动模式：

```bash
conda activate course_env
python Spider.py
```
单进程下会自动在 1、2、3 页之间快速循环，满员课程直接跳过，只抢有空位名额的课程。

之后照着控制台的提醒做就好了，需要f12，然后查看并复制课程id，输入后按enter。
![1](/pic/1.png)



![2](/pic/2.png)

之后浏览器会重复发送请求直到选课成功。

欢迎大佬们帮忙改进。