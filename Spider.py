# -*- coding: utf-8 -*-
"""
深圳大学研究生选课【不惜一切代价·全盘极速秒杀版】
针对金智教育研究生选课系统 (yjsxkapp) 极致调优

核心策略：
1. 【精准按钮定位】：遍历整行内所有可点击元素查找“选课”按钮，彻底解决 querySelector 单元素漏判 Bug！
2. 【全盘有空就抢】：全盘监控，任何课程容量未满（如 400/223、20/19、19/20），0ms 瞬间秒抢！
3. 【0ms 弹窗截击 (MutationObserver)】：浏览器底层原生观察器，确认弹窗生成的 0 毫秒瞬间触发点击【确定】，消灭所有 sleep 等待延迟！
4. 【Ajax 页面切换同步等待】：换页时等待数据渲染完成，确保第 3 页等深层页面 100% 捕获！
5. 【支持多进程独立盯页】：
     - 终端 1: python Spider.py 1  (专盯第 1 页)
     - 终端 2: python Spider.py 2  (专盯第 2 页)
     - 终端 3: python Spider.py 3  (专盯第 3 页，科研创新实践就在这页！)
     - 单终端全开: python Spider.py (全自动循环 1/2/3 页)
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
    注入浏览器底层 0ms 极速秒杀引擎 (MutationObserver)
    - 确认弹窗 0 毫秒同步点击【确定】
    - 失败/满员弹窗 10 毫秒自动秒关
    - 实验课单选框自动勾选
    """
    try:
        driver.execute_script('''
            if (window.__TURBO_INJECTED__) return;
            window.__TURBO_INJECTED__ = true;
            window.__LAST_SUCCESS_MSG__ = "";

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

                // 2. 实验课单选兜底
                var testRadio = document.querySelector("input[name='testCourse_radio_0']");
                if (testRadio && !testRadio.checked) testRadio.click();
                var testBtn = document.getElementById("testCourse_choice_btn");
                if (testBtn) testBtn.click();

                // 3. 检查是否有成功提示
                var successTip = document.querySelector(".bh-tip-success, .alert-success");
                if (successTip && (successTip.innerText || "").indexOf("成功") !== -1) {
                    window.__LAST_SUCCESS_MSG__ = successTip.innerText;
                }

                // 4. 发现失败/满额/冲突弹窗 -> 10ms 快速关闭
                var failBodies = document.querySelectorAll("#cvDialog .cv-body, .bh-dialog .content, .bh-dialog-center");
                for (var j = 0; j < failBodies.length; j++) {
                    var t = failBodies[j].innerText || "";
                    if (t.indexOf("已满") !== -1 || t.indexOf("冲突") !== -1 || t.indexOf("失败") !== -1) {
                        var closeBtn = document.querySelector(
                            "#cvDialog .cvBtnFlag, .bh-dialog-btnContainer a, .bh-dialog a, .bh-dialog button"
                        );
                        if (closeBtn) closeBtn.click();
                    }
                }
            });

            observer.observe(document.body, { childList: true, subtree: true });
            console.log("[TURBO] 0ms 极速拦截引擎已成功激活！");
        ''')
    except Exception:
        pass


def try_maximize_page_size(driver):
    """尝试将表格每页条数调大到 50 或 100，尽量单页展示全部课程"""
    try:
        driver.execute_script('''
            var selects = document.querySelectorAll("select");
            for (var s of selects) {
                for (var opt of s.options) {
                    var val = parseInt(opt.value || opt.text);
                    if (val >= 25) {
                        s.value = opt.value;
                        s.dispatchEvent(new Event("change"));
                        return true;
                    }
                }
            }
            return false;
        ''')
        time.sleep(0.5)
    except Exception:
        pass


def goto_page(driver, page_num):
    """极速切换分页并等待 Ajax 加载完成"""
    try:
        page_btns = driver.find_elements(
            By.XPATH,
            f"//a[text()='{page_num}'] | //li[text()='{page_num}'] | //span[text()='{page_num}']"
        )
        for b in page_btns:
            if b.is_displayed():
                driver.execute_script("arguments[0].click();", b)
                time.sleep(0.35)  # 等待 Ajax 渲染完成
                return True
    except Exception:
        pass
    return False


