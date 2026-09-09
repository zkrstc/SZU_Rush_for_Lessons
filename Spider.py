# -*- coding: utf-8 -*-
"""
深圳大学研究生选课极速抢课脚本 (SZU Graduate Student Course Rush)
针对金智教育研究生选课系统 (yjsxkapp) 定制

核心策略：
1. 【满员直接排除】：容量为 20/20、10/10、30/30 等满额课程 0 毫秒跳过，不发无效请求，不弹框；
2. 【有空位秒杀】：一旦检测到容量未满（如 19/20、400/277 或有人退课），毫秒级触发“选课”并秒点确认；
3. 【秒点确认框】：深度适配金智教育 bh-dialog 的 <a> 和 <button> 确认按钮，杜绝卡在“确定要选择吗”；
4. 【支持多进程独立盯页】：
     - 终端 1: python Spider.py 1  (只盯第 1 页，超高频刷新)
     - 终端 2: python Spider.py 2  (只盯第 2 页，超高频刷新)
     - 终端 3: python Spider.py 3  (只盯第 3 页，超高频刷新)
     - 或直接运行: python Spider.py (单进程全自动轮询全部页面)
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
    print('\a', end='', flush=True)


def check_capacity_available(row_text):
    """
    检查容量是否未满（容量满了直接排除）：
    返回: (is_available, capacity_str)
    """
    match = re.search(r'(\d+)\s*/\s*(\d+)', row_text)
    if match:
        a = int(match.group(1))
        b = int(match.group(2))
        cap_str = f"{a}/{b}"
        # 两数相等，说明已满员 (如 20/20, 10/10, 30/30)
        if a == b:
            return False, cap_str
        # 两数不等，说明有名额空缺 (如 19/20 或 400/277)
        return True, cap_str

    if '已满' in row_text or '满员' in row_text:
        return False, "已满"

    return True, "未知"


def goto_page(driver, page_num):
    """切换分页"""
    try:
        page_btns = driver.find_elements(
            By.XPATH,
            f"//a[text()='{page_num}'] | //li[text()='{page_num}'] | //span[text()='{page_num}']"
        )
        for b in page_btns:
            if b.is_displayed():
                driver.execute_script("arguments[0].click();", b)
                time.sleep(0.3)
                return True
    except Exception:
        pass
    return False


def refresh_current_grid(driver, page_target=None):
    """轻量刷新表格数据以获取最新容量"""
    try:
        search_btns = driver.find_elements(By.XPATH, "//button[contains(., '查询') or contains(., '搜索')]")
        if search_btns and search_btns[0].is_displayed():
            driver.execute_script("arguments[0].click();", search_btns[0])
            time.sleep(0.25)
            return True

        if page_target:
            goto_page(driver, str(page_target))
            return True
    except Exception:
        pass
    return False


def confirm_choose(driver):
    """
    极速秒点确认选课弹窗
    针对金智教育 (bh-dialog / cvDialog) 的 <a> 链接和 <button> 深度适配
    """
    # 1. 优先使用 JS 点击确定（支持 a 和 button）
    try:
        clicked = driver.execute_script('''
            // 金智常用弹窗按钮容器
            var targets = document.querySelectorAll(
                "div.bh-dialog a, div.bh-dialog button, div.bh-dialog-btnContainer a, div.bh-dialog-btnContainer button, " +
                ".bh-btn-primary, #cvDialog .cv-sure, #cvDialog .cvBtnFlag, .modal-footer button, .modal-footer a"
            );
            for (var b of targets) {
                var txt = (b.innerText || b.textContent || b.value || "").trim();
                if (txt.indexOf("确定") !== -1 || txt.indexOf("确认") !== -1 || txt.indexOf("是") !== -1) {
                    b.click();
                    return true;
                }
            }
            // 兜底：所有包含'确定'的按钮或链接
            var all = document.querySelectorAll("a.bh-btn, button.bh-btn, a, button");
            for (var b of all) {
                var txt = (b.innerText || b.textContent || b.value || "").trim();
                if (txt === "确定" || txt === "确认") {
                    b.click();
                    return true;
                }
            }
            return false;
        ''')
        if clicked:
            return True
    except Exception:
        pass

    # 2. Selenium XPath 兜底
    try:
        btns = driver.find_elements(
            By.XPATH,
            "//*[contains(@class, 'bh-dialog') or contains(@class, 'modal') or @id='cvDialog']"
            "//*[self::a or self::button or self::span][contains(text(), '确定') or contains(text(), '确认')]"
            " | //a[text()='确定' or text()='确认']"
            " | //button[text()='确定' or text()='确认']"
        )
        for b in btns:
            if b.is_displayed():
                driver.execute_script("arguments[0].click();", b)
                return True
    except Exception:
        pass
    return False


def close_dialogs(driver):
    """快速关闭提示弹窗/错误对话框"""
    try:
        driver.execute_script('''
            var btns = document.querySelectorAll(
                "#cvDialog .cvBtnFlag, #cvDialog button, .bh-dialog-btnContainer a, .bh-dialog-btnContainer button, .modal-footer button"
            );
            for (var b of btns) {
                var txt = (b.innerText || b.textContent || b.value || "").trim();
                if (txt.indexOf("知道了") !== -1 || txt.indexOf("关闭") !== -1 || txt.indexOf("确定") !== -1) {
                    if (b.offsetWidth > 0 && b.offsetHeight > 0) {
                        b.click();
                    }
                }
            }
        ''')
    except Exception:
        pass


def check_feedback(driver):
    """
    检测操作结果: 'success' | 'already' | 'fail' | 'none'
    若发现是二次确认框，自动点击确认！
    """
    # 1. 成功浮动提示 (bh-tip-success)
    success_tips = driver.find_elements(
        By.XPATH,
        "/html/body/div[contains(@class, 'bh-tip-success')]//div[@class='bh-tip-content']"
        " | //*[contains(@class, 'alert-success')]"
        " | //*[contains(@class, 'bh-tip') and contains(., '成功')]"
    )
    for st in success_tips:
        if st.is_displayed() and st.text:
            return 'success', st.text

    # 2. 对话框信息 (bh-dialog / cvDialog)
    dialog_bodies = driver.find_elements(
        By.XPATH,
        "//div[@id='cvDialog']//div[@class='cv-body']/div"
        " | //div[contains(@class, 'bh-dialog')]//div[contains(@class, 'content')]"
        " | //div[contains(@class, 'bh-dialog')]//div[contains(@class, 'bh-dialog-center')]"
        " | //div[contains(@class, 'modal-body')]"
    )
    for db in dialog_bodies:
        if db.is_displayed() and db.text:
            text = db.text.strip()
            # 如果是二次确认提示：“确定要选择吗？”，立刻点“确定”！
            if any(kw in text for kw in ['确定要选择', '确定选择', '是否确认', '确认选择']):
                print("  👉 检测到二次确认框，立即点击【确定】！")
                confirm_choose(driver)
                time.sleep(0.4)
                return check_feedback(driver)

            if '已经存在选课结果' in text or '已选' in text:
                return 'already', text
            if '成功' in text:
                return 'success', text
            return 'fail', text

    return 'none', ''


def scan_and_rush(driver, already_selected_set):
    """
    扫描当前表格中的课程：
    - 满额课程：0 耗时直接排除
    - 有空额课程：毫秒级发起抢课并自动确认
    """
    rows = driver.find_elements(By.XPATH, "//table//tr[td]")
    if not rows:
        return 0, 0

    checked_count = 0
    available_count = 0

    for row in rows:
        try:
            row_text = row.text.strip()
            if not row_text:
                continue

            # 课程名/课程代码
            parts = row_text.split('\n')[0].split('\t')
            course_name = parts[0].strip()

            if course_name in already_selected_set:
                continue

            if '退选' in row_text or '已选' in row_text:
                already_selected_set.add(course_name)
                print(f"✅ 该课程已在选课结果中: {course_name}")
                continue

            checked_count += 1

            # 【核心逻辑】：容量满直接排除！
            is_available, cap_str = check_capacity_available(row_text)
            if not is_available:
                continue

            # 发现未满课程！
            available_count += 1
            print(f"\n🚨 [{time.strftime('%H:%M:%S')}] 发现空位课程！【{course_name}】容量: {cap_str}，正在极速抢占...")

            btn_candidates = row.find_elements(
                By.XPATH,
                ".//button[contains(., '选课')] | .//a[contains(., '选课')] | .//span[contains(., '选课')]"
            )
            if not btn_candidates:
                continue

            btn = btn_candidates[0]
            # 极速点击“选课”按钮
            driver.execute_script("arguments[0].click();", btn)

            # 连续毫秒级尝试点击确认弹窗（应对动画延迟）
            for _ in range(3):
                time.sleep(0.15)
                if confirm_choose(driver):
                    break

            # 实验课单选兜底
            try:
                driver.execute_script('''
                    var r = document.querySelector("input[name='testCourse_radio_0']");
                    var b = document.getElementById("testCourse_choice_btn");
                    if (r) r.click();
                    if (b) b.click();
                ''')
            except Exception:
                pass

            time.sleep(0.4)
            res_type, msg = check_feedback(driver)

            if res_type in ('success', 'already'):
                print(f"🎉🎉🎉【抢课成功！】{course_name}！系统提示: {msg}\n")
                already_selected_set.add(course_name)
                play_alert()
            elif res_type == 'fail':
                print(f"  └ 提示: {msg}")
            close_dialogs(driver)

        except Exception:
            close_dialogs(driver)

    return checked_count, available_count


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

    print("=" * 65)
    print(" SZU 研究生选课【极速秒杀版】启动")
    print(f" 入口地址: {url}")
    if page_target:
        print(f" 🚀 多进程专属模式: 独占死盯【第 {page_target} 页】（超高频监控）")
    else:
        print(" 🚀 全自动模式: 轮询全部页面（容量满直接排除，有空位秒抢）")
    print("=" * 65)

    driver = webdriver.Chrome()
    driver.get(url)

    print('\n👉 请在弹出的浏览器中登录研究生选课系统...')

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
        time.sleep(1.5)

    already_selected = set()
    round_idx = 0

    if page_target:
        print(f"🔥 已锁定第 {page_target} 页，开始极速高频监听...\n")
        goto_page(driver, page_target)
        time.sleep(0.5)

        while True:
            round_idx += 1
            checked, avail = scan_and_rush(driver, already_selected)
            if round_idx % 10 == 0:
                print(f"[{time.strftime('%H:%M:%S')}] 第 {round_idx} 轮扫描完成 (第 {page_target} 页, 监控 {checked} 门课, 满员已全排除)")
            refresh_current_grid(driver, page_target)
            time.sleep(0.2)

    else:
        print("🔥 开始跨页扫描抢课（容量满直接跳过）...\n")
        while True:
            round_idx += 1
            # 扫描第 1 页
            scan_and_rush(driver, already_selected)

            # 切换第 2 页
            if goto_page(driver, '2'):
                scan_and_rush(driver, already_selected)

            # 切换第 3 页
            if goto_page(driver, '3'):
                scan_and_rush(driver, already_selected)

            # 回到第 1 页
            goto_page(driver, '1')

            if round_idx % 5 == 0:
                print(f"[{time.strftime('%H:%M:%S')}] 全页第 {round_idx} 轮扫描完成，持续监听中...")

            time.sleep(0.3)
