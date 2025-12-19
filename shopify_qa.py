#!/usr/bin/env python3
"""
Seat Cover Solutions - QA Automation (Ready to Paste)

Fixes implemented:
1) Step 1/3 -> Step 2/3:
   - Click "Select Seat Options"
   - If Step 2 doesn't appear, auto-select required Vehicle fields (Trim + Cab) then retry
2) Step 2/3 -> Step 3/3:
   - Click "Select Color Options"
3) More robust seat selection:
   - Avoid hardcoded input IDs
4) Best-effort overlay/chat dismissal to prevent blocked clicks

Usage:
  python shopify_qa.py <url1> [url2] ...
  OR create urls.txt with one URL per line
"""

import asyncio
import json
import os
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright


class SeatCoverQA:
    def __init__(self):
        self.screenshot_dir = Path("./qa-screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        self.issues = []
        self.screenshot_counter = 0
        self.performance_data = []

    # ----------------------------
    # Utility: overlays / popups
    # ----------------------------
    async def dismiss_overlays(self, page):
        """Best-effort dismissal of popups/widgets that may intercept clicks."""
        close_selectors = [
            'button[aria-label="Close"]',
            'button[aria-label="close"]',
            'button:has-text("Close")',
            'button:has-text("CLOSE")',
            'button:has-text("×")',
            'button:has-text("✕")',
            '[role="dialog"] button[aria-label="Close"]',
            '[role="dialog"] button:has-text("Close")',
        ]

        for sel in close_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click(force=True, timeout=2000)
                    await page.wait_for_timeout(600)
            except:
                pass

        # Hide common chat widgets (best-effort)
        try:
            await page.evaluate(
                """() => {
                    const selectors = [
                      'iframe[src*="tawk"]',
                      'iframe[src*="intercom"]',
                      'iframe[src*="crisp"]',
                      'iframe[src*="zendesk"]',
                      'iframe[title*="chat"]',
                      'iframe[title*="Chat"]',
                      'div[id*="chat"]',
                      'div[class*="chat"]'
                    ];
                    for (const sel of selectors) {
                      document.querySelectorAll(sel).forEach(el => {
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                      });
                    }
                }"""
            )
        except:
            pass

    # ----------------------------
    # Utility: click helper
    # ----------------------------
    async def click_first_working(self, page, selectors, label, screenshot_prefix, url, device, highlight_js=None):
        """Try selectors in order; click the first visible one."""
        for selector in selectors:
            try:
                print(f"  🔍 Trying selector: {selector}")
                el = await page.wait_for_selector(selector, timeout=8000)
                if not el:
                    continue
                if not await el.is_visible():
                    continue

                await el.scroll_into_view_if_needed()
                await page.wait_for_timeout(800)

                if highlight_js:
                    try:
                        await page.evaluate(highlight_js, el)
                        await page.wait_for_timeout(700)
                    except:
                        pass

                await self.take_screenshot(
                    page, url, device, f"{screenshot_prefix}_highlighted",
                    f"{label} highlighted (selector: {selector})"
                )

                print(f"  ✓ Found with selector: {selector}")
                print("  🖱️  Clicking...")
                await el.click(force=True, timeout=5000)
                await page.wait_for_timeout(2500)
                return True, selector
            except Exception as e:
                print(f"     ❌ Failed: {str(e)[:140]}")
                continue

        return False, None

    # ----------------------------
    # Step 1 helpers: dropdowns
    # ----------------------------
    async def _select_first_valid_option(self, page, select_locator, placeholder_texts=None):
        """
        Select the first non-placeholder option from a native <select>.
        Returns True if selection is set/confirmed.
        """
        placeholder_texts = placeholder_texts or ["trim", "select", "choose", "option"]

        try:
            sel = page.locator(select_locator).first
            if await sel.count() == 0:
                return False

            current_value = await sel.input_value()

            options = await sel.locator("option").all()
            for opt in options:
                val = (await opt.get_attribute("value")) or ""
                label = (await opt.text_content()) or ""
                norm_label = label.strip().lower()
                norm_val = val.strip().lower()

                # skip placeholders / empty
                if not val.strip():
                    continue
                if any(t in norm_label for t in placeholder_texts):
                    continue
                if any(t in norm_val for t in placeholder_texts):
                    continue

                # already selected? good
                if current_value.strip() == val.strip():
                    return True

                await sel.select_option(val)
                await page.wait_for_timeout(1200)
                return True
        except:
            return False

        return False

    async def ensure_vehicle_details_completed(self, page, url, device):
        """
        Some pages require selecting Trim + Cab size to enable "Select Seat Options".
        Best-effort for native <select> dropdowns.
        """
        await self.dismiss_overlays(page)

        trim_selectors = [
            'select:has(option:has-text("Trim"))',
            'select[name*="trim" i]',
            'select[id*="trim" i]',
            'select[aria-label*="trim" i]',
        ]

        cab_selectors = [
            'select:has(option:has-text("Cab"))',
            'select[name*="cab" i]',
            'select[id*="cab" i]',
            'select[aria-label*="cab" i]',
        ]

        changed_any = False

        # Trim
        for s in trim_selectors:
            changed = await self._select_first_valid_option(page, s, placeholder_texts=["trim", "select", "choose"])
            if changed:
                print("  ✓ Vehicle details: Trim selected (best-effort)")
                changed_any = True
                await self.take_screenshot(page, url, device, "03b_trim_selected", "Selected Trim (best-effort)")
                break

        # Cab size
        for s in cab_selectors:
            changed = await self._select_first_valid_option(page, s, placeholder_texts=["cab", "select", "choose"])
            if changed:
                print("  ✓ Vehicle details: Cab size selected (best-effort)")
                changed_any = True
                await self.take_screenshot(page, url, device, "03c_cab_selected", "Selected Cab size (best-effort)")
                break

        if changed_any:
            await page.wait_for_timeout(2000)
            await self.dismiss_overlays(page)

        return changed_any

    async def ensure_step2_seat_type(self, page, url, device):
        """
        Ensure we're on Step 2/3 (Seat Type).
        Attempt:
          1) Click "Select Seat Options"
          2) If Step 2 not reached, select Trim/Cab and retry
        """
        await self.dismiss_overlays(page)

        # If Step 2 already visible
        try:
            if (await page.query_selector('text="Step 2/3"') or
                await page.query_selector('text=Seat Type') or
                await page.query_selector('input[name="Seats[]"]')):
                print("  ✓ Already on Step 2/3 (Seat Type)")
                return True
        except:
            pass

        async def click_select_seat_options():
            seat_options_cta = [
                'button:has-text("Select Seat Options")',
                'a:has-text("Select Seat Options")',
                'text=Select Seat Options',
                'button:has-text("Select seat options")',
                'a:has-text("Select seat options")',
            ]
            highlight_js = """(el) => {
                el.style.outline = '5px solid #009688';
                el.style.outlineOffset = '3px';
                el.style.backgroundColor = 'rgba(0,150,136,0.12)';
            }"""
            clicked, _ = await self.click_first_working(
                page, seat_options_cta, "Select Seat Options", "03_select_seat_options",
                url, device, highlight_js=highlight_js
            )
            return clicked

        print("\n[STEP 3.5] ➡️ Moving from Step 1/3 to Step 2/3...")

        # Attempt 1
        clicked = await click_select_seat_options()
        if clicked:
            await self.dismiss_overlays(page)
            for s in ['text="Step 2/3"', 'text=Seat Type', 'input[name="Seats[]"]']:
                try:
                    await page.wait_for_selector(s, timeout=12000)
                    print(f"  ✓ Step 2/3 detected via: {s}")
                    return True
                except:
                    continue

        # Attempt 2: Fill Trim/Cab then retry
        print("  ⚠️ Step 2 not reached. Trying to select required fields (Trim/Cab) then retry...")
        await self.ensure_vehicle_details_completed(page, url, device)

        clicked = await click_select_seat_options()
        if clicked:
            await self.dismiss_overlays(page)
            for s in ['text="Step 2/3"', 'text=Seat Type', 'input[name="Seats[]"]']:
                try:
                    await page.wait_for_selector(s, timeout=15000)
                    print(f"  ✓ Step 2/3 detected via: {s}")
                    return True
                except:
                    continue

        # Fail
        await self.take_screenshot(page, url, device, "03_ERROR_step2_not_reached",
                                  'ERROR: Could not reach Step 2/3 (Seat Type) even after Trim/Cab selection')
        await self.log_issue({
            'url': url, 'device': device, 'severity': 'critical',
            'category': 'Step 2 Not Reached',
            'issue': 'Could not advance to Step 2/3. "Select Seat Options" likely disabled due to required vehicle fields.',
            'screenshot': f"{self.screenshot_counter:04d}",
            'timestamp': datetime.now().isoformat()
        })
        return False

    # ----------------------------
    # Main test flow
    # ----------------------------
    async def test_url(self, url, device="desktop"):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )

            if device == "mobile":
                context = await browser.new_context(
                    viewport={"width": 375, "height": 812},
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
                    is_mobile=True,
                    has_touch=True,
                    locale="en-US",
                    timezone_id="America/New_York"
                )
            else:
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    locale="en-US",
                    timezone_id="America/New_York"
                )

            page = await context.new_page()

            try:
                print(f"\n{'='*80}")
                print(f"🔍 TESTING: {url}")
                print(f"Device: {device.upper()}")
                print(f"{'='*80}")

                # STEP 1: Load
                print("\n[STEP 1] 📄 Loading page...")
                start_time = time.time()

                response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")

                print("  ⏱️  Waiting for network idle...")
                try:
                    await page.wait_for_load_state("networkidle", timeout=60000)
                    print("  ✓ Network idle reached")
                except:
                    print("  ⚠️  Network didn't fully idle (some resources still loading)")

                load_time = time.time() - start_time
                print(f"  ✓ Page loaded in {load_time:.2f}s | HTTP {response.status}")

                print("  ⏱️  Waiting 5 seconds for render...")
                await page.wait_for_timeout(5000)
                await self.dismiss_overlays(page)

                await self.take_screenshot(page, url, device, "01_initial_page_load", "Initial page after loading")

                # STEP 2: Scroll sections
                print("\n[STEP 2] 📸 Capturing page sections...")
                await self.capture_page_sections(page, url, device)

                # STEP 3: Images
                print("\n[STEP 3] 🖼️ Checking images...")
                await self.check_images(page, url, device)

                # Back to top before interactions
                await page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
                await page.wait_for_timeout(2000)
                await page.wait_for_timeout(2000)
                await self.dismiss_overlays(page)

                # Ensure Step 2 is available (Step 1->2) with Trim/Cab fallback
                await self.ensure_step2_seat_type(page, url, device)

                # STEP 4: Seat selection
                print("\n[STEP 4] 🎯 Selecting 'Front & Rear Seats'...")
                await self.take_screenshot(page, url, device, "04_before_seat_selection", "Before selecting seat option")
                await self.dismiss_overlays(page)

                seat_selectors = [
                    'label:has-text("Front & Rear Seats")',
                    'text=Front & Rear Seats',
                    'input[name="Seats[]"][value="Bundle"]',
                    'input[value="Bundle"]',
                ]
                seat_highlight_js = """(el) => {
                    const container = el.closest('label') || el.closest('div') || el;
                    container.style.outline = '5px solid red';
                    container.style.outlineOffset = '3px';
                    container.style.backgroundColor = 'rgba(255,0,0,0.10)';
                }"""

                seat_clicked, _ = await self.click_first_working(
                    page, seat_selectors, "Front & Rear Seats", "04a_seat_option",
                    url, device, highlight_js=seat_highlight_js
                )

                if not seat_clicked:
                    await self.take_screenshot(page, url, device, "04_ERROR_seat_not_clicked", "ERROR: Seat selection failed")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'critical',
                        'category': 'Seat Selection Failed',
                        'issue': 'Could not click Front & Rear Seats option (Step 2/3)',
                        'screenshot': f"{self.screenshot_counter:04d}",
                        'timestamp': datetime.now().isoformat()
                    })

                await page.wait_for_timeout(1500)

                # STEP 4.5: Select Color Options (Step 2->3)
                print("\n[STEP 4.5] ➡️ Clicking 'Select Color Options' (Step 2 -> Step 3)...")
                await self.dismiss_overlays(page)

                continue_selectors = [
                    'button:has-text("Select Color Options")',
                    'a:has-text("Select Color Options")',
                    'text=Select Color Options',
                    'button:has-text("Select color options")',
                    'a:has-text("Select color options")',
                ]
                continue_highlight_js = """(el) => {
                    el.style.outline = '5px solid blue';
                    el.style.outlineOffset = '3px';
                    el.style.backgroundColor = 'rgba(0,0,255,0.10)';
                }"""

                continued, _ = await self.click_first_working(
                    page, continue_selectors, "Select Color Options", "04c_select_color_options",
                    url, device, highlight_js=continue_highlight_js
                )

                if not continued:
                    await self.take_screenshot(page, url, device, "04c_ERROR_continue_not_clicked",
                                              "WARNING: Could not click Select Color Options")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'high',
                        'category': 'Step Progression',
                        'issue': 'Could not click Select Color Options; Step 3 may not appear',
                        'screenshot': f"{self.screenshot_counter:04d}",
                        'timestamp': datetime.now().isoformat()
                    })

                # STEP 5: Wait for Step 3
                print("\n[STEP 5] 🎨 Waiting for Step 3 (Color Details)...")
                await self.dismiss_overlays(page)

                step3_found = False
                for s in ['text="Step 3/3"', 'text=Color', 'input[name="Color"]', 'label[for^="default-color-"]']:
                    try:
                        await page.wait_for_selector(s, timeout=15000)
                        print(f"  ✓ Step 3 detected via: {s}")
                        step3_found = True
                        break
                    except:
                        continue

                await self.take_screenshot(page, url, device, "05_step3_color_section",
                                          "Step 3/3 - Color section (or current state)")

                # STEP 6: Select color
                print("\n[STEP 6] ⚫ Selecting a color...")
                await self.dismiss_overlays(page)

                color_selectors = [
                    'label[for^="default-color-"]:has-text("Wine")',
                    'label:has-text("Wine Red")',
                    'label:has-text("Black")',
                    'input[name="Color"]',
                ]
                color_highlight_js = """(el) => {
                    const container = el.closest('label') || el.closest('div') || el;
                    container.style.outline = '5px solid green';
                    container.style.outlineOffset = '3px';
                    container.style.backgroundColor = 'rgba(0,255,0,0.10)';
                }"""

                await self.click_first_working(
                    page, color_selectors, "Color Option", "06a_color_option",
                    url, device, highlight_js=color_highlight_js
                )

                await self.take_screenshot(page, url, device, "06b_color_selected", "After selecting (or verifying) color")

                # STEP 7: Add to cart
                print("\n[STEP 7] 🛒 Looking for Add to Cart...")
                await page.wait_for_timeout(2000)
                await self.dismiss_overlays(page)

                await self.take_screenshot(page, url, device, "07_before_add_to_cart", "Before clicking Add to Cart")

                add_to_cart_selectors = [
                    'button:has-text("Add to Cart")',
                    'button:has-text("ADD TO CART")',
                    'button[name="add"]',
                    'form[action*="/cart/add"] button',
                    'button[type="submit"]:has-text("Add")',
                ]

                cart_added = False
                for selector in add_to_cart_selectors:
                    try:
                        add_button = await page.wait_for_selector(selector, timeout=8000)
                        if add_button and await add_button.is_visible():
                            if await add_button.is_disabled():
                                continue
                            await add_button.scroll_into_view_if_needed()
                            await page.wait_for_timeout(800)
                            await self.dismiss_overlays(page)

                            await page.evaluate("""(el) => {
                                el.style.outline = '5px solid orange';
                                el.style.outlineOffset = '3px';
                                el.style.backgroundColor = 'rgba(255,165,0,0.10)';
                            }""", add_button)

                            await self.take_screenshot(page, url, device, "07a_add_cart_highlighted",
                                                      f"Add to Cart highlighted (selector: {selector})")

                            await add_button.click(force=True)
                            await page.wait_for_timeout(4500)

                            await self.take_screenshot(page, url, device, "07b_after_add_to_cart",
                                                      "After Add to Cart - checking for cart drawer")
                            cart_added = True
                            print("  ✓ Added to cart")
                            break
                    except:
                        continue

                if not cart_added:
                    await self.take_screenshot(page, url, device, "07_ERROR_add_cart_failed", "ERROR: Add to cart failed")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'critical',
                        'category': 'Add to Cart Failed',
                        'issue': 'Could not find or click Add to Cart button',
                        'screenshot': f"{self.screenshot_counter:04d}",
                        'timestamp': datetime.now().isoformat()
                    })

                # STEP 8: Checkout
                print("\n[STEP 8] 💳 Looking for checkout button...")
                await page.wait_for_timeout(2500)
                await self.dismiss_overlays(page)

                checkout_selectors = [
                    'button:has-text("Checkout")',
                    'a:has-text("Checkout")',
                    'a[href*="/checkout"]',
                    '.cart-drawer button:has-text("Checkout")',
                    '.cart-popup a:has-text("Checkout")',
                ]

                checkout_found = False
                for selector in checkout_selectors:
                    try:
                        checkout_btn = await page.wait_for_selector(selector, timeout=8000)
                        if checkout_btn and await checkout_btn.is_visible():
                            await checkout_btn.scroll_into_view_if_needed()
                            await page.wait_for_timeout(800)
                            await self.dismiss_overlays(page)

                            await page.evaluate("""(el) => {
                                el.style.outline = '5px solid purple';
                                el.style.outlineOffset = '3px';
                                el.style.backgroundColor = 'rgba(128,0,128,0.10)';
                            }""", checkout_btn)

                            await self.take_screenshot(page, url, device, "08a_checkout_button_highlighted",
                                                      f"Checkout highlighted (selector: {selector})")

                            await checkout_btn.click(force=True)
                            try:
                                await page.wait_for_load_state("networkidle", timeout=20000)
                            except:
                                pass

                            await page.wait_for_timeout(6000)
                            await self.take_screenshot(page, url, device, "08b_checkout_page_loaded", "Checkout page loaded")
                            checkout_found = True
                            break
                    except:
                        continue

                if not checkout_found:
                    await self.take_screenshot(page, url, device, "08_ERROR_checkout_not_found", "ERROR: Checkout not found")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'critical',
                        'category': 'Checkout Not Found',
                        'issue': 'Could not find checkout button in cart',
                        'screenshot': f"{self.screenshot_counter:04d}",
                        'timestamp': datetime.now().isoformat()
                    })

                await self.take_screenshot(page, url, device, "09_final_page_state", "Final page state")

                print(f"\n{'='*80}")
                print(f"✓ Completed testing {url} ({device}) | Screenshots: {self.screenshot_counter}")
                print(f"{'='*80}")

            except Exception as e:
                print(f"\n{'='*80}")
                print(f"✗ FATAL ERROR: {str(e)}")
                print(f"{'='*80}")

                await self.take_screenshot(page, url, device, "ERROR_test_crashed", f"Test crashed: {str(e)}")
                await self.log_issue({
                    'url': url, 'device': device, 'severity': 'critical',
                    'category': 'Test Crashed',
                    'issue': f"Test failed with exception: {str(e)}",
                    'screenshot': f"{self.screenshot_counter:04d}",
                    'timestamp': datetime.now().isoformat()
                })

            await browser.close()

    # ----------------------------
    # Reporting / screenshots
    # ----------------------------
    async def capture_page_sections(self, page, url, device):
        """Capture page in scrolling sections."""
        try:
            page_height = await page.evaluate("document.body.scrollHeight")
            viewport_height = await page.evaluate("window.innerHeight")

            print(f"  📏 Page: {page_height}px, Viewport: {viewport_height}px")

            scroll_pos = 0
            section_num = 1
            max_sections = 15

            while scroll_pos < page_height and section_num <= max_sections:
                await page.evaluate(f'window.scrollTo({{top: {scroll_pos}, behavior: "smooth"}})')
                await page.wait_for_timeout(1200)

                await self.take_screenshot(
                    page, url, device,
                    f"02_scroll_section_{section_num:02d}",
                    f"Scroll section {section_num} at {scroll_pos}px"
                )

                scroll_pos += viewport_height - 150
                section_num += 1

            print(f"  ✓ Captured {section_num - 1} scroll sections")

            await page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
            await page.wait_for_timeout(1500)

        except Exception as e:
            print(f"  ⚠️  Scroll capture error: {str(e)}")

    async def check_images(self, page, url, device):
        """Check for broken images."""
        try:
            broken = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('img'))
                    .filter(img => !img.complete || img.naturalWidth === 0)
                    .length;
            }''')
            total = await page.evaluate('() => document.querySelectorAll("img").length')

            if broken > 0:
                print(f"  ⚠️  {broken} of {total} images failed to load")
                await self.log_issue({
                    'url': url, 'device': device, 'severity': 'high',
                    'category': 'Broken Images',
                    'issue': f'{broken} of {total} images failed to load',
                    'screenshot': f"{self.screenshot_counter:04d}",
                    'timestamp': datetime.now().isoformat()
                })
            else:
                print(f"  ✓ All {total} images loaded successfully")
        except Exception as e:
            print(f"  ⚠️  Image check error: {str(e)}")

    async def take_screenshot(self, page, url, device, step_name, description):
        """Take a screenshot with metadata."""
        try:
            self.screenshot_counter += 1
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{self.screenshot_counter:04d}_{device}_{step_name}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            await page.screenshot(path=filepath, full_page=False)
            print(f"  📸 [{self.screenshot_counter:04d}] {description}")
            return str(filepath)
        except Exception as e:
            print(f"  ✗ Screenshot error: {str(e)}")
            return None

    async def log_issue(self, issue):
        """Log an issue."""
        self.issues.append(issue)
        severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        emoji = severity_emoji.get(issue.get("severity", ""), "⚪")
        print(f"\n  {emoji} LOGGED ISSUE:")
        print(f"     Category: {issue.get('category')}")
        print(f"     Details: {issue.get('issue')}")

    async def run_tests(self, urls):
        """Run tests on all URLs."""
        print("\n" + "=" * 80)
        print("🔍 SEAT COVER SOLUTIONS - QA AUTOMATION (Ready)")
        print("Step 1->2 (Trim/Cab) + Step 2->3 (Color) handled")
        print("=" * 80)

        cleaned_urls = []
        for url in urls:
            cleaned = url.strip().replace("\r", "").replace("\n", "")
            if cleaned and cleaned.startswith("http"):
                cleaned_urls.append(cleaned)
                print(f"  ✓ Will test: {cleaned}")
            else:
                print(f"  ⚠️  Skipping invalid URL: {repr(url)}")

        for u in cleaned_urls:
            await self.test_url(u, "desktop")
            await asyncio.sleep(3)
            await self.test_url(u, "mobile")
            await asyncio.sleep(3)

        with open("qa-report.json", "w") as f:
            json.dump(self.issues, f, indent=2)

        print("\n📦 Creating screenshots ZIP...")
        zip_path = "qa-screenshots.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for screenshot in self.screenshot_dir.glob("*.png"):
                zipf.write(screenshot, screenshot.name)

        zip_size = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"  ✓ ZIP created: {zip_size:.2f} MB")
        print(f"✅ COMPLETE | Screenshots: {self.screenshot_counter} | Issues: {len(self.issues)}")
        return self.issues


async def main():
    urls = sys.argv[1:] if len(sys.argv) > 1 else []

    if not urls and os.path.exists("urls.txt"):
        with open("urls.txt") as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    if not urls:
        print("❌ Error: No URLs provided")
        print("\nUsage:")
        print("  python shopify_qa.py <url1> [url2] ...")
        print("  OR create urls.txt with one URL per line")
        sys.exit(1)

    qa = SeatCoverQA()
    await qa.run_tests(urls)


if __name__ == "__main__":
    asyncio.run(main())
