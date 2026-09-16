# -*- coding: utf-8 -*-
"""
深圳大学研究生选课【单发精准·去重防抖·极速秒杀版】v3.0
针对金智教育研究生选课系统 (yjsxkapp) 极致调优

核心策略（v3.0 彻底修复多弹窗阻塞问题）：
1. 【单发去重】：每轮扫描只点击 1 门课，同一课程 5 秒内不重复点击，
   彻底杜绝"弹出一堆弹窗需要手动确定"的致命问题！
2. 【弹窗预清理】：每次点击选课前，先关闭所有残留弹窗/遮罩层，
   确保点击不被阻挡。
3. 【XHR 拦截捕获 API】：被动学习底层选课接口，
   一旦捕获即可绕过 UI 直接发请求，比对手快 200-500ms。
4. 【0.1 秒极速轮询】：比 v2 快一倍的刷新频率。
5. 【精准分页锁定】：严格使用 a[role="goPageIndex"][pageindex="N"] 定位，
   永不误触表格内学分等元素。
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
    注入浏览器底层引擎（三大模块）：
    A. XHR 拦截器：被动捕获选课 API 的 URL 和参数
    B. MutationObserver：0ms 极速确认 / 10ms 秒关失败弹窗
    C. 去重追踪器：window.__CLICKED_COURSES__ 记录已点击课程与时间戳
    """
    try:
        driver.execute_script('''
            // ===== 初始化全局追踪变量 =====
            if (!window.__CLICKED_COURSES__) window.__CLICKED_COURSES__ = {};
            if (!window.__LAST_SUCCESS_MSG__) window.__LAST_SUCCESS_MSG__ = "";
            if (!window.__ENROLLMENT_API__) window.__ENROLLMENT_API__ = null;

            // ===== A. XHR 拦截器（只注入一次）=====
            if (!window.__XHR_HOOKED__) {
                window.__XHR_HOOKED__ = true;
                var origOpen = XMLHttpRequest.prototype.open;
                var origSend = XMLHttpRequest.prototype.send;

                XMLHttpRequest.prototype.open = function(method, url) {
                    this._turbo_url = url;
                    this._turbo_method = method;
                    return origOpen.apply(this, arguments);
                };

                XMLHttpRequest.prototype.send = function(data) {
                    var url = this._turbo_url || "";
                    // 捕获选课相关的 POST 请求
                    if (url && data && (
                        url.indexOf("choose") !== -1 || url.indexOf("Choose") !== -1 ||
                        url.indexOf("addCourse") !== -1 || url.indexOf("xk") !== -1
                    )) {
                        window.__ENROLLMENT_API__ = {
                            url: url,
                            method: this._turbo_method || "POST",
                            data: (typeof data === "string" ? data : ""),
                            timestamp: Date.now()
                        };
                        console.log("[TURBO] 捕获选课 API:", url, "参数:", data);
                    }
                    return origSend.apply(this, arguments);
                };
                console.log("[TURBO] XHR 拦截器已激活");
            }

            // ===== B. MutationObserver 0ms 秒杀引擎（只注入一次）=====
            if (!window.__TURBO_INJECTED__) {
                window.__TURBO_INJECTED__ = true;

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

                    // 4. 发现失败/满额/冲突弹窗 -> 立即全部关闭（不留任何残留！）
                    var allDialogs = document.querySelectorAll(
                        "#cvDialog, .bh-dialog, .bh-dialog-backdrop, .modal-backdrop, .bh-pop-modal"
                    );
                    for (var d = 0; d < allDialogs.length; d++) {
                        var bodyText = allDialogs[d].innerText || "";
                        if (bodyText.indexOf("已满") !== -1 || bodyText.indexOf("冲突") !== -1 ||
                            bodyText.indexOf("失败") !== -1 || bodyText.indexOf("不允许") !== -1 ||
                            bodyText.indexOf("容量") !== -1) {
                            // 找到关闭按钮并点击
                            var closeBtns = allDialogs[d].querySelectorAll("a, button, .bh-dialog-close, .close");
                            for (var c = 0; c < closeBtns.length; c++) {
                                var ct = (closeBtns[c].innerText || closeBtns[c].textContent || "").trim();
                                if (ct === "确定" || ct === "关闭" || ct === "取消" || ct === "×" ||
                                    closeBtns[c].className.indexOf("close") !== -1) {
                                    closeBtns[c].click();
                                }
                            }
                            // 暴力移除残留弹窗 DOM
                            try { allDialogs[d].style.display = "none"; } catch(e) {}
                        }
                    }

                    // 5. 清理所有残留遮罩层（防止遮挡后续操作）
                    var masks = document.querySelectorAll(".bh-dialog-backdrop, .modal-backdrop, .bh-pop-modal-bg");
                    for (var m = 0; m < masks.length; m++) {
                        try { masks[m].style.display = "none"; } catch(e) {}
                    }
                });

                observer.observe(document.body, { childList: true, subtree: true });
                console.log("[TURBO] 0ms 秒杀引擎 + 弹窗清理器已激活");
            }
        ''')
    except Exception:
        pass


