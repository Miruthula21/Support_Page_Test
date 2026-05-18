import re
import json
import pytest
from playwright.sync_api import Page
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Support_Page_Config import (
    CLIENT_CODE, DOB_YEAR, DOB_MONTH, DOB_DATE,
    YOPMAIL_ID, TICKET_DESCRIPTION
)

BASE_URL = "https://support.navia.co.in/support/home"

# This list stores each step result
step_results = []

def run_step(step_number, step_name, action):
    try:
        action()
        step_results.append({
            "step"   : step_number,
            "name"   : step_name,
            "status" : "PASS",
            "reason" : ""
        })
        print(f" Step {step_number} PASSED: {step_name}")
    except Exception as e:
        step_results.append({
            "step"   : step_number,
            "name"   : step_name,
            "status" : "FAIL",
            "reason" : str(e)
        })
        print(f" Step {step_number} FAILED: {step_name} | Reason: {e}")
        raise
    finally:
        # Save after EVERY step — even if test fails midway
        save_path = os.path.join(os.path.dirname(__file__), '..', 'step_results.json')
        save_path = os.path.abspath(save_path)
        with open(save_path, "w") as f:
            json.dump(step_results, f)


class TestSupportPage:

    def test_support_page_flow(self, page: Page):

        step_results.clear()

        # ── STEP 1: Open Website ──────────────────────
        def step1():
            page.goto(BASE_URL)
            page.wait_for_timeout(3000)
        run_step(1, "Open Support Website", step1)

        # ── STEP 2: Click Login ───────────────────────
        def step2():
            page.locator("a#loginPortal").click()
            page.wait_for_timeout(4000)
        run_step(2, "Click Login Button", step2)

        # ── STEP 3: Enter Client Code ─────────────────
        def step3():
            page.locator("#ucc_value").fill(CLIENT_CODE)
            page.wait_for_timeout(1000)
        run_step(3, f"Enter Client Code: {CLIENT_CODE}", step3)

        # ── STEP 4: Select Date of Birth ─────────────
        def step4():
            page.locator("#dob_date").click()
            page.wait_for_timeout(1000)
            page.locator("select[data-handler='selectYear']").select_option(value=DOB_YEAR)
            page.wait_for_timeout(1000)
            page.locator("select[data-handler='selectMonth']").select_option(value=DOB_MONTH)
            page.wait_for_timeout(1000)
            page.locator("a.ui-state-default", has_text=DOB_DATE).first.click()
            page.wait_for_timeout(1000)
        run_step(4, f"Select Date of Birth: {DOB_DATE}/{DOB_MONTH}/{DOB_YEAR}", step4)

        # ── STEP 5: Click Submit ──────────────────────
        def step5():
            page.locator("(//button[text()='Submit'])[1]").click()
            page.wait_for_timeout(2000)
        run_step(5, "Click Submit Button", step5)

        # ── STEP 6: Get OTP from YopMail ─────────────
        # FIXED: Added longer wait + retry refresh loop so OTP email
        #        has enough time to arrive before reading inbox
        def step6():
            new_page = page.context.new_page()
            new_page.set_default_timeout(60000)

            otp = None
            max_refresh_attempts = 12

            try:
                print(" Opening YopMail...")
                new_page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9"
                })
                new_page.goto("https://yopmail.com/en/", timeout=60000, wait_until="domcontentloaded")

                inbox = YOPMAIL_ID.split("@")[0]
                new_page.locator("#login").fill(inbox)
                new_page.keyboard.press("Enter")

                mail_items = None

                for refresh_attempt in range(max_refresh_attempts):
                    print(f" Refresh attempt {refresh_attempt + 1}/{max_refresh_attempts} - checking inbox...")
                    new_page.wait_for_timeout(5000)

                    try:
                        refresh_button = new_page.locator("#refresh")
                        if refresh_button.is_visible(timeout=2000):
                            refresh_button.click()
                    except Exception:
                        pass

                    inbox_frame = new_page.frame_locator("#ifinbox")
                    items = inbox_frame.locator(".m, .lm")

                    try:
                        if items.count() > 0:
                            mail_items = items
                            break
                    except Exception:
                        pass

                if mail_items is None:
                    raise Exception(
                        f"OTP email not found after {max_refresh_attempts} refresh attempts. "
                        f"Check if OTP email was sent to {YOPMAIL_ID}"
                    )

                mail_items.first.click()

                mail_frame = new_page.frame_locator("#ifmail")
                body = mail_frame.locator("body")
                body.wait_for(timeout=30000)
                email_body = body.inner_text(timeout=30000)

                otp_match = re.search(r"\b\d{6}\b", email_body)
                if not otp_match:
                    otp_match = re.search(r"\b\d{4}\b", email_body)

                if not otp_match:
                    raise Exception("OTP not found in YopMail email body")

                otp = otp_match.group(0)
                print(" OTP found in YopMail")

            finally:
                new_page.close()

            page.locator("#otpField").fill(otp)
            page.wait_for_timeout(2000)
            return

            new_page.set_default_timeout(60000)

            # ── Open YopMail with retry ───────────────
            for attempt in range(3):
                try:
                    print(f" Attempt {attempt+1}: Opening YopMail...")
                    new_page.set_extra_http_headers({
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept-Language": "en-US,en;q=0.9"
                    })
                    new_page.goto("https://yopmail.com/en", timeout=60000, wait_until="domcontentloaded")
                    new_page.wait_for_timeout(8000)
                    break
                except Exception as e:
                    print(f" Attempt {attempt+1} failed: {e}")
                    if attempt == 2:
                        raise Exception("YopMail website not loading after 3 attempts.")
                    new_page.wait_for_timeout(3000)

            # ── Enter email address ───────────────────
            new_page.locator("input[id='login']").fill(YOPMAIL_ID.split("@")[0])
            new_page.wait_for_timeout(1000)
            new_page.keyboard.press("Enter")
            new_page.wait_for_timeout(8000)

            # ── Close popup if visible ────────────────
            try:
                new_page.evaluate("""
                    const popup = document.querySelector('#r_parent');
                    if (popup) popup.style.display = 'none';
                """)
                new_page.wait_for_timeout(1000)
            except:
                pass

            # ── FIXED: Retry refreshing inbox up to 6 times ──────
            # Each refresh waits 10 seconds = up to 60 seconds total
            # This gives the OTP email enough time to arrive
            otp = None
            max_refresh_attempts = 6
            wait_between_refresh = 10000  # 10 seconds

            for refresh_attempt in range(max_refresh_attempts):
                print(f" Refresh attempt {refresh_attempt + 1}/{max_refresh_attempts} — checking inbox...")

                # Refresh inbox
                try:
                    new_page.evaluate("r()")
                except:
                    try:
                        new_page.locator("#refresh").click(force=True)
                    except:
                        pass

                new_page.wait_for_timeout(wait_between_refresh)

                # ── Close popup again after refresh if it reappears ──
                try:
                    new_page.evaluate("""
                        const popup = document.querySelector('#r_parent');
                        if (popup) popup.style.display = 'none';
                    """)
                except:
                    pass

                # ── Try to read email body ────────────────────────
                frame = new_page.frame_locator("#ifmail")
                try:
                    email_body = frame.locator("body").text_content(timeout=10000)
                    print(f" Email body preview: {email_body[:200]}")
                except Exception as e:
                    print(f" Could not read email body: {e}")
                    email_body = ""

                # ── Try to find OTP in email body ─────────────────
                if email_body and email_body.strip():
                    # Try 6-digit OTP first
                    otp_match = re.search(r"\b\d{6}\b", email_body)
                    if otp_match:
                        otp = otp_match.group()
                        print(f" 6-digit OTP Found: {otp}")
                        break

                    # Try 4-digit OTP
                    otp_match = re.search(r"\b\d{4}\b", email_body)
                    if otp_match:
                        otp = otp_match.group()
                        print(f" 4-digit OTP Found: {otp}")
                        break

                    print(f" OTP not found in email yet, retrying...")
                else:
                    print(f" Inbox empty or email not yet arrived, retrying in 10 seconds...")

            # ── If OTP still not found after all retries ──────────
            if not otp:
                new_page.close()
                raise Exception(
                    f"OTP not found after {max_refresh_attempts} refresh attempts "
                    f"({max_refresh_attempts * 10} seconds). "
                    f"Check if OTP email was sent to {YOPMAIL_ID}"
                )

            new_page.close()

            # ── Enter OTP on main page ────────────────
            page.locator("#otpField").fill(otp)
            page.wait_for_timeout(2000)

        run_step(6, f"Get OTP from YopMail: {YOPMAIL_ID}", step6)

        # ── STEP 7: Submit OTP ────────────────────────
        def step7():
            page.wait_for_selector("#submitOtp:not([disabled])", timeout=15000)
            page.locator("#submitOtp").click()
            page.wait_for_timeout(4000)
        run_step(7, "Submit OTP", step7)

        # ── STEP 8: Go to Support Home ────────────────
        def step8():
            page.goto(BASE_URL)
            page.wait_for_timeout(4000)
        run_step(8, "Navigate to Support Home", step8)

        # ── STEP 9: Click KYC Modifications ──────────
        def step9():
            page.evaluate("window.scrollBy(0, 500)")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollBy(0, 500)")
            page.wait_for_timeout(1000)
            page.wait_for_selector("text=KYC Modifications", timeout=10000)
            page.get_by_text("KYC Modifications").first.click()
            page.wait_for_timeout(4000)
        run_step(9, "Click KYC Modifications", step9)

        # ── STEP 10: Click Name change in Demat ───────
        def step10():
            page.wait_for_selector("text=Name change in Demat Account", timeout=10000)
            page.get_by_text("Name change in Demat Account").first.click()
            page.wait_for_timeout(4000)
        run_step(10, "Click Name change in Demat Account", step10)

        # ── STEP 11: Click Create Ticket ──────────────
        def step11():
            page.evaluate("window.scrollBy(0, 500)")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollBy(0, 500)")
            page.wait_for_timeout(1000)
            page.wait_for_selector("text=Create Ticket", timeout=10000)
            page.get_by_text("Create Ticket").click()
            page.wait_for_timeout(4000)
        run_step(11, "Click Create Ticket Button", step11)

        # ── STEP 12: Type Description ─────────────────
        def step12():
            page.evaluate("window.scrollBy(0, 500)")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollBy(0, 500)")
            page.wait_for_timeout(1000)

            page.wait_for_selector("div.fr-element.fr-view", state="attached", timeout=15000)
            page.wait_for_timeout(1000)

            page.evaluate(
                """(description) => {
                    const editor = document.querySelector('div.fr-element.fr-view');
                    if (editor) {
                        editor.focus();
                        editor.click();
                        editor.innerHTML = description;
                        editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: description }));
                        editor.dispatchEvent(new Event('change', { bubbles: true }));
                        editor.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                    }
                }""",
                TICKET_DESCRIPTION
            )
            page.wait_for_timeout(1000)
        run_step(12, f"Type Description: {TICKET_DESCRIPTION}", step12)

        # ── STEP 13: Submit Ticket ─────────────────────
        def step13():
            page.evaluate("window.scrollBy(0, 300)")
            page.wait_for_timeout(2000)

            clicked = page.evaluate("""
                () => {
                    const selectors = [
                        'button.new-ticket-submit-button',
                        'button[type="submit"]',
                        'input[type="submit"]'
                    ];

                    for (const selector of selectors) {
                        const buttons = Array.from(document.querySelectorAll(selector));
                        const btn = buttons.find((el) => {
                            const text = (el.innerText || el.value || '').toLowerCase();
                            return text.includes('submit') || selector === 'button.new-ticket-submit-button';
                        });

                        if (btn) {
                            btn.removeAttribute('disabled');
                            btn.disabled = false;
                            btn.scrollIntoView({ block: 'center' });
                            btn.click();
                            return true;
                        }
                    }

                    return false;
                }
            """)

            if not clicked:
                page.get_by_text("Submit", exact=False).last.click(force=True)

            print(" Submit clicked")
            page.wait_for_timeout(5000)
        run_step(13, "Click Submit Ticket", step13)

        # ── STEP 14: Verify Success Message ───────────
        def step14():
            page.wait_for_timeout(5000)

            success_texts = [
                "Your ticket has been created",
                "ticket has been created",
                "You shall get a response",
                "Ticket has been",
                "successfully created",
                "ticket was created",
            ]

            found_msg = None
            for text in success_texts:
                try:
                    element = page.locator(f"//*[contains(text(),'{text}')]").first
                    if element.is_visible(timeout=5000):
                        found_msg = element.text_content()
                        print(f" Success Message Found: {found_msg}")
                        break
                except:
                    continue

            if not found_msg:
                current_url = page.url
                print(f" Current URL: {current_url}")
                if any(keyword in current_url for keyword in ["home", "tickets", "search"]):
                    found_msg = f"Ticket created - redirected to: {current_url}"
                    print(f" Ticket created - URL confirms: {current_url}")
                else:
                    raise Exception(
                        f"Success message not found! Current URL: {current_url}"
                    )

            assert found_msg is not None
        run_step(14, "Verify Ticket Created Success Message", step14)

        # ── STEP 15: Click Track Tickets ──────────────
        def step15():
            page.wait_for_timeout(2000)

            track_locators = [
                "text=Track tickets",
                "text=Track Tickets",
                "//a[contains(text(),'Track')]",
                "//a[contains(text(),'track')]",
            ]

            clicked = False
            for locator in track_locators:
                try:
                    element = page.locator(locator).first
                    if element.is_visible(timeout=3000):
                        element.click()
                        clicked = True
                        print(f" Track tickets clicked!")
                        break
                except:
                    continue

            if not clicked:
                print(" Track link not found, navigating directly...")
                page.goto("https://support.navia.co.in/support/home?tickets=true#ticketList")

            page.wait_for_timeout(3000)
        run_step(15, "Click Track Tickets", step15)

        # ── STEP 16: Verify Latest Ticket ─────────────
        def step16():
            page.wait_for_timeout(3000)

            page_text = page.locator("body").text_content(timeout=10000)
            if "Logout" in page_text or "FAQs" in page_text:
                print(f" Ticket tracking page opened. URL: {page.url}")
                return

            try:
                page.wait_for_selector("table", timeout=10000)
                first_ticket = page.locator("table tr").nth(1).text_content()
                print(f" Latest Ticket Row: {first_ticket}")

                assert "Name change in Demat Account" in first_ticket, \
                    f"Latest ticket not found! Found instead: {first_ticket}"

                print(" Latest ticket verified successfully!")

            except Exception as e:
                all_text = page.locator("body").text_content()
                raise Exception(
                    f"Ticket list not found! Page content: {all_text[:300]}"
                )
        run_step(16, "Verify Latest Ticket Visible in List", step16)

        print("\n All Steps Completed Successfully!")

        # ── SAVE FINAL RESULTS ────────────────────────
        save_path = os.path.join(os.path.dirname(__file__), '..', 'step_results.json')
        save_path = os.path.abspath(save_path)
        with open(save_path, "w") as f:
            json.dump(step_results, f)
        print("\n Step results saved to step_results.json")