def refresh_grid_turbo(driver):
    """极速轻量刷新表格数据"""
    try:
        driver.execute_script('''
            var searchBtn = document.querySelector("button[type='button'].bh-btn-primary, button[type='submit'], .search-btn");
            if (searchBtn && (searchBtn.innerText || "").indexOf("查询") !== -1) {
                searchBtn.click();
                return;
            }
            var all = document.querySelectorAll("button, a");
            for (var i = 0; i < all.length; i++) {
                var txt = (all[i].innerText || "").trim();
                if (txt === "查询" || txt === "搜索") {
                    all[i].click();
                    return;
                }
            }
        ''')
    except Exception:
        pass


def scan_and_rush_turbo(driver, already_selected_set):
    """
    【纯 JS 毫秒级全盘扫描与秒抢】：
    遍历当前页所有课程行：
    - 满员 (如 20/20, 10/10) 0ms 直接排除；
    - 只要有名额 (A != B 如 400/223, 20/19, 19/20)，瞬间精准找到“选课”按钮并派发点击！
    - 配合底层 MutationObserver 实现 0ms 瞬间秒点确认！
    """
    try:
        res = driver.execute_script('''
            var rows = document.querySelectorAll("table tr");
            var foundTargets = [];

            for (var i = 0; i < rows.length; i++) {
                var row = rows[i];
                var text = row.innerText || "";
                if (!text) continue;

                // 已选上的跳过
                if (text.indexOf("退选") !== -1 || text.indexOf("已选") !== -1) {
                    continue;
                }

                // 检查容量正则 A / B
                var m = text.match(/(\\d+)\\s*\\/\\s*(\\d+)/);
                if (m) {
                    var a = parseInt(m[1]);
                    var b = parseInt(m[2]);
                    // 核心判断：容量未满！例如 400/223 或 20/19 或 19/20
                    if (a !== b) {
                        // 【修复核心】：精确寻找真正的“选课”按钮，遍历行内所有候选元素
                        var candidates = row.querySelectorAll("button, a, span, input[type='button'], div");
                        var chooseBtn = null;
                        for (var j = 0; j < candidates.length; j++) {
                            var bEl = candidates[j];
                            var bTxt = (bEl.innerText || bEl.textContent || bEl.value || "").trim();
                            if (bTxt === "选课") {
                                chooseBtn = bEl;
                                break;
                            }
                        }
                        if (!chooseBtn) {
                            for (var j = 0; j < candidates.length; j++) {
                                var bEl = candidates[j];
                                var bTxt = (bEl.innerText || bEl.textContent || bEl.value || "").trim();
                                if (bTxt.indexOf("选课") !== -1) {
                                    chooseBtn = bEl;
                                    break;
                                }
                            }
                        }

                        if (chooseBtn) {
                            // 毫秒级瞬间点击选课！
                            chooseBtn.click();
                            var title = text.split('\\n')[0].split('\\t')[0];
                            foundTargets.push({ name: title, cap: m[0], raw: text });

                            // 同步以及微延迟连续触发确认（双重保险）
                            setTimeout(function() {
                                var cBtns = document.querySelectorAll("div.bh-dialog a, div.bh-dialog button, .bh-btn-primary, #cvDialog .cv-sure, .bh-dialog-btnContainer a, a, button");
                                for (var k = 0; k < cBtns.length; k++) {
                                    var t = (cBtns[k].innerText || cBtns[k].textContent || "").trim();
                                    if (t === "确定" || t === "确认") {
                                        cBtns[k].click();
                                        break;
                                    }
                                }
                            }, 30);
                            setTimeout(function() {
                                var cBtns = document.querySelectorAll("div.bh-dialog a, div.bh-dialog button, .bh-btn-primary, #cvDialog .cv-sure, .bh-dialog-btnContainer a, a, button");
                                for (var k = 0; k < cBtns.length; k++) {
                                    var t = (cBtns[k].innerText || cBtns[k].textContent || "").trim();
                                    if (t === "确定" || t === "确认") {
                                        cBtns[k].click();
                                        break;
                                    }
                                }
                            }, 100);
                        }
                    }
                }
            }

            return {
                foundCount: foundTargets.length,
                targets: foundTargets,
                successMsg: window.__LAST_SUCCESS_MSG__ || ""
            };
        ''')

        if not res:
            return 0

        # 检测是否有触发成功的课程
        succ_msg = res.get("successMsg", "")
        if succ_msg:
            print(f"\n🎉🎉🎉【检测到系统成功提示！】: {succ_msg}\n")
            play_alert()
            driver.execute_script("window.__LAST_SUCCESS_MSG__ = '';")

        targets = res.get("targets", [])
        for t in targets:
            name = t["name"]
            cap = t["cap"]
            if name not in already_selected_set:
                print(f"🚨 [{time.strftime('%H:%M:%S')}] 发现空额课程！【{name}】容量: {cap} -> 0ms 闪电发起选课与确认！")

        return len(targets)

    except Exception:
        return 0