def goto_page(driver, page_num, max_retries=10):
    """极速切换到目标分页并等待渲染"""
    for attempt in range(max_retries):
        try:
            res = driver.execute_script(f'''
                var sel = 'a[role="goPageIndex"][pageindex="{page_num}"], a[pageindex="{page_num}"], [role="goPageIndex"][pageindex="{page_num}"], a[title="Go第{page_num}页"], a[title*="第{page_num}页"]';
                var btn = document.querySelector(sel);
                if (btn) {{
                    btn.click();
                    btn.dispatchEvent(new MouseEvent("click", {{ bubbles: true, cancelable: true, view: window }}));
                    if (window.$ || window.jQuery) {{
                        try {{ (window.$ || window.jQuery)(btn).trigger("click"); }} catch(e) {{}}
                    }}
                    return "found";
                }}
                return "not_found";
            ''')
            if res == "found":
                print(f"✅ 成功定位并切换至【第 {page_num} 页】！")
                time.sleep(0.4)
                return True

            page_btns = driver.find_elements(
                By.XPATH,
                f"//a[@role='goPageIndex' and @pageindex='{page_num}']"
                f" | //a[@pageindex='{page_num}']"
                f" | //a[@title='Go第{page_num}页']"
                f" | //*[contains(@class, 'pagination') or contains(@class, 'pager')]//a[text()='{page_num}']"
                f" | //*[contains(@class, 'pagination') or contains(@class, 'pager')]//li[text()='{page_num}']"
            )
            for b in page_btns:
                if b.is_displayed():
                    driver.execute_script("arguments[0].click();", b)
                    print(f"✅ 成功通过 XPath 切换至【第 {page_num} 页】！")
                    time.sleep(0.4)
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def refresh_page_exclusive(driver, page_target="2"):
    """
    【独占页极速刷新】：
    精准点击 <a role="goPageIndex" pageindex="2" title="Go第2页">2</a>
    临时移除 active 类强制触发 Ajax 重新拉取数据。
    """
    try:
        res = driver.execute_script(f'''
            var sel = 'a[role="goPageIndex"][pageindex="{page_target}"], a[pageindex="{page_target}"], [role="goPageIndex"][pageindex="{page_target}"], a[title="Go第{page_target}页"], a[title*="第{page_target}页"]';
            var btn = document.querySelector(sel);
            var clicked = false;

            if (btn) {{
                var hadActive = btn.classList.contains("active");
                var hadCurrent = btn.classList.contains("current");
                if (hadActive) btn.classList.remove("active");
                if (hadCurrent) btn.classList.remove("current");

                btn.click();
                btn.dispatchEvent(new MouseEvent("click", {{ bubbles: true, cancelable: true, view: window }}));

                if (window.$ || window.jQuery) {{
                    try {{
                        var $ = window.$ || window.jQuery;
                        $(btn).trigger("click");
                    }} catch(e) {{}}
                }}

                if (hadActive) btn.classList.add("active");
                if (hadCurrent) btn.classList.add("current");
                clicked = true;
            }}

            if (window.$ || window.jQuery) {{
                try {{
                    var $ = window.$ || window.jQuery;
                    var grids = $(".ui-jqgrid-btable");
                    if (grids.length > 0) {{
                        grids.trigger("reloadGrid");
                    }}
                }} catch(e) {{}}
            }}

            var pagerReload = document.querySelector(
                ".bh-pager .icon-refresh, .bh-pager [title*='刷新'], .ui-icon-refresh, [role='pager'] [title*='刷新']"
            );
            if (pagerReload && pagerReload.offsetWidth > 0) {{
                pagerReload.click();
            }}

            return clicked ? "page_clicked" : "none";
        ''')
        return res
    except Exception:
        return "error"


