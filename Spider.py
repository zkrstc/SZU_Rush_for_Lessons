# -*- coding: utf-8 -*-
"""
深圳大学研究生选课【定页死盯·精准容量·极速刷新秒杀版】
针对金智教育研究生选课系统 (yjsxkapp) 极致调优

核心修复与策略：
1. 【容量识别 Bug 彻底根除】：
     针对单元格 <td> 严格精确匹配，彻底避免上课教室门牌号（如致理楼202）与容量（20/20）拼接成 20220/20 的解析错误！
     满员（20/20, 10/10）绝对排除，真正有空额（如 400/223, 20/19, 19/20）立马触发！
2. 【独占死盯指定页，防跳回第 1 页】：
     - 传 1 盯第 1 页
     - 传 2 盯第 2 页 (默认)
     - 传 3 盯第 3 页
     高频重新触发当前页码加载，绝不跳回第 1 页！
3. 【极速 0ms 瞬间秒选与确认】：
     全行穿透检索，一旦发现未满额课程，0ms 瞬间点击【选课】并通过底层 MutationObserver 0ms 瞬间秒点【确定】！
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
                    "div.bh-dialog-btnContainer button, .bh-btn-primary, #cvDialog .cv-sure, #cvDialog .cvBtnFlag, " +
                    ".bh-dialog-btn, .bh-color-primary"
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
            console.log("[TURBO] 0ms 极速拦截引擎已激活！");
        ''')
    except Exception:
        pass


def goto_page(driver, page_num):
    """极速切换到目标分页并等待渲染"""
    try:
        page_btns = driver.find_elements(
            By.XPATH,
            f"//a[text()='{page_num}'] | //li[text()='{page_num}'] | //span[text()='{page_num}']"
        )
        for b in page_btns:
            if b.is_displayed():
                driver.execute_script("arguments[0].click();", b)
                time.sleep(0.35)
                return True
    except Exception:
        pass
    return False


def refresh_page_exclusive(driver, page_target="2"):
    """
    【独占页刷新】：
    高频点击该页专属的刷新/重载入口：
    1. 查找分页栏的刷新图标按钮 (.ui-icon-refresh, [title*='刷新'])
    2. 重新点击当前页码按钮（如 '2'），触发深大系统 Ajax 重新拉取当前页最新数据，绝不跳回第 1 页！
    """
    try:
        res = driver.execute_script(f'''
            // 1. 查找分页器自带的局部刷新按钮 (不会重置页码)
            var pagerReload = document.querySelector(
                ".ui-icon-refresh, [id*='refresh_'], .ui-pg-button .fa-refresh, [title*='刷新']"
            );
            if (pagerReload && pagerReload.offsetWidth > 0) {{
                pagerReload.click();
                return "pager_refresh";
            }}

            // 2. 重新点击当前页码按钮（在 Wisedu 中直接刷新该页最新数据）
            var pageBtns = document.querySelectorAll("a, li, span");
            for (var i = 0; i < pageBtns.length; i++) {{
                var el = pageBtns[i];
                var txt = (el.innerText || el.textContent || "").trim();
                if (txt === "{page_target}") {{
                    el.click();
                    return "page_click_{page_target}";
                }}
            }}

            return "none";
        ''')
        return res
    except Exception:
        return "error"


def scan_and_rush_turbo(driver, already_selected_set):
    """
    【单元格级别精确容量分析与毫秒级秒抢】：
    - 针对每一个 <td> 独立匹配纯正容量 `^\\d+/\\d+$`；
    - 彻底杜绝与教室编号粘连；
    - 满额（20/20, 10/10）严格排除；
    - 发现未满额（如 400/223, 20/19, 19/20）：
      深入遍历整行所有标签，精准定位“选课”按钮并瞬间点击！
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

                // 【单元格级严格匹配容量】：遍历当前行的每一个 td 单元格
                var tds = row.querySelectorAll("td");
                var hasAvailableSeat = false;
                var realCap = "";

                for (var k = 0; k < tds.length; k++) {
                    var cellText = (tds[k].innerText || tds[k].textContent || "").trim();
                    // 严格匹配纯数字/纯数字格式
                    var m = cellText.match(/^(\\d+)\\s*\\/\\s*(\\d+)$/);
                    if (m) {
                        realCap = m[0];
                        var num1 = parseInt(m[1]);
                        var num2 = parseInt(m[2]);
                        // 核心判断：只有两数不相等，才是真正有名额！
                        if (num1 !== num2) {
                            hasAvailableSeat = true;
                        }
                        break;
                    }
                }

                // 真正检测到有名额！
                if (hasAvailableSeat) {
                    // 全行穿透遍历寻找真正的“选课”按钮
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
                        // 瞬间点击选课！
                        chooseBtn.click();
                        var title = text.split('\\n')[0].split('\\t')[0];
                        foundTargets.push({ name: title, cap: realCap });

                        // 同步触发确认弹窗点击（与 MutationObserver 形成双保险）
                        setTimeout(function() {
                            var cBtns = document.querySelectorAll(
                                "div.bh-dialog a, div.bh-dialog button, .bh-btn-primary, #cvDialog .cv-sure, .bh-dialog-btnContainer a, a, button"
                            );
                            for (var k = 0; k < cBtns.length; k++) {
                                var t = (cBtns[k].innerText || cBtns[k].textContent || "").trim();
                                if (t === "确定" || t === "确认") {
                                    cBtns[k].click();
                                    break;
                                }
                            }
                        }, 20);
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

        succ_msg = res.get("successMsg", "")
        if succ_msg:
            print(f"\n🎉🎉🎉【检测到系统成功提示！】: {succ_msg}\n")
            play_alert()
            driver.execute_script("window.__LAST_SUCCESS_MSG__ = '';")

        targets = res.get("targets", [])
        for t in targets:
            name = t["name"]
            cap = t["cap"]
            print(f"\n🚨 [{time.strftime('%H:%M:%S')}] 真正发现空位！【{name}】真实容量: {cap} -> 0ms 瞬间发起选课并确认！\n")
            play_alert()

        return len(targets)

    except Exception:
        return 0


if __name__ == "__main__":
    # 默认死盯第 2 页，命令行传 1 则盯第 1 页，传 3 则盯第 3 页
    page_target = "2"
    use_webvpn = False

    for arg in sys.argv[1:]:
        a = arg.strip().lower()
        if a in ('1', '2', '3'):
            page_target = a
        elif 'webvpn' in a:
            use_webvpn = True

    url = WEBVPN_URL if use_webvpn else TARGET_URL

    print("=" * 70)
    print(" 🚀 SZU 研究生选课【定页死盯·精准容量·极速刷新秒杀版】启动")
    print(f" 入口地址: {url}")
    print(f" 🎯 锁定目标: 【100% 专一死盯第 {page_target} 页】（绝不跳回第 1 页！）")
    print(f" 🔄 刷新策略: 单元格严格独立提取真实容量，高频刷新当前页，有空必秒选！")
    print(" ⚡ 极速能力: 全行穿透选课定位 + 0ms 原生 DOM 秒确认 + 10ms 满额秒关")
    print("=" * 70)

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

    # 直奔目标页面（例如第 2 页）
    print(f"📍 直奔目标页面: 切换并锁定在【第 {page_target} 页】...")
    goto_page(driver, page_target)
    time.sleep(0.5)

    # 注入浏览器 0ms 秒杀引擎
    inject_turbo_engine(driver)

    already_selected = set()
    round_count = 0

    print(f"🔥 全力开火！持续高频刷新死盯第 {page_target} 页，只要有名额立马秒抢！\n")

    while True:
        round_count += 1
        inject_turbo_engine(driver)

        # 1. 毫秒级精准扫描当前页（单元格独立提取），真正发现空额立马秒选
        hit_count = scan_and_rush_turbo(driver, already_selected)

        # 2. 刷新当前页（点击当前页码或分页器重载，绝不跳回第 1 页！）
        refresh_page_exclusive(driver, page_target)

        if round_count % 15 == 0:
            print(f"[{time.strftime('%H:%M:%S')}] 🔄 正在高频刷新死盯第 {page_target} 页 (第 {round_count} 轮, 满员全排除, 有空必秒抢)")

        # 3. 极速等待 0.2 秒
        time.sleep(0.2)
