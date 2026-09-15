# -*- coding: utf-8 -*-
"""
深圳大学研究生选课【不惜一切代价·极限秒杀版】
针对金智教育研究生选课系统 (yjsxkapp) 极致调优

核心加速技术：
1. 【0ms 弹窗截击 (MutationObserver)】：直接在浏览器底层注入原生观察器，确认弹窗生成的 0 毫秒瞬间触发点击，彻底消灭一切 sleep 延迟！
2. 【满员弹窗 10ms 闪电关闭】：失败提示框出现 10 毫秒内秒关，绝不阻碍下一击！
3. 【极限高频轮询 (100ms)】：告别秒级等待，每 100ms 刷新与扫描，有退课秒抢！
4. 【默认死磕核心目标：2706145-深度学习（02）施斯】：
   自动锁定第 2 页（深度学习所在页），死咬不放，不惜一切代价抢下！
"""

import os
import re
import sys
import time
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By

TARGET_URL = 'https://ehall.szu.edu.cn/yjsxkapp/sys/xsxkapp/xsxkHome/gotoChooseCourse.do'
WEBVPN_URL = 'https://ehall-szu-edu-cn.webvpn.szu.edu.cn/yjsxkapp/sys/xsxkapp/xsxkHome/gotoChooseCourse.do'

# 核心狙击目标（默认深度学习02）
SNIPER_TARGET = {
    "code": "2706145",
    "name": "深度学习（02）",
    "teacher": "施斯",
    "page": "2"
}


def play_alert():
    """抢课成功提示音"""
    if os.path.exists('warn.mp3'):
        if platform.system() == 'Darwin':
            os.system('afplay warn.mp3 &')
            return
        try:
            from playsound import playsound
            playsound('warn.mp3')
            return
        except Exception:
            pass
    print('\a\a\a', end='', flush=True)


def inject_turbo_engine(driver):
    """
    注入浏览器底层 0ms 极速拦截引擎 (MutationObserver)
    实现确认弹窗 0 毫秒秒点、错误弹窗 10 毫秒秒关
    """
    try:
        driver.execute_script('''
            if (window.__TURBO_INJECTED__) return;
            window.__TURBO_INJECTED__ = true;
            window.__RUSH_SUCCESS__ = false;

            var observer = new MutationObserver(function(mutations) {
                // 1. 发现确认弹窗 -> 0ms 瞬间点击【确定】
                var confirmBtns = document.querySelectorAll(
                    "div.bh-dialog a, div.bh-dialog button, div.bh-dialog-btnContainer a, " +
                    "div.bh-dialog-btnContainer button, .bh-btn-primary, #cvDialog .cv-sure, #cvDialog .cvBtnFlag"
                );
                for (var i = 0; i < confirmBtns.length; i++) {
                    var b = confirmBtns[i];
                    var txt = (b.innerText || b.textContent || "").trim();
                    if (txt.indexOf("确定") !== -1 || txt.indexOf("确认") !== -1 || txt.indexOf("是") !== -1) {
                        b.click();
                        break;
                    }
                }

                // 2. 检查成功提示
                var successTip = document.querySelector(".bh-tip-success, .alert-success");
                if (successTip && (successTip.innerText || "").indexOf("成功") !== -1) {
                    window.__RUSH_SUCCESS__ = true;
                }

                // 3. 发现失败/满额弹窗 -> 立即闪电关闭
                var failBodies = document.querySelectorAll("#cvDialog .cv-body, .bh-dialog .content, .bh-dialog-center");
                for (var j = 0; j < failBodies.length; j++) {
                    var t = failBodies[j].innerText || "";
                    if (t.indexOf("已满") !== -1 || t.indexOf("冲突") !== -1 || t.indexOf("失败") !== -1) {
                        var closeBtn = document.querySelector("#cvDialog .cvBtnFlag, .bh-dialog-btnContainer a, .bh-dialog a, .bh-dialog button");
                        if (closeBtn) closeBtn.click();
                    }
                }
            });

            observer.observe(document.body, { childList: true, subtree: true });
            console.log("[TURBO] 0ms 极速秒杀引擎已注入！");
        ''')
    except Exception:
        pass


def goto_page(driver, page_num):
    """极速切换分页"""
    try:
        page_btns = driver.find_elements(
            By.XPATH,
            f"//a[text()='{page_num}'] | //li[text()='{page_num}'] | //span[text()='{page_num}']"
        )
        for b in page_btns:
            if b.is_displayed():
                driver.execute_script("arguments[0].click();", b)
                time.sleep(0.2)
                return True
    except Exception:
        pass
    return False


def refresh_grid_turbo(driver, page_target="2"):
    """极速刷新当前表格（100ms级轻量拉取）"""
    try:
        driver.execute_script('''
            // 优先点击“查询”或搜索按钮触发无感局部刷新
            var searchBtn = document.querySelector("button[type='button'].bh-btn-primary, button[type='submit'], .search-btn");
            if (searchBtn) {
                searchBtn.click();
                return;
            }
            var allBtns = document.querySelectorAll("button");
            for (var b of allBtns) {
                if ((b.innerText || "").indexOf("查询") !== -1 || (b.innerText || "").indexOf("搜索") !== -1) {
                    b.click();
                    return;
                }
            }
        ''')
    except Exception:
        pass