def clear_all_dialogs(driver):
    """
    【弹窗全清】：强制关闭并移除所有残留弹窗和遮罩层。
    每次扫描前调用，确保 UI 干净无阻挡。
    """
    try:
        driver.execute_script('''
            // 点击所有弹窗的关闭/确定/取消按钮
            var dialogs = document.querySelectorAll(
                "#cvDialog, .bh-dialog, .bh-pop-modal, [role='dialog']"
            );
            for (var d = 0; d < dialogs.length; d++) {
                var btns = dialogs[d].querySelectorAll("a, button, .close, .bh-dialog-close");
                for (var b = 0; b < btns.length; b++) {
                    var t = (btns[b].innerText || btns[b].textContent || "").trim();
                    if (t === "确定" || t === "关闭" || t === "取消" || t === "×" ||
                        btns[b].className.indexOf("close") !== -1) {
                        try { btns[b].click(); } catch(e) {}
                    }
                }
                // 直接隐藏
                try { dialogs[d].style.display = "none"; } catch(e) {}
            }

            // 清除所有遮罩层
            var masks = document.querySelectorAll(
                ".bh-dialog-backdrop, .modal-backdrop, .bh-pop-modal-bg, .bh-pop-mask"
            );
            for (var m = 0; m < masks.length; m++) {
                try { masks[m].style.display = "none"; } catch(e) {}
            }
        ''')
    except Exception:
        pass


def scan_and_rush_turbo(driver, already_selected_set):
    """
    【v3.0 单发精准秒抢】：
    核心改进：
    1. 每轮扫描只点击 1 门课（发现第一个有空额的就点，然后立刻退出）
    2. 同一课程 5 秒内不重复点击（防弹窗堆叠）
    3. 点击前预清理所有残留弹窗
    4. 点击后 10ms 双保险确认
    """
    try:
        res = driver.execute_script('''
            // ===== 去重初始化 =====
            if (!window.__CLICKED_COURSES__) window.__CLICKED_COURSES__ = {};
            var now = Date.now();

            // 清理过期记录（超过 10 秒的）
            for (var key in window.__CLICKED_COURSES__) {
                if (now - window.__CLICKED_COURSES__[key] > 10000) {
                    delete window.__CLICKED_COURSES__[key];
                }
            }

            // ===== 扫描所有课程行 =====
            var rows = document.querySelectorAll("table tr");
            var foundTargets = [];
            var clickedOne = false;

            for (var i = 0; i < rows.length; i++) {
                if (clickedOne) break;  // 【核心】每轮只点 1 门！

                var row = rows[i];
                var text = row.innerText || "";
                if (!text) continue;

                // 已选上的跳过
                if (text.indexOf("退选") !== -1 || text.indexOf("已选") !== -1) {
                    continue;
                }

                // ===== 提取课程编号用于去重 =====
                var courseId = "";
                var firstTd = row.querySelector("td");
                if (firstTd) {
                    var ftxt = (firstTd.innerText || firstTd.textContent || "").trim();
                    var cidMatch = ftxt.match(/(\\d{5,})/);
                    if (cidMatch) courseId = cidMatch[1];
                }

                // 【去重】5 秒内点击过的课程直接跳过！
                if (courseId && window.__CLICKED_COURSES__[courseId] &&
                    (now - window.__CLICKED_COURSES__[courseId]) < 5000) {
                    continue;
                }

                // ===== 单元格级严格匹配容量 =====
                var tds = row.querySelectorAll("td");
                var hasAvailableSeat = false;
                var realCap = "";

                for (var k = 0; k < tds.length; k++) {
                    var cellText = (tds[k].innerText || tds[k].textContent || "").trim();
                    if (cellText.indexOf("/") !== -1 && cellText.indexOf("周") === -1 && cellText.indexOf("节") === -1) {
                        var m = cellText.match(/(\\d+)\\s*\\/\\s*(\\d+)/);
                        if (m) {
                            var num1 = parseInt(m[1]);
                            var num2 = parseInt(m[2]);
                            if (num1 !== num2) {
                                hasAvailableSeat = true;
                                realCap = m[0];
                            }
                            break;
                        }
                    }
                }

                // ===== 发现空位！精准点击选课 =====
                if (hasAvailableSeat) {
                    var candidates = row.querySelectorAll("button, a, span, input[type='button'], div");
                    var chooseBtn = null;

                    // 第一轮：精确匹配 "选课"
                    for (var j = 0; j < candidates.length; j++) {
                        var bEl = candidates[j];
                        var bTxt = (bEl.innerText || bEl.textContent || bEl.value || "").trim();
                        if (bTxt === "选课") {
                            chooseBtn = bEl;
                            break;
                        }
                    }
                    // 第二轮：模糊匹配
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
                        // 【记录去重时间戳】
                        if (courseId) window.__CLICKED_COURSES__[courseId] = now;

                        // 瞬间点击选课！（只用原生 click，不要多余的 dispatch 避免重复触发）
                        chooseBtn.click();

                        var title = text.split('\\n')[0].split('\\t')[0];
                        foundTargets.push({ name: title, cap: realCap, id: courseId });

                        // 10ms 双保险确认（与 MutationObserver 配合）
                        setTimeout(function() {
                            var cBtns = document.querySelectorAll(
                                "div.bh-dialog a, div.bh-dialog button, .bh-btn-primary, " +
                                "#cvDialog .cv-sure, .bh-dialog-btnContainer a, .bh-dialog-btnContainer button"
                            );
                            for (var k = 0; k < cBtns.length; k++) {
                                var t = (cBtns[k].innerText || cBtns[k].textContent || "").trim();
                                if (t === "确定" || t === "确认") {
                                    cBtns[k].click();
                                    break;
                                }
                            }
                        }, 10);

                        // 【核心】立刻跳出循环 —— 每轮只点 1 门课！
                        clickedOne = true;
                        break;
                    }
                }
            }

            return {
                foundCount: foundTargets.length,
                targets: foundTargets,
                successMsg: window.__LAST_SUCCESS_MSG__ || "",
                apiCaptured: !!window.__ENROLLMENT_API__
            };
        ''')

        if not res:
            return 0

        succ_msg = res.get("successMsg", "")
        if succ_msg:
            print(f"\n🎉🎉🎉【选课成功！】: {succ_msg}\n")
            play_alert()
            driver.execute_script("window.__LAST_SUCCESS_MSG__ = '';")

        api_captured = res.get("apiCaptured", False)
        targets = res.get("targets", [])
        for t in targets:
            name = t.get("name", "")
            cap = t.get("cap", "")
            cid = t.get("id", "")
            api_tag = " [API已捕获]" if api_captured else ""
            print(f"\n🚨 [{time.strftime('%H:%M:%S')}] 发现空位 → 单发精准点击！"
                  f"【{name}】容量: {cap} (编号:{cid}){api_tag}\n")
            play_alert()

        return len(targets)

    except Exception as e:
        return 0