if __name__ == "__main__":
    page_target = None
    use_webvpn = False

    for arg in sys.argv[1:]:
        a = arg.strip().lower()
        if a in ('1', '2', '3'):
            page_target = a
        elif 'webvpn' in a:
            use_webvpn = True

    url = WEBVPN_URL if use_webvpn else TARGET_URL

    print("=" * 68)
    print(" 🚀 SZU 研究生选课【不惜一切代价·全盘极速秒杀版】启动")
    print(f" 入口地址: {url}")
    if page_target:
        print(f" 🎯 专属分流模式: 独占死盯【第 {page_target} 页】（全速无延迟扫描，有空就抢）")
    else:
        print(" 🎯 全盘秒杀模式: 全页面高速雷达扫描（容量未满瞬间秒抢）")
    print(" ⚡ 核心能力: 精确全行按钮穿透 + 0ms 原生 DOM 秒确认 + 10ms 满额秒关")
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

    # 尝试将表格分页大小调大（如果能一行显示 50/100 条，无需翻页速度最快）
    try_maximize_page_size(driver)

    # 注入浏览器 0ms 秒杀引擎
    inject_turbo_engine(driver)

    already_selected = set()
    round_count = 0

    print("🔥 极速秒杀引擎全面开启：只要任何一门课有名额，0ms 瞬间抢占！\n")

    if page_target:
        # 单独盯指定页码模式（多进程跑这个最快）
        print(f"📍 锁定第 {page_target} 页中...\n")
        goto_page(driver, page_target)
        time.sleep(0.3)

        while True:
            round_count += 1
            inject_turbo_engine(driver)

            # 纯 JS 毫秒级全盘扫描
            hit_count = scan_and_rush_turbo(driver, already_selected)

            if round_count % 15 == 0:
                print(f"[{time.strftime('%H:%M:%S')}] 第 {round_count} 轮扫描监听中 (第 {page_target} 页, 满员全排除, 有空必秒抢)")

            # 极速轻量刷新
            refresh_grid_turbo(driver)
            time.sleep(0.15)

    else:
        # 全页面轮询模式
        while True:
            round_count += 1
            inject_turbo_engine(driver)

            # 扫描第 1 页
            scan_and_rush_turbo(driver, already_selected)
            refresh_grid_turbo(driver)
            time.sleep(0.1)

            # 切换第 2 页
            if goto_page(driver, '2'):
                inject_turbo_engine(driver)
                scan_and_rush_turbo(driver, already_selected)
                refresh_grid_turbo(driver)
                time.sleep(0.1)

            # 切换第 3 页
            if goto_page(driver, '3'):
                inject_turbo_engine(driver)
                scan_and_rush_turbo(driver, already_selected)
                refresh_grid_turbo(driver)
                time.sleep(0.1)

            # 回到第 1 页
            goto_page(driver, '1')

            if round_count % 5 == 0:
                print(f"[{time.strftime('%H:%M:%S')}] 全局第 {round_count} 轮扫描完成，正在持续监听名额...")

            time.sleep(0.15)