def sniper_strike(driver, target):
    """
    【狂暴狙击手一击】：
    对目标课程（如深度学习02）发起毫秒级点击并自动秒确认
    返回: (status, message)
    """
    code = target["code"]
    teacher = target["teacher"]

    try:
        res = driver.execute_script(f'''
            var rows = document.querySelectorAll("table tr");
            for (var i = 0; i < rows.length; i++) {{
                var row = rows[i];
                var text = row.innerText || "";
                if (text.indexOf("{code}") !== -1 && (!"{teacher}" || text.indexOf("{teacher}") !== -1)) {{
                    // 检查是否已经是已选状态
                    if (text.indexOf("退选") !== -1 || text.indexOf("已选") !== -1) {{
                        return {{ status: "already", text: text }};
                    }}
                    // 提取容量
                    var m = text.match(/(\\d+)\\s*\\/\\s*(\\d+)/);
                    var cap = m ? m[0] : "未知";
                    var isAvail = m ? (parseInt(m[1]) !== parseInt(m[2])) : true;

                    var btn = row.querySelector("button, a, span");
                    if (btn && (btn.innerText.indexOf("选课") !== -1 || btn.textContent.indexOf("选课") !== -1)) {{
                        // 毫秒级直接派发点击！
                        btn.click();
                        return {{ status: "clicked", cap: cap, isAvail: isAvail, text: text }};
                    }}
                }}
            }}
            return {{ status: "not_found" }};
        ''')

        if not res:
            return "none", ""

        status = res.get("status")
        if status == "already":
            return "already", res.get("text", "")

        if status == "clicked":
            cap = res.get("cap", "")
            is_avail = res.get("isAvail", False)
            return "clicked", f"容量: {cap}"

        return "not_found", ""

    except Exception as e:
        return "error", str(e)


def check_overall_success(driver):
    """检查是否抢课成功"""
    try:
        is_succ = driver.execute_script('''
            if (window.__RUSH_SUCCESS__) return true;
            var tip = document.querySelector(".bh-tip-success, .alert-success");
            if (tip && (tip.innerText || "").indexOf("成功") !== -1) return true;
            return false;
        ''')
        return bool(is_succ)
    except Exception:
        return False


if __name__ == "__main__":
    url = TARGET_URL
    target_page = "2"  # 默认锁定第 2 页（深度学习 02 施斯 所在页面）
    target_name = "2706145-深度学习（02）施斯"

    # 参数支持：可传入指定页码或课号
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg in ('1', '2', '3'):
            target_page = arg
        elif 'webvpn' in arg.lower():
            url = WEBVPN_URL

    print("=" * 68)
    print(" 🚀 SZU 研究生选课【不惜一切代价·极限秒杀版】启动")
    print(f" 🎯 核心锁定目标: 【{target_name}】")
    print(f" 📍 锁定常驻分页: 第 {target_page} 页（绝不来回翻页浪费算力）")
    print(" ⚡ 加速特性: 0ms 原生弹窗秒确认 + 10ms 满额秒关 + 100ms 极速刷新")
    print("=" * 68)

    # 启动 Chrome
    driver = webdriver.Chrome()
    driver.get(url)

    print('\n👉 请在弹出的浏览器中完成登录...')

    # 监听登录状态
    while True:
        try:
            curr_url = driver.current_url
            page_text = driver.page_source
            if 'gotoChooseCourse.do' in curr_url and 'authserver' not in curr_url:
                print('⚡ 登录成功，已进入选课界面！\n')
                break
            if any(k in page_text for k in ['计算机与软件学院', '博弈论', '开课院系', '方案内课程', '已选课程']):
                print('⚡ 登录成功，已识别到课程列表！\n')
                break
        except Exception:
            pass
        time.sleep(1)

    # 登录成功后，常驻第 2 页（目标所在页）
    print(f"📍 正在直奔目标所在分页: 第 {target_page} 页...")
    goto_page(driver, target_page)
    time.sleep(0.5)

    # 注入浏览器 0ms 极速秒杀引擎
    inject_turbo_engine(driver)

    print(f"\n🔥 极限秒杀火力全开！全速死磕【{target_name}】，有退课瞬间秒杀！\n")

    strike_count = 0
    start_time = time.time()

    while True:
        strike_count += 1

        # 确保极速拦截引擎处于活动状态
        inject_turbo_engine(driver)

        # 毫秒级狙击一击！
        status, detail = sniper_strike(driver, SNIPER_TARGET)

        if status == "already":
            print(f"\n🎉🎉🎉【恭喜！目标已成功选上！】{target_name}！\n")
            play_alert()
            break

        if check_overall_success(driver):
            print(f"\n🎉🎉🎉【检测到系统成功提示：选课成功！】{target_name}！\n")
            play_alert()
            break

        if status == "clicked":
            # 击中目标，打印状态
            if strike_count % 10 == 0:
                print(f"[{time.strftime('%H:%M:%S')}] ⚡ 第 {strike_count} 次极速狙击中... ({detail})")

        elif status == "not_found":
            # 当前未找到，尝试切回目标页
            goto_page(driver, target_page)

        # 极速轻量刷新表格获取最新名额
        refresh_grid_turbo(driver, target_page)

        # 极限短等待：100毫秒
        time.sleep(0.1)