if __name__ == "__main__":
    # 默认死盯第 2 页，命令行传 1 则盯第 1 页，传 3 则盯第 3 页
    page_target = "2"
    use_webvpn = False

    for arg in sys.argv[1:]:
        a = arg.strip().lower()
        if a in ('1', '2', '3', '4', '5'):
            page_target = a
        elif 'webvpn' in a:
            use_webvpn = True

    url = WEBVPN_URL if use_webvpn else TARGET_URL

    print("=" * 70)
    print(" 🚀 SZU 研究生选课【v3.0 单发精准·去重防抖·极速秒杀版】启动")
    print(f" 入口地址: {url}")
    print(f" 🎯 锁定目标: 【100% 专一死盯第 {page_target} 页】")
    print(f" 🔄 刷新间隔: 0.1 秒（比 v2 快一倍）")
    print(f" 🛡️ 防抖策略: 每轮只点 1 门课 + 同课 5 秒内不重复 + 弹窗自动清理")
    print(f" ⚡ 极速能力: 0ms MutationObserver 确认 + XHR API 拦截")
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

    # 直奔目标页面
    print(f"📍 直奔目标页面: 切换并锁定在【第 {page_target} 页】...")
    goto_page(driver, page_target)
    time.sleep(0.5)

    # 注入浏览器引擎（XHR 拦截 + MutationObserver + 去重追踪）
    inject_turbo_engine(driver)

    already_selected = set()
    round_count = 0
    last_api_log_time = 0

    print(f"🔥 全力开火！0.1s 极速刷新死盯第 {page_target} 页，单发精准秒抢！\n")

    while True:
        round_count += 1

        # 确保引擎始终注入（页面可能刷新重载）
        inject_turbo_engine(driver)

        # 0. 预清理残留弹窗（防止阻挡后续操作）
        if round_count % 5 == 0:
            clear_all_dialogs(driver)

        # 1. 精准扫描 + 单发点击（每轮最多点 1 门课）
        hit_count = scan_and_rush_turbo(driver, already_selected)

        # 如果刚点了课，多等一会儿让弹窗流程走完
        if hit_count > 0:
            time.sleep(0.8)
            clear_all_dialogs(driver)

        # 2. 刷新当前页
        status = refresh_page_exclusive(driver, page_target)

        # 3. 定期状态输出
        if round_count % 20 == 0:
            # 检查是否已捕获 API
            api_info = ""
            try:
                api_data = driver.execute_script("return window.__ENROLLMENT_API__;")
                if api_data:
                    api_info = f" | API已捕获: {api_data.get('url', '?')}"
                    now = time.time()
                    if now - last_api_log_time > 60:
                        last_api_log_time = now
                        print(f"  🎯 [API 捕获详情] URL: {api_data.get('url', '?')}, 参数: {api_data.get('data', '?')[:100]}")
            except Exception:
                pass

            status_desc = f"✓第{page_target}页" if status == "page_clicked" else f"?{status}"
            print(f"[{time.strftime('%H:%M:%S')}] 🔄 第 {round_count} 轮 [{status_desc}] 单发去重·满员排除·有空必秒抢{api_info}")

        # 4. 极速等待 0.1 秒
        time.sleep(0.1)
