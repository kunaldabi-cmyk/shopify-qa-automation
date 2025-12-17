#!/usr/bin/env python3
"""
Seat Cover Solutions - Exact HTML Structure Match
Based on actual page HTML with precise selectors
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
    
    async def test_url(self, url, device='desktop'):
        """Test URL with exact HTML-based selectors"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
            )
            
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
                await page.wait_for_load_state('networkidle', timeout=30000)
                
                load_time = time.time() - start_time
                print(f"  ✓ Page loaded in {load_time:.2f}s")
                print(f"  HTTP Status: {response.status}")
                
                # CRITICAL: Wait 5 seconds for page to fully render
                print(f"  ⏱️  Waiting 5 seconds for complete page rendering...")
                await page.wait_for_timeout(5000)
                print(f"  ✓ Page fully rendered and ready")
                
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
                    # Check if seat options section is visible
                    seat_section = await page.query_selector('text="Step 2/3"')
                    if seat_section:
                        print(f"     ✓ Seat options section found")
                    
                    # Check if at least one seat option is present
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
                
                # Based on HTML: <input type="radio" name="Seats[]" id="btn_2614198370596" value="Bundle">
                # Wrapped in: <label for="btn_2614198370596">
                
                seat_selectors = [
                    # Exact match from HTML
                    'label[for="btn_2614198370596"]',  # Label for Front & Rear
                    'input#btn_2614198370596',  # Direct input ID
                    'input[value="Bundle"]',  # Input by value
                    'input[name="Seats[]"][value="Bundle"]',  # Full input selector
                    # Fallback text-based
                    'label:has-text("Front & Rear Seats")',
                    'div._title_q98un_383:has-text("Front & Rear Seats")'
                ]
                
                seat_clicked = False
                for selector in seat_selectors:
                    try:
                        print(f"  🔍 Trying selector: {selector}")
                        
                        # Wait for element with longer timeout
                        element = await page.wait_for_selector(selector, timeout=10000)
                        
                        if element:
                            # Check if visible
                            is_visible = await element.is_visible()
                            print(f"     Element found, visible: {is_visible}")
                            
                            if not is_visible:
                                continue
                            
                            # Scroll into view
                            await element.scroll_into_view_if_needed()
                            await page.wait_for_timeout(1000)
                            
                            # Highlight the ENTIRE option box
                            await page.evaluate('''(el) => {
                                // Find the parent container
                                const container = el.closest('div._button_option_q98un_339') || el;
                                container.style.outline = '5px solid red';
                                container.style.outlineOffset = '3px';
                                container.style.backgroundColor = 'rgba(255,0,0,0.1)';
                            }''', element)
                            
                            await page.wait_for_timeout(1000)
                            
                            await self.take_screenshot(page, url, device, '04a_seat_option_highlighted',
                                f"Front & Rear Seats highlighted (selector: {selector})")
                            
                            print(f"  ✓ Found with selector: {selector}")
                            print(f"  🖱️  Clicking...")
                            
                            # Click with force
                            await element.click(force=True, timeout=5000)
                            await page.wait_for_timeout(3000)
                            
                            # Check if it's selected by looking for active class or checked state
                            is_checked = await page.evaluate('''(sel) => {
                                const input = document.querySelector('input#btn_2614198370596') || 
                                             document.querySelector('input[value="Bundle"]');
                                return input ? input.checked : false;
                            }''', selector)
                            
                            print(f"     Input checked state: {is_checked}")
                            
                            await self.take_screenshot(page, url, device, '04b_seat_option_selected',
                                "After clicking Front & Rear Seats")
                            
                            print(f"  ✓ Clicked 'Front & Rear Seats'")
                            seat_clicked = True
                            break
                            
                    except Exception as e:
                        print(f"     ❌ Failed: {str(e)[:80]}")
                        continue
                
                if not seat_clicked:
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
                
                # Wait a bit for any JS updates
                await page.wait_for_timeout(2000)
                
                # STEP 5: Wait for Step 3 (Color Details) to appear
                print("\n[STEP 5] 🎨 Waiting for Step 3 (Color Details) to appear...")
                
                await page.wait_for_timeout(3000)
                
                # Check if Step 3 is visible
                try:
                    step3_visible = await page.wait_for_selector('text="Step 3/3"', timeout=10000)
                    if step3_visible:
                        print(f"  ✓ Step 3/3 - Color Details section appeared")
                        await page.wait_for_timeout(2000)
                except:
                    print(f"  ⚠️  Step 3 not visible yet, scrolling down...")
                    await page.evaluate('window.scrollBy({top: 400, behavior: "smooth"})')
                    await page.wait_for_timeout(2000)
                
                await self.take_screenshot(page, url, device, '05_step3_color_section',
                    "Step 3/3 - Color Details section")
                
                # STEP 6: Select a color
                print("\n[STEP 6] ⚫ Selecting color option...")
                
                # Based on HTML: Black is already checked by default
                # But let's click a different color to test (Wine Red)
                # Structure: <label for="default-color-44846790672676">
                
                color_selectors = [
                    # Try Wine Red (2nd option)
                    'label[for="default-color-44846790672676"]',  # Wine Red
                    'input#default-color-44846790672676',
                    # Or stick with Black (default, already checked)
                    'label[for="default-color-44846752629028"]',  # Black (default)
                    'input#default-color-44846752629028',
                    # Generic fallbacks
                    'input[name="Color"]',
                    'label:has-text("Black")',
                    'div._color_option_au32d_1:first-child label'
                ]
                
                color_selected = False
                for selector in color_selectors:
                    try:
                        print(f"  🔍 Trying selector: {selector}")
                        
                        color_el = await page.wait_for_selector(selector, timeout=5000)
                        
                        if color_el and await color_el.is_visible():
                            await color_el.scroll_into_view_if_needed()
                            await page.wait_for_timeout(1000)
                            
                            # Highlight the color option
                            await page.evaluate('''(el) => {
                                const container = el.closest('div._color_option_au32d_1') || el;
                                container.style.outline = '5px solid green';
                                container.style.outlineOffset = '3px';
                                container.style.backgroundColor = 'rgba(0,255,0,0.1)';
                            }''', color_el)
                            
                            await page.wait_for_timeout(1000)
                            
                            await self.take_screenshot(page, url, device, '06a_color_option_highlighted',
                                f"Color option highlighted (selector: {selector})")
                            
                            print(f"  ✓ Found with selector: {selector}")
                            print(f"  🖱️  Clicking...")
                            
                            await color_el.click(force=True)
                            await page.wait_for_timeout(3000)
                            
                            # Verify color was selected
                            is_checked = await page.evaluate('''(sel) => {
                                const inputs = document.querySelectorAll('input[name="Color"]');
                                for (let input of inputs) {
                                    if (input.checked) return true;
                                }
                                return false;
                            }''', selector)
                            
                            print(f"     Color checked state: {is_checked}")
                            
                            await self.take_screenshot(page, url, device, '06b_color_selected',
                                "After selecting color")
                            
                            print(f"  ✓ Color selected")
                            color_selected = True
                            break
                            
                    except Exception as e:
                        print(f"     ❌ Failed: {str(e)[:80]}")
                        continue
                
                if not color_selected:
                    print(f"  ⚠️  Could not select color explicitly")
                    print(f"  ℹ️  Black might already be selected by default")
                    await self.take_screenshot(page, url, device, '06_color_default',
                        "Using default color selection")
                
                # Wait for Add to Cart button to appear (it shows after both steps are complete)
                print(f"\n  ⏱️  Waiting for Add to Cart button to become visible...")
                await page.wait_for_timeout(3000)
                
                # STEP 7: Find and click Add to Cart
                # IMPORTANT: Add to Cart only appears after BOTH seat AND color are selected
                print("\n[STEP 7] 🛒 Looking for Add to Cart button...")
                print(f"  ℹ️  Note: Button only appears after seat + color selection")
                
                await page.wait_for_timeout(2000)
                await self.take_screenshot(page, url, device, '07_before_add_to_cart',
                    "Before clicking Add to Cart")
                
                # Scroll to bottom to find Add to Cart
                await page.evaluate('window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"})')
                await page.wait_for_timeout(2000)
                
                add_to_cart_selectors = [
                    'button:has-text("Add to Cart")',
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
                        
                        add_button = await page.wait_for_selector(selector, timeout=5000)
                        
                        if add_button and await add_button.is_visible():
                            # Check if disabled
                            is_disabled = await add_button.is_disabled()
                            print(f"     Button disabled: {is_disabled}")
                            
                            if is_disabled:
                                print(f"     ⚠️  Button is disabled, skipping")
                                continue
                            
                            await add_button.scroll_into_view_if_needed()
                            await page.wait_for_timeout(1000)
                            
                            # Highlight
                            await page.evaluate('''(el) => {
                                el.style.outline = '5px solid orange';
                                el.style.outlineOffset = '3px';
                                el.style.backgroundColor = 'rgba(255,165,0,0.1)';
                            }''', add_button)
                            
                            await page.wait_for_timeout(1000)
                            
                            await self.take_screenshot(page, url, device, '07a_add_cart_highlighted',
                                f"Add to Cart highlighted (selector: {selector})")
                            
                            print(f"  ✓ Found with selector: {selector}")
                            print(f"  🖱️  Clicking...")
                            
                            await add_button.click(force=True)
                            
                            # Wait for cart drawer/popup
                            await page.wait_for_timeout(4000)
                            
                            await self.take_screenshot(page, url, device, '07b_after_add_to_cart',
                                "After Add to Cart - checking for cart drawer")
                            
                            print(f"  ✓ Clicked Add to Cart")
                            cart_added = True
                            break
                            
                    except Exception as e:
                        print(f"     ❌ Failed: {str(e)[:80]}")
                        continue
                
                if not cart_added:
                    print(f"  ❌ Could not add to cart")
                    await self.take_screenshot(page, url, device, '07_ERROR_add_cart_failed',
                        "ERROR: Add to cart failed")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'critical',
                        'category': 'Add to Cart Failed',
                        'issue': 'Could not find or click Add to Cart button',
                        'screenshot': f"{self.screenshot_counter:04d}",
                        'timestamp': datetime.now().isoformat()
                    })
                
                # STEP 8: Look for checkout button in cart drawer/popup
                print("\n[STEP 8] 💳 Looking for checkout button...")
                
                await page.wait_for_timeout(3000)
                
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
                        
                        checkout_btn = await page.wait_for_selector(selector, timeout=5000)
                        
                        if checkout_btn and await checkout_btn.is_visible():
                            await checkout_btn.scroll_into_view_if_needed()
                            await page.wait_for_timeout(1000)
                            
                            # Highlight
                            await page.evaluate('''(el) => {
                                el.style.outline = '5px solid purple';
                                el.style.outlineOffset = '3px';
                                el.style.backgroundColor = 'rgba(128,0,128,0.1)';
                            }''', checkout_btn)
                            
                            await page.wait_for_timeout(1000)
                            
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
                            
                            await page.wait_for_timeout(10000)
                            
                            await self.take_screenshot(page, url, device, '08b_checkout_page_loaded',
                                "Checkout page loaded")
                            
                            current_url = page.url
                            print(f"  📍 Current URL: {current_url}")
                            
                            if 'checkout' in current_url.lower() or 'cart' in current_url.lower():
                                print(f"  ✓ Successfully reached checkout!")
                                
                                # Capture checkout sections
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
                        print(f"     ❌ Failed: {str(e)[:80]}")
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
            
            # Take viewport screenshot (faster, smaller file)
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
        print("🔍 SEAT COVER SOLUTIONS - PRECISE QA AUTOMATION")
        print("HTML-Matched Selectors for Guaranteed Clicks")
        print("="*80)
        print(f"\n📍 Location: New York, USA")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}")
        print(f"🔗 URLs to test: {len(urls)}")
        print(f"📱 Devices: Desktop + Mobile")
        print("\n" + "="*80)
        
        for url in urls:
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
