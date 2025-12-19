#!/usr/bin/env python3
"""
Seat Cover Solutions - Exact HTML Structure Match (Corrected)
Fixes:
- Click the required "Select Color Options" CTA after seat selection (Step 2 -> Step 3)
- Add best-effort popup/chat overlay dismissal (can block clicks, especially on mobile)
- Wait for Step 3 using robust selectors (not just "Step 3/3" text)
- Improve verification of seat/color selection
- Small stability improvements around interactions
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
        self.screenshot_dir = Path('./qa-screenshots')
        self.screenshot_dir.mkdir(exist_ok=True)
        self.issues = []
        self.screenshot_counter = 0
        self.performance_data = []

    async def dismiss_overlays(self, page):
        """
        Best-effort dismissal of common popups/widgets that may intercept clicks.
        This is intentionally conservative: it tries a few generic close selectors,
        and also hides obvious chat widgets if present.
        """
        # Try clicking common "close" buttons
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

        # If a chat widget is overlaying the UI, hide it (best-effort)
        try:
            await page.evaluate(
                """() => {
                    const candidates = [
                      'iframe[src*="tawk"]',
                      'iframe[src*="intercom"]',
                      'iframe[src*="crisp"]',
                      'iframe[src*="zendesk"]',
                      'iframe[title*="chat"]',
                      'iframe[title*="Chat"]',
                      'div[id*="chat"]',
                      'div[class*="chat"]'
                    ];
                    for (const sel of candidates) {
                      document.querySelectorAll(sel).forEach(el => {
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                      });
                    }
                  }"""
            )
        except:
            pass

    async def click_first_working(self, page, selectors, label, screenshot_prefix, url, device, highlight_js=None):
        """
        Try selectors in order; click the first visible one.
        Returns (clicked: bool, used_selector: str|None).
        """
        for selector in selectors:
            try:
                print(f"  🔍 Trying selector: {selector}")
                el = await page.wait_for_selector(selector, timeout=8000)
                if not el:
                    continue

                visible = await el.is_visible()
                print(f"     Element found, visible: {visible}")
                if not visible:
                    continue

                await el.scroll_into_view_if_needed()
                await page.wait_for_timeout(800)

                if highlight_js:
                    try:
                        await page.evaluate(highlight_js, el)
                        await page.wait_for_timeout(700)
                    except:
                        pass

                await self.take_screenshot(page, url, device, f"{screenshot_prefix}_highlighted",
                                          f"{label} highlighted (selector: {selector})")

                print(f"  ✓ Found with selector: {selector}")
                print(f"  🖱️  Clicking...")
                await el.click(force=True, timeout=5000)
                await page.wait_for_timeout(2500)
                return True, selector

            except Exception as e:
                print(f"     ❌ Failed: {str(e)[:100]}")
                continue

        return False, None

    async def test_url(self, url, device='desktop'):
        """Test URL with exact HTML-based selectors"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
            )

            # NOTE: You had America/New_York here. Leaving it as-is since your store may be US-focused.
            # If you want reports aligned to IST, change timezone_id to "Asia/Kolkata".
            if device == 'mobile':
                context = await browser.new_context(
                    viewport={'width': 375, 'height': 812},
                    user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
                    is_mobile=True,
                    has_touch=True,
                    locale='en-US',
                    timezone_id='America/New_York'
                )
            else:
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    locale='en-US',
                    timezone_id='America/New_York'
                )

            page = await context.new_page()

            try:
                print(f"\n{'='*80}")
                print(f"🔍 TESTING: {url}")
                print(f"Device: {device.upper()}")
                print('='*80)

                # STEP 1: Load page
                print("\n[STEP 1] 📄 Loading page...")
                start_time = time.time()

                response = await page.goto(url, timeout=60000, wait_until='domcontentloaded')

                print(f"  ⏱️  Waiting for network to be idle...")
                try:
                    await page.wait_for_load_state('networkidle', timeout=60000)
                    print(f"  ✓ Network idle reached")
                except Exception:
                    print(f"  ⚠️  Network didn't fully idle (still loading some resources)")

                load_time = time.time() - start_time
                print(f"  ✓ Page loaded in {load_time:.2f}s")
                print(f"  HTTP Status: {response.status}")

                # CRITICAL: Wait 5 seconds for page to fully render
                print(f"  ⏱️  Waiting 5 seconds for complete page rendering...")
                await page.wait_for_timeout(5000)
                print(f"  ✓ Page fully rendered and ready")

                # Dismiss overlays early
                await self.dismiss_overlays(page)

                # Screenshot 1: Initial page
                await self.take_screenshot(page, url, device, '01_initial_page_load',
                                          "Initial page after loading")

                # STEP 2: Scroll and capture sections
                print("\n[STEP 2] 📸 Capturing page sections...")
                await self.capture_page_sections(page, url, device)

                # STEP 3: Check images
                print("\n[STEP 3] 🖼️ Checking images...")
                await self.check_images(page, url, device)

                # Scroll back to top
                await page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
                await page.wait_for_timeout(2000)

                # Additional stability wait before interactions
                print(f"\n  ⏱️  Waiting 5 more seconds before starting interactions...")
                await page.wait_for_timeout(5000)

                # Verify critical elements are present
                print(f"  🔍 Verifying page elements are ready...")
                try:
                    seat_section = await page.query_selector('text="Step 2/3"')
                    if seat_section:
                        print(f"     ✓ Seat options section found")

                    seat_option = await page.query_selector('input[name="Seats[]"]')
                    if seat_option:
                        print(f"     ✓ Seat selection inputs found")

                    print(f"  ✓ Page elements verified - ready to begin interactions")
                except:
                    print(f"  ⚠️  Could not verify all elements, continuing anyway...")

                # STEP 4: Click "Front & Rear Seats"
                print("\n[STEP 4] 🎯 Selecting 'Front & Rear Seats'...")

                await self.take_screenshot(page, url, device, '04_before_seat_selection',
                                          "Before selecting seat option")

                await self.dismiss_overlays(page)

                seat_selectors = [
                    # Exact match from HTML (your existing)
                    'label[for="btn_2614198370596"]',
                    'input#btn_2614198370596',
                    'input[value="Bundle"]',
                    'input[name="Seats[]"][value="Bundle"]',
                    # Fallback text-based
                    'label:has-text("Front & Rear Seats")',
                    'div._title_q98un_383:has-text("Front & Rear Seats")'
                ]

                seat_highlight_js = """(el) => {
                    const container = el.closest('div._button_option_q98un_339') || el;
                    container.style.outline = '5px solid red';
                    container.style.outlineOffset = '3px';
                    container.style.backgroundColor = 'rgba(255,0,0,0.1)';
                }"""

                seat_clicked, used_seat_selector = await self.click_first_working(
                    page,
                    seat_selectors,
                    "Front & Rear Seats",
                    "04a_seat_option",
                    url,
                    device,
                    highlight_js=seat_highlight_js
                )

                # Verify selection (check the specific input)
                if seat_clicked:
                    is_checked = await page.evaluate(
                        """() => {
                            const input = document.querySelector('input#btn_2614198370596') ||
                                          document.querySelector('input[name="Seats[]"][value="Bundle"]') ||
                                          document.querySelector('input[value="Bundle"]');
                            return input ? input.checked : false;
                        }"""
                    )
                    print(f"     Input checked state: {is_checked}")
                    await self.take_screenshot(page, url, device, '04b_seat_option_selected',
                                              "After selecting Front & Rear Seats")
                else:
                    print(f"  ❌ Could not click 'Front & Rear Seats'")
                    await self.take_screenshot(page, url, device, '04_ERROR_seat_not_clicked',
                                              "ERROR: Seat selection failed")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'critical',
                        'category': 'Seat Selection Failed',
                        'issue': 'Could not click Front & Rear Seats option',
                        'screenshot': f"{self.screenshot_counter:04d}",
                        'timestamp': datetime.now().isoformat()
                    })

                await page.wait_for_timeout(1500)

                # STEP 4.5: Click "Select Color Options" (THIS WAS MISSING)
                print("\n[STEP 4.5] ➡️ Proceeding to Step 3 by clicking 'Select Color Options'...")

                await self.dismiss_overlays(page)

                continue_selectors = [
                    'button:has-text("Select Color Options")',
                    'a:has-text("Select Color Options")',
                    'text=Select Color Options',
                    # Some themes render "Select color options" with different casing
                    'button:has-text("Select color options")',
                    'a:has-text("Select color options")',
                ]

                continue_highlight_js = """(el) => {
                    el.style.outline = '5px solid blue';
                    el.style.outlineOffset = '3px';
                    el.style.backgroundColor = 'rgba(0,0,255,0.1)';
                }"""

                continued, _ = await self.click_first_working(
                    page,
                    continue_selectors,
                    "Select Color Options",
                    "04c_select_color_options",
                    url,
                    device,
                    highlight_js=continue_highlight_js
                )

                if not continued:
                    # Not always fatal (some pages may auto-advance), but in your screenshots it *was* required.
                    print("  ⚠️  Could not click 'Select Color Options' (may be auto-advanced or selector changed)")
                    await self.take_screenshot(page, url, device, '04c_ERROR_continue_not_clicked',
                                              "WARNING: Could not click Select Color Options")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'high',
                        'category': 'Step Progression',
                        'issue': 'Could not click Select Color Options; Step 3 may not appear',
                        'screenshot': f"{self.screenshot_counter:04d}",
                        'timestamp': datetime.now().isoformat()
                    })

                # STEP 5: Wait for Step 3 (Color Details) to appear - more robust
                print("\n[STEP 5] 🎨 Waiting for Step 3 (Color Details) to appear...")

                await page.wait_for_timeout(1500)
                await self.dismiss_overlays(page)

                step3_found = False
                step3_wait_selectors = [
                    'text="Step 3/3"',
                    'text=Color Details',
                    'input[name="Color"]',
                    'div._color_option_au32d_1',
                    'label[for^="default-color-"]',
                ]

                for s in step3_wait_selectors:
                    try:
                        await page.wait_for_selector(s, timeout=12000)
                        step3_found = True
                        print(f"  ✓ Step 3 detected via: {s}")
                        break
                    except:
                        continue

                if not step3_found:
                    print(f"  ⚠️  Step 3 not detected yet; scrolling down a bit and retrying...")
                    await page.evaluate('window.scrollBy({top: 500, behavior: "smooth"})')
                    await page.wait_for_timeout(2000)

                await self.take_screenshot(page, url, device, '05_step3_color_section',
                                          "Step 3/3 - Color Details section (or current state)")

                # STEP 6: Select a color
                print("\n[STEP 6] ⚫ Selecting color option...")

                await self.dismiss_overlays(page)

                color_selectors = [
                    # Prefer Wine Red to validate change
                    'label[for="default-color-44846790672676"]',
                    'input#default-color-44846790672676',
                    # Or Black (default)
                    'label[for="default-color-44846752629028"]',
                    'input#default-color-44846752629028',
                    # Generic fallbacks
                    'input[name="Color"]',
                    'label:has-text("Black")',
                    'div._color_option_au32d_1:first-child label'
                ]

                color_highlight_js = """(el) => {
                    const container = el.closest('div._color_option_au32d_1') || el;
                    container.style.outline = '5px solid green';
                    container.style.outlineOffset = '3px';
                    container.style.backgroundColor = 'rgba(0,255,0,0.1)';
                }"""

                color_selected, _ = await self.click_first_working(
                    page,
                    color_selectors,
                    "Color Option",
                    "06a_color_option",
                    url,
                    device,
                    highlight_js=color_highlight_js
                )

                # Verify any Color input is checked
                try:
                    any_color_checked = await page.evaluate(
                        """() => {
                            const inputs = document.querySelectorAll('input[name="Color"]');
                            for (const input of inputs) {
                                if (input.checked) return true;
                            }
                            return false;
                        }"""
                    )
                except:
                    any_color_checked = False

                if color_selected or any_color_checked:
                    print(f"  ✓ Color selected/verified (any checked: {any_color_checked})")
                    await self.take_screenshot(page, url, device, '06b_color_selected',
                                              "After selecting (or verifying) color")
                else:
                    print(f"  ⚠️  Could not select color explicitly (may be default-selected or selector changed)")
                    await self.take_screenshot(page, url, device, '06_color_default',
                                              "Using default color selection (or unable to verify)")

                # Wait for Add to Cart button to appear (it shows after steps complete)
                print(f"\n  ⏱️  Waiting for Add to Cart button to become visible...")
                await page.wait_for_timeout(2500)
                await self.dismiss_overlays(page)

                # STEP 7: Find and click Add to Cart
                print("\n[STEP 7] 🛒 Looking for Add to Cart button...")
                print(f"  ℹ️  Note: Button may appear only after seat + color + progression")

                await self.take_screenshot(page, url, device, '07_before_add_to_cart',
                                          "Before clicking Add to Cart")

                # Scroll near bottom (but not always full bottom; some themes keep ATC mid-page)
                await page.evaluate('window.scrollBy({top: 700, behavior: "smooth"})')
                await page.wait_for_timeout(1500)

                add_to_cart_selectors = [
                    'button:has-text("Add to Cart")',
                    'button:has-text("ADD TO CART")',
                    'input[value*="Add to Cart"]',
                    'button[name="add"]',
                    'button.add-to-cart',
                    'button[type="submit"]:has-text("Add")',
                    'form[action*="/cart/add"] button',
                    '.product-form button[type="submit"]',
                    'button:has-text("Add to Bag")',
                    'button:has-text("Buy Now")',
                    '#AddToCart',
                    '.btn-add-to-cart'
                ]

                cart_added = False
                for selector in add_to_cart_selectors:
                    try:
                        print(f"  🔍 Trying selector: {selector}")

                        add_button = await page.wait_for_selector(selector, timeout=6000)
                        if add_button and await add_button.is_visible():
                            # Check if disabled
                            is_disabled = await add_button.is_disabled()
                            print(f"     Button disabled: {is_disabled}")

                            if is_disabled:
                                print(f"     ⚠️  Button is disabled, skipping")
                                continue

                            await add_button.scroll_into_view_if_needed()
                            await page.wait_for_timeout(800)

                            await self.dismiss_overlays(page)

                            # Highlight
                            await page.evaluate(
                                """(el) => {
                                    el.style.outline = '5px solid orange';
                                    el.style.outlineOffset = '3px';
                                    el.style.backgroundColor = 'rgba(255,165,0,0.1)';
                                }""",
                                add_button
                            )

                            await page.wait_for_timeout(700)

                            await self.take_screenshot(page, url, device, '07a_add_cart_highlighted',
                                                      f"Add to Cart highlighted (selector: {selector})")

                            print(f"  ✓ Found with selector: {selector}")
                            print(f"  🖱️  Clicking...")

                            await add_button.click(force=True)

                            # Wait for cart drawer/popup
                            await page.wait_for_timeout(4500)

                            await self.take_screenshot(page, url, device, '07b_after_add_to_cart',
                                                      "After Add to Cart - checking for cart drawer")

                            print(f"  ✓ Clicked Add to Cart")
                            cart_added = True
                            break

                    except Exception as e:
                        print(f"     ❌ Failed: {str(e)[:100]}")
                        continue

                if not cart_added:
                    print(f"  ❌ Could not add to cart")
                    await self.take_screenshot(page, url, device, '07_ERROR_add_cart_failed',
                                              "ERROR: Add to cart failed")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'critical',
                        'category': 'Add to Cart Failed',
                        'issue': 'Could not find or click Add to Cart button (likely Step 3 not reached or button blocked)',
                        'screenshot': f"{self.screenshot_counter:04d}",
                        'timestamp': datetime.now().isoformat()
                    })

                # STEP 8: Look for checkout button in cart drawer/popup
                print("\n[STEP 8] 💳 Looking for checkout button...")

                await page.wait_for_timeout(2500)
                await self.dismiss_overlays(page)

                checkout_selectors = [
                    'button:has-text("Checkout")',
                    'a:has-text("Checkout")',
                    'button:has-text("Continue to Checkout")',
                    'a:has-text("Continue to Checkout")',
                    'button:has-text("Proceed to Checkout")',
                    'a:has-text("Proceed to Checkout")',
                    'a[href*="/checkout"]',
                    'button[onclick*="checkout"]',
                    '.cart-drawer button:has-text("Checkout")',
                    '.cart-popup a:has-text("Checkout")',
                    '#checkout-button',
                    '.checkout-button'
                ]

                checkout_found = False
                for selector in checkout_selectors:
                    try:
                        print(f"  🔍 Trying selector: {selector}")

                        checkout_btn = await page.wait_for_selector(selector, timeout=6000)

                        if checkout_btn and await checkout_btn.is_visible():
                            await checkout_btn.scroll_into_view_if_needed()
                            await page.wait_for_timeout(800)

                            await self.dismiss_overlays(page)

                            # Highlight
                            await page.evaluate(
                                """(el) => {
                                    el.style.outline = '5px solid purple';
                                    el.style.outlineOffset = '3px';
                                    el.style.backgroundColor = 'rgba(128,0,128,0.1)';
                                }""",
                                checkout_btn
                            )

                            await page.wait_for_timeout(700)

                            await self.take_screenshot(page, url, device, '08a_checkout_button_highlighted',
                                                      f"Checkout button highlighted (selector: {selector})")

                            print(f"  ✓ Found with selector: {selector}")
                            print(f"  🖱️  Clicking...")

                            await checkout_btn.click(force=True)

                            # Wait for navigation
                            print(f"  ⏱️  Waiting for checkout page to load...")
                            try:
                                await page.wait_for_load_state('networkidle', timeout=20000)
                            except:
                                print(f"     ⚠️  Network didn't idle, continuing anyway")

                            await page.wait_for_timeout(7000)

                            await self.take_screenshot(page, url, device, '08b_checkout_page_loaded',
                                                      "Checkout page loaded")

                            current_url = page.url
                            print(f"  📍 Current URL: {current_url}")

                            if 'checkout' in current_url.lower() or 'cart' in current_url.lower():
                                print(f"  ✓ Successfully reached checkout!")
                                await self.capture_checkout_sections(page, url, device)
                            else:
                                print(f"  ⚠️  URL doesn't contain 'checkout' or 'cart'")
                                await self.log_issue({
                                    'url': url, 'device': device, 'severity': 'medium',
                                    'category': 'Checkout Navigation',
                                    'issue': f'Clicked checkout but URL is: {current_url}',
                                    'screenshot': f"{self.screenshot_counter:04d}",
                                    'timestamp': datetime.now().isoformat()
                                })

                            checkout_found = True
                            break

                    except Exception as e:
                        print(f"     ❌ Failed: {str(e)[:100]}")
                        continue

                if not checkout_found:
                    print(f"  ❌ Could not find checkout button")
                    await self.take_screenshot(page, url, device, '08_ERROR_checkout_not_found',
                                              "ERROR: Checkout button not found")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'critical',
                        'category': 'Checkout Not Found',
                        'issue': 'Could not find checkout button in cart',
                        'screenshot': f"{self.screenshot_counter:04d}",
                        'timestamp': datetime.now().isoformat()
                    })

                # Final screenshot
                await self.take_screenshot(page, url, device, '09_final_page_state',
                                          "Final page state")

                print(f"\n{'='*80}")
                print(f"✓ Completed testing {url} ({device})")
                print(f"📸 Total screenshots: {self.screenshot_counter}")
                print(f"{'='*80}")

            except Exception as e:
                print(f"\n{'='*80}")
                print(f"✗ FATAL ERROR: {str(e)}")
                print(f"{'='*80}")

                await self.take_screenshot(page, url, device, 'ERROR_test_crashed',
                                          f"Test crashed: {str(e)}")

                await self.log_issue({
                    'url': url, 'device': device, 'severity': 'critical',
                    'category': 'Test Crashed',
                    'issue': f'Test failed with exception: {str(e)}',
                    'screenshot': f"{self.screenshot_counter:04d}",
                    'timestamp': datetime.now().isoformat()
                })

            await browser.close()

    async def capture_page_sections(self, page, url, device):
        """Capture page in scrolling sections"""
        try:
            page_height = await page.evaluate('document.body.scrollHeight')
            viewport_height = await page.evaluate('window.innerHeight')

            print(f"  📏 Page: {page_height}px, Viewport: {viewport_height}px")

            scroll_pos = 0
            section_num = 1
            max_sections = 15

            while scroll_pos < page_height and section_num <= max_sections:
                await page.evaluate(f'window.scrollTo({{top: {scroll_pos}, behavior: "smooth"}})')
                await page.wait_for_timeout(1200)

                await self.take_screenshot(page, url, device,
                                          f'02_scroll_section_{section_num:02d}',
                                          f"Scroll section {section_num} at {scroll_pos}px")

                scroll_pos += viewport_height - 150
                section_num += 1

            print(f"  ✓ Captured {section_num-1} scroll sections")

            # Back to top
            await page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
            await page.wait_for_timeout(1500)

        except Exception as e:
            print(f"  ⚠️  Scroll capture error: {str(e)}")

    async def check_images(self, page, url, device):
        """Check for broken images"""
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

    async def capture_checkout_sections(self, page, url, device):
        """Capture checkout page in sections"""
        try:
            print(f"  📸 Capturing checkout page sections...")

            # Top
            await page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
            await page.wait_for_timeout(1500)
            await self.take_screenshot(page, url, device,
                                      '08c_checkout_top',
                                      "Checkout page - top section")

            # Middle
            page_height = await page.evaluate('document.body.scrollHeight')
            await page.evaluate(f'window.scrollTo({{top: {page_height//2}, behavior: "smooth"}})')
            await page.wait_for_timeout(1500)
            await self.take_screenshot(page, url, device,
                                      '08d_checkout_middle',
                                      "Checkout page - middle section")

            # Bottom
            await page.evaluate(f'window.scrollTo({{top: {page_height}, behavior: "smooth"}})')
            await page.wait_for_timeout(1500)
            await self.take_screenshot(page, url, device,
                                      '08e_checkout_bottom',
                                      "Checkout page - bottom section")

            print(f"  ✓ Captured 3 checkout sections")

        except Exception as e:
            print(f"  ⚠️  Checkout capture error: {str(e)}")

    async def take_screenshot(self, page, url, device, step_name, description):
        """Take a screenshot with metadata"""
        try:
            self.screenshot_counter += 1
            timestamp = datetime.now().strftime('%H%M%S')

            filename = f"{self.screenshot_counter:04d}_{device}_{step_name}_{timestamp}.png"
            filepath = self.screenshot_dir / filename

            await page.screenshot(path=filepath, full_page=False)

            print(f"  📸 [{self.screenshot_counter:04d}] {description}")

            return str(filepath)
        except Exception as e:
            print(f"  ✗ Screenshot error: {str(e)}")
            return None

    async def log_issue(self, issue):
        """Log an issue"""
        self.issues.append(issue)
        severity_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
        emoji = severity_emoji.get(issue['severity'], '⚪')
        print(f"\n  {emoji} LOGGED ISSUE:")
        print(f"     Category: {issue['category']}")
        print(f"     Details: {issue['issue']}")

    async def run_tests(self, urls):
        """Run tests on all URLs"""
        print("\n" + "="*80)
        print("🔍 SEAT COVER SOLUTIONS - PRECISE QA AUTOMATION (Corrected)")
        print("Includes Step 2 -> Step 3 progression + overlay handling")
        print("="*80)
        print(f"\n📍 Location: New York, USA")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}")
        print(f"🔗 URLs to test: {len(urls)}")
        print(f"📱 Devices: Desktop + Mobile")
        print("\n" + "="*80)

        cleaned_urls = []
        for url in urls:
            cleaned = url.strip().replace('\r', '').replace('\n', '')
            if cleaned and cleaned.startswith('http'):
                cleaned_urls.append(cleaned)
                print(f"  ✓ Will test: {cleaned}")
            else:
                print(f"  ⚠️  Skipping invalid URL: {repr(url)}")

        print(f"\n  Total valid URLs: {len(cleaned_urls)}")
        print("=" * 80)

        for url in cleaned_urls:
            await self.test_url(url, 'desktop')
            await asyncio.sleep(3)
            await self.test_url(url, 'mobile')
            await asyncio.sleep(3)

        # Save reports
        with open('qa-report.json', 'w') as f:
            json.dump(self.issues, f, indent=2)

        # Create ZIP
        print("\n📦 Creating screenshots ZIP...")
        zip_path = 'qa-screenshots.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for screenshot in self.screenshot_dir.glob('*.png'):
                zipf.write(screenshot, screenshot.name)

        zip_size = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"  ✓ ZIP created: {zip_size:.2f} MB")

        print("\n" + "="*80)
        print("✅ TESTING COMPLETE!")
        print("="*80)
        print(f"\n📸 Total Screenshots: {self.screenshot_counter}")
        print(f"🐛 Total Issues: {len(self.issues)}")
        print(f"📁 ZIP Size: {zip_size:.2f} MB")

        if self.issues:
            critical = len([i for i in self.issues if i['severity'] == 'critical'])
            high = len([i for i in self.issues if i['severity'] == 'high'])
            print(f"\n⚠️  Issues breakdown:")
            print(f"   🔴 Critical: {critical}")
            print(f"   🟠 High: {high}")

        print("\n" + "="*80)

        return self.issues


async def main():
    urls = sys.argv[1:] if len(sys.argv) > 1 else []

    if not urls:
        if os.path.exists('urls.txt'):
            with open('urls.txt') as f:
                urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

    if not urls:
        print("❌ Error: No URLs provided")
        print("\nUsage:")
        print("  python shopify_qa.py <url1> [url2] ...")
        print("  OR create urls.txt with one URL per line")
        sys.exit(1)

    qa = SeatCoverQA()
    await qa.run_tests(urls)


if __name__ == '__main__':
    asyncio.run(main())
